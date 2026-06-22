"""
reasoner.py — Scores listings using Claude vision based on the user's visual taste profile.

Requires ANTHROPIC_API_KEY env var and at least one liked listing with an image.
"""

import base64
import logging
import time

import requests
import anthropic

import config

log = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return _client
    except Exception as e:
        log.error(f"Could not initialize Anthropic client: {e}")
        return None


def _load_image_b64(url: str) -> tuple:
    """Download image and return (base64_data, media_type)."""
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    media_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        media_type = "image/jpeg"
    return base64.standard_b64encode(resp.content).decode("utf-8"), media_type


def _image_block(url: str) -> dict | None:
    try:
        data, media_type = _load_image_b64(url)
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        }
    except Exception as e:
        log.debug(f"Skipping image {url}: {e}")
        return None


def build_taste_profile(liked_listings: list) -> str:
    """Analyze liked dress images and return a written visual taste profile."""
    client = _get_client()
    if not client or not liked_listings:
        return ""

    content = [{"type": "text", "text": "Here are figure skating dresses this user has liked:"}]
    loaded = 0
    for listing in liked_listings[:6]:
        url = listing.get("image", "")
        if not url:
            continue
        block = _image_block(url)
        if block:
            content.append(block)
            content.append({"type": "text", "text": f"${listing.get('price', 0):.2f}"})
            loaded += 1
        if loaded >= 5:
            break

    if loaded == 0:
        return ""

    content.append({
        "type": "text",
        "text": (
            "Describe this user's visual taste profile in 3-4 sentences. "
            "Focus on: silhouette, embellishments, fabric/texture, and overall aesthetic. "
            "Do NOT factor in color — the user is open to all colors except yellow and orange. "
            "Be specific and concrete about what makes these dresses appealing beyond color."
        ),
    })

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        log.error(f"Claude taste profile error: {e}")
        return ""


def score_listing(listing: dict, taste_profile: str) -> tuple:
    """Score one listing image against the taste profile. Returns (score, reason)."""
    client = _get_client()
    url = listing.get("image", "")
    if not client or not url or not taste_profile:
        return None, None

    block = _image_block(url)
    if not block:
        return None, None

    content = [
        {
            "type": "text",
            "text": (
                f"User's visual taste profile for figure skating dresses:\n{taste_profile}\n\n"
                "Rate this dress 1-10 on how well it matches the profile. "
                "Scoring rules:\n"
                "- Color does NOT affect the score — the user likes all colors except yellow and orange. "
                "Only deduct points if the dress is clearly yellow or orange.\n"
                "- Judge skirt style only from what is clearly visible in the image. "
                "If the skirt is partially visible or ambiguous, do not penalize it.\n"
                "- Focus scoring on: silhouette, embellishments (crystals, beading), "
                "fabric quality, and competition-readiness.\n"
                "Reply in this exact format:\n"
                "SCORE: [1-10]\n"
                "REASON: [one sentence]"
            ),
        },
        block,
    ]

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            messages=[{"role": "user", "content": content}],
        )
        text = response.content[0].text.strip()
        score, reason = None, None
        for line in text.splitlines():
            if line.startswith("SCORE:"):
                try:
                    score = int(line.replace("SCORE:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()
        return score, reason
    except Exception as e:
        log.error(f"Claude scoring error: {e}")
        return None, None


def run_reasoning(listings_db: dict, feedback: dict, force_rescore: bool = False) -> tuple:
    """Score unscored listings against the user's taste profile.

    Returns (updated_listings_db, count_scored).
    """
    if not config.ANTHROPIC_API_KEY:
        log.info("ANTHROPIC_API_KEY not set — skipping reasoning.")
        return listings_db, 0

    liked_ids = [k for k, v in feedback.items() if v.get("liked")]
    liked_listings = [listings_db[k] for k in liked_ids if k in listings_db]

    if not liked_listings:
        log.info("No liked listings yet — need at least one to build a taste profile.")
        return listings_db, 0

    log.info(f"Building taste profile from {len(liked_listings)} liked dress(es)...")
    taste_profile = build_taste_profile(liked_listings)
    if not taste_profile:
        log.warning("Could not build taste profile.")
        return listings_db, 0

    log.info(f"Profile: {taste_profile[:120]}...")

    to_score = [
        (item_id, item)
        for item_id, item in listings_db.items()
        if ("ai_score" not in item or force_rescore)
        and feedback.get(item_id, {}).get("liked") is not False
    ]
    log.info(f"Scoring {len(to_score)} listing(s)...")

    scored = 0
    for item_id, item in to_score:
        score, reason = score_listing(item, taste_profile)
        if score is not None:
            item["ai_score"] = score
            item["ai_reasoning"] = reason or ""
            scored += 1
            log.info(f"  {score}/10 — {item.get('title', '')[:50]}")
        time.sleep(0.5)

    return listings_db, scored
