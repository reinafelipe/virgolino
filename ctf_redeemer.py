"""
Polymarket CTF Redeem Script
Calls redeemPositions on the Conditional Tokens Framework contract.
"""
from web3 import Web3
import config
import logging

logger = logging.getLogger(__name__)

# Polymarket CTF Contract on Polygon
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC on Polygon

# Minimal ABI for redeemPositions
CTF_ABI = [
    {
        "inputs": [
            {"internalType": "contract IERC20", "name": "collateralToken", "type": "address"},
            {"internalType": "bytes32", "name": "parentCollectionId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "conditionId", "type": "bytes32"},
            {"internalType": "uint256[]", "name": "indexSets", "type": "uint256[]"}
        ],
        "name": "redeemPositions",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "conditionId", "type": "bytes32"}
        ],
        "name": "payoutDenominator",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class CTFRedeemer:
    def __init__(self):
        # Use multiple RPC options for reliability
        rpc_urls = [
            "https://polygon.llamarpc.com",
            "https://polygon-bor-rpc.publicnode.com",
            "https://polygon-rpc.com"
        ]
        
        self.w3 = None
        for rpc in rpc_urls:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))
                if w3.is_connected():
                    self.w3 = w3
                    logger.info(f"Connected to RPC: {rpc}")
                    break
            except:
                continue
        
        if not self.w3:
            raise ConnectionError("Failed to connect to any Polygon RPC")
        
        self.account = self.w3.eth.account.from_key(config.PRIVATE_KEY)
        self.ctf = self.w3.eth.contract(
            address=Web3.to_checksum_address(CTF_ADDRESS),
            abi=CTF_ABI
        )
        logger.info(f"CTFRedeemer initialized for address: {self.account.address}")


    def is_condition_resolved(self, condition_id: str) -> bool:
        """Check if a condition has been resolved (payout denominator > 0)."""
        try:
            condition_bytes = bytes.fromhex(condition_id.replace("0x", ""))
            payout_denom = self.ctf.functions.payoutDenominator(condition_bytes).call()
            return payout_denom > 0
        except Exception as e:
            logger.error(f"Error checking condition: {e}")
            return False

    def redeem(self, condition_id: str) -> dict:
        """
        Redeem winning positions for a resolved condition.
        
        Args:
            condition_id: The conditionId (bytes32 hex string) of the resolved market
            
        Returns:
            dict with transaction hash or error
        """
        try:
            condition_bytes = bytes.fromhex(condition_id.replace("0x", ""))
            zero_bytes = bytes(32)  # parentCollectionId = 0x0
            
            # Index sets for binary outcomes: [1, 2] covers both Yes and No
            index_sets = [1, 2]
            
            # Build transaction
            tx = self.ctf.functions.redeemPositions(
                Web3.to_checksum_address(USDC_ADDRESS),
                zero_bytes,
                condition_bytes,
                index_sets
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 137  # Polygon
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, config.PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"✅ Redeem TX sent: {tx_hash.hex()}")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                logger.info(f"🎉 Redeem successful! Block: {receipt.blockNumber}")
                return {"success": True, "tx_hash": tx_hash.hex(), "block": receipt.blockNumber}
            else:
                logger.error(f"Redeem failed in block {receipt.blockNumber}")
                return {"success": False, "error": "Transaction reverted"}
                
        except Exception as e:
            logger.error(f"Redeem error: {e}")
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test with a known resolved condition ID
    # You would get this from the market data
    redeemer = CTFRedeemer()
    print(f"Connected to Polygon. Account: {redeemer.account.address}")
