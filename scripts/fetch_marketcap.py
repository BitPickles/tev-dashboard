#!/usr/bin/env python3
"""Fetch BTC and Total crypto market cap from CoinCap API (free, no key needed)"""
import json
import requests
from datetime import datetime
import time

def fetch_coincap_btc():
    """Fetch BTC market cap history from CoinCap"""
    print("Fetching BTC market cap from CoinCap...")
    
    # CoinCap provides history - we need to fetch in chunks
    # Start from 2021-09-14
    start_ts = int(datetime(2021, 9, 14).timestamp() * 1000)
    end_ts = int(datetime.now().timestamp() * 1000)
    
    data = {}
    interval = "d1"  # Daily
    
    url = f"https://api.coincap.io/v2/assets/bitcoin/history"
    params = {"interval": interval, "start": start_ts, "end": end_ts}
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        for item in result.get("data", []):
            date = item["date"][:10]  # YYYY-MM-DD
            # CoinCap gives price, we need to calculate mcap
            # They don't have direct mcap in history, but we can use price * supply
            # Actually let's check if they have marketCap
            if "marketCapUsd" in item:
                data[date] = float(item["marketCapUsd"])
        
        print(f"Got {len(data)} BTC data points")
    except Exception as e:
        print(f"Error: {e}")
    
    return data

def fetch_total_mcap_alternative():
    """Try alternative sources for total market cap"""
    print("Note: Total market cap requires premium API, skipping for now")
    return {}

def main():
    btc_mcaps = fetch_coincap_btc()
    total_mcaps = fetch_total_mcap_alternative()
    
    # Combine data
    all_dates = sorted(set(btc_mcaps.keys()) | set(total_mcaps.keys()))
    
    data = []
    for date in all_dates:
        entry = {"date": date}
        if date in btc_mcaps:
            entry["btc_mcap"] = btc_mcaps[date]
        if date in total_mcaps:
            entry["total_mcap"] = total_mcaps[date]
        if len(entry) > 1:
            data.append(entry)
    
    if data:
        output_path = "indicators/data/marketcap.json"
        with open(output_path, "w") as f:
            json.dump(data, f)
        print(f"Saved {len(data)} records to {output_path}")
    else:
        print("No data fetched")

if __name__ == "__main__":
    main()
