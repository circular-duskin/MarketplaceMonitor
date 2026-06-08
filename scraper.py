"""
scraper.py — Fetches new figure skating dress listings from eBay
and logs anything not seen before.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import requests

import config

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── File logger for new listings ───────────────────────────────────────────────
listing_logger = logging.getLogger("listings")
listing_logger.setLevel(logging.INFO)
listing_logger.propagate = False  # Don't double-print to console

fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(message)s"))
listing_logger.addHandler(fh)


# ── Persistence helpers ────────────────────────────────────────────────────────

def load_seen() -> set:
    if not Path(config.SEEN_FILE).exists():
        return set()
    with open(config.SEEN_FILE, "r") as f:
        return set(json.load(f))


def save_seen(seen: set) -> None:
    with open(config.SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def load_listings_db() -> dict:
    if not Path(config.LISTINGS_DB).exists():
        return {}
    with open(config.LISTINGS_DB, "r") as f:
        return json.load(f)


def save_listings_db(db: dict) -> None:
    with open(config.LISTINGS_DB, "w") as f:
        json.dump(db, f, indent=2)


def load_feedback() -> dict:
    if not Path(config.FEEDBACK_FILE).exists():
        return {}
    with open(config.FEEDBACK_FILE, "r") as f:
        return json.load(f)


# ── eBay API ───────────────────────────────────────────────────────────────────

def get_access_token() -> str:
    """Exchange App ID (client credentials) for an OAuth token."""
    import base64
    # For Browse API we need a full OAuth token.
    # eBay client credentials flow requires Client ID + Client Secret.
    # If you only have an App ID, see README for how to get Client Secret.
    client_id = config.EBAY_APP_ID
    client_secret = config.EBAY_CLIENT_SECRET

    if not client_secret:
        raise EnvironmentError(
            "Set the EBAY_CLIENT_SECRET environment variable. See README."
        )

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def search_ebay(query: str, token: str) -> list[dict]:
    """Run one search query against the eBay Browse API."""
    filters = []

    if config.CONDITION == "used":
        filters.append("conditionIds:{3000|4000|5000|6000}")  # used condition codes
    elif config.CONDITION == "new":
        filters.append("conditionIds:{1000}")

    if config.MIN_PRICE_USD and config.MAX_PRICE_USD:
        filters.append("priceCurrency:USD")
        filters.append(f"price:[{config.MIN_PRICE_USD}..{config.MAX_PRICE_USD}]")

    # Build aspect_filter to mirror eBay's structured Size + Department facets.
    aspect_parts = [f"categoryId:{config.EBAY_CATEGORY_ID}"]
    if config.SIZE_ASPECTS:
        aspect_parts.append("Size:{" + "|".join(config.SIZE_ASPECTS) + "}")
    if config.DEPARTMENT:
        aspect_parts.append(f"Department:{{{config.DEPARTMENT}}}")

    params = {
        "q": query,
        "category_ids": config.EBAY_CATEGORY_ID,
        "aspect_filter": ",".join(aspect_parts),
        "limit": config.RESULTS_PER_QUERY,
        "filter": ",".join(filters) if filters else None,
        "sort": "newlyListed",
    }
    params = {k: v for k, v in params.items() if v is not None}

    resp = requests.get(
        config.EBAY_API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": config.EBAY_MARKETPLACE,
            "Content-Type": "application/json",
        },
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("itemSummaries", [])


# ── Filtering ──────────────────────────────────────────────────────────────────

def matches_size(title: str) -> bool:
    """Return True if SIZE_KEYWORDS is empty (all sizes) or a keyword matches."""
    if not config.SIZE_KEYWORDS:
        return True
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in config.SIZE_KEYWORDS)


def passes_price(item: dict) -> bool:
    try:
        price = float(item["price"]["value"])
        return config.MIN_PRICE_USD <= price <= config.MAX_PRICE_USD
    except (KeyError, TypeError, ValueError):
        return False  # Skip if price is missing/malformed


# ── Formatting ─────────────────────────────────────────────────────────────────

def format_listing(item: dict, seller_tag: str = "") -> str:
    title = item.get("title", "No title")
    price = item.get("price", {})
    price_str = f"${float(price.get('value', 0)):.2f}" if price else "N/A"
    condition = item.get("condition", "Unknown condition")
    url = item.get("itemWebUrl", "No URL")
    image_url = item.get("image", {}).get("imageUrl", "No image")
    item_id = item.get("itemId", "?")
    seller = item.get("seller", {}).get("username", "unknown")
    location = item.get("itemLocation", {}).get("city", "")
    seller_line = f"  Seller    : {seller}  |  Location: {location}"
    if seller_tag:
        seller_line += f"  [{seller_tag}]"

    return (
        f"\n{'─'*60}\n"
        f"  {title}\n"
        f"  Price     : {price_str}  |  Condition: {condition}\n"
        f"{seller_line}\n"
        f"  ID        : {item_id}\n"
        f"  Listing   : {url}\n"
        f"  Image     : {image_url}\n"
        f"  Found at  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )


# ── Main run ───────────────────────────────────────────────────────────────────

def run_scrape() -> int:
    """Fetch all queries, filter, log new listings. Returns count of new finds."""
    log.info("Starting scrape run…")

    try:
        token = get_access_token()
    except Exception as e:
        log.error(f"Could not get eBay token: {e}")
        return 0

    seen = load_seen()
    listings_db = load_listings_db()
    feedback = load_feedback()

    # Build seller reputation from past ratings.
    seller_likes: dict[str, int] = {}
    seller_dislikes: dict[str, int] = {}
    for v in feedback.values():
        s = v.get("seller", "")
        if v.get("liked"):
            seller_likes[s] = seller_likes.get(s, 0) + 1
        else:
            seller_dislikes[s] = seller_dislikes.get(s, 0) + 1

    new_count = 0

    for query in config.SEARCH_QUERIES:
        log.info(f"Searching: '{query}'")
        try:
            items = search_ebay(query, token)
        except requests.HTTPError as e:
            log.error(f"eBay API error for '{query}': {e}")
            continue

        log.info(f"  → {len(items)} results returned")

        for item in items:
            item_id = item.get("itemId")
            if not item_id or item_id in seen:
                continue

            title = item.get("title", "")
            if not matches_size(title):
                continue
            if not passes_price(item):
                continue

            seller = item.get("seller", {}).get("username", "unknown")
            likes = seller_likes.get(seller, 0)
            dislikes = seller_dislikes.get(seller, 0)
            if likes and not dislikes:
                seller_tag = f"liked seller +{likes}"
            elif dislikes and not likes:
                seller_tag = f"disliked seller -{dislikes}"
            elif likes and dislikes:
                seller_tag = f"+{likes}/-{dislikes}"
            else:
                seller_tag = ""

            # Save structured record for review.py.
            listings_db[item_id] = {
                "title": title,
                "price": float(item.get("price", {}).get("value", 0)),
                "condition": item.get("condition", ""),
                "seller": seller,
                "location": item.get("itemLocation", {}).get("city", ""),
                "url": item.get("itemWebUrl", ""),
                "image": item.get("image", {}).get("imageUrl", ""),
                "found_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "listed_at": item.get("itemCreationDate", ""),
            }

            seen.add(item_id)
            new_count += 1
            listing_logger.info(format_listing(item, seller_tag))
            tag_str = f" [{seller_tag}]" if seller_tag else ""
            log.info(f"  ✓ New listing: {title[:60]}{tag_str}")

    save_seen(seen)
    save_listings_db(listings_db)
    with open(config.LAST_QUERIED_FILE, "w") as f:
        json.dump({"last_queried": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)
    log.info(f"Scrape complete. {new_count} new listing(s) found.")
    return new_count


if __name__ == "__main__":
    run_scrape()
