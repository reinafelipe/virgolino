import logging
import config

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Portfolio-level risk management.
    Tracks active positions and enforces capital protection rules.
    """
    
    def __init__(self):
        self.initial_capital = config.INITIAL_CAPITAL
        self.current_capital = config.INITIAL_CAPITAL  # Track live balance
        self.max_positions = config.MAX_POSITIONS
        self.stop_loss_pct = config.STOP_LOSS_PCT
        self.take_profit_pct = getattr(config, 'TAKE_PROFIT_PCT', 0.30)
        
        # Dynamic stake params
        self.stake_divisor = getattr(config, 'STAKE_DIVISOR', 20)
        self.min_stake = getattr(config, 'MIN_STAKE', 5.0)
        self.max_stake = getattr(config, 'MAX_STAKE', 50.0)
        
        self.active_positions = []
        self.total_pnl = 0.0
        
        logger.info(f"RiskManager: Capital=${self.current_capital}, Initial=${self.initial_capital}, Dynamic Stake (${self.min_stake}-${self.max_stake})")
    
    def get_dynamic_stake(self) -> float:
        """Calculate stake based on current portfolio value."""
        import math
        stake = math.floor(self.current_capital / self.stake_divisor)
        return max(self.min_stake, min(stake, self.max_stake))
    
    def update_capital(self, pnl: float):
        """Update capital after trade result."""
        self.current_capital += pnl
        self.total_pnl += pnl
        logger.info(f"Capital updated: ${self.current_capital:.2f} (PnL: ${pnl:+.2f})")
    
    def get_current_exposure(self):
        """Total USD currently at risk."""
        return sum(p.get('size', 0) for p in self.active_positions)
    
    def can_open_position(self, amount: float, asset: str) -> bool:
        """Check if we can open a new position."""
        # Check position count
        if len(self.active_positions) >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached. Cannot open.")
            return False
        
        # Check position size (use dynamic stake as max)
        max_allowed = self.get_dynamic_stake() * 1.5  # 50% buffer
        if amount > max_allowed:
            logger.warning(f"Position size ${amount} exceeds dynamic max ${max_allowed:.0f}.")
            return False
        
        # Check total exposure against capital
        current_exposure = self.get_current_exposure()
        max_exposure = self.current_capital * 0.5  # Max 50% of capital in positions
        if current_exposure + amount > max_exposure:
            logger.warning(f"Exposure would exceed 50% of capital. Current: ${current_exposure}, Adding: ${amount}")
            return False
        
        # Check if already holding this asset
        for p in self.active_positions:
            if p.get('asset') == asset:
                logger.warning(f"Already holding position in {asset}. Skipping.")
                return False
        
        return True
    
    def record_position(self, asset: str, side: str, size: float, token_id: str, order_id: str, entry_price: float, expiry: float = None):
        """Record a new position."""
        position = {
            'asset': asset,
            'side': side,
            'size': size,
            'token_id': token_id,
            'order_id': order_id,
            'entry_price': entry_price,
            'expiry': expiry or (time.time() + 900)  # Default 15 mins
        }
        self.active_positions.append(position)
        logger.info(f"Position recorded: {asset} {side} ${size} @ ${entry_price:.3f} (Expires: {datetime.fromtimestamp(position['expiry']).strftime('%H:%M:%S') if position['expiry'] else 'N/A'})")

    def get_take_profit_signals(self, engine) -> list:
        """
        Check all active positions for 30% profit.
        Returns list of (token_id, size, asset) to sell.
        """
        signals = []
        for p in self.active_positions:
            token_id = p['token_id']
            entry_price = p['entry_price']
            
            try:
                # Use engine to get current price (best bid if selling)
                book = engine.client.get_order_book(token_id)
                current_price = 0.0
                if hasattr(book, 'bids') and book.bids:
                    current_price = float(book.bids[0].price)
                
                if current_price > 0:
                    profit_pct = (current_price - entry_price) / entry_price
                    if profit_pct >= self.take_profit_pct:
                        logger.info(f"🔥 TAKE PROFIT TRIGGERED for {p['asset']}: {profit_pct*100:.1f}% gain!")
                        signals.append(p)
            except Exception as e:
                logger.debug(f"Could not check TP for {token_id}: {e}")
                
        return signals

    def cleanup_expired_positions(self, current_usdc_balance: float = None):
        """
        Remove positions that have passed their expiry time.
        If current_usdc_balance is provided, update internal capital tracking.
        """
        import time
        now = time.time()
        initial_count = len(self.active_positions)
        
        # Keep only positions that haven't expired or are still within a small buffer (5 mins)
        # We give a buffer to allow for resolution/cleanup
        self.active_positions = [p for p in self.active_positions if p.get('expiry', 0) > (now - 300)]
        
        removed = initial_count - len(self.active_positions)
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired positions from memory.")
            
        if current_usdc_balance is not None:
            # Sync internal capital with actual wallet balance
            self.current_capital = current_usdc_balance
            logger.info(f"RiskManager capital synced to actual balance: ${self.current_capital:.2f}")
    
    def check_stop_loss(self, current_balance: float) -> bool:
        """Check if we should stop trading due to losses."""
        loss = self.initial_capital - current_balance
        max_loss = self.initial_capital * self.stop_loss_pct
        
        if loss >= max_loss:
            logger.critical(f"STOP LOSS TRIGGERED! Loss: ${loss:.2f} >= Max: ${max_loss:.2f}")
            return True
        return False
    
    def get_status(self) -> dict:
        """Return current risk status."""
        return {
            'active_positions': len(self.active_positions),
            'current_exposure': self.get_current_exposure(),
            'current_capital': self.current_capital,
            'positions': self.active_positions
        }
