"""
Zerodha Kite API Integration Module
"""
from kiteconnect import KiteConnect, KiteTicker
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
from enum import Enum


class OrderStatus(Enum):
    COMPLETE = "COMPLETE"
    OPEN = "OPEN"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    

class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class OptionContract:
    """Represents an option contract"""
    symbol: str
    strike: float
    expiry: datetime
    option_type: str  # CE or PE
    instrument_token: int
    lot_size: int
    underlying: str
    ltp: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    quantity: int
    average_price: float
    ltp: float
    pnl: float
    unrealized_pnl: float
    realized_pnl: float


@dataclass
class Order:
    """Represents a trading order"""
    order_id: str
    symbol: str
    transaction_type: str
    quantity: int
    price: float
    order_type: str
    status: OrderStatus
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: float = 0.0


class ZerodhaAPI:
    """Zerodha Kite API wrapper for options trading"""
    
    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        
        # Cache for instruments and market data
        self._instruments_cache = {}
        self._options_cache = {}
        self._last_cache_update = None
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now()
        
        # Skip weekends
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
            
        # Market hours: 9:15 AM to 3:30 PM
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def get_instruments(self, exchange: str = "NFO") -> pd.DataFrame:
        """Get all instruments for the given exchange"""
        try:
            if (self._last_cache_update is None or 
                datetime.now() - self._last_cache_update > timedelta(hours=1)):
                
                instruments = self.kite.instruments(exchange)
                self._instruments_cache[exchange] = pd.DataFrame(instruments)
                self._last_cache_update = datetime.now()
                self.logger.info(f"Updated instruments cache for {exchange}")
            
            return self._instruments_cache[exchange]
        
        except Exception as e:
            self.logger.error(f"Error fetching instruments: {e}")
            return pd.DataFrame()
    
    def get_option_chain(self, underlying: str, expiry: Optional[str] = None) -> List[OptionContract]:
        """Get option chain for given underlying and expiry"""
        try:
            instruments_df = self.get_instruments("NFO")
            
            # Filter for the underlying
            option_instruments = instruments_df[
                (instruments_df['name'] == underlying) & 
                (instruments_df['instrument_type'].isin(['CE', 'PE']))
            ].copy()
            
            if expiry:
                option_instruments = option_instruments[option_instruments['expiry'] == expiry]
            else:
                # Get nearest expiry
                option_instruments['expiry'] = pd.to_datetime(option_instruments['expiry'])
                nearest_expiry = option_instruments['expiry'].min()
                option_instruments = option_instruments[option_instruments['expiry'] == nearest_expiry]
            
            # Convert to OptionContract objects
            option_contracts = []
            for _, row in option_instruments.iterrows():
                contract = OptionContract(
                    symbol=row['tradingsymbol'],
                    strike=float(row['strike']),
                    expiry=pd.to_datetime(row['expiry']),
                    option_type=row['instrument_type'],
                    instrument_token=int(row['instrument_token']),
                    lot_size=int(row['lot_size']),
                    underlying=underlying
                )
                option_contracts.append(contract)
            
            return option_contracts
        
        except Exception as e:
            self.logger.error(f"Error fetching option chain: {e}")
            return []
    
    def get_underlying_ltp(self, symbol: str) -> Optional[float]:
        """Get last traded price for underlying asset"""
        try:
            # Get instrument token for underlying
            instruments_df = self.get_instruments("NSE")
            underlying_instrument = instruments_df[instruments_df['tradingsymbol'] == symbol]
            
            if underlying_instrument.empty:
                self.logger.warning(f"Underlying {symbol} not found")
                return None
            
            instrument_token = underlying_instrument.iloc[0]['instrument_token']
            quote = self.kite.quote([instrument_token])
            
            return quote[str(instrument_token)]['last_price']
        
        except Exception as e:
            self.logger.error(f"Error fetching underlying LTP: {e}")
            return None
    
    def get_itm_options(self, underlying: str, option_type: str, 
                       itm_depth: int = 1, expiry: Optional[str] = None) -> List[OptionContract]:
        """Get ITM options based on current underlying price"""
        try:
            # Get current underlying price
            underlying_ltp = self.get_underlying_ltp(underlying)
            if not underlying_ltp:
                return []
            
            # Get option chain
            option_chain = self.get_option_chain(underlying, expiry)
            
            # Filter by option type
            options = [opt for opt in option_chain if opt.option_type == option_type]
            
            if option_type == "CE":  # Calls
                # For calls, ITM means strike < underlying price
                itm_options = [opt for opt in options if opt.strike < underlying_ltp]
                # Sort by strike descending to get closest ITM strikes first
                itm_options.sort(key=lambda x: x.strike, reverse=True)
            else:  # Puts
                # For puts, ITM means strike > underlying price
                itm_options = [opt for opt in options if opt.strike > underlying_ltp]
                # Sort by strike ascending to get closest ITM strikes first
                itm_options.sort(key=lambda x: x.strike)
            
            # Return the requested ITM depth
            return itm_options[:itm_depth] if len(itm_options) >= itm_depth else itm_options
        
        except Exception as e:
            self.logger.error(f"Error fetching ITM options: {e}")
            return []
    
    def get_quotes(self, instruments: List[str]) -> Dict[str, Dict]:
        """Get real-time quotes for given instruments"""
        try:
            return self.kite.quote(instruments)
        except Exception as e:
            self.logger.error(f"Error fetching quotes: {e}")
            return {}
    
    def get_historical_data(self, instrument_token: int, interval: str, 
                          from_date: datetime, to_date: datetime) -> pd.DataFrame:
        """Get historical OHLCV data"""
        try:
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            return pd.DataFrame(data)
        
        except Exception as e:
            self.logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def place_order(self, symbol: str, transaction_type: str, quantity: int, 
                   order_type: str = "MARKET", price: Optional[float] = None,
                   trigger_price: Optional[float] = None, 
                   product: str = "MIS") -> Optional[str]:
        """Place a trading order"""
        try:
            order_params = {
                'tradingsymbol': symbol,
                'exchange': "NFO",
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'product': product
            }
            
            if price:
                order_params['price'] = price
            if trigger_price:
                order_params['trigger_price'] = trigger_price
            
            order_id = self.kite.place_order(**order_params)
            self.logger.info(f"Order placed: {order_id} for {symbol}")
            return order_id
        
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            self.kite.cancel_order(order_id=order_id)
            self.logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return False
    
    def modify_order(self, order_id: str, **kwargs) -> bool:
        """Modify an existing order"""
        try:
            self.kite.modify_order(order_id=order_id, **kwargs)
            self.logger.info(f"Order modified: {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error modifying order: {e}")
            return False
    
    def get_orders(self) -> List[Order]:
        """Get all orders for the day"""
        try:
            orders_data = self.kite.orders()
            orders = []
            
            for order_data in orders_data:
                order = Order(
                    order_id=order_data['order_id'],
                    symbol=order_data['tradingsymbol'],
                    transaction_type=order_data['transaction_type'],
                    quantity=order_data['quantity'],
                    price=order_data.get('price', 0.0),
                    order_type=order_data['order_type'],
                    status=OrderStatus(order_data['status']),
                    filled_quantity=order_data.get('filled_quantity', 0),
                    pending_quantity=order_data.get('pending_quantity', 0),
                    average_price=order_data.get('average_price', 0.0)
                )
                orders.append(order)
            
            return orders
        
        except Exception as e:
            self.logger.error(f"Error fetching orders: {e}")
            return []
    
    def get_positions(self) -> List[Position]:
        """Get current positions"""
        try:
            positions_data = self.kite.positions()
            positions = []
            
            for pos_data in positions_data['day']:  # Day positions
                if pos_data['quantity'] != 0:  # Only active positions
                    position = Position(
                        symbol=pos_data['tradingsymbol'],
                        quantity=pos_data['quantity'],
                        average_price=pos_data['average_price'],
                        ltp=pos_data['last_price'],
                        pnl=pos_data['pnl'],
                        unrealized_pnl=pos_data['unrealised_pnl'],
                        realized_pnl=pos_data['realised_pnl']
                    )
                    positions.append(position)
            
            return positions
        
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_account_balance(self) -> Dict[str, float]:
        """Get account balance and margin information"""
        try:
            margins = self.kite.margins()
            return {
                'cash': margins['equity']['net'],
                'available_margin': margins['equity']['available']['live_balance'],
                'used_margin': margins['equity']['utilised']['debits']
            }
        except Exception as e:
            self.logger.error(f"Error fetching account balance: {e}")
            return {'cash': 0.0, 'available_margin': 0.0, 'used_margin': 0.0}


# Paper Trading Mock API (for testing)
class PaperTradingAPI:
    """Mock API for paper trading simulation"""
    
    def __init__(self, initial_balance: float = 100000.0):
        self.balance = initial_balance
        self.positions = {}
        self.orders = {}
        self.order_counter = 1
        self.logger = logging.getLogger(__name__)
        
        # Use real API for market data
        self.real_api = None
    
    def set_real_api(self, api: ZerodhaAPI):
        """Set real API instance for market data"""
        self.real_api = api
    
    def place_order(self, symbol: str, transaction_type: str, quantity: int, 
                   order_type: str = "MARKET", price: Optional[float] = None) -> str:
        """Simulate order placement"""
        order_id = f"PAPER_{self.order_counter:06d}"
        self.order_counter += 1
        
        # Get current market price if real API is available
        if self.real_api:
            quotes = self.real_api.get_quotes([symbol])
            market_price = quotes.get(symbol, {}).get('last_price', price or 100.0)
        else:
            market_price = price or 100.0
        
        # Simulate immediate execution for market orders
        if order_type == "MARKET":
            self._execute_order(order_id, symbol, transaction_type, quantity, market_price)
        
        self.orders[order_id] = Order(
            order_id=order_id,
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price=market_price,
            order_type=order_type,
            status=OrderStatus.COMPLETE,
            filled_quantity=quantity,
            average_price=market_price
        )
        
        self.logger.info(f"Paper order executed: {order_id} - {transaction_type} {quantity} {symbol} @ {market_price}")
        return order_id
    
    def _execute_order(self, order_id: str, symbol: str, transaction_type: str, 
                      quantity: int, price: float):
        """Execute paper trade"""
        total_value = quantity * price
        
        if transaction_type == "BUY":
            self.balance -= total_value
            current_qty = self.positions.get(symbol, 0)
            self.positions[symbol] = current_qty + quantity
        else:  # SELL
            self.balance += total_value
            current_qty = self.positions.get(symbol, 0)
            self.positions[symbol] = current_qty - quantity
            
            if self.positions[symbol] == 0:
                del self.positions[symbol]
    
    def get_account_balance(self) -> Dict[str, float]:
        """Get paper trading balance"""
        return {
            'cash': self.balance,
            'available_margin': self.balance,
            'used_margin': 0.0
        }
    
    # Delegate market data methods to real API
    def __getattr__(self, name):
        if self.real_api and hasattr(self.real_api, name):
            return getattr(self.real_api, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")