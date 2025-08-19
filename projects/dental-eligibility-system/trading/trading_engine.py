"""
Main Trading Engine for Zerodha Options Trading System
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
from dataclasses import dataclass
import schedule

from config import ConfigManager, TradingConfig
from kite_api import ZerodhaAPI, PaperTradingAPI, OptionContract
from price_action import PriceActionAnalyzer, PriceActionSignal
from risk_manager import RiskManager, OptionsRiskManager, TradeRisk


@dataclass
class ActivePosition:
    """Represents an active trading position"""
    symbol: str
    strategy_name: str
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float]
    target_price: Optional[float]
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    
    def update_price(self, new_price: float):
        """Update current price and P&L"""
        self.current_price = new_price
        self.unrealized_pnl = self.quantity * (new_price - self.entry_price)


class TradingEngine:
    """Main trading engine that orchestrates all trading activities"""
    
    def __init__(self, config_file: str = "strategies.json"):
        # Initialize components
        self.config_manager = ConfigManager(config_file)
        self.setup_logging()
        
        # Initialize API
        system_settings = self.config_manager.system_settings
        if system_settings.trading_mode == "paper":
            self.api = PaperTradingAPI()
            if hasattr(system_settings, 'kite_api_key'):  # For market data
                real_api = ZerodhaAPI(system_settings.kite_api_key, system_settings.kite_access_token)
                self.api.set_real_api(real_api)
        else:
            self.api = ZerodhaAPI(system_settings.kite_api_key, system_settings.kite_access_token)
        
        # Initialize other components
        self.price_analyzer = PriceActionAnalyzer()
        self.risk_manager = OptionsRiskManager(system_settings.dict())
        
        # Trading state
        self.active_positions: Dict[str, ActivePosition] = {}
        self.pending_orders: Dict[str, dict] = {}
        self.last_signal_time: Dict[str, datetime] = {}
        
        # Control flags
        self.is_running = False
        self.main_thread: Optional[threading.Thread] = None
        
        self.logger.info("Trading Engine initialized")
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config_manager.system_settings.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config_manager.system_settings.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the trading engine"""
        if self.is_running:
            self.logger.warning("Trading engine is already running")
            return
        
        self.is_running = True
        self.logger.info("Starting Trading Engine")
        
        # Schedule daily reset
        schedule.every().day.at("09:00").do(self.daily_reset)
        
        # Start main trading loop in a separate thread
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        
        self.logger.info("Trading Engine started successfully")
    
    def stop(self):
        """Stop the trading engine"""
        self.logger.info("Stopping Trading Engine")
        self.is_running = False
        
        if self.main_thread:
            self.main_thread.join(timeout=10)
        
        self.logger.info("Trading Engine stopped")
    
    def daily_reset(self):
        """Reset daily limits and state"""
        self.logger.info("Performing daily reset")
        self.risk_manager.reset_daily_limits()
        self.last_signal_time.clear()
    
    def _main_loop(self):
        """Main trading loop"""
        while self.is_running:
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Check if market is open
                if not self.api.is_market_open():
                    time.sleep(60)  # Check every minute when market is closed
                    continue
                
                # Process enabled strategies
                enabled_strategies = self.config_manager.get_enabled_strategies()
                for strategy in enabled_strategies:
                    self._process_strategy(strategy)
                
                # Update existing positions
                self._update_positions()
                
                # Check exit conditions
                self._check_exits()
                
                # Sleep before next iteration
                time.sleep(30)  # Check every 30 seconds during market hours
                
            except Exception as e:
                self.logger.error(f"Error in main trading loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def _process_strategy(self, strategy: TradingConfig):
        """Process a single trading strategy"""
        try:
            strategy_name = strategy.strategy_name
            
            # Check if we're within trading hours for this strategy
            current_time = datetime.now().time()
            start_time = datetime.strptime(strategy.entry_time_start, "%H:%M").time()
            end_time = datetime.strptime(strategy.entry_time_end, "%H:%M").time()
            
            if not (start_time <= current_time <= end_time):
                return
            
            # Check cooldown period
            if strategy_name in self.last_signal_time:
                time_since_last = datetime.now() - self.last_signal_time[strategy_name]
                if time_since_last < timedelta(minutes=strategy.cooldown_minutes):
                    return
            
            # Check maximum positions limit
            strategy_positions = [pos for pos in self.active_positions.values() 
                                if pos.strategy_name == strategy_name]
            
            if len(strategy_positions) >= strategy.max_positions:
                return
            
            # Get suitable ITM options
            suitable_options = self._find_suitable_options(strategy)
            
            if not suitable_options:
                return
            
            # Analyze each option for trading signals
            for option_contract in suitable_options:
                signal = self._analyze_option_for_signal(option_contract, strategy)
                
                if signal and self._should_take_signal(signal, strategy):
                    self._execute_trade(option_contract, signal, strategy)
                    self.last_signal_time[strategy_name] = datetime.now()
                    break  # Only take one signal per strategy per cycle
        
        except Exception as e:
            self.logger.error(f"Error processing strategy {strategy.strategy_name}: {e}")
    
    def _find_suitable_options(self, strategy: TradingConfig) -> List[OptionContract]:
        """Find options that match strategy criteria"""
        try:
            # Get ITM options for the underlying
            itm_options = self.api.get_itm_options(
                underlying=strategy.underlying,
                option_type=strategy.option_type,
                itm_depth=strategy.itm_depth
            )
            
            if not itm_options:
                return []
            
            # Filter by ITM amount
            underlying_ltp = self.api.get_underlying_ltp(strategy.underlying)
            if not underlying_ltp:
                return []
            
            suitable_options = []
            for option in itm_options:
                if strategy.option_type == "CE":
                    itm_amount = underlying_ltp - option.strike
                else:  # PE
                    itm_amount = option.strike - underlying_ltp
                
                if strategy.min_itm_amount <= itm_amount <= strategy.max_itm_amount:
                    suitable_options.append(option)
            
            return suitable_options
            
        except Exception as e:
            self.logger.error(f"Error finding suitable options: {e}")
            return []
    
    def _analyze_option_for_signal(self, option_contract: OptionContract, 
                                 strategy: TradingConfig) -> Optional[PriceActionSignal]:
        """Analyze option for trading signal"""
        try:
            # Get historical data for underlying (since option data might be limited)
            underlying_data = self._get_underlying_data(strategy.underlying, strategy.lookback_periods)
            
            if underlying_data.empty:
                return None
            
            # Generate trading signal using price action analysis
            signal = self.price_analyzer.generate_trading_signal(
                df=underlying_data,
                strategy_config=strategy.dict()
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error analyzing option for signal: {e}")
            return None
    
    def _get_underlying_data(self, underlying: str, lookback_periods: int) -> 'pd.DataFrame':
        """Get historical data for underlying asset"""
        try:
            # Get instrument token for underlying
            instruments_df = self.api.get_instruments("NSE")
            underlying_instrument = instruments_df[instruments_df['tradingsymbol'] == underlying]
            
            if underlying_instrument.empty:
                self.logger.warning(f"Underlying {underlying} not found")
                return None
            
            instrument_token = underlying_instrument.iloc[0]['instrument_token']
            
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_periods + 10)  # Extra buffer
            
            historical_data = self.api.get_historical_data(
                instrument_token=instrument_token,
                interval="5minute",
                from_date=start_date,
                to_date=end_date
            )
            
            return historical_data.tail(lookback_periods * 5)  # 5 minutes bars
            
        except Exception as e:
            self.logger.error(f"Error getting underlying data: {e}")
            return None
    
    def _should_take_signal(self, signal: PriceActionSignal, strategy: TradingConfig) -> bool:
        """Determine if we should act on the trading signal"""
        try:
            # Check signal strength and confidence
            if signal.confidence < 0.5:  # Minimum confidence threshold
                return False
            
            # Check if signal direction matches strategy option type
            if strategy.option_type == "CE" and signal.signal_type != "BUY":
                return False
            elif strategy.option_type == "PE" and signal.signal_type != "SELL":
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating signal: {e}")
            return False
    
    def _execute_trade(self, option_contract: OptionContract, signal: PriceActionSignal, 
                      strategy: TradingConfig):
        """Execute a trade based on the signal"""
        try:
            # Get account balance
            account_info = self.api.get_account_balance()
            available_balance = account_info.get('available_margin', 100000)
            
            # Calculate stop loss and target
            current_price = self._get_option_price(option_contract)
            if not current_price:
                self.logger.warning(f"Could not get price for {option_contract.symbol}")
                return
            
            stop_loss, target_price = self._calculate_exit_levels(
                entry_price=current_price,
                strategy=strategy,
                signal=signal
            )
            
            # Calculate position size
            quantity = self.risk_manager.calculate_position_size(
                strategy_config=strategy.dict(),
                entry_price=current_price,
                stop_loss=stop_loss,
                account_balance=available_balance
            )
            
            # Validate trade with risk manager
            is_valid, message, risk_level = self.risk_manager.validate_trade(
                symbol=option_contract.symbol,
                quantity=quantity,
                price=current_price,
                stop_loss=stop_loss,
                account_balance=available_balance
            )
            
            if not is_valid:
                self.logger.warning(f"Trade rejected: {message}")
                return
            
            # Place the order
            order_id = self.api.place_order(
                symbol=option_contract.symbol,
                transaction_type="BUY",  # Always buying options in this system
                quantity=quantity,
                order_type="MARKET"
            )
            
            if order_id:
                # Record the position
                position = ActivePosition(
                    symbol=option_contract.symbol,
                    strategy_name=strategy.strategy_name,
                    quantity=quantity,
                    entry_price=current_price,
                    entry_time=datetime.now(),
                    stop_loss=stop_loss,
                    target_price=target_price,
                    current_price=current_price
                )
                
                self.active_positions[option_contract.symbol] = position
                
                # Record trade in risk manager
                self.risk_manager.record_trade(
                    symbol=option_contract.symbol,
                    quantity=quantity,
                    price=current_price,
                    trade_type="BUY"
                )
                
                self.logger.info(f"Trade executed: BUY {quantity} {option_contract.symbol} @ {current_price:.2f}")
                self.logger.info(f"Stop Loss: {stop_loss:.2f}, Target: {target_price:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
    
    def _get_option_price(self, option_contract: OptionContract) -> Optional[float]:
        """Get current market price for option"""
        try:
            quotes = self.api.get_quotes([option_contract.symbol])
            quote_data = quotes.get(option_contract.symbol)
            
            if quote_data:
                return quote_data.get('last_price')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting option price: {e}")
            return None
    
    def _calculate_exit_levels(self, entry_price: float, strategy: TradingConfig, 
                             signal: PriceActionSignal) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and target price levels"""
        try:
            stop_loss = None
            target_price = None
            
            # Calculate stop loss
            if strategy.stop_loss_type == "percentage":
                stop_loss = entry_price * (1 - strategy.stop_loss_value / 100)
            elif strategy.stop_loss_type == "amount":
                stop_loss = entry_price - strategy.stop_loss_value
            elif signal.stop_loss:
                stop_loss = signal.stop_loss
            
            # Calculate target price
            if strategy.profit_target_type == "percentage":
                target_price = entry_price * (1 + strategy.profit_target_value / 100)
            elif strategy.profit_target_type == "amount":
                target_price = entry_price + strategy.profit_target_value
            elif strategy.profit_target_type == "risk_reward" and stop_loss:
                risk_amount = entry_price - stop_loss
                target_price = entry_price + (risk_amount * strategy.profit_target_value)
            elif signal.target:
                target_price = signal.target
            
            return stop_loss, target_price
            
        except Exception as e:
            self.logger.error(f"Error calculating exit levels: {e}")
            return None, None
    
    def _update_positions(self):
        """Update prices and P&L for all active positions"""
        try:
            if not self.active_positions:
                return
            
            symbols = list(self.active_positions.keys())
            quotes = self.api.get_quotes(symbols)
            
            for symbol, position in self.active_positions.items():
                quote_data = quotes.get(symbol)
                if quote_data:
                    current_price = quote_data.get('last_price', position.current_price)
                    position.update_price(current_price)
            
        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")
    
    def _check_exits(self):
        """Check exit conditions for all active positions"""
        try:
            positions_to_exit = []
            
            for symbol, position in self.active_positions.items():
                # Get strategy config
                strategy = self.config_manager.get_strategy(position.strategy_name)
                if not strategy:
                    continue
                
                # Check time-based exit
                current_time = datetime.now().time()
                exit_time = datetime.strptime(strategy.exit_time, "%H:%M").time()
                
                if current_time >= exit_time:
                    positions_to_exit.append((symbol, "Time-based exit"))
                    continue
                
                # Create TradeRisk object for risk manager
                trade_risk = TradeRisk(
                    symbol=symbol,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    current_price=position.current_price,
                    stop_loss=position.stop_loss,
                    target_price=position.target_price
                )
                
                # Check exit conditions
                should_exit, reason = self.risk_manager.should_exit_position(
                    trade_risk=trade_risk,
                    strategy_config=strategy.dict()
                )
                
                if should_exit:
                    positions_to_exit.append((symbol, reason))
            
            # Execute exits
            for symbol, reason in positions_to_exit:
                self._exit_position(symbol, reason)
                
        except Exception as e:
            self.logger.error(f"Error checking exits: {e}")
    
    def _exit_position(self, symbol: str, reason: str):
        """Exit a position"""
        try:
            position = self.active_positions.get(symbol)
            if not position:
                return
            
            # Place sell order
            order_id = self.api.place_order(
                symbol=symbol,
                transaction_type="SELL",
                quantity=position.quantity,
                order_type="MARKET"
            )
            
            if order_id:
                # Record the trade
                self.risk_manager.record_trade(
                    symbol=symbol,
                    quantity=-position.quantity,  # Negative for sell
                    price=position.current_price,
                    trade_type="SELL",
                    pnl=position.unrealized_pnl
                )
                
                self.logger.info(f"Position exited: {symbol} - {reason}")
                self.logger.info(f"P&L: ₹{position.unrealized_pnl:.2f}")
                
                # Remove from active positions
                del self.active_positions[symbol]
        
        except Exception as e:
            self.logger.error(f"Error exiting position {symbol}: {e}")
    
    def get_portfolio_status(self) -> Dict:
        """Get comprehensive portfolio status"""
        try:
            account_info = self.api.get_account_balance()
            positions = list(self.active_positions.values())
            
            total_pnl = sum(pos.unrealized_pnl for pos in positions)
            total_positions_value = sum(abs(pos.quantity * pos.current_price) for pos in positions)
            
            risk_summary = self.risk_manager.get_risk_summary(
                account_balance=account_info.get('available_margin', 100000)
            )
            
            return {
                'timestamp': datetime.now().isoformat(),
                'account_balance': account_info,
                'active_positions_count': len(positions),
                'total_unrealized_pnl': total_pnl,
                'total_positions_value': total_positions_value,
                'risk_summary': risk_summary,
                'active_positions': [
                    {
                        'symbol': pos.symbol,
                        'strategy': pos.strategy_name,
                        'quantity': pos.quantity,
                        'entry_price': pos.entry_price,
                        'current_price': pos.current_price,
                        'unrealized_pnl': pos.unrealized_pnl,
                        'entry_time': pos.entry_time.isoformat()
                    }
                    for pos in positions
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio status: {e}")
            return {'error': str(e)}


def main():
    """Main function to run the trading engine"""
    engine = TradingEngine()
    
    try:
        # Start the engine
        engine.start()
        
        # Keep the main thread alive
        while engine.is_running:
            time.sleep(60)
            
            # Print status every 5 minutes
            if datetime.now().minute % 5 == 0:
                status = engine.get_portfolio_status()
                print(f"Active Positions: {status['active_positions_count']}")
                print(f"Unrealized P&L: ₹{status['total_unrealized_pnl']:.2f}")
                
    except KeyboardInterrupt:
        print("Shutting down trading engine...")
        engine.stop()


if __name__ == "__main__":
    main()