import os

# --- eBay API Credentials (set these as environment variables) ---
EBAY_APP_ID = os.environ.get("EBAY_APP_ID", "")
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET", "")


# --- eBay Search Terms ---
SEARCH_QUERIES = [
    "figure skating dress brad griffies",
    "figure skating dress competition",
    "figure skating dress custom",
]

# --- Filters ---
MAX_PRICE_USD = 800
MIN_PRICE_USD = 10
CONDITION = ""

EBAY_CATEGORY_ID = "261510"
SIZE_ASPECTS = ["S", "XS", "4", "6"]
DEPARTMENT = "Women"
SIZE_KEYWORDS = []

# --- BradGStock (bradgstock.com) ---
BRADG_COLLECTIONS = ["dresses", "beaded", "un-beaded-stock", "stock-sale"]
BRADG_SIZES = ["Adult Small", "Adult XSmall"]  # must appear in product title

# --- Scheduling ---
CHECK_INTERVAL_MINUTES = 360

# --- Output ---
LOG_FILE = "listings.log"
SEEN_FILE = "seen_listings.json"
LISTINGS_DB = "listings_db.json"
FEEDBACK_FILE = "feedback.json"
LAST_QUERIED_FILE = "last_queried.json"

# --- eBay API Settings ---
EBAY_API_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_MARKETPLACE = "EBAY_US"
RESULTS_PER_QUERY = 50
