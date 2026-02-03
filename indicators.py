"""
Technical Indicators Module for Swing 15min Strategy
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(close: pd.Series, period: int = 20, std_dev: int = 2) -> tuple:
    """
    Calculate Bollinger Bands.
    Returns: (upper_band, middle_band, lower_band)
    """
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower


def detect_bb_lower_reversal(close: pd.Series, lower_band: pd.Series, lookback: int = 3) -> bool:
    """
    Detect bullish reversal: Price pierced lower band and closed back inside.
    Checks if any of the last 'lookback' candles touched below lower band,
    and the current candle closed above it.
    """
    if len(close) < lookback + 1 or len(lower_band) < lookback + 1:
        return False
    
    # Check if any recent candle touched below lower band
    touched_lower = False
    for i in range(-lookback, 0):
        if close.iloc[i] < lower_band.iloc[i]:
            touched_lower = True
            break
    
    # Current candle closed above lower band
    closed_above = close.iloc[-1] > lower_band.iloc[-1]
    
    return touched_lower and closed_above


def detect_bb_upper_reversal(close: pd.Series, upper_band: pd.Series, lookback: int = 3) -> bool:
    """
    Detect bearish reversal: Price pierced upper band and closed back inside.
    """
    if len(close) < lookback + 1 or len(upper_band) < lookback + 1:
        return False
    
    touched_upper = False
    for i in range(-lookback, 0):
        if close.iloc[i] > upper_band.iloc[i]:
            touched_upper = True
            break
    
    closed_below = close.iloc[-1] < upper_band.iloc[-1]
    
    return touched_upper and closed_below


def calculate_spot_change_pct(close: pd.Series, lookback_candles: int = 1) -> float:
    """
    Calculate percentage change in spot price over last N candles.
    For 5m candles, lookback=1 means last 5 minutes.
    """
    if len(close) < lookback_candles + 1:
        return 0.0
    
    old_price = close.iloc[-(lookback_candles + 1)]
    current_price = close.iloc[-1]
    
    if old_price == 0:
        return 0.0
    
    return ((current_price - old_price) / old_price) * 100


def calculate_support_resistance(close: pd.Series, lookback: int = 20) -> tuple:
    """
    Simple support/resistance based on recent lows/highs.
    Returns (support_level, resistance_level)
    """
    if len(close) < lookback:
        return close.iloc[-1] * 0.99, close.iloc[-1] * 1.01
    
    recent = close.iloc[-lookback:]
    support = recent.min()
    resistance = recent.max()
    
    return support, resistance
