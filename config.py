import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Credentials
API_KEY = os.getenv("POLYMARKET_API_KEY")
API_SECRET = os.getenv("POLYMARKET_SECRET")
API_PASSPHRASE = os.getenv("POLYMARKET_PASSPHRASE")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PROFILE_ADDRESS = os.getenv("PROFILE_ADDRESS")

# Trading Config
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon Mainnet

# =====================
# ASSETS: BTC + ETH ONLY (Best performers)
# =====================
ASSETS = {
    'BTC': {
        'binance_symbol': 'BTCUSDT',
        'polymarket_keywords': ['bitcoin', 'btc'],
        'ema_period': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,  # Swing strategy: extremes only
        'rsi_oversold': 30,
        'min_liquidity_usd': 500,
    },
    'ETH': {
        'binance_symbol': 'ETHUSDT',
        'polymarket_keywords': ['ethereum', 'eth'],
        'ema_period': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'min_liquidity_usd': 300,
    },
}

# =====================
# RISK MANAGEMENT
# =====================
INITIAL_CAPITAL = 96.0  # Current balance
MAX_POSITIONS = 2  # One per asset
STOP_LOSS_PCT = 0.20  # Stop trading if down 20%
TAKE_PROFIT_PCT = 0.30  # Exit at 30% profit on position

# DYNAMIC STAKE SIZING
# Formula: floor(portfolio / STAKE_DIVISOR), bounded by min/max
STAKE_DIVISOR = 20  # $100 portfolio = $5 stake
MIN_STAKE = 5.0
MAX_STAKE = 50.0
MAX_PORTFOLIO_EXPOSURE = 100.0  # Per-position calculated dynamically

# Time Management
ENTRY_WINDOW_START_MIN = 2  # Start trading at minute 2 of cycle
ENTRY_WINDOW_END_MIN = 12  # Stop trading at minute 12 (3 min before expiry)

# Strategy Config
TIMEFRAME = '5m'  # For analysis logic
MARKET_TIMEFRAME_MINUTES = 15  # We look for markets expiring in 15m

if not API_KEY or not PRIVATE_KEY:
    print("WARNING: API Key or Private Key not found in environment variables.")
