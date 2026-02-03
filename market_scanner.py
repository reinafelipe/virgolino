import requests
import logging
from datetime import datetime, timedelta, timezone
import config

logger = logging.getLogger(__name__)

class MarketScanner:
    def __init__(self):
        self.gamma_url = "https://gamma-api.polymarket.com/events"

    def get_markets_for_asset(self, asset: str, quick_scan=False):
        """
        Find 15-minute up/down markets for a specific asset.
        Returns list of market dicts with clob_token_ids.
        """
        if asset not in config.ASSETS:
            logger.warning(f"Unknown asset: {asset}")
            return []
        
        keywords = config.ASSETS[asset]['polymarket_keywords']
        
        try:
            markets_found = []
            
            params = {
                "limit": 100,
                "active": "true",
                "closed": "false",
                "order": "endDate",
                "ascending": "true",
                "ascending": "true",
                "offset": 0
            }
            
            # Use specific search to reduce result set size
            if keywords:
                params["q"] = keywords[0]
            
            
            now = datetime.now(timezone.utc)
            
            target_window_start = now
            target_window_end = now + timedelta(minutes=60)
            
            max_pages = 15  # Increased to find current markets
            
            for page in range(max_pages):
                resp = requests.get(self.gamma_url, params=params, timeout=5)  # 5 second timeout
                events = resp.json()
                
                if not events:
                    break
                
                # Skip if entire batch is in the past
                last_event_date_str = events[-1].get('endDate', '')
                try:
                    le_clean = last_event_date_str.replace("Z", "")
                    if "." in le_clean: le_clean = le_clean.split(".")[0]
                    le_date = datetime.strptime(le_clean, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    if le_date < now:
                        params['offset'] += 100
                        continue
                except:
                    pass

                for event in events:
                    title = event.get('title', '').lower()
                    end_date_str = event.get('endDate')
                    logger.info(f"DEBUG: Inspecting '{title}' Ends: {end_date_str}")
                    
                    # Check if title matches any keyword for this asset
                    
                    # Check if title matches any keyword for this asset
                    if not any(kw in title for kw in keywords):
                        continue
                    
                    # Must be "up or down" market
                    if 'up' not in title or 'down' not in title:
                        continue
                    
                    end_date_str = event.get('endDate')
                    if not end_date_str: continue
                    
                    try:
                        clean_date = end_date_str.replace("Z", "")
                        if "." in clean_date: clean_date = clean_date.split(".")[0]
                        end_date = datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                        
                        # STRICT 15-MIN FILTERING
                        # Regex to match patterns like "1:45PM-2:00PM" or "14:45-15:00"
                        import re
                        time_pattern = r'\d{1,2}:\d{2}(?:[APM]{2})?-\d{1,2}:\d{2}(?:[APM]{2})?'
                        time_match = re.search(time_pattern, title)
                        
                        if not time_match:
                            logger.debug(f"Skipping '{title}' - No 15-min time interval found")
                            continue
                            
                        if target_window_start <= end_date <= target_window_end:
                            for m in event.get('markets', []):
                                clob_token_ids = m.get('clobTokenIds', [])
                                outcomes = m.get('outcomes', [])
                                
                                if not clob_token_ids:
                                    continue
                                
                                # Parse JSON string if needed
                                import json
                                if isinstance(clob_token_ids, str):
                                    try:
                                        clob_token_ids = json.loads(clob_token_ids)
                                    except:
                                        continue
                                
                                if isinstance(outcomes, str):
                                    try:
                                        outcomes = json.loads(outcomes)
                                    except:
                                        outcomes = []
                                
                                market_data = {
                                    'asset': asset,
                                    'id': m.get('id'),
                                    'question': m.get('question'),
                                    'end_date': end_date,
                                    'event_id': event.get('id'),
                                    'slug': event.get('slug'),
                                    'clob_token_ids': clob_token_ids,
                                    'outcomes': outcomes
                                }
                                markets_found.append(market_data)
                                
                                if quick_scan and markets_found:
                                    return markets_found
                                    
                    except ValueError:
                        continue
                
                if markets_found:
                    break
                    
                params['offset'] += 100
            
            return markets_found
            
        except Exception as e:
            logger.error(f"Error scanning markets for {asset}: {e}")
            return []

    def get_all_asset_markets(self):
        """
        Scan for markets across all configured assets.
        Returns dict: {asset: [markets]}
        """
        all_markets = {}
        
        for asset in config.ASSETS.keys():
            logger.info(f"Scanning {asset} markets...")
            markets = self.get_markets_for_asset(asset, quick_scan=True)
            all_markets[asset] = markets
            if markets:
                logger.info(f"  Found {len(markets)} {asset} market(s)")
            else:
                logger.debug(f"  No {asset} markets in window")
        
        return all_markets

    def check_orderbook_liquidity(self, client, token_id: str, min_liquidity: float) -> bool:
        """
        Check if orderbook has sufficient liquidity.
        Returns True if liquidity >= min_liquidity USD.
        """
        try:
            book = client.get_order_book(token_id)
            
            # Calculate total ask liquidity (sellers)
            total_liquidity = 0.0
            
            if hasattr(book, 'asks') and book.asks:
                for ask in book.asks[:5]:  # Top 5 levels
                    price = float(ask.price) if hasattr(ask, 'price') else float(ask.get('price', 0))
                    size = float(ask.size) if hasattr(ask, 'size') else float(ask.get('size', 0))
                    total_liquidity += price * size
            elif isinstance(book, dict) and 'asks' in book:
                for ask in book['asks'][:5]:
                    total_liquidity += float(ask['price']) * float(ask['size'])
            
            logger.debug(f"Token {token_id[:20]}... liquidity: ${total_liquidity:.2f}")
            return total_liquidity >= min_liquidity
            
        except Exception as e:
            logger.warning(f"Liquidity check failed: {e}")
            return False


if __name__ == "__main__":
    scanner = MarketScanner()
    all_markets = scanner.get_all_asset_markets()
    for asset, markets in all_markets.items():
        print(f"{asset}: {len(markets)} markets")
        for m in markets:
            print(f"  - {m['question']}")
