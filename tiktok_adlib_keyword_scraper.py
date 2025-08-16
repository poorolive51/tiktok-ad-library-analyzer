```python
tiktok_adlib_keyword_scraper.py

A script to collect TikTok Ad Library ad IDs for a given keyword, country, and time range using the TikTok Commercial Content API.

Requirements:
- Python 3.8+
- requests
- python-dotenv
- python-dateutil

Setup:
1. Install dependencies: pip install requests python-dotenv python-dateutil
2. Create a `.env` file in the same directory with:
   TIKTOK_CLIENT_KEY=your_client_key_here
   TIKTOK_CLIENT_SECRET=your_client_secret_here
3. Run: python tiktok_adlib_keyword_scraper.py keyword1 keyword2 ...
```

```python
import os
import sys
import time
import json
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# -----------------------
# CONFIGURATION
# -----------------------
COUNTRY = "NL"  # Two-letter ISO country code
MONTHS_BACK = 12  # How far back to search from today
MAX_ADS_PER_REQUEST = 20  # TikTok API max per request
DATE_INCREMENT_DAYS = 10  # Chunk size for date ranges
MAX_PAGES = 1000  # Safety limit for pagination
MAX_TOTAL_ADS = 10000  # Max ads collected per keyword
FIXED_RATE_LIMIT_DELAY = 1  # Delay between requests (seconds)

# -----------------------
# AUTHENTICATION
# -----------------------
load_dotenv()
client_key = os.getenv("TIKTOK_CLIENT_KEY")
client_secret = os.getenv("TIKTOK_CLIENT_SECRET")

if not client_key or not client_secret:
    raise ValueError("Please set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in your .env file.")

# Get access token (valid for 2 hours)
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
token_data = {
    "client_key": client_key,
    "client_secret": client_secret,
    "grant_type": "client_credentials"
}

print("Fetching access token...")
token_resp = requests.post(TOKEN_URL, data=token_data)
token_resp.raise_for_status()
token_json = token_resp.json()
access_token = token_json.get("access_token")

if not access_token:
    raise RuntimeError(f"Failed to get access token: {token_json}")

print(f"Access token obtained. Expires in: {token_json.get('expires_in', 'N/A')} seconds.")

# -----------------------
# BASE API SETTINGS
# -----------------------
AD_QUERY_URL = "https://open.tiktokapis.com/v2/research/adlib/ad/query/"
base_headers = {
    "authorization": f"bearer {access_token}",
    "Content-Type": "application/json"
}
query_fields = "ad.id,ad.first_shown_date,ad.last_shown_date,advertiser.business_name"

# -----------------------
# MAIN FUNCTION
# -----------------------
def collect_ad_ids(search_term):
    """Collect unique ad IDs for a given keyword over the past MONTHS_BACK months."""
    today = datetime.now()
    max_date_dt = today - timedelta(days=1)
    start_date_dt = max_date_dt - relativedelta(months=MONTHS_BACK)
    
    all_ads = []
    seen_ids = set()
    current_date = start_date_dt

    while current_date < max_date_dt:
        chunk_start = current_date.strftime("%Y%m%d")
        chunk_end_dt = min(current_date + timedelta(days=DATE_INCREMENT_DAYS - 1), max_date_dt)
        chunk_end = chunk_end_dt.strftime("%Y%m%d")
        
        print(f"\nSearching ads from {chunk_start} to {chunk_end} for '{search_term}'")
        
        offset = 0
        page_count = 0
        has_more = True
        
        while has_more and page_count < MAX_PAGES and len(all_ads) < MAX_TOTAL_ADS:
            page_count += 1
            request_body = {
                "filters": {
                    "ad_published_date_range": {
                        "min": chunk_start,
                        "max": chunk_end
                    },
                    "country": COUNTRY
                },
                "search_term": search_term,
                "search_type": "fuzzy_phrase",
                "max_count": MAX_ADS_PER_REQUEST,
                "offset": offset
            }
            
            try:
                resp = requests.post(
                    AD_QUERY_URL,
                    headers=base_headers,
                    params={"fields": query_fields},
                    json=request_body
                )
                
                if resp.status_code == 429:  # Rate-limited: wait and retry
                    print("Rate limited. Waiting 5s...")
                    time.sleep(5)
                    continue
                
                resp.raise_for_status()
                data = resp.json().get("data", {})
                ads = data.get("ads", [])
                
                for ad in ads:
                    ad_id = ad.get("ad", {}).get("id")
                    if ad_id and ad_id not in seen_ids:
                        seen_ids.add(ad_id)
                        all_ads.append({
                            "id": ad_id,
                            "basic_info": ad
                        })
                
                offset = data.get("offset", offset + MAX_ADS_PER_REQUEST)
                has_more = data.get("has_more", False)
                
                if has_more:
                    time.sleep(FIXED_RATE_LIMIT_DELAY)
            except requests.RequestException as e:
                print(f"Request error: {e}")
                break
        
        current_date += timedelta(days=DATE_INCREMENT_DAYS)

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    min_date = start_date_dt.strftime("%Y%m%d")
    max_date = max_date_dt.strftime("%Y%m%d")
    keyword_safe = "".join(c if c.isalnum() else "_" for c in search_term)
    filename = f"tiktok_ad_ids_{COUNTRY}_{keyword_safe}_{min_date}_to_{max_date}_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_ads, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(all_ads)} ads to {filename}")
    return filename

# -----------------------
# ENTRY POINT
# -----------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tiktok_adlib_keyword_scraper.py <keyword1> <keyword2> ...")
        sys.exit(1)
    
    for kw in sys.argv[1:]:
        collect_ad_ids(kw)
```