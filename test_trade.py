"""
Quick Trade Test - Uses cached market data, no API search needed
"""
import time
from execution import ExecutionEngine
from market_scanner import MarketScanner

print("=" * 50)
print("QUICK TRADE TEST")
print("=" * 50)

# 1. Initialize (this should take < 3 seconds)
start = time.time()
print("Connecting to Polymarket...", end=" ", flush=True)
engine = ExecutionEngine()
print(f"Done ({time.time()-start:.1f}s)")

# 2. Get current BTC market from scanner
print("Finding BTC market...", end=" ", flush=True)
start = time.time()
scanner = MarketScanner()
markets = scanner.get_markets_for_asset('BTC', quick_scan=True)
print(f"Done ({time.time()-start:.1f}s)")

if not markets:
    print("ERROR: No BTC market found!")
    exit(1)

market = markets[0]
print(f"Market: {market.get('question', 'Unknown')}")

# 3. Get UP token ID
token_ids = market.get('clob_token_ids', [])
if len(token_ids) < 1:
    print("ERROR: No token IDs!")
    exit(1)

up_token = token_ids[0]
print(f"UP Token: {up_token[:20]}...")

# 4. Get orderbook and best ask
print("Getting orderbook...", end=" ", flush=True)
start = time.time()
book = engine.client.get_order_book(up_token)
print(f"Done ({time.time()-start:.1f}s)")

if hasattr(book, 'asks') and book.asks:
    best_ask = float(book.asks[0].price)
else:
    best_ask = 0.50

print(f"Best Ask: ${best_ask:.3f}")

# 5. Place minimum buy order
min_size = 1.0  # 1 share minimum
cost = min_size * best_ask

print(f"\nPlacing BUY order: {min_size} shares @ ${best_ask:.3f} = ${cost:.2f}")
print("Executing...", end=" ", flush=True)
start = time.time()

resp = engine.place_order(
    token_id=up_token,
    side='BUY',
    price=best_ask,
    size=min_size
)

exec_time = time.time() - start
print(f"Done ({exec_time:.1f}s)")

print(f"\nResult: {resp}")

if resp and resp.get('success'):
    order_id = resp.get('orderID', 'unknown')
    print(f"\n✅ ORDER PLACED! ID: {order_id}")
    print(f"\nWaiting 3 minutes before selling...")
    
    # Wait 3 minutes
    for i in range(180, 0, -30):
        print(f"  {i}s remaining...")
        time.sleep(30)
    
    # Sell (cancel order or place sell)
    print("Cancelling order...")
    cancel_resp = engine.cancel_order(order_id)
    print(f"Cancel result: {cancel_resp}")
else:
    print(f"\n❌ ORDER FAILED: {resp}")

print("\n" + "=" * 50)
print("TEST COMPLETE")
print("=" * 50)
