from py_clob_client.client import ClobClient
import config
import logging

logging.basicConfig(level=logging.INFO)

def check_allowance():
    if not config.PRIVATE_KEY:
        print("Missing PRIVATE KEY")
        return

    try:
        client = ClobClient(
            host=config.HOST,
            key=config.PRIVATE_KEY,
            chain_id=config.CHAIN_ID,
            signature_type=0
        )
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        print("Connected with Derived Creds.")
        
        # Check Balance & Allowance
        # Note: methods might be get_balance_allowance(params) or just ()
        # Let's try default
        print("Fetching Balance/Allowance...")
        res = client.get_balance_allowance()
        print(f"Result: {res}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_allowance()
