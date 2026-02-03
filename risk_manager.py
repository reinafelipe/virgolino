import logging
import config
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Portfolio-level risk management.
    Tracks active positions and enforces capital protection rules.
    
    Position Sizing:
    - Each position = 5% of current cash
    - Max total exposure = 10% (2 positions)
    """
    
    def __init__(self):
        self.initial_capital = config.INITIAL_CAPITAL
        self.current_capital = config.INITIAL_CAPITAL  # Track live balance
        self.max_positions = config.MAX_POSITIONS
        self.stop_loss_pct = config.STOP_LOSS_PCT
        self.take_profit_pct = getattr(config, 'TAKE_PROFIT_PCT', 0.30)
        
        # Percentage-based position sizing
        self.position_size_pct = getattr(config, 'POSITION_SIZE_PCT', 0.05)  # 5% per position
        self.max_total_exposure_pct = getattr(config, 'MAX_TOTAL_EXPOSURE_PCT', 0.10)  # 10% max
        self.min_stake = getattr(config, 'MIN_STAKE', 1.0)
        
        self.active_positions = []
        self.total_pnl = 0.0
        
        logger.info(f"RiskManager: Capital=${self.current_capital}, Position Size={self.position_size_pct*100:.0f}% (${self.current_capital * self.position_size_pct:.2f})")
    
    def get_position_size(self) -> float:
        """
        Calculate position size as 5% of current cash.
        Returns the USD amount to bet.
        """
        size = self.current_capital * self.position_size_pct
        return max(self.min_stake, size)
    
    def get_dynamic_stake(self) -> float:
        """Alias for get_position_size for backward compatibility."""
        return self.get_position_size()

    
    def update_capital(self, pnl: float):
        """Update capital after trade result."""
        self.current_capital += pnl
        self.total_pnl += pnl
        logger.info(f"Capital updated: ${self.current_capital:.2f} (PnL: ${pnl:+.2f})")
    
    def get_current_exposure(self):
        """Total USD currently at risk."""
        return sum(p.get('size', 0) for p in self.active_positions)
    
    def can_open_position(self, amount: float, asset: str) -> bool:
        """
        Check if we can open a new position.
        
        Rules:
        - Max 2 positions (1 BTC, 1 ETH)
        - Max 10% total exposure
        - No duplicate assets
        """
        # Check position count
        if len(self.active_positions) >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached. Cannot open.")
            return False
        
        # Check total exposure against 10% limit
        current_exposure = self.get_current_exposure()
        max_exposure = self.current_capital * self.max_total_exposure_pct
        
        if current_exposure + amount > max_exposure:
            logger.warning(f"Exposure would exceed {self.max_total_exposure_pct*100:.0f}% limit. Current: ${current_exposure:.2f}, Adding: ${amount:.2f}, Max: ${max_exposure:.2f}")
            return False
        
        # Check if already holding this asset
        for p in self.active_positions:
            if p.get('asset') == asset:
                logger.warning(f"Already holding position in {asset}. Skipping.")
                return False
        
        return True

    
    def record_position(self, asset: str, side: str, size: float, token_id: str, order_id: str, 
                         entry_price: float, expiry: float = None, condition_id: str = None,
                         support_level: float = None, resistance_level: float = None,
                         shares: float = None, binance_symbol: str = None, spot_price_at_entry: float = None):
        """
        Record a new position with full context for TP/SL monitoring.
        
        Args:
            support_level: Price level that would invalidate a DOWN bet
            resistance_level: Price level that would invalidate an UP bet
            shares: Number of shares bought
            binance_symbol: Symbol for monitoring spot price (e.g., 'BTCUSDT')
            spot_price_at_entry: Spot price at time of entry
        """
        position = {
            'asset': asset,
            'side': side,
            'size': size,  # USD cost
            'shares': shares or (size / entry_price if entry_price > 0 else 0),
            'token_id': token_id,
            'order_id': order_id,
            'entry_price': entry_price,
            'condition_id': condition_id,
            'expiry': expiry or (time.time() + 900),
            'support_level': support_level,
            'resistance_level': resistance_level,
            'binance_symbol': binance_symbol or f"{asset}USDT",
            'spot_price_at_entry': spot_price_at_entry,
            'entry_time': time.time()
        }
        self.active_positions.append(position)
        
        # Log with support/resistance info
        sl_info = f"Support: ${support_level:.0f}" if support_level else ""
        rl_info = f"Resistance: ${resistance_level:.0f}" if resistance_level else ""
        level_info = sl_info or rl_info
        
        logger.info(f"Position recorded: {asset} {side} {shares:.2f} shares @ ${entry_price:.3f} | {level_info}")




    def get_take_profit_signals(self, engine) -> list:
        """
        Check all active positions for 30% profit on Polymarket.
        Returns list of positions to sell.
        """
        signals = []
        for p in self.active_positions:
            token_id = p['token_id']
            entry_price = p['entry_price']
            
            try:
                book = engine.client.get_order_book(token_id)
                current_price = 0.0
                if hasattr(book, 'bids') and book.bids:
                    current_price = float(book.bids[0].price)
                
                if current_price > 0:
                    profit_pct = (current_price - entry_price) / entry_price
                    if profit_pct >= self.take_profit_pct:
                        logger.info(f"🔥 TAKE PROFIT TRIGGERED for {p['asset']}: {profit_pct*100:.1f}% gain! (${entry_price:.3f} → ${current_price:.3f})")
                        p['exit_reason'] = 'TAKE_PROFIT'
                        p['current_price'] = current_price
                        signals.append(p)
            except Exception as e:
                logger.debug(f"Could not check TP for {token_id}: {e}")
                
        return signals

    def get_technical_stop_loss_signals(self) -> list:
        """
        Check if underlying asset (BTC/ETH) has broken support/resistance levels.
        This is a TECHNICAL stop loss based on price action, not just % loss.
        
        For DOWN bets: If price breaks ABOVE resistance, our bet is invalidated
        For UP bets: If price breaks BELOW support, our bet is invalidated
        
        Returns list of positions to exit.
        """
        import requests
        signals = []
        
        for p in self.active_positions:
            side = p.get('side', '').upper()
            symbol = p.get('binance_symbol', f"{p['asset']}USDT")
            support = p.get('support_level')
            resistance = p.get('resistance_level')
            
            if not support and not resistance:
                continue
            
            try:
                # Get current spot price from Binance
                r = requests.get('https://api.binance.com/api/v3/ticker/price', 
                                params={'symbol': symbol}, timeout=5)
                current_spot = float(r.json()['price'])
                
                # Check technical invalidation
                if side == 'DOWN' and resistance:
                    # If we bet DOWN and price breaks ABOVE resistance, exit
                    if current_spot > resistance:
                        pct_above = ((current_spot - resistance) / resistance) * 100
                        logger.warning(f"🛑 TECH STOP LOSS: {p['asset']} broke resistance ${resistance:.0f}! Current: ${current_spot:.0f} (+{pct_above:.1f}%)")
                        p['exit_reason'] = 'TECH_SL_RESISTANCE_BREAK'
                        p['spot_at_exit'] = current_spot
                        signals.append(p)
                        
                elif side == 'UP' and support:
                    # If we bet UP and price breaks BELOW support, exit
                    if current_spot < support:
                        pct_below = ((support - current_spot) / support) * 100
                        logger.warning(f"🛑 TECH STOP LOSS: {p['asset']} broke support ${support:.0f}! Current: ${current_spot:.0f} (-{pct_below:.1f}%)")
                        p['exit_reason'] = 'TECH_SL_SUPPORT_BREAK'
                        p['spot_at_exit'] = current_spot
                        signals.append(p)
                        
            except Exception as e:
                logger.debug(f"Could not check tech SL for {p['asset']}: {e}")
        
        return signals

    def monitor_all_positions(self, engine) -> list:
        """
        Main monitoring function that checks all exit conditions:
        1. Take Profit (30% gain on Polymarket odds)
        2. Technical Stop Loss (support/resistance break on spot)
        
        Returns list of positions that should be exited.
        """
        exit_signals = []
        
        # Check Take Profit
        tp_signals = self.get_take_profit_signals(engine)
        exit_signals.extend(tp_signals)
        
        # Check Technical Stop Loss
        sl_signals = self.get_technical_stop_loss_signals()
        # Avoid duplicates
        for sl in sl_signals:
            if sl not in exit_signals:
                exit_signals.append(sl)
        
        return exit_signals

    def execute_exit(self, engine, position: dict) -> dict:
        """
        Execute a position exit (sell all shares at market).
        Returns result of the trade.
        """
        token_id = position['token_id']
        shares = position.get('shares', 0)
        asset = position['asset']
        reason = position.get('exit_reason', 'UNKNOWN')
        
        if shares <= 0:
            return {'success': False, 'error': 'No shares to sell'}
        
        try:
            # Get best bid
            book = engine.client.get_order_book(token_id)
            if not hasattr(book, 'bids') or not book.bids:
                return {'success': False, 'error': 'No bids available'}
            
            best_bid = float(book.bids[0].price)
            
            logger.info(f"💰 EXITING {asset}: Selling {shares:.2f} shares @ ${best_bid:.3f} | Reason: {reason}")
            
            result = engine.place_order(
                token_id=token_id,
                side='SELL',
                price=best_bid,
                size=shares
            )
            
            if result and result.get('success'):
                # Calculate P&L
                entry_price = position.get('entry_price', best_bid)
                pnl = (best_bid - entry_price) * shares
                pnl_pct = ((best_bid - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                
                logger.info(f"✅ EXIT COMPLETE: {asset} | P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
                
                # Remove from active positions
                self.active_positions = [p for p in self.active_positions if p['token_id'] != token_id]
                
                return {'success': True, 'pnl': pnl, 'exit_price': best_bid}
            else:
                return {'success': False, 'error': str(result)}
                
        except Exception as e:
            logger.error(f"Exit error for {asset}: {e}")
            return {'success': False, 'error': str(e)}



    def cleanup_expired_positions(self, current_usdc_balance: float = None):
        """
        Remove positions that have passed their expiry time.
        Attempts CTF redeem for resolved markets.
        If current_usdc_balance is provided, update internal capital tracking.
        """
        import time
        now = time.time()
        initial_count = len(self.active_positions)
        
        # Separate expired from active positions
        expired = [p for p in self.active_positions if p.get('expiry', 0) <= (now - 300)]
        
        # Attempt to redeem expired positions with condition_id
        for p in expired:
            cid = p.get('condition_id')
            if cid:
                try:
                    from ctf_redeemer import CTFRedeemer
                    redeemer = CTFRedeemer()
                    if redeemer.is_condition_resolved(cid):
                        logger.info(f"🎰 Auto-redeeming {p['asset']} position...")
                        result = redeemer.redeem(cid)
                        if result.get('success'):
                            logger.info(f"✅ Auto-redeem successful: {result.get('tx_hash', '')[:20]}...")
                        else:
                            logger.warning(f"Auto-redeem failed: {result.get('error')}")
                except Exception as e:
                    logger.debug(f"Could not auto-redeem {p['asset']}: {e}")
        
        # Keep only positions that haven't expired or are still within a small buffer (5 mins)
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
