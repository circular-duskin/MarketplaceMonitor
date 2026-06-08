# ============================================================
# Figure Skating Dress Monitor — Search Configuration
# ============================================================
# Copy this file to config.py and fill in your values.
# Get a free eBay App ID at: https://developer.ebay.com/

# --- eBay API Credentials ---
EBAY_APP_ID = "YourName-AppName-PRD-xxxxxxxxx-xxxxxxxx"

# --- Search Terms ---
SEARCH_QUERIES = [
    "figure skating dresses brad griffies",
]

# --- Filters ---
MAX_PRICE_USD = 800       # Skip anything above this price
MIN_PRICE_USD = 10        # Skip suspiciously cheap listings
CONDITION = "used"        # "used", "new", or None for both

# eBay structured facets — more reliable than keyword matching on title text.
EBAY_CATEGORY_ID = "261510"          # Figure Skating category
SIZE_ASPECTS = ["S", "XS", "4", "6"] # eBay Size facet values
DEPARTMENT = "Women"

# Title keyword fallback — empty means rely entirely on eBay's aspect filters above.
SIZE_KEYWORDS = []

# --- Scheduling ---
CHECK_INTERVAL_MINUTES = 360  # How often to poll eBay

# --- Output ---
LOG_FILE = "listings.log"
SEEN_FILE = "seen_listings.json"
LISTINGS_DB = "listings_db.json"
FEEDBACK_FILE = "feedback.json"
LAST_QUERIED_FILE = "last_queried.json"

# --- eBay API Settings (you probably don't need to change these) ---
EBAY_API_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_MARKETPLACE = "EBAY_US"
RESULTS_PER_QUERY = 50
