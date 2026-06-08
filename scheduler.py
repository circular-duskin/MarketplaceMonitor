"""
scheduler.py — Runs the scraper on a repeating schedule.

Usage:
    python scheduler.py

Press Ctrl+C to stop.
"""

import logging
import time
from datetime import datetime

import schedule

import config
from scraper import run_scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def job():
    log.info(f"⏰  Scheduled run triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_scrape()


if __name__ == "__main__":
    interval = config.CHECK_INTERVAL_MINUTES
    log.info(f"🛼  Figure Skating Dress Monitor started.")
    log.info(f"    Checking eBay every {interval} minutes.")
    log.info(f"    New listings → {config.LOG_FILE}")
    log.info(f"    Press Ctrl+C to stop.\n")

    # Run immediately on start, then on schedule
    job()

    schedule.every(interval).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)
