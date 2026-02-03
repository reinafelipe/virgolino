import requests
import json
from datetime import datetime, timedelta

def test_gamma():
    # Gamma API endpoint
    url = "https://gamma-api.polymarket.com/events"
    
    # query params
    params = {
        "limit": 100,
        "active": "true",
        "closed": "false",
        "order": "endDate",
        "ascending": "true",
        "offset": 0
    }
    
    print(f"Fetching from {url}...")
    
    found_today = False
    
    try:
        while not found_today and params['offset'] < 1000: # Scan up to 1000 markets
            print(f"  Fetching offset {params['offset']}...")
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            
            if not data:
                print("No more data.")
                break
                
            for item in data:
                end_date_str = item.get('endDate')
                if not end_date_str: continue
                if '2026-02-03' in end_date_str:
                    print(f"FOUND MATCHING DATE: {item.get('title')} | {end_date_str}")
                    found_today = True
            
            params['offset'] += 100
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gamma()
