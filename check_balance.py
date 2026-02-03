from execution import ExecutionEngine
import logging
import sys
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckBalance")

def check():
    logger.info("Initializing Engine...")
    try:
        engine = ExecutionEngine()
    except Exception as e:
        logger.error(f"Failed to init engine: {e}")
        return

    logger.info("Fetching Balance/Allowance...")
    
    # 1. Derive EOA Address
    from eth_account import Account
    try:
        acct = Account.from_key(config.PRIVATE_KEY)
        print(f"Derived EOA Address (from Private Key): {acct.address}")
        print(f"Configured Profile Address: {config.PROFILE_ADDRESS}")
    except Exception as e:
        print(f"Could not derive address: {e}")

    # 2. Try different auth combinations
    from py_clob_client.client import ClobClient, BalanceAllowanceParams
    
    combinations = [
        {"sig": 0, "desc": "EOA (MetaMask Standard)"},
        {"sig": 1, "desc": "Proxy (Email/Magic/PolyProxy)"},
        {"sig": 2, "desc": "Proxy (Browser/Other)"}
    ]

    for combo in combinations:
        print(f"\n--- Testing {combo['desc']} (sig={combo['sig']}) ---")
        try:
            client = ClobClient(
                host=config.HOST,
                key=config.PRIVATE_KEY,
                chain_id=config.CHAIN_ID,
                signature_type=combo['sig'],
                funder=config.PROFILE_ADDRESS # Always verify against the funds holder
            )
            # Create creds for this specific client config? 
            # Actually creds are derived from key, but client struct matters.
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)
            
            res = client.get_balance_allowance(
                params=BalanceAllowanceParams(asset_type="COLLATERAL")
            )
            print(f"Result: {res}")
        except Exception as e:
            print(f"Failed: {e}")
            
    print(f"----------------------\n")

if __name__ == "__main__":
    check()
