"""
Price Action Analysis Module for Options Trading
"""
import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Optional, Tuple, Literal
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging


@dataclass
class PriceActionSignal:
    """Represents a price action trading signal"""
    signal_type: Literal["BUY", "SELL", "HOLD"]
    strength: float  # 0-1, where 1 is strongest
    price: float
    timestamp: datetime
    reason: str
    confidence: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None


@dataclass
class MarketStructure:
    """Market structure analysis results"""
    trend: Literal["UPTREND", "DOWNTREND", "SIDEWAYS"]
    swing_high: float
    swing_low: float
    support_level: float
    resistance_level: float
    trend_strength: float
    volatility: float


class PriceActionAnalyzer:
    """Analyzes price action for trading signals"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_market_structure(self, df: pd.DataFrame, 
                               lookback: int = 20) -> MarketStructure:
        """Analyze overall market structure"""
        try:
            if len(df) < lookback:
                raise ValueError(f"Not enough data. Need at least {lookback} candles")
            
            # Calculate swing points
            highs = df['high'].rolling(window=5, center=True).max()
            lows = df['low'].rolling(window=5, center=True).min()
            
            swing_highs = df['high'][(df['high'] == highs) & (df['high'].shift(2) < df['high']) & (df['high'].shift(-2) < df['high'])]
            swing_lows = df['low'][(df['low'] == lows) & (df['low'].shift(2) > df['low']) & (df['low'].shift(-2) > df['low'])]
            
            # Determine trend
            recent_data = df.tail(lookback)
            sma_20 = recent_data['close'].mean()
            current_price = df['close'].iloc[-1]
            
            # Simple trend determination
            if current_price > sma_20 and df['close'].iloc[-1] > df['close'].iloc[-10]:
                trend = "UPTREND"
            elif current_price < sma_20 and df['close'].iloc[-1] < df['close'].iloc[-10]:
                trend = "DOWNTREND"
            else:
                trend = "SIDEWAYS"
            
            # Support and resistance levels
            recent_highs = recent_data['high'].tail(10)
            recent_lows = recent_data['low'].tail(10)
            
            resistance = recent_highs.max()
            support = recent_lows.min()
            
            # Volatility (ATR-based)
            atr = ta.volatility.AverageTrueRange(
                high=df['high'], low=df['low'], close=df['close']
            ).average_true_range().iloc[-1]
            
            volatility = atr / current_price * 100  # ATR as percentage of price
            
            # Trend strength (based on slope of moving average)
            ma_slope = (df['close'].rolling(20).mean().iloc[-1] - 
                       df['close'].rolling(20).mean().iloc[-5]) / 5
            trend_strength = abs(ma_slope) / current_price * 100
            
            return MarketStructure(
                trend=trend,
                swing_high=swing_highs.iloc[-1] if not swing_highs.empty else resistance,
                swing_low=swing_lows.iloc[-1] if not swing_lows.empty else support,
                support_level=support,
                resistance_level=resistance,
                trend_strength=min(trend_strength, 1.0),
                volatility=volatility
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing market structure: {e}")
            # Return default structure
            current_price = df['close'].iloc[-1]
            return MarketStructure(
                trend="SIDEWAYS",
                swing_high=current_price * 1.02,
                swing_low=current_price * 0.98,
                support_level=current_price * 0.98,
                resistance_level=current_price * 1.02,
                trend_strength=0.5,
                volatility=2.0
            )
    
    def detect_breakout(self, df: pd.DataFrame, threshold: float = 0.5, 
                       volume_confirmation: bool = True) -> Optional[PriceActionSignal]:
        """Detect breakout patterns"""
        try:
            if len(df) < 20:
                return None
            
            current_price = df['close'].iloc[-1]
            current_volume = df['volume'].iloc[-1] if 'volume' in df.columns else 1000
            
            # Calculate resistance and support levels
            lookback_period = min(20, len(df))
            recent_data = df.tail(lookback_period)
            
            resistance = recent_data['high'].max()
            support = recent_data['low'].min()
            avg_range = (recent_data['high'] - recent_data['low']).mean()
            
            # Average volume
            avg_volume = recent_data['volume'].mean() if 'volume' in recent_data.columns else current_volume
            
            # Breakout conditions
            breakout_threshold = avg_range * threshold / 100
            
            # Bullish breakout
            if (current_price > resistance + breakout_threshold):
                volume_ok = not volume_confirmation or current_volume > avg_volume * 1.2
                
                if volume_ok:
                    confidence = min(
                        (current_price - resistance) / avg_range * 2,
                        1.0
                    )
                    
                    return PriceActionSignal(
                        signal_type="BUY",
                        strength=confidence,
                        price=current_price,
                        timestamp=df.index[-1] if hasattr(df.index[-1], 'timestamp') else datetime.now(),
                        reason=f"Bullish breakout above resistance {resistance:.2f}",
                        confidence=confidence,
                        stop_loss=resistance * 0.995,  # Just below breakout level
                        target=current_price + (current_price - support) * 0.618  # Fibonacci extension
                    )
            
            # Bearish breakout (breakdown)
            elif (current_price < support - breakout_threshold):
                volume_ok = not volume_confirmation or current_volume > avg_volume * 1.2
                
                if volume_ok:
                    confidence = min(
                        (support - current_price) / avg_range * 2,
                        1.0
                    )
                    
                    return PriceActionSignal(
                        signal_type="SELL",
                        strength=confidence,
                        price=current_price,
                        timestamp=df.index[-1] if hasattr(df.index[-1], 'timestamp') else datetime.now(),
                        reason=f"Bearish breakdown below support {support:.2f}",
                        confidence=confidence,
                        stop_loss=support * 1.005,  # Just above breakdown level
                        target=current_price - (resistance - current_price) * 0.618  # Fibonacci extension
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting breakout: {e}")
            return None
    
    def detect_pullback(self, df: pd.DataFrame, 
                       market_structure: MarketStructure) -> Optional[PriceActionSignal]:
        """Detect pullback entry opportunities"""
        try:
            if len(df) < 15:
                return None
            
            current_price = df['close'].iloc[-1]
            
            # For uptrend pullbacks
            if market_structure.trend == "UPTREND":
                # Look for price pulling back to support/moving average
                sma_20 = df['close'].rolling(20).mean().iloc[-1]
                
                # Check if price has pulled back to MA or support
                if (current_price <= sma_20 * 1.005 and  # At or slightly above MA
                    current_price > market_structure.support_level and  # Above major support
                    df['close'].iloc[-2] < df['close'].iloc[-3]):  # Showing signs of reversal
                    
                    confidence = min(
                        (current_price - market_structure.support_level) / 
                        (market_structure.resistance_level - market_structure.support_level),
                        0.8
                    )
                    
                    return PriceActionSignal(
                        signal_type="BUY",
                        strength=confidence,
                        price=current_price,
                        timestamp=df.index[-1] if hasattr(df.index[-1], 'timestamp') else datetime.now(),
                        reason=f"Pullback to support in uptrend at {current_price:.2f}",
                        confidence=confidence,
                        stop_loss=market_structure.support_level * 0.99,
                        target=market_structure.resistance_level * 0.95
                    )
            
            # For downtrend pullbacks
            elif market_structure.trend == "DOWNTREND":
                # Look for price pulling back to resistance/moving average
                sma_20 = df['close'].rolling(20).mean().iloc[-1]
                
                if (current_price >= sma_20 * 0.995 and  # At or slightly below MA
                    current_price < market_structure.resistance_level and  # Below major resistance
                    df['close'].iloc[-2] > df['close'].iloc[-3]):  # Showing signs of reversal
                    
                    confidence = min(
                        (market_structure.resistance_level - current_price) / 
                        (market_structure.resistance_level - market_structure.support_level),
                        0.8
                    )
                    
                    return PriceActionSignal(
                        signal_type="SELL",
                        strength=confidence,
                        price=current_price,
                        timestamp=df.index[-1] if hasattr(df.index[-1], 'timestamp') else datetime.now(),
                        reason=f"Pullback to resistance in downtrend at {current_price:.2f}",
                        confidence=confidence,
                        stop_loss=market_structure.resistance_level * 1.01,
                        target=market_structure.support_level * 1.05
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting pullback: {e}")
            return None
    
    def calculate_volatility_bands(self, df: pd.DataFrame, 
                                 period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
        """Calculate Bollinger Band-like volatility bands"""
        try:
            if len(df) < period:
                return {'upper': df['close'].iloc[-1] * 1.02, 
                       'middle': df['close'].iloc[-1], 
                       'lower': df['close'].iloc[-1] * 0.98}
            
            close = df['close']
            
            # Calculate moving average and standard deviation
            ma = close.rolling(period).mean().iloc[-1]
            std = close.rolling(period).std().iloc[-1]
            
            upper_band = ma + (std * std_dev)
            lower_band = ma - (std * std_dev)
            
            return {
                'upper': upper_band,
                'middle': ma,
                'lower': lower_band
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility bands: {e}")
            current_price = df['close'].iloc[-1]
            return {'upper': current_price * 1.02, 'middle': current_price, 'lower': current_price * 0.98}
    
    def analyze_momentum(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze momentum indicators"""
        try:
            if len(df) < 14:
                return {'rsi': 50.0, 'momentum': 0.0, 'rate_of_change': 0.0}
            
            # RSI
            rsi = ta.momentum.RSIIndicator(df['close']).rsi().iloc[-1]
            
            # Price momentum (10-period)
            momentum = ((df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]) * 100
            
            # Rate of change (5-period)
            roc = ((df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]) * 100
            
            return {
                'rsi': rsi if not np.isnan(rsi) else 50.0,
                'momentum': momentum if not np.isnan(momentum) else 0.0,
                'rate_of_change': roc if not np.isnan(roc) else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing momentum: {e}")
            return {'rsi': 50.0, 'momentum': 0.0, 'rate_of_change': 0.0}
    
    def generate_trading_signal(self, df: pd.DataFrame, 
                              strategy_config: dict) -> Optional[PriceActionSignal]:
        """Generate comprehensive trading signal based on configuration"""
        try:
            # Get market structure
            market_structure = self.analyze_market_structure(df, strategy_config.get('lookback_periods', 20))
            
            # Get momentum indicators
            momentum = self.analyze_momentum(df)
            
            signal = None
            
            # Check entry trigger type
            entry_trigger = strategy_config.get('entry_trigger', 'breakout')
            
            if entry_trigger == "breakout":
                signal = self.detect_breakout(
                    df, 
                    threshold=strategy_config.get('breakout_threshold', 0.5),
                    volume_confirmation=strategy_config.get('volume_confirmation', True)
                )
            
            elif entry_trigger == "pullback":
                signal = self.detect_pullback(df, market_structure)
            
            elif entry_trigger == "market_open":
                # Simple market open signal based on gap and momentum
                if len(df) >= 2:
                    gap = (df['open'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
                    
                    if abs(gap) > 0.2:  # Significant gap
                        signal_type = "BUY" if gap > 0 else "SELL"
                        
                        signal = PriceActionSignal(
                            signal_type=signal_type,
                            strength=min(abs(gap) / 2, 1.0),
                            price=df['close'].iloc[-1],
                            timestamp=df.index[-1] if hasattr(df.index[-1], 'timestamp') else datetime.now(),
                            reason=f"Market open gap of {gap:.2f}%",
                            confidence=0.6
                        )
            
            # Enhance signal with momentum confirmation
            if signal and momentum['rsi'] != 50.0:
                if signal.signal_type == "BUY" and momentum['rsi'] > 70:
                    signal.confidence *= 0.7  # Reduce confidence for overbought
                elif signal.signal_type == "SELL" and momentum['rsi'] < 30:
                    signal.confidence *= 0.7  # Reduce confidence for oversold
                elif signal.signal_type == "BUY" and 40 < momentum['rsi'] < 60:
                    signal.confidence *= 1.1  # Increase confidence for neutral RSI
                elif signal.signal_type == "SELL" and 40 < momentum['rsi'] < 60:
                    signal.confidence *= 1.1
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error generating trading signal: {e}")
            return None