"""
Configuration management for Zerodha Options Trading System
"""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import json
from pathlib import Path


class TradingConfig(BaseModel):
    """Configuration for individual trading strategy"""
    
    # Strategy Identity
    strategy_name: str = Field(..., description="Name of the strategy")
    enabled: bool = Field(True, description="Whether this strategy is enabled")
    
    # Instrument Selection
    underlying: str = Field(..., description="Underlying symbol (e.g., NIFTY, BANKNIFTY)")
    option_type: Literal["CE", "PE"] = Field(..., description="Call or Put options")
    expiry_preference: Literal["current", "next", "monthly"] = Field("current", description="Which expiry to trade")
    
    # ITM Configuration
    itm_depth: int = Field(1, description="How many strikes ITM (1=1st ITM, 2=2nd ITM, etc.)")
    min_itm_amount: float = Field(10.0, description="Minimum ITM amount in points")
    max_itm_amount: float = Field(200.0, description="Maximum ITM amount in points")
    
    # Entry Conditions
    entry_time_start: str = Field("09:30", description="Start time for entry (HH:MM)")
    entry_time_end: str = Field("14:30", description="End time for entry (HH:MM)")
    entry_trigger: Literal["market_open", "breakout", "pullback", "manual"] = Field("breakout", description="Entry trigger type")
    
    # Price Action Parameters
    lookback_periods: int = Field(20, description="Lookback periods for price action analysis")
    breakout_threshold: float = Field(0.5, description="Breakout threshold as % of average range")
    volume_confirmation: bool = Field(True, description="Require volume confirmation")
    min_volume_ratio: float = Field(1.2, description="Minimum volume ratio vs average")
    
    # Position Sizing
    position_type: Literal["fixed_amount", "risk_based", "percentage"] = Field("risk_based", description="Position sizing method")
    position_size: float = Field(10000.0, description="Position size in INR (for fixed_amount)")
    risk_percentage: float = Field(2.0, description="Risk per trade as % of capital (for risk_based)")
    
    # Risk Management
    stop_loss_type: Literal["percentage", "amount", "atr_multiple"] = Field("percentage", description="Stop loss type")
    stop_loss_value: float = Field(20.0, description="Stop loss value (% or amount or ATR multiple)")
    
    # Exit Criteria
    profit_target_type: Literal["percentage", "amount", "risk_reward"] = Field("risk_reward", description="Profit target type")
    profit_target_value: float = Field(1.5, description="Profit target value (% or amount or RR ratio)")
    
    # Time-based Exit
    exit_time: str = Field("15:20", description="Mandatory exit time (HH:MM)")
    exit_before_expiry_days: int = Field(0, description="Exit N days before expiry (0=same day OK)")
    
    # Advanced Settings
    max_positions: int = Field(1, description="Maximum concurrent positions for this strategy")
    cooldown_minutes: int = Field(30, description="Cooldown between trades in minutes")
    allow_reentry: bool = Field(False, description="Allow re-entry after stop loss")


class SystemSettings(BaseSettings):
    """System-wide settings loaded from environment"""
    
    # API Configuration
    kite_api_key: str = Field(..., env="KITE_API_KEY")
    kite_api_secret: str = Field(..., env="KITE_API_SECRET")
    kite_access_token: Optional[str] = Field(None, env="KITE_ACCESS_TOKEN")
    
    # Trading Mode
    trading_mode: Literal["paper", "live"] = Field("paper", env="TRADING_MODE")
    
    # Risk Limits
    max_daily_loss: float = Field(5000.0, env="MAX_DAILY_LOSS")
    max_position_size: float = Field(50000.0, env="MAX_POSITION_SIZE")
    risk_per_trade: float = Field(2.0, env="RISK_PER_TRADE")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("trading.log", env="LOG_FILE")
    
    # Database
    database_url: str = Field("sqlite:///trades.db", env="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class ConfigManager:
    """Manages trading configurations and strategies"""
    
    def __init__(self, config_file: str = "strategies.json"):
        self.config_file = Path(config_file)
        self.system_settings = SystemSettings()
        self.strategies: Dict[str, TradingConfig] = {}
        self.load_strategies()
    
    def load_strategies(self) -> None:
        """Load strategies from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for strategy_data in data.get('strategies', []):
                        strategy = TradingConfig(**strategy_data)
                        self.strategies[strategy.strategy_name] = strategy
            except Exception as e:
                print(f"Error loading strategies: {e}")
    
    def save_strategies(self) -> None:
        """Save strategies to JSON file"""
        try:
            data = {
                'strategies': [strategy.dict() for strategy in self.strategies.values()]
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving strategies: {e}")
    
    def add_strategy(self, strategy: TradingConfig) -> None:
        """Add a new trading strategy"""
        self.strategies[strategy.strategy_name] = strategy
        self.save_strategies()
    
    def get_strategy(self, name: str) -> Optional[TradingConfig]:
        """Get a specific strategy by name"""
        return self.strategies.get(name)
    
    def get_enabled_strategies(self) -> List[TradingConfig]:
        """Get all enabled strategies"""
        return [strategy for strategy in self.strategies.values() if strategy.enabled]
    
    def remove_strategy(self, name: str) -> bool:
        """Remove a strategy"""
        if name in self.strategies:
            del self.strategies[name]
            self.save_strategies()
            return True
        return False
    
    def update_strategy(self, name: str, updates: dict) -> bool:
        """Update a strategy with new parameters"""
        if name in self.strategies:
            strategy_dict = self.strategies[name].dict()
            strategy_dict.update(updates)
            self.strategies[name] = TradingConfig(**strategy_dict)
            self.save_strategies()
            return True
        return False


# Create example strategy configuration
def create_example_strategies() -> Dict[str, TradingConfig]:
    """Create example strategy configurations"""
    
    strategies = {}
    
    # Example 1: NIFTY Call Options - Breakout Strategy
    nifty_call_breakout = TradingConfig(
        strategy_name="NIFTY_CALL_BREAKOUT",
        enabled=True,
        underlying="NIFTY",
        option_type="CE",
        expiry_preference="current",
        itm_depth=2,  # 2nd ITM call
        min_itm_amount=20.0,
        max_itm_amount=150.0,
        entry_time_start="09:45",
        entry_time_end="14:00",
        entry_trigger="breakout",
        lookback_periods=15,
        breakout_threshold=0.6,
        volume_confirmation=True,
        min_volume_ratio=1.3,
        position_type="risk_based",
        risk_percentage=1.5,
        stop_loss_type="percentage",
        stop_loss_value=25.0,  # 25% stop loss
        profit_target_type="risk_reward",
        profit_target_value=2.0,  # 1:2 RR ratio
        exit_time="15:15",
        max_positions=1,
        cooldown_minutes=45
    )
    
    # Example 2: BANKNIFTY Put Options - Pullback Strategy
    banknifty_put_pullback = TradingConfig(
        strategy_name="BANKNIFTY_PUT_PULLBACK",
        enabled=True,
        underlying="BANKNIFTY",
        option_type="PE",
        expiry_preference="current",
        itm_depth=1,  # 1st ITM put
        min_itm_amount=50.0,
        max_itm_amount=300.0,
        entry_time_start="10:00",
        entry_time_end="13:30",
        entry_trigger="pullback",
        lookback_periods=20,
        breakout_threshold=0.4,
        volume_confirmation=True,
        min_volume_ratio=1.1,
        position_type="fixed_amount",
        position_size=20000.0,
        stop_loss_type="percentage",
        stop_loss_value=30.0,
        profit_target_type="percentage",
        profit_target_value=40.0,
        exit_time="15:10",
        max_positions=2,
        cooldown_minutes=30,
        allow_reentry=False
    )
    
    strategies[nifty_call_breakout.strategy_name] = nifty_call_breakout
    strategies[banknifty_put_pullback.strategy_name] = banknifty_put_pullback
    
    return strategies


if __name__ == "__main__":
    # Create example configuration file
    config_manager = ConfigManager()
    
    # Add example strategies if no strategies exist
    if not config_manager.strategies:
        example_strategies = create_example_strategies()
        for strategy in example_strategies.values():
            config_manager.add_strategy(strategy)
        
        print("Created example strategies configuration file: strategies.json")
        print("Available strategies:")
        for name in example_strategies.keys():
            print(f"  - {name}")