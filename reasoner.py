"""
reasoner.py — Scores listings using Gemini Vision based on the user's visual taste profile.

Requires GEMINI_API_KEY env var and at least one liked listing with an image.
"""

import io
import logging
import time

import requests

import config

log = logging.getLogger(__name__)

_model = None

def _get_model():
    global _model
    if _model is not None:
        return _model
    if not config.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
        return _model
    except Exception as e:
        log.error(f"Could not initialize Gemini: {e}")
        return None


def _load_image(url: str):
    from PIL import Image
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


def build_taste_profile(liked_listings: list) -> str:
    """Analyze liked dress images and return a written visual taste profile."""
    model = _get_model()
    if not model or not liked_listings:
        return ""

    parts = ["Here are figure skating dresses this user has liked:"]
    loaded = 0
    for listing in liked_listings[:6]:
        url = listing.get("image", "")
        if not url:
            continue
        try:
            parts.append(_load_image(url))
            parts.append(f"${listing.get('price', 0):.2f}")
            loaded += 1
        except Exception as e:
            log.debug(f"Skipping image {url}: {e}")
        if loaded >= 5:
            break

    if loaded == 0:
        return ""

    parts.append(
        "\nDescribe this user's visual taste profile in 3-4 sentences. "
        "Focus on: silhouette, colors, embellishments, fabric/texture, and overall aesthetic. "
        "Be specific and concrete."
    )

    try:
        response = model.generate_content(parts)
        return response.text.strip()
    except Exception as e:
        log.error(f"Gemini taste profile error: {e}")
        return ""


def score_listing(listing: dict, taste_profile: str) -> tuple:
    """Score one listing image against the taste profile. Returns (score, reason)."""
    model = _get_model()
    url = listing.get("image", "")
    if not model or not url or not taste_profile:
        return None, None

    try:
        img = _load_image(url)
    except Exception as e:
        log.debug(f"Could not load image for scoring: {e}")
        return None, None

    prompt = (
        f"User's visual taste profile for figure skating dresses:\n{taste_profile}\n\n"
        "Rate this dress 1-10 on how well it matches the profile. "
        "Reply in this exact format:\n"
        "SCORE: [1-10]\n"
        "REASON: [one sentence]"
    )

    try:
        response = model.generate_content([prompt, img])
        score, reason = None, None
        for line in response.text.strip().splitlines():
            if line.startswith("SCORE:"):
                try:
                    score = int(line.replace("SCORE:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()
        return score, reason
    except Exception as e:
        log.error(f"Gemini scoring error: {e}")
        return None, None


def run_reasoning(listings_db: dict, feedback: dict, force_rescore: bool = False) -> tuple:
    """Score unscored listings against the user's taste profile.

    Returns (updated_listings_db, count_scored).
    """
    if not config.GEMINI_API_KEY:
        log.info("GEMINI_API_KEY not set — skipping reasoning.")
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
        time.sleep(1.5)  # stay under 15 req/min free tier limit

    return listings_db, scored
