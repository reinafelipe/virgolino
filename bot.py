"""
Polymarket Swing 15min Trading Bot v3.0
Features:
- Price Divergence (Spot vs Polymarket Odds)
- RSI Extremes + Bollinger Bands confirmation
- Time-based entry windows (Minutes 2-12)
- Strict money management ($5 stake, 30% TP)
"""
from market_scanner import MarketScanner
from risk_manager import RiskManager
import time
import logging
import signal
import sys
import os
import config
from execution import ExecutionEngine
from strategy import SwingStrategy
import pandas as pd
import requests
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PolymarketBot")

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    logger.info("Stopping bot...")
    running = False

signal.signal(signal.SIGINT, signal_handler)


def fetch_price_history(symbol: str) -> pd.DataFrame:
    """Fetch 5m candles from Binance."""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "5m",
        "limit": 50
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if not isinstance(data, list):
            logger.error(f"Binance API error for {symbol}: {data}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        return df
    except Exception as e:
        logger.error(f"Failed to fetch {symbol} prices: {e}")
        return pd.DataFrame()


def get_polymarket_odds(client, token_id: str) -> float:
    """
    Get current odds (best ask price) for a Polymarket token.
    Returns value between 0.0 and 1.0.
    """
    try:
        book = client.get_order_book(token_id)
        if hasattr(book, 'asks') and book.asks:
            return float(book.asks[0].price)
        elif isinstance(book, dict) and 'asks' in book and book['asks']:
            return float(book['asks'][0]['price'])
        return 0.50  # Default neutral
    except Exception as e:
        logger.warning(f"Failed to get odds: {e}")
        return 0.50


def get_minutes_to_expiry(market: dict) -> int:
    """
    Calculate minutes remaining until market expiry.
    """
    try:
        end_date = market.get('end_date')
        if not end_date:
            return 15  # Default
        
        now = datetime.now(timezone.utc)
        diff = end_date - now
        return max(0, int(diff.total_seconds() / 60))
    except:
        return 15


def is_in_entry_window(minutes_remaining: int) -> bool:
    """Check if we are in the valid entry window."""
    min_remaining = 15 - config.ENTRY_WINDOW_END_MIN
    max_remaining = 15 - config.ENTRY_WINDOW_START_MIN
    return min_remaining <= minutes_remaining <= max_remaining

def check_daily_maintenance(engine: ExecutionEngine):
    """
    Regenerate API keys daily at dawn (Portugal time 4:00-4:15 AM).
    """
    if not engine:
        return
        
    now = datetime.now()
    # Check if hour is 4 AM and minute < 15
    if now.hour == 4 and now.minute < 15:
        # Check if we already did it today (use a flag or a file)
        flag_file = ".maintenance_done"
        today = now.strftime("%Y-%m-%d")
        
        try:
            if os.path.exists(flag_file):
                with open(flag_file, "r") as f:
                    if f.read().strip() == today:
                        return
                        
            logger.info("DAWN MAINTENANCE: Refreshing API credentials...")
            success = engine.refresh_credentials()
            if success:
                logger.info("Maintenance complete. Keys refreshed.")
                with open(flag_file, "w") as f:
                    f.write(today)
            else:
                logger.error("Maintenance failed to refresh keys.")
        except Exception as e:
            logger.error(f"Maintenance error: {e}")


def main():
    global running
    
    logger.info("=" * 60)
    logger.info("    POLYMARKET SWING BOT v4.0 (BTC+ETH)")
    logger.info("=" * 60)
    logger.info(f"Assets: {list(config.ASSETS.keys())}")
    logger.info(f"Capital: ${config.INITIAL_CAPITAL:.2f}")
    position_pct = getattr(config, 'POSITION_SIZE_PCT', 0.05) * 100
    max_exposure_pct = getattr(config, 'MAX_TOTAL_EXPOSURE_PCT', 0.10) * 100
    logger.info(f"Position Size: {position_pct:.0f}% per trade (${config.INITIAL_CAPITAL * position_pct/100:.2f})")
    logger.info(f"Max Exposure: {max_exposure_pct:.0f}% total (2 positions)")
    logger.info(f"Entry Window: Minutes {config.ENTRY_WINDOW_START_MIN}-{config.ENTRY_WINDOW_END_MIN}")
    logger.info("=" * 60)

    
    # Initialize components
    try:
        engine = ExecutionEngine()
    except Exception as e:
        logger.error(f"Failed to initialize execution engine: {e}")
        engine = None
    
    scanner = MarketScanner()
    risk_manager = RiskManager()
    
    # Create per-asset strategies
    strategies = {asset: SwingStrategy(asset) for asset in config.ASSETS.keys()}
    
    cycle_count = 0
    
    while running:
        # 0. Daily Maintenance
        check_daily_maintenance(engine)
        
        cycle_count += 1
        logger.info(f"\n{'='*40}")
        logger.info(f"CYCLE {cycle_count}")
        logger.info(f"{'='*40}")
        
        # 0.5 Update balance and cleanup
        try:
            if engine:
                current_bal = engine.get_balance()
                risk_manager.cleanup_expired_positions(current_bal)
                
                # Monitor all positions for TP and Technical SL
                if risk_manager.active_positions:
                    exit_signals = risk_manager.monitor_all_positions(engine)
                    
                    for pos in exit_signals:
                        reason = pos.get('exit_reason', 'UNKNOWN')
                        logger.info(f"[{pos['asset']}] EXIT SIGNAL: {reason}")
                        
                        result = risk_manager.execute_exit(engine, pos)
                        if result.get('success'):
                            pnl = result.get('pnl', 0)
                            logger.info(f"[{pos['asset']}] EXIT COMPLETE | P&L: ${pnl:+.2f}")
                        else:
                            logger.error(f"[{pos['asset']}] EXIT FAILED: {result.get('error')}")

            else:
                risk_manager.cleanup_expired_positions()
        except Exception as e:
            logger.error(f"Cleanup/TP error: {e}")
        
        # Log risk status
        status = risk_manager.get_status()
        current_stake = risk_manager.get_dynamic_stake()
        logger.info(f"Capital: ${risk_manager.current_capital:.2f} | Stake: ${current_stake:.0f} | Positions: {status['active_positions']}/{config.MAX_POSITIONS}")
        
        # Scan all markets
        try:
            all_markets = scanner.get_all_asset_markets()
        except Exception as e:
            logger.error(f"Scanner error: {e}")
            time.sleep(30)
            continue
        
        # Process each asset
        for asset, asset_config in config.ASSETS.items():
            if not running:
                break
            
            # 1. Check if market exists
            markets = all_markets.get(asset, [])
            if not markets:
                logger.debug(f"[{asset}] No market available")
                continue
            
            target_market = markets[0]
            
            # 2. Check time window
            minutes_remaining = get_minutes_to_expiry(target_market)
            
            if not is_in_entry_window(minutes_remaining):
                logger.debug(f"[{asset}] Outside entry window ({minutes_remaining} mins left)")
                continue
            
            logger.info(f"[{asset}] {minutes_remaining} mins to expiry - IN WINDOW")
            
            # 3. Fetch price data
            symbol = asset_config['binance_symbol']
            history = fetch_price_history(symbol)
            
            if history.empty:
                logger.warning(f"[{asset}] No price data available")
                continue
            
            # 4. Get Polymarket odds for divergence calculation
            token_ids = target_market.get('clob_token_ids', [])
            outcomes = target_market.get('outcomes', [])
            
            up_odds = 0.50
            if engine and token_ids:
                # Token 0 is usually "Up"
                up_odds = get_polymarket_odds(engine.client, token_ids[0])
                logger.debug(f"[{asset}] Polymarket UP odds: {up_odds:.2f}")
            
            # 5. Generate signal
            strategy = strategies[asset]
            result = strategy.analyze_market(history, polymarket_up_odds=up_odds)
            signal = result['signal']
            
            if signal == 'NEUTRAL':
                continue
            
            logger.info(f"[{asset}] SIGNAL: {signal} | RSI={result['rsi']:.1f} | Div={result['divergence']:.1f}%")
            
            # 6. Get dynamic stake and check risk
            position_size = risk_manager.get_dynamic_stake()
            if not risk_manager.can_open_position(position_size, asset):
                logger.warning(f"[{asset}] Risk manager blocked trade")
                continue
            
            # 7. Check liquidity
            if engine:
                # Determine correct token based on signal
                token_index = 0 if signal == 'UP' else 1
                
                if len(token_ids) <= token_index:
                    logger.error(f"[{asset}] Invalid token index")
                    continue
                
                token_id = token_ids[token_index]
                min_liquidity = asset_config['min_liquidity_usd']
                
                if not scanner.check_orderbook_liquidity(engine.client, token_id, min_liquidity):
                    logger.warning(f"[{asset}] Insufficient liquidity (min: ${min_liquidity})")
                    continue
                
                # 8. Get best price
                try:
                    book = engine.client.get_order_book(token_id)
                    best_ask = 0.99
                    
                    if hasattr(book, 'asks') and book.asks:
                        best_ask = float(book.asks[0].price)
                    elif isinstance(book, dict) and 'asks' in book and book['asks']:
                        best_ask = float(book['asks'][0]['price'])
                    else:
                        logger.warning(f"[{asset}] No asks, using fallback price")
                        best_ask = 0.50
                    
                    # 9. Calculate size
                    size_shares = round(position_size / best_ask, 2)
                    estimated_cost = size_shares * best_ask
                    
                    logger.info(f"[{asset}] EXECUTING: {signal} {size_shares} shares @ ${best_ask:.3f} (Est: ${estimated_cost:.2f})")
                    logger.info(f"[{asset}] MARKET: {target_market.get('question')}")
                    
                    # 10. Place order
                    resp = engine.place_order(
                        token_id=token_id,
                        side='BUY',
                        price=best_ask,
                        size=size_shares
                    )
                    
                    if resp and resp.get('success'):
                        order_id = resp.get('orderID', 'unknown')
                        logger.info(f"[{asset}] ORDER PLACED: {order_id}")
                        
                        # Get current spot price for reference
                        current_spot = history['close'].iloc[-1] if not history.empty else 0
                        
                        # For DOWN bets, resistance is the key level (price going above invalidates)
                        # For UP bets, support is the key level (price going below invalidates)
                        support_level = result['support'] if signal == 'UP' else None
                        resistance_level = result['resistance'] if signal == 'DOWN' else None
                        
                        risk_manager.record_position(
                            asset=asset,
                            side=signal,
                            size=estimated_cost,
                            token_id=token_id,
                            order_id=order_id,
                            entry_price=best_ask,
                            expiry=target_market.get('end_date').timestamp() if target_market.get('end_date') else None,
                            condition_id=target_market.get('condition_id'),
                            support_level=support_level,
                            resistance_level=resistance_level,
                            shares=size_shares,
                            binance_symbol=asset_config['binance_symbol'],
                            spot_price_at_entry=current_spot
                        )
                        
                        # Log the key level for monitoring
                        if signal == 'DOWN':
                            logger.info(f"[{asset}] TECH SL SET: Exit if price > ${resistance_level:.0f}")
                        else:
                            logger.info(f"[{asset}] TECH SL SET: Exit if price < ${support_level:.0f}")


                    else:
                        logger.error(f"[{asset}] Order failed: {resp}")
                        
                except Exception as e:
                    logger.error(f"[{asset}] Trade error: {e}")
            else:
                logger.warning("Execution engine unavailable")
        
        # Sleep between cycles - shorter when monitoring active positions
        if running:
            if risk_manager.active_positions:
                # Active positions: check every 15 seconds for faster TP/SL reaction
                logger.info(f"Monitoring {len(risk_manager.active_positions)} position(s)... [15s cycle]")
                time.sleep(15)
            else:
                # No positions: normal 60 second cycle
                logger.info("Sleeping 60s...")
                time.sleep(60)

    
    logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
