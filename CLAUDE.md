# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

MarketplaceMonitor is a Python scraper that monitors eBay for used figure skating dresses matching configurable size, price, and condition filters. It deduplicates results across runs, logs new finds to a file, and can run as a one-time check or on a recurring schedule.

## Setup

```bash
pip install -r requirements.txt
export EBAY_CLIENT_SECRET="your_secret_here"
```

Edit `config.py` to set your eBay App ID, search queries, size keywords, price range, and check interval.

## Running

```bash
# One-time search (for testing)
python scraper.py

# Continuous polling (default: every 30 minutes)
python scheduler.py
```

## Architecture

Three files do all the work:

- **`config.py`** — All user-tunable settings: eBay credentials, search terms, size keywords, price range, file paths, polling interval.
- **`scraper.py`** — Core logic: OAuth token fetch, eBay Browse API calls, filtering (`matches_size`, `passes_price`), dedup against `seen_listings.json`, and appending matches to `listings.log`.
- **`scheduler.py`** — Thin wrapper that calls `scraper.run_scrape()` on a timer using the `schedule` library.

**Data flow:** `scheduler.py` → `scraper.run_scrape()` → OAuth → load seen IDs → for each query, hit eBay API → filter by size/price/condition → log new items → save seen IDs.

**Outputs:**
- `listings.log` — append-only human-readable log of new finds
- `seen_listings.json` — persisted set of already-seen listing IDs; delete this file to reset dedup state

## Key Conventions

- All configuration lives in `config.py` as `SCREAMING_SNAKE_CASE` constants — avoid hardcoding values elsewhere.
- Two loggers are used intentionally: the main logger goes to console, and a separate `listings` logger writes only to `listings.log` (keeps console clean).
- Dict access uses `.get()` with defaults throughout to handle malformed API responses without crashing.
- Per-query errors are caught and logged without stopping the run — the loop continues to the next query.
