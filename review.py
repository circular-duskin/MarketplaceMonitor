"""
review.py — Walk through unreviewed listings and rate them liked/disliked.

Usage:
    python review.py

Commands during review:
    y  — like this dress
    n  — dislike this dress
    s  — skip for now (ask again next time)
    q  — quit and save progress
"""

import json
from datetime import datetime
from pathlib import Path

import config


def load_json(path, default):
    if not Path(path).exists():
        return default
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_review():
    listings_db = load_json(config.LISTINGS_DB, {})
    feedback = load_json(config.FEEDBACK_FILE, {})

    if not listings_db:
        print("No listings found. Run scraper.py first.")
        return

    unreviewed = [
        (item_id, item)
        for item_id, item in listings_db.items()
        if item_id not in feedback
    ]
    # Newest first.
    unreviewed.sort(key=lambda x: x[1].get("found_at", ""), reverse=True)

    if not unreviewed:
        print("All listings have been reviewed.")
        _print_summary(feedback)
        return

    print(f"\n{len(unreviewed)} unreviewed listing(s).  [y] like  [n] dislike  [s] skip  [q] quit\n")

    reviewed = 0
    for item_id, item in unreviewed:
        print("─" * 60)
        print(f"  {item['title']}")
        print(f"  Price     : ${item['price']:.2f}  |  Condition: {item['condition']}")
        print(f"  Seller    : {item['seller']}")
        print(f"  Found at  : {item['found_at']}")
        print(f"  Listing   : {item['url']}")
        print(f"  Image     : {item['image']}")
        print()

        while True:
            raw = input("  [y/n/s/q]: ").strip().lower()
            if raw in ("y", "n", "s", "q"):
                break
            print("  Enter y, n, s, or q.")

        if raw == "q":
            print(f"\nStopped early. {reviewed} new rating(s) saved.")
            break

        if raw in ("y", "n"):
            feedback[item_id] = {
                "liked": raw == "y",
                "title": item["title"],
                "price": item["price"],
                "seller": item["seller"],
                "url": item["url"],
                "image": item["image"],
                "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_json(config.FEEDBACK_FILE, feedback)
            reviewed += 1
            print(f"  {'Liked.' if raw == 'y' else 'Disliked.'}\n")
        else:
            print("  Skipped.\n")

    print(f"\nDone. {reviewed} new rating(s) saved.")
    _print_summary(feedback)


def _print_summary(feedback: dict):
    liked = [v for v in feedback.values() if v.get("liked")]
    disliked = [v for v in feedback.values() if not v.get("liked")]
    print(f"Total ratings: {len(liked)} liked, {len(disliked)} disliked.\n")

    if liked:
        print("Liked sellers:")
        seller_counts: dict[str, int] = {}
        for v in liked:
            s = v["seller"]
            seller_counts[s] = seller_counts.get(s, 0) + 1
        for seller, count in sorted(seller_counts.items(), key=lambda x: -x[1]):
            print(f"  {seller} ({count})")

    if disliked:
        print("\nDisliked sellers:")
        seller_counts = {}
        for v in disliked:
            s = v["seller"]
            seller_counts[s] = seller_counts.get(s, 0) + 1
        for seller, count in sorted(seller_counts.items(), key=lambda x: -x[1]):
            print(f"  {seller} ({count})")


if __name__ == "__main__":
    run_review()
