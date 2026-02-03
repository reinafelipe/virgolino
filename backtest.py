import pandas as pd
import requests
import logging
from strategy import SniperStrategy
import config
import math

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Backtest")

def fetch_history(symbol, days=7):
    """Fetch history for N days using pagination (Binance limit 1000 candles)"""
    all_dfs = []
    current_end = None
    
    print(f"Fetching {days} days for {symbol}...", end=" ", flush=True)
    
    for _ in range(10): 
        print(".", end="", flush=True)
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": "5m", "limit": 1000}
        if current_end:
            params['endTime'] = current_end
            
        try:
            r = requests.get(url, params=params, timeout=5)
            data = r.json()
        except:
            break
            
        if not data or not isinstance(data, list): break
        
        oldest_ts = data[0][0]
        current_end = oldest_ts - 1
        
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        all_dfs.append(df)
        
        start_date = pd.to_datetime(oldest_ts, unit='ms')
        if (pd.Timestamp.now() - start_date).days > days:
            break
            
    print(" Done.")
    if not all_dfs: return pd.DataFrame()
    
    final_df = pd.concat(all_dfs[::-1], ignore_index=True)
    final_df = final_df.drop_duplicates(subset=['open_time']).sort_values('open_time')
    
    final_df['close'] = final_df['close'].astype(float)
    final_df['open'] = final_df['open'].astype(float)
    final_df['high'] = final_df['high'].astype(float)
    final_df['low'] = final_df['low'].astype(float)
    final_df['open_time'] = pd.to_datetime(final_df['open_time'], unit='ms')
    return final_df


def calculate_stake(portfolio_value: float, base: float = 20.0, min_stake: float = 5.0, max_stake: float = 50.0) -> float:
    """
    Calculate stake based on portfolio value.
    Formula: stake = floor(portfolio / base)
    Example: $96 / 20 = $4.8 -> $5 (min). $120 / 20 = $6.
    """
    stake = math.floor(portfolio_value / base)
    return max(min_stake, min(stake, max_stake))


def run_backtest_dynamic():
    """
    Run backtest with DYNAMIC stake sizing.
    Stake grows with portfolio in $1 increments.
    """
    
    # Starting capital
    portfolio = 96.0  # User's current balance
    
    wins = 0
    losses = 0
    trades = 0
    
    # Collect all trades across all assets with timestamps to process chronologically
    all_trades = []
    
    print(f"\n{'='*60}")
    print(f"BACKTEST REPORT - DYNAMIC STAKES (Last 7 Days)")
    print(f"Starting Capital: ${portfolio:.2f}")
    print(f"Stake Formula: floor(portfolio / 20), min $5, in $1 steps")
    print(f"{'='*60}")

    # First pass: collect all signals with timestamps
    for asset, asset_config in config.ASSETS.items():
        symbol = asset_config['binance_symbol']
        
        df = fetch_history(symbol, days=7)
        print(f"Loaded {len(df)} candles for {asset}")
        strategy = SniperStrategy(asset)
        
        position = None
        start_idx = 25
        
        for i in range(start_idx, len(df)):
            history_window = df.iloc[:i+1]
            current_bar = df.iloc[i]
            
            res = strategy.analyze_market(history_window, polymarket_up_odds=0.50)
            signal = res['signal']
            
            if position:
                position['candles_held'] += 1
                
                if position['candles_held'] >= 3:
                    exit_price = current_bar['close']
                    entry_price = position['entry_price']
                    
                    won = False
                    if position['side'] == 'UP':
                        won = exit_price > entry_price
                    else:
                        won = exit_price < entry_price
                    
                    all_trades.append({
                        'timestamp': current_bar['open_time'],
                        'asset': asset,
                        'side': position['side'],
                        'won': won,
                        'entry_price': entry_price,
                        'exit_price': exit_price
                    })
                    
                    position = None
            
            elif signal != 'NEUTRAL':
                position = {
                    'side': signal,
                    'entry_price': current_bar['close'],
                    'time': current_bar['open_time'],
                    'candles_held': 0
                }

    # Sort trades chronologically
    all_trades.sort(key=lambda x: x['timestamp'])
    
    print(f"\nTotal Signals: {len(all_trades)}")
    print(f"\n--- Simulating with Dynamic Stakes ---\n")
    
    # Second pass: simulate with dynamic stakes
    for trade in all_trades:
        current_stake = calculate_stake(portfolio)
        
        # PnL based on current stake
        if trade['won']:
            # Win: Get back stake + 80% profit (simulating 0.55 odds)
            pnl = current_stake * 0.8
            wins += 1
        else:
            # Loss: Lose entire stake
            pnl = -current_stake
            losses += 1
        
        portfolio += pnl
        trades += 1
        
        outcome = "WIN" if trade['won'] else "LOSS"
        
        # Print some trades to show progression
        if trades % 100 == 0 or trades <= 10 or trades >= len(all_trades) - 5:
            print(f"Trade #{trades}: {trade['asset']} {trade['side']} | Stake: ${current_stake:.0f} | {outcome} | PnL: ${pnl:.2f} | Portfolio: ${portfolio:.2f}")

    print(f"\n{'='*60}")
    print(f"FINAL PORTFOLIO: ${portfolio:.2f}")
    print(f"TOTAL PROFIT: ${portfolio - 96:.2f}")
    print(f"ROI: {((portfolio - 96) / 96 * 100):.1f}%")
    print(f"Trades: {trades} | Wins: {wins} | Losses: {losses} | Win Rate: {(wins/trades*100) if trades else 0:.1f}%")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_backtest_dynamic()
