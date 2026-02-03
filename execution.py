from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, ApiCreds
from py_clob_client.constants import POLYGON
import config
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ExecutionEngine:
    def __init__(self):
        self.host = config.HOST
        self.chain_id = config.CHAIN_ID
        self.client = self._connect()

    def refresh_credentials(self) -> bool:
        """Derive fresh API keys and update the .env file."""
        try:
            logger.info("Regenerating API credentials from blockchain...")
            temp_client = ClobClient(
                host=self.host,
                key=config.PRIVATE_KEY,
                chain_id=self.chain_id,
                signature_type=2,
                funder=config.PROFILE_ADDRESS
            )
            creds = temp_client.create_or_derive_api_creds()
            
            # Update .env file manually to ensure persistence
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            if os.path.exists(env_path):
                lines = []
                with open(env_path, 'r') as f:
                    for line in f:
                        if any(x in line for x in ["POLYMARKET_API_KEY", "POLYMARKET_SECRET", "POLYMARKET_PASSPHRASE"]):
                            continue
                        lines.append(line)
                
                lines.append(f"POLYMARKET_API_KEY={creds.api_key}\n")
                lines.append(f"POLYMARKET_SECRET={creds.api_secret}\n")
                lines.append(f"POLYMARKET_PASSPHRASE={creds.api_passphrase}\n")
                
                with open(env_path, 'w') as f:
                    f.writelines(lines)
                
                # Update current config in memory
                config.API_KEY = creds.api_key
                config.API_SECRET = creds.api_secret
                config.API_PASSPHRASE = creds.api_passphrase
                
                logger.info("Successfully updated .env with fresh keys.")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return False

    def _connect(self) -> ClobClient:
        if not config.PRIVATE_KEY:
            raise ValueError("Missing PRIVATE_KEY")
        
        try:
             client = ClobClient(
                host=self.host,
                key=config.PRIVATE_KEY, 
                chain_id=self.chain_id,
                signature_type=2,
                funder=config.PROFILE_ADDRESS
            )
             
             if config.API_KEY and config.API_SECRET and config.API_PASSPHRASE:
                 from py_clob_client.clob_types import ApiCreds
                 creds = ApiCreds(
                     api_key=config.API_KEY,
                     api_secret=config.API_SECRET,
                     api_passphrase=config.API_PASSPHRASE
                 )
                 client.set_api_creds(creds)
                 logger.info("Connected with existing credentials")
             else:
                 self.refresh_credentials()
                 from py_clob_client.clob_types import ApiCreds
                 creds = ApiCreds(
                     api_key=config.API_KEY,
                     api_secret=config.API_SECRET,
                     api_passphrase=config.API_PASSPHRASE
                 )
                 client.set_api_creds(creds)
             
             return client
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def get_balance(self) -> float:
        """Get the USDC (collateral) balance."""
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
        try:
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            resp = self.client.get_balance_allowance(params)
            raw_balance = float(resp.get("balance", 0))
            return raw_balance / 1_000_000.0  # Normalized USDC
        except Exception as e:
            logger.error(f"Error getting USDC balance: {e}")
            return 0.0

    def get_token_balance(self, token_id: str) -> float:
        """Get the share balance for a specific token ID (scaled from raw units)."""
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
        try:
            params = BalanceAllowanceParams(
                asset_type=AssetType.CONDITIONAL,
                token_id=token_id
            )
            resp = self.client.get_balance_allowance(params)
            raw_balance = float(resp.get("balance", 0))
            return raw_balance / 1_000_000.0 # Polymarket tokens usually have 6 decimals
        except Exception as e:
            logger.error(f"Error getting token balance for {token_id}: {e}")
            return 0.0

    def liquidate_token(self, token_id: str):
        """Fetch current balance and sell everything at best bid."""
        balance = self.get_token_balance(token_id)
        if balance > 0:
            logger.info(f"Liquidating total position: {balance} shares for {token_id}")
            # Get best bid
            try:
                book = self.client.get_order_book(token_id)
                price = float(book.bids[0].price) if hasattr(book, 'bids') and book.bids else 0.01
                return self.place_order(token_id, 'SELL', price, balance)
            except Exception as e:
                logger.error(f"Liquidation error: {e}")
                return None
        return {"success": True, "message": "No balance to liquidate"}

    def place_order(self, token_id: str, side: str, price: float, size: float):
        """
        Place a limit order.
        side: 'BUY' or 'SELL'
        price: 0.0 to 1.0
        size: Amount of shares
        """
        order_args = OrderArgs(
            price=price,
            size=size,
            side=side.upper(), # 'BUY' or 'SELL'
            token_id=token_id,
        )
        try:
            # 1. Sign Order
            signed_order = self.client.create_order(order_args)
            # 2. Post Order
            from py_clob_client.clob_types import OrderType
            resp = self.client.post_order(signed_order, OrderType.GTC)
            logger.info(f"Order placed: {resp}")
            return resp
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None

    def cancel_all(self):
        try:
            self.client.cancel_all()
            logger.info("Cancelled all orders")
        except Exception as e:
            logger.error(f"Failed to cancel orders: {e}")

    def redeem_winning_position(self, token_id: str) -> dict:
        """
        Redeem a winning position by selling at 0.99 price.
        Polymarket doesn't have a direct redeem API, so we sell winning tokens
        at near-$1 price to effectively cash out.
        """
        try:
            balance = self.get_token_balance(token_id)
            if balance <= 0:
                logger.info(f"No balance to redeem for token {token_id[:15]}...")
                return {"success": True, "message": "No balance"}
            
            logger.info(f"🎰 REDEEMING {balance:.4f} winning shares for token {token_id[:15]}...")
            
            # Sell at 0.99 to cash out winning position
            # Winning tokens are worth $1, so selling at 0.99 nets us ~99% of value
            result = self.place_order(
                token_id=token_id,
                side='SELL',
                price=0.99,
                size=balance
            )
            
            if result and result.get('success'):
                payout = balance * 0.99
                logger.info(f"✅ REDEEMED: {balance:.4f} shares → ${payout:.2f} USDC")
                return {"success": True, "payout": payout, "shares": balance}
            else:
                logger.warning(f"Redeem order failed: {result}")
                return {"success": False, "error": str(result)}
                
        except Exception as e:
            logger.error(f"Redeem error for {token_id[:15]}...: {e}")
            return {"success": False, "error": str(e)}

    def check_and_redeem_all(self, token_ids: list) -> float:
        """
        Check multiple token IDs and redeem any with positive balance.
        Returns total USDC recovered.
        """
        total_redeemed = 0.0
        for token_id in token_ids:
            result = self.redeem_winning_position(token_id)
            if result.get('success') and result.get('payout'):
                total_redeemed += result['payout']
        return total_redeemed
