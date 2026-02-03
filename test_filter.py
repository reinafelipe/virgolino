
from market_scanner import MarketScanner
import logging

logging.basicConfig(level=logging.INFO)
scanner = MarketScanner()

print("Testing Market Scanner Filter...")
markets = scanner.get_all_asset_markets()

for asset, m_list in markets.items():
    print(f"\n{asset}:")
    for m in m_list:
        print(f"  - {m['question']} | End: {m['end_date']}")
