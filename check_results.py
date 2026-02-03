
import logging
import config
from execution import ExecutionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckResults")

def check():
    engine = ExecutionEngine()
    
    # 1. Check Collateral Balance
    balance = engine.get_balance()
    logger.info(f"Current USDC Balance: {balance / 1_000_000.0} USDC")
    
    # 2. Check for open positions (Conditional tokens)
    # Corrected tokens from logs:
    tokens = [
        "115062078834792977196234233499044140051435680046218547053338733949526603829278", # BTC UP (Matched at 18:51)
        "6216218870820960832802976905328390814644286354075345823560778720716379009475",  # ETH UP (Matched at 18:51)
    ]
    
    for token in tokens:
        bal = engine.get_token_balance(token)
        logger.info(f"Token {token[:10]}... Balance: {bal} shares")
        
    # 3. Check for any pending orders
    try:
        orders = engine.client.get_orders()
        logger.info(f"Open Orders: {len(orders)}")
    except Exception as e:
        logger.error(f"Error getting orders: {e}")

if __name__ == "__main__":
    check()
