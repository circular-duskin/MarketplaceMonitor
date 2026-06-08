# 🛼 Figure Skating Dress Monitor

Monitors eBay for used figure skating dresses and logs new listings to a file.
Built to be extended — email/Discord alerts and more marketplaces can be added later.

---

## Setup

### 1. Get a free eBay Developer account

1. Go to [developer.ebay.com](https://developer.ebay.com/) and sign in with your eBay account (or create one).
2. Click **"Get a Developer Account"** if prompted.
3. Go to **"My Account" → "Application Keysets"**.
4. Click **"Create a Keyset"** → choose **Production**.
5. You'll get three values:
   - **App ID (Client ID)** ← put this in `config.py`
   - **Dev ID**
   - **Cert ID (Client Secret)** ← you'll set this as an environment variable

### 2. Configure your search

Edit `config.py`:

```python
EBAY_APP_ID = "YourAppID-..."   # from step above

MAX_PRICE_USD = 150             # your budget
SIZE_KEYWORDS = ["adult small", "AS", "size 4"]  # your size(s)
CHECK_INTERVAL_MINUTES = 30     # how often to check
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your Client Secret as an environment variable

**Mac/Linux:**
```bash
export EBAY_CLIENT_SECRET="YourCertID-..."
```

**Windows (Command Prompt):**
```cmd
set EBAY_CLIENT_SECRET=YourCertID-...
```

**Windows (PowerShell):**
```powershell
$env:EBAY_CLIENT_SECRET="YourCertID-..."
```

> Tip: Add the export line to your `~/.zshrc` or `~/.bashrc` so you don't have to re-enter it each session.

### 5. Run it

**One-time search (good for testing):**
```bash
python scraper.py
```

**Continuous monitoring:**
```bash
python scheduler.py
```

---

## Output

- **Console** — shows each run, how many results eBay returned, and which new listings passed your filters.
- **`listings.log`** — every new listing that matched your filters, with title, price, condition, seller, and URL.
- **`seen_listings.json`** — internal dedup tracker. Delete this file to re-log all current listings from scratch.

### Example log entry

```
────────────────────────────────────────────────────────────
  Mondor Figure Skating Dress Adult Small AS Purple Velvet
  Price     : $45.00  |  Condition: Used
  Seller    : iceskatemom99  |  Location: Chicago
  ID        : v1|123456789|0
  URL       : https://www.ebay.com/itm/123456789
  Found at  : 2026-06-06 14:32:01
```

---

## Customization

| What | Where |
|------|-------|
| Search terms | `SEARCH_QUERIES` in `config.py` |
| Price range | `MIN_PRICE_USD` / `MAX_PRICE_USD` in `config.py` |
| Sizes to match | `SIZE_KEYWORDS` in `config.py` |
| Check frequency | `CHECK_INTERVAL_MINUTES` in `config.py` |

---

## What's next (easy upgrades)

- **Email alerts** — add `smtplib` calls in `scraper.py` when `new_count > 0`
- **Discord webhook** — one `requests.post()` call to a Discord webhook URL
- **Poshmark** — add a `poshmark.py` scraper using `requests` + `BeautifulSoup`
- **Run 24/7** — deploy on a free [Railway](https://railway.app) or [Render](https://render.com) instance
