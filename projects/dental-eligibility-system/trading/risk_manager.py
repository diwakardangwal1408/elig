"""
Risk Management Module for Options Trading
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskMetrics:
    """Risk metrics for portfolio/strategy"""
    total_capital: float
    available_capital: float
    used_capital: float
    daily_pnl: float
    total_pnl: float
    max_drawdown: float
    current_positions: int
    risk_per_trade: float
    portfolio_risk: float
    var_1day: float  # Value at Risk for 1 day
    
    
@dataclass
class TradeRisk:
    """Risk assessment for individual trade"""
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: Optional[float]
    target_price: Optional[float]
    
    # Risk metrics
    position_value: float = field(init=False)
    risk_amount: float = field(init=False)
    reward_amount: float = field(init=False)
    risk_reward_ratio: float = field(init=False)
    portfolio_risk_pct: float = field(init=False)
    max_loss_pct: float = field(init=False)
    
    def __post_init__(self):
        self.position_value = abs(self.quantity * self.entry_price)
        
        if self.stop_loss:
            self.risk_amount = abs(self.quantity * (self.entry_price - self.stop_loss))
            self.max_loss_pct = (self.risk_amount / self.position_value) * 100
        else:
            self.risk_amount = 0
            self.max_loss_pct = 0
            
        if self.target_price:
            self.reward_amount = abs(self.quantity * (self.target_price - self.entry_price))
        else:
            self.reward_amount = 0
            
        if self.risk_amount > 0:
            self.risk_reward_ratio = self.reward_amount / self.risk_amount
        else:
            self.risk_reward_ratio = 0


class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Risk limits
        self.max_daily_loss = config.get('max_daily_loss', 5000.0)
        self.max_position_size = config.get('max_position_size', 50000.0)
        self.max_portfolio_risk = config.get('max_portfolio_risk', 10.0)  # % of capital
        self.risk_per_trade = config.get('risk_per_trade', 2.0)  # % of capital
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_daily_trades = config.get('max_daily_trades', 10)
        self.positions = {}
        self.trade_history = []
        
        # Circuit breakers
        self.trading_halted = False
        self.halt_reason = ""
        
    def assess_portfolio_risk(self, positions: List, account_balance: float) -> RiskMetrics:
        """Assess overall portfolio risk"""
        try:
            total_position_value = sum(abs(pos.quantity * pos.ltp) for pos in positions)
            available_capital = account_balance
            used_capital = total_position_value
            
            # Calculate portfolio VaR (simplified)
            portfolio_volatility = 0.02  # 2% assumed daily volatility
            var_1day = total_position_value * portfolio_volatility * 1.65  # 95% confidence
            
            # Calculate current portfolio risk
            total_risk = sum(self._calculate_position_risk(pos) for pos in positions)
            portfolio_risk_pct = (total_risk / available_capital * 100) if available_capital > 0 else 0
            
            # Calculate max drawdown (simplified - would need historical data)
            max_drawdown = max(0, -min(pos.pnl for pos in positions)) if positions else 0
            
            return RiskMetrics(
                total_capital=available_capital + used_capital,
                available_capital=available_capital,
                used_capital=used_capital,
                daily_pnl=self.daily_pnl,
                total_pnl=sum(pos.pnl for pos in positions),
                max_drawdown=max_drawdown,
                current_positions=len(positions),
                risk_per_trade=self.risk_per_trade,
                portfolio_risk=portfolio_risk_pct,
                var_1day=var_1day
            )
            
        except Exception as e:
            self.logger.error(f"Error assessing portfolio risk: {e}")
            return RiskMetrics(
                total_capital=account_balance,
                available_capital=account_balance,
                used_capital=0,
                daily_pnl=0,
                total_pnl=0,
                max_drawdown=0,
                current_positions=0,
                risk_per_trade=self.risk_per_trade,
                portfolio_risk=0,
                var_1day=0
            )
    
    def _calculate_position_risk(self, position) -> float:
        """Calculate risk for a single position"""
        # This would ideally use Greeks for options, simplified here
        position_value = abs(position.quantity * position.ltp)
        # Assume 30% max loss for options (theta decay + price movement)
        estimated_risk = position_value * 0.3
        return estimated_risk
    
    def validate_trade(self, symbol: str, quantity: int, price: float, 
                      stop_loss: Optional[float] = None, 
                      account_balance: float = 100000) -> Tuple[bool, str, RiskLevel]:
        """Validate if trade meets risk criteria"""
        try:
            # Check if trading is halted
            if self.trading_halted:
                return False, f"Trading halted: {self.halt_reason}", RiskLevel.CRITICAL
            
            # Check daily loss limit
            if self.daily_pnl <= -self.max_daily_loss:
                return False, f"Daily loss limit exceeded: {self.daily_pnl:.2f}", RiskLevel.CRITICAL
            
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                return False, f"Daily trade limit exceeded: {self.daily_trades}", RiskLevel.HIGH
            
            # Calculate position size
            position_value = abs(quantity * price)
            
            # Check maximum position size
            if position_value > self.max_position_size:
                return False, f"Position size {position_value:.2f} exceeds limit {self.max_position_size:.2f}", RiskLevel.HIGH
            
            # Check if we have enough capital
            if position_value > account_balance * 0.9:  # Leave 10% buffer
                return False, f"Insufficient capital for position size {position_value:.2f}", RiskLevel.HIGH
            
            # Calculate risk amount
            risk_amount = 0
            if stop_loss:
                risk_amount = abs(quantity * (price - stop_loss))
            else:
                # If no stop loss, assume 25% risk for options
                risk_amount = position_value * 0.25
            
            # Check risk per trade limit
            risk_pct = (risk_amount / account_balance) * 100
            if risk_pct > self.risk_per_trade:
                return False, f"Trade risk {risk_pct:.2f}% exceeds limit {self.risk_per_trade:.2f}%", RiskLevel.MEDIUM
            
            # Determine risk level
            if risk_pct > self.risk_per_trade * 0.8:
                risk_level = RiskLevel.HIGH
            elif risk_pct > self.risk_per_trade * 0.5:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            return True, "Trade approved", risk_level
            
        except Exception as e:
            self.logger.error(f"Error validating trade: {e}")
            return False, f"Validation error: {e}", RiskLevel.CRITICAL
    
    def calculate_position_size(self, strategy_config: dict, entry_price: float, 
                              stop_loss: float, account_balance: float) -> int:
        """Calculate optimal position size based on risk management"""
        try:
            position_type = strategy_config.get('position_type', 'risk_based')
            
            if position_type == 'fixed_amount':
                # Fixed amount position sizing
                target_value = strategy_config.get('position_size', 10000.0)
                quantity = int(target_value / entry_price)
                
            elif position_type == 'percentage':
                # Percentage of capital
                percentage = strategy_config.get('position_size', 5.0) / 100
                target_value = account_balance * percentage
                quantity = int(target_value / entry_price)
                
            else:  # risk_based (default)
                # Risk-based position sizing
                risk_per_trade_pct = strategy_config.get('risk_percentage', self.risk_per_trade)
                risk_amount = account_balance * (risk_per_trade_pct / 100)
                
                if stop_loss and stop_loss != entry_price:
                    risk_per_share = abs(entry_price - stop_loss)
                    quantity = int(risk_amount / risk_per_share)
                else:
                    # If no stop loss, use conservative position sizing
                    max_position_value = account_balance * 0.1  # 10% of capital
                    quantity = int(max_position_value / entry_price)
            
            # Apply maximum position size limit
            max_quantity = int(self.max_position_size / entry_price)
            quantity = min(quantity, max_quantity)
            
            # Ensure minimum viable quantity
            quantity = max(quantity, 1)
            
            return quantity
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            # Return conservative default
            return int(5000 / entry_price)  # ₹5000 position
    
    def should_exit_position(self, trade_risk: TradeRisk, 
                           strategy_config: dict) -> Tuple[bool, str]:
        """Determine if position should be exited"""
        try:
            current_pnl = trade_risk.quantity * (trade_risk.current_price - trade_risk.entry_price)
            current_pnl_pct = (current_pnl / trade_risk.position_value) * 100
            
            # Stop loss check
            if trade_risk.stop_loss:
                if trade_risk.quantity > 0:  # Long position
                    if trade_risk.current_price <= trade_risk.stop_loss:
                        return True, f"Stop loss triggered at {trade_risk.current_price:.2f}"
                else:  # Short position
                    if trade_risk.current_price >= trade_risk.stop_loss:
                        return True, f"Stop loss triggered at {trade_risk.current_price:.2f}"
            
            # Profit target check
            if trade_risk.target_price:
                if trade_risk.quantity > 0:  # Long position
                    if trade_risk.current_price >= trade_risk.target_price:
                        return True, f"Profit target reached at {trade_risk.current_price:.2f}"
                else:  # Short position
                    if trade_risk.current_price <= trade_risk.target_price:
                        return True, f"Profit target reached at {trade_risk.current_price:.2f}"
            
            # Percentage-based exits
            profit_target_type = strategy_config.get('profit_target_type', 'percentage')
            profit_target_value = strategy_config.get('profit_target_value', 20.0)
            
            if profit_target_type == 'percentage':
                if current_pnl_pct >= profit_target_value:
                    return True, f"Profit target {profit_target_value:.1f}% reached"
            
            elif profit_target_type == 'amount':
                if current_pnl >= profit_target_value:
                    return True, f"Profit target ₹{profit_target_value:.0f} reached"
            
            # Emergency exit conditions
            if current_pnl_pct <= -50:  # 50% loss
                return True, "Emergency exit: 50% loss"
            
            return False, ""
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
            return False, ""
    
    def update_daily_pnl(self, pnl_change: float):
        """Update daily P&L tracking"""
        self.daily_pnl += pnl_change
        
        # Check for daily loss limit breach
        if self.daily_pnl <= -self.max_daily_loss:
            self.halt_trading("Daily loss limit exceeded")
    
    def halt_trading(self, reason: str):
        """Halt all trading activities"""
        self.trading_halted = True
        self.halt_reason = reason
        self.logger.warning(f"Trading halted: {reason}")
    
    def resume_trading(self):
        """Resume trading activities"""
        self.trading_halted = False
        self.halt_reason = ""
        self.logger.info("Trading resumed")
    
    def reset_daily_limits(self):
        """Reset daily limits (call at start of new trading day)"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.resume_trading()
        self.logger.info("Daily limits reset")
    
    def record_trade(self, symbol: str, quantity: int, price: float, 
                    trade_type: str, pnl: float = 0):
        """Record completed trade"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'trade_type': trade_type,
            'pnl': pnl
        }
        
        self.trade_history.append(trade_record)
        self.daily_trades += 1
        
        if pnl != 0:
            self.update_daily_pnl(pnl)
        
        self.logger.info(f"Trade recorded: {trade_type} {quantity} {symbol} @ {price:.2f}")
    
    def get_risk_summary(self, account_balance: float = 100000) -> Dict:
        """Get comprehensive risk summary"""
        return {
            'trading_status': 'ACTIVE' if not self.trading_halted else 'HALTED',
            'halt_reason': self.halt_reason,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'max_daily_loss': self.max_daily_loss,
            'max_daily_trades': self.max_daily_trades,
            'risk_per_trade': self.risk_per_trade,
            'max_position_size': self.max_position_size,
            'capital_utilization': (self.daily_pnl / account_balance) * 100,
            'trades_remaining': max(0, self.max_daily_trades - self.daily_trades),
            'loss_limit_remaining': max(0, self.max_daily_loss + self.daily_pnl)
        }


class OptionsRiskManager(RiskManager):
    """Specialized risk manager for options trading"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Options-specific risk parameters
        self.max_theta_decay = config.get('max_theta_decay', 5.0)  # % per day
        self.min_days_to_expiry = config.get('min_days_to_expiry', 7)
        self.max_vega_exposure = config.get('max_vega_exposure', 10000.0)  # Total vega exposure
    
    def validate_options_trade(self, option_contract, quantity: int, 
                             days_to_expiry: int, iv: float = None) -> Tuple[bool, str]:
        """Validate options-specific risk factors"""
        try:
            # Check days to expiry
            if days_to_expiry < self.min_days_to_expiry:
                return False, f"Options expires in {days_to_expiry} days, minimum is {self.min_days_to_expiry}"
            
            # Check implied volatility (if available)
            if iv and iv > 50:  # High IV threshold
                self.logger.warning(f"High implied volatility: {iv:.1f}%")
            
            # Estimate theta decay risk
            position_value = abs(quantity * option_contract.ltp) if hasattr(option_contract, 'ltp') else 0
            estimated_daily_decay = position_value * (self.max_theta_decay / 100)
            
            if estimated_daily_decay > self.max_daily_loss * 0.3:  # 30% of daily loss limit
                return False, f"Estimated daily theta decay {estimated_daily_decay:.2f} too high"
            
            return True, "Options trade approved"
            
        except Exception as e:
            self.logger.error(f"Error validating options trade: {e}")
            return False, f"Options validation error: {e}"
    
    def calculate_options_risk(self, positions: List) -> Dict:
        """Calculate options-specific risk metrics"""
        total_theta = sum(getattr(pos, 'theta', -10) * abs(pos.quantity) for pos in positions)
        total_vega = sum(getattr(pos, 'vega', 5) * abs(pos.quantity) for pos in positions)
        total_gamma = sum(getattr(pos, 'gamma', 1) * abs(pos.quantity) for pos in positions)
        
        return {
            'total_theta': total_theta,  # Daily decay
            'total_vega': total_vega,    # Volatility sensitivity
            'total_gamma': total_gamma,  # Delta sensitivity
            'theta_risk_pct': (abs(total_theta) / self.max_daily_loss) * 100,
            'vega_exposure': abs(total_vega)
        }