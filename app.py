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
from datetime import datetime
from pathlib import Path

import schedule
from flask import Flask, jsonify, render_template, request

import config
from scraper import run_scrape

app = Flask(__name__)


def _scheduler_loop():
    def job():
        run_scrape()

    job()  # run immediately on start
    schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)


def start_scheduler():
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()


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
        })
    listings.sort(key=lambda x: x.get("found_at", ""), reverse=True)

    unreviewed = sum(1 for l in listings if not l["already_liked"])
    last_queried = load_json(config.LAST_QUERIED_FILE, {}).get("last_queried", "Never")
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


if __name__ == "__main__":
    start_scheduler()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
