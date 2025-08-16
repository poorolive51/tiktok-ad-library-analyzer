"""
tiktok_adlib_ad_details.py

Fetch full details for a list of TikTok ad IDs using the TikTok Commercial Content API.

Usage:
    python tiktok_adlib_ad_details.py input_ad_ids.json output_ad_details.json

Requirements:
    pip install requests python-dotenv

The input JSON should be generated from tiktok_adlib_keyword_scraper.py.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# -----------------------
# AUTHENTICATION
# -----------------------
def fetch_access_token():
    """Authenticate and return a TikTok API access token."""
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")

    if not client_key or not client_secret:
        raise ValueError("Please set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in your .env file.")

    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    token_data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    token_json = response.json()

    if "access_token" not in token_json:
        raise RuntimeError(f"Failed to retrieve access token: {token_json}")

    print(f"Access token obtained. Expires in: {token_json.get('expires_in', 'N/A')} seconds.")
    return token_json["access_token"]

# -----------------------
# FETCH DETAILS FOR ONE AD
# -----------------------
def fetch_ad_details(access_token, ad_id):
    """Retrieve detailed metadata for a single TikTok ad."""
    ad_detail_url = (
        "https://open.tiktokapis.com/v2/research/adlib/ad/detail/"
        "?fields=ad.id,ad.first_shown_date,ad.last_shown_date,"
        "ad.image_urls,ad.videos,ad.reach,ad.rejection_info,"
        "ad_group.targeting_info,advertiser.business_id,"
        "advertiser.business_name,advertiser.paid_for_by,advertiser.profile_url"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"ad_id": ad_id}

    try:
        resp = requests.post(ad_detail_url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"Error fetching ad {ad_id}: {e}")
        return {"ad_id": ad_id, "error": str(e)}

# -----------------------
# MAIN EXECUTION
# -----------------------
def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} input_file.json output_file.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Load environment variables
    load_dotenv()

    # Authenticate
    access_token = fetch_access_token()

    # Load ad IDs from file
    with open(input_file, "r", encoding="utf-8") as f:
        ads_data = json.load(f)

    ad_ids = [ad["id"] for ad in ads_data if "id" in ad]
    print(f"Found {len(ad_ids)} ad IDs to process.")

    # Fetch details for each ad
    all_details = []
    for idx, ad_id in enumerate(ad_ids, start=1):
        print(f"[{idx}/{len(ad_ids)}] Fetching details for ad {ad_id}...")
        details = fetch_ad_details(access_token, ad_id)
        all_details.append(details)

    # Save results to output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_details, f, indent=2, ensure_ascii=False)

    print(f"✅ Done! Results saved to {output_file}")

if __name__ == "__main__":
    main()