"""
schwab_chain_download.py
Author: Louie :)

↳ What it does
1. Uses your refresh-token to grab a fresh *access* token (OAuth2 “POST Token” endpoint).
2. Calls the /marketdata/v1/chains REST endpoint to pull the full options-chain
   for the symbol + expiration you specify.
3. Saves the raw JSON to   <TICKER>_<EXPIRY>_<YYYY-MM-DD>.json   in the working folder.
"""

import os, sys, json, datetime
import requests
import time
from typing import Optional

# Update URLs for production
TOKEN_URL  = "https://api.schwab.com/v1/oauth/token"
CHAINS_URL = "https://api.schwab.com/marketdata/v1/chains"


def get_access_token(client_id: str, refresh_token: str, retry_count: int = 3) -> Optional[str]:
    """Refresh and return a short-lived Bearer token with retry logic."""
    for attempt in range(retry_count):
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "refresh_token": refresh_token,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["access_token"]
        except requests.exceptions.RequestException as e:
            if attempt == retry_count - 1:
                print(f"Failed to get access token after {retry_count} attempts: {e}")
                return None
            time.sleep(2 ** attempt)  # Exponential backoff


def download_chain(symbol: str, expiry: str, bearer: str, retry_count: int = 3) -> Optional[dict]:
    """Grab the option-chain with retry logic and rate limit handling."""
    for attempt in range(retry_count):
        try:
            params = {
                "symbol": symbol,
                "contractType": "ALL",   # calls + puts
                "fromDate": expiry,
                "toDate":   expiry,
            }
            r = requests.get(
                CHAINS_URL, 
                headers={"Authorization": f"Bearer {bearer}"}, 
                params=params, 
                timeout=15
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt == retry_count - 1:
                print(f"Failed to download chain after {retry_count} attempts: {e}")
                return None
            if r.status_code == 429:  # Rate limit
                time.sleep(60)  # Wait longer for rate limits
            else:
                time.sleep(2 ** attempt)


def main() -> None:
    symbol = input("Ticker (e.g. SOXL): ").upper().strip()
    expiry = input("Expiration (YYYY-MM-DD): ").strip()

    # Expect these two secrets as environment variables for safety.
    client_id      = os.getenv("SCHWAB_CLIENT_ID")
    refresh_token  = os.getenv("SCHWAB_REFRESH_TOKEN")
    if not (client_id and refresh_token):
        sys.exit("✘  Set SCHWAB_CLIENT_ID and SCHWAB_REFRESH_TOKEN env vars first.")

    token = get_access_token(client_id, refresh_token)
    if not token:
        sys.exit("✘ Failed to get access token")

    chain = download_chain(symbol, expiry, token)
    if not chain:
        sys.exit("✘ Failed to download options chain")
    
    outname = f"{symbol}_{expiry}_{datetime.date.today()}.json"
    with open(outname, "w") as f:
        json.dump(chain, f, indent=2)
    print(f"✓  Saved chain to {outname}")


if __name__ == "__main__":
    main()
