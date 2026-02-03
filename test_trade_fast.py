"""
ULTRA FAST TRADE TEST - Fixed Token ID
"""
import time
import os
from execution import ExecutionEngine

# OID identified manually for February 3, 11:30AM-11:45AM ET
# Question: Will Bitcoin be above $103,425.00 at 11:45 AM ET? (Estimated)
TOKEN_ID = "80506317619154789432898952636733921268652574960586338310715806607014130182964"

print("=" * 50)
print("ULTRA FAST TRADE TEST")
print("=" * 50)

start_time = time.time()

# 1. Initialize
print(f"[{time.time()-start_time:.2f}s] Connecting...", end=" ", flush=True)
engine = ExecutionEngine()
print(f"Done")

# 2. Get orderbook
print(f"[{time.time()-start_time:.2f}s] Getting best price...", end=" ", flush=True)
book = engine.client.get_order_book(TOKEN_ID)
if hasattr(book, 'asks') and book.asks:
    best_ask = float(book.asks[0].price)
else:
    best_ask = 0.50
print(f"Done (${best_ask:.3f})")

# 3. Buy $1 worth (approx 1 share if price is ~0.50)
# Minimum 1 share required by Polymarket CLOB normally
size = 2.0 
print(f"[{time.time()-start_time:.2f}s] Placing order: BUY {size} YES @ ${best_ask:.3f}...", end=" ", flush=True)

resp = engine.place_order(
    token_id=TOKEN_ID,
    side='BUY',
    price=best_ask,
    size=size
)

if resp and resp.get('success'):
    order_id = resp.get('orderID', 'unknown')
    print(f"\n\n✅ SUCCESS! Order placed in {time.time()-start_time:.1f} seconds.")
    print(f"Order ID: {order_id}")
    print("\nVerifique seu dashboard no Polymarket agora!")
    
    print(f"\nWaiting 3 minutes before selling...")
    time.sleep(180)
    
    print("\nSelling/Cancelling...")
    # In a limit order context, if it didn't fill yet, we cancel. 
    # If it filled, we'd need to sell. For a test, a cancel or a 1-cent sell is enough.
    cancel_resp = engine.client.cancel_order(order_id)
    print(f"Result: {cancel_resp}")
else:
    print(f"\n\n❌ FAILED: {resp}")

print("\n" + "=" * 50)
