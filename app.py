"""
app.py — Web interface for reviewing listings.
Also runs the scraper scheduler in a background thread.

Usage:
    python app.py
    Open http://localhost:8080 in your browser.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import schedule
from flask import Flask, jsonify, render_template, request

import config
from scraper import run_scrape, save_listings_db
from reasoner import run_reasoning

app = Flask(__name__)
log = app.logger


def _scheduler_loop():
    def job():
        run_scrape()
        listings_db = load_json(config.LISTINGS_DB, {})
        feedback = load_json(config.FEEDBACK_FILE, {})
        updated_db, count = run_reasoning(listings_db, feedback)
        if count:
            save_listings_db(updated_db)

    job()  # run immediately on start
    schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)


def start_scheduler():
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()


_PT = ZoneInfo("America/Los_Angeles")


def to_pacific(dt_str: str) -> str:
    if not dt_str or dt_str == "Never":
        return "Never"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        pt = dt.astimezone(_PT)
        tz_label = "PDT" if pt.dst() else "PST"
        return pt.strftime(f"%b %-d, %Y %-I:%M %p {tz_label}")
    except Exception:
        return dt_str


def listing_age(listed_at: str) -> str:
    if not listed_at:
        return ""
    try:
        dt = datetime.fromisoformat(listed_at.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
        if days == 0:
            return "Listed today"
        if days == 1:
            return "Listed yesterday"
        return f"Listed {days} days ago"
    except Exception:
        return ""


def load_json(path, default):
    if not Path(path).exists():
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/")
def index():
    listings_db = load_json(config.LISTINGS_DB, {})
    feedback = load_json(config.FEEDBACK_FILE, {})

    listings = []
    for item_id, item in listings_db.items():
        fb = feedback.get(item_id)
        if fb and not fb.get("liked"):
            continue  # disliked — hide permanently
        listings.append({
            "id": item_id,
            **item,
            "already_liked": fb.get("liked", False) if fb else False,
            "age": listing_age(item.get("listed_at", "")),
            "ai_score": item.get("ai_score"),
            "ai_reasoning": item.get("ai_reasoning", ""),
        })
    listings.sort(key=lambda x: (x["ai_score"] is not None, x.get("ai_score", 0), x.get("found_at", "")), reverse=True)

    unreviewed = sum(1 for l in listings if not l["already_liked"])
    last_queried = to_pacific(load_json(config.LAST_QUERIED_FILE, {}).get("last_queried", "Never"))
    return render_template("index.html", listings=listings, unreviewed=unreviewed, last_queried=last_queried)


@app.route("/rate", methods=["POST"])
def rate():
    data = request.json
    item_id = data.get("item_id")
    action = data.get("action")

    if not item_id or action not in ("like", "dislike", "skip"):
        return jsonify({"error": "invalid"}), 400

    if action == "skip":
        return jsonify({"ok": True})

    listings_db = load_json(config.LISTINGS_DB, {})
    feedback = load_json(config.FEEDBACK_FILE, {})

    item = listings_db.get(item_id, {})
    feedback[item_id] = {
        "liked": action == "like",
        "title": item.get("title", ""),
        "price": item.get("price", 0),
        "seller": item.get("seller", ""),
        "url": item.get("url", ""),
        "image": item.get("image", ""),
        "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_json(config.FEEDBACK_FILE, feedback)

    return jsonify({"ok": True})


@app.route("/rescore", methods=["POST"])
def rescore():
    def do_rescore():
        listings_db = load_json(config.LISTINGS_DB, {})
        feedback = load_json(config.FEEDBACK_FILE, {})
        updated_db, count = run_reasoning(listings_db, feedback, force_rescore=True)
        save_listings_db(updated_db)
        log.info(f"Rescore complete: {count} listing(s) scored.")

    threading.Thread(target=do_rescore, daemon=True).start()
    return jsonify({"ok": True})


if __name__ == "__main__":
    start_scheduler()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
