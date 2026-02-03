
import logging
import sys
import pandas as pd
from market_scanner import MarketScanner
from strategy import SwingStrategy
from bot import fetch_price_history, get_minutes_to_expiry, get_polymarket_odds
import config

# Setup console logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Diagnose")

def diagnose():
    print("--- DIAGNOSTIC RUN ---")
    scanner = MarketScanner()
    
    # Check assets
    for asset, asset_config in config.ASSETS.items():
        print(f"\nAnalyzing {asset}...")
        
        # 1. Market Scan
        all_markets = scanner.get_all_asset_markets()
        markets = all_markets.get(asset, [])
        if not markets:
            print(f"❌ No active markets found for {asset}.")
            continue
            
        target_market = markets[0]
        print(f"✅ Found Market: {target_market.get('question')}")
        
        # 2. Time Window
        minutes_remaining = get_minutes_to_expiry(target_market)
        print(f"⏱  Minutes to Expiry: {minutes_remaining}")
        
        in_window = config.ENTRY_WINDOW_START_MIN <= (15 - minutes_remaining) <= config.ENTRY_WINDOW_END_MIN
        # Note: logic in bot.py is: 
        # min_remaining = 15 - config.ENTRY_WINDOW_END_MIN  (15-12 = 3)
        # max_remaining = 15 - config.ENTRY_WINDOW_START_MIN (15-2 = 13)
        # return min_remaining <= minutes_remaining <= max_remaining
        # So acceptable remaining is [3, 13]
        
        lower_bound = 15 - config.ENTRY_WINDOW_END_MIN
        upper_bound = 15 - config.ENTRY_WINDOW_START_MIN
        
        if lower_bound <= minutes_remaining <= upper_bound:
             print(f"✅ In Entry Window (Remaining: {minutes_remaining}m, Allowed: {lower_bound}-{upper_bound}m)")
        else:
             print(f"❌ Outside Entry Window (Remaining: {minutes_remaining}m, Allowed: {lower_bound}-{upper_bound}m)")

        # 3. Price History
        symbol = asset_config['binance_symbol']
        history = fetch_price_history(symbol)
        if history.empty:
            print("❌ Failed to fetch Binance price history.")
            continue
        
        current_price = history['close'].iloc[-1]
        print(f"💰 Current Binance Price: ${current_price:.2f}")

        # 4. Strategy Analysis
        strategy = SwingStrategy(asset)
        # We don't have the engine client here easily without auth, so we skip polymarket odds specific divergence for now unless we want to init the client.
        # But SwingStrategy might handle None for odds or we can just pass 0.5
        
        result = strategy.analyze_market(history, polymarket_up_odds=0.50)
        
        print(f"📊 Indicators:")
        print(f"   RSI: {result['rsi']:.2f}")
        print(f"   Bollinger Upper: {result['bb_upper']:.2f}")
        print(f"   Bollinger Lower: {result['bb_lower']:.2f}")
        print(f"   Signal: {result['signal']}")
        
        if result['signal'] == 'NEUTRAL':
            print("   -> No trade signal generated.")
        else:
            print(f"   -> STRATEGY TRIGGERED: {result['signal']}")

if __name__ == "__main__":
    diagnose()
