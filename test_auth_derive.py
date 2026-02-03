from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
import config
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAuthDerive")

def test():
    print("Testing Auth with Derived Credentials (MetaMask/EOA Flow)...")
    if not config.PRIVATE_KEY:
        print("ERROR: PRIVATE_KEY is missing from .env")
        return

    try:
        # According to docs: "signature_type=0 (default): Standard EOA ... includes MetaMask"
        HOST = "https://clob.polymarket.com"
        CHAIN_ID = 137
        
        # Initialize client with just the key and signature_type=0 (EOA)
        client = ClobClient(
            host=HOST,
            key=config.PRIVATE_KEY,
            chain_id=CHAIN_ID,
            signature_type=0
        )
        
        print("Client initialized. Checking methods for allowances...")
        # Inspect signature
        import inspect
        print(f"Signature: {inspect.signature(client.update_balance_allowance)}")
        print(f"Doc: {client.update_balance_allowance.__doc__}")

        
        print("Client initialized. Attempting to derive API creds...")
        creds = client.create_or_derive_api_creds()
        print(f"Derived Creds: API Key={creds.api_key}")
        
        client.set_api_creds(creds)
        
        print("Credentials set. Testing authenticated call (get_trades)...")
        trades = client.get_trades()
        print(f"Success! Fetched {len(trades)} trades.")
        
    except Exception as e:
        print(f"Auth Method 0 Failed: {e}")
        print("Trying Signature Type 1...")
        try:
             client = ClobClient(
                host=HOST,
                key=config.PRIVATE_KEY,
                chain_id=CHAIN_ID,
                signature_type=1
            )
             creds = client.create_or_derive_api_creds()
             client.set_api_creds(creds)
             trades = client.get_trades()
             print(f"Success with Type 1! Fetched {len(trades)} trades.")
        except Exception as e2:
            print(f"Auth Method 1 Failed: {e2}")

if __name__ == "__main__":
    test()
