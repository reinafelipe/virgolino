"""
Swing 15min Strategy
Combines: Price Divergence + RSI Extremes + Bollinger Bands Confirmation
"""
import pandas as pd
import config
import logging
from indicators import (
    calculate_rsi,
    calculate_bollinger_bands,
    detect_bb_lower_reversal,
    detect_bb_upper_reversal,
    calculate_spot_change_pct,
    calculate_support_resistance
)

logger = logging.getLogger(__name__)


class SwingStrategy:
    def __init__(self, asset: str = 'BTC'):
        self.asset = asset
        
        # Load asset-specific parameters
        if asset in config.ASSETS:
            params = config.ASSETS[asset]
            self.rsi_period = params.get('rsi_period', 14)
        else:
            self.rsi_period = 14
        
        # Swing strategy constants
        self.rsi_oversold = 30  # Buy UP when RSI < 30
        self.rsi_overbought = 70  # Buy DOWN when RSI > 70
        self.bb_period = 20
        self.bb_std = 2
        self.divergence_threshold = 10.0  # 10% divergence = value signal
        
        logger.info(f"SwingStrategy for {asset}: RSI<{self.rsi_oversold} for UP, RSI>{self.rsi_overbought} for DOWN")

    def calculate_implied_probability(self, spot_change_pct: float) -> float:
        """
        Convert spot price change to implied probability.
        Logic: If BTC up 0.3%, implied UP prob ~ 50% + (0.3 * 10) = 53%
        """
        base_prob = 50.0
        # Sensitivity factor: 10% prob shift per 1% price move
        return base_prob + (spot_change_pct * 10)

    def detect_divergence(self, spot_change_pct: float, polymarket_odds: float) -> float:
        """
        Detect value when market underprices probability.
        Returns divergence percentage (positive = UP undervalued, negative = DOWN undervalued)
        """
        implied_prob = self.calculate_implied_probability(spot_change_pct)
        market_prob = polymarket_odds * 100  # Convert 0.35 to 35%
        
        divergence = implied_prob - market_prob
        return divergence

    def analyze_market(self, history_df: pd.DataFrame, polymarket_up_odds: float = 0.50) -> dict:
        """
        Analyze market with full Swing 15min logic.
        
        Args:
            history_df: DataFrame with 'close' column (5m candles)
            polymarket_up_odds: Current "UP" contract price (0.0 to 1.0)
        
        Returns:
            dict with signal, confidence, and debug info
        """
        result = {
            'signal': 'NEUTRAL',
            'confidence': 0.0,
            'rsi': 0.0,
            'spot_change_pct': 0.0,
            'divergence': 0.0,
            'bb_reversal': False,
            'support': 0.0,
            'resistance': 0.0
        }
        
        if len(history_df) < self.bb_period + 5:
            return result
        
        close = history_df['close']
        current_price = close.iloc[-1]
        
        # 1. Calculate RSI
        rsi = calculate_rsi(close, self.rsi_period)
        current_rsi = rsi.iloc[-1]
        result['rsi'] = current_rsi
        
        # 2. Calculate Bollinger Bands
        upper_bb, mid_bb, lower_bb = calculate_bollinger_bands(close, self.bb_period, self.bb_std)
        
        # 3. Detect BB Reversals
        bb_bullish = detect_bb_lower_reversal(close, lower_bb)
        bb_bearish = detect_bb_upper_reversal(close, upper_bb)
        result['bb_reversal'] = bb_bullish or bb_bearish
        
        # 4. Calculate Spot Change (last 1 candle = 5 mins)
        spot_change = calculate_spot_change_pct(close, lookback_candles=1)
        result['spot_change_pct'] = spot_change
        
        # 5. Calculate Divergence
        divergence = self.detect_divergence(spot_change, polymarket_up_odds)
        result['divergence'] = divergence
        
        # 6. Calculate Support/Resistance
        support, resistance = calculate_support_resistance(close, lookback=20)
        result['support'] = support
        result['resistance'] = resistance
        
        # =====================
        # SIGNAL GENERATION
        # =====================
        
        signal = 'NEUTRAL'
        confidence = 0.0
        reasons = []
        
        # BUY UP CONDITIONS:
        # - RSI < 30 (Oversold)
        # - AND (Divergence > +10% OR BB Lower Reversal)
        # - AND price near support
        
        if current_rsi < self.rsi_oversold:
            reasons.append(f"RSI={current_rsi:.1f}<{self.rsi_oversold}")
            
            if divergence > self.divergence_threshold:
                reasons.append(f"Divergence={divergence:.1f}%")
                signal = 'UP'
                confidence = 0.9
            elif bb_bullish:
                reasons.append("BB Lower Reversal")
                signal = 'UP'
                confidence = 0.85
            elif abs(current_price - support) / current_price < 0.005:  # Within 0.5% of support
                reasons.append(f"Near Support ${support:.2f}")
                signal = 'UP'
                confidence = 0.8
        
        # BUY DOWN CONDITIONS:
        # - RSI > 70 (Overbought)
        # - AND (Divergence < -10% OR BB Upper Reversal)
        # - AND price near resistance
        
        elif current_rsi > self.rsi_overbought:
            reasons.append(f"RSI={current_rsi:.1f}>{self.rsi_overbought}")
            
            if divergence < -self.divergence_threshold:
                reasons.append(f"Divergence={divergence:.1f}%")
                signal = 'DOWN'
                confidence = 0.9
            elif bb_bearish:
                reasons.append("BB Upper Reversal")
                signal = 'DOWN'
                confidence = 0.85
            elif abs(current_price - resistance) / current_price < 0.005:
                reasons.append(f"Near Resistance ${resistance:.2f}")
                signal = 'DOWN'
                confidence = 0.8
        
        result['signal'] = signal
        result['confidence'] = confidence
        
        if signal != 'NEUTRAL':
            logger.info(f"[{self.asset}] SIGNAL: {signal} | {' + '.join(reasons)}")
        else:
            logger.debug(f"[{self.asset}] Price={current_price:.2f}, RSI={current_rsi:.1f}, Div={divergence:.1f}% -> NEUTRAL")
        
        return result


# Alias for backwards compatibility
SniperStrategy = SwingStrategy
