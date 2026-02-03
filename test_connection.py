from execution import ExecutionEngine
from py_clob_client.client import ClobClient
import config
import logging

logging.basicConfig(level=logging.INFO)

def test():
    print("Testing connection...")
    try:
        engine = ExecutionEngine()
        print("ClobClient created.")
        
        # Try to fetch balance/collateral
        # Note: get_collateral_balance not always available on all clients directly, 
        # checking if we can get account info.
        # engine.client.get_account_balance() or similar might be needed.
        # Let's try a safe call like get_api_keys or get_notifications if balance fails
        # But commonly we want to check if we can place orders or see balance.
        
        # For now, let's just print that we connected successfully if no error raised in init
        print("Connection successful!")
        
        # Inspect available methods
        # print(dir(engine.client))
        
        try:
            # Try to fetch open orders (requires Auth)
            orders = engine.client.get_orders()
            print(f"Open Orders: {orders}")
        except Exception as e:
            print(f"Could not fetch orders (Auth check): {e}")

    except Exception as e:
        print(f"Connection FAILED: {e}")

    print("\nTesting Public Endpoint (No Auth)...")
    try:
        # Client without creds
        public_client = ClobClient(host=config.HOST, chain_id=config.CHAIN_ID)
        # Fetch a simple market or sampling
        # get_markets arguments might need specific params
        markets = public_client.get_markets(next_cursor="") 
        print(f"Public Market Fetch Success! Found {len(markets['data'])} markets.")
    except Exception as e:
        print(f"Public Market Fetch Failed: {e}")

if __name__ == "__main__":
    test()
