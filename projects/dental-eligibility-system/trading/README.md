# 🎯 Zerodha Options Trading System

A comprehensive automated trading system for ITM (In-The-Money) options trading on the Zerodha platform using price action strategies.

## 🌟 Features

### ✅ **Automated ITM Options Trading**
- Automatically identifies and trades ITM options based on configurable depth
- Support for both Call (CE) and Put (PE) options
- Configurable ITM amount ranges

### ✅ **Price Action Strategies**
- **Breakout Strategy**: Detects breakouts above resistance/below support
- **Pullback Strategy**: Identifies pullback opportunities in trending markets
- **Market Open Strategy**: Gap-based trading at market open
- Volume confirmation and momentum analysis

### ✅ **Advanced Risk Management**
- Position sizing based on risk percentage or fixed amounts
- Multiple stop-loss types (percentage, fixed amount, ATR-based)
- Daily loss limits and position size limits
- Risk-reward ratio based profit targets
- Circuit breakers and trading halts

### ✅ **Multi-Strategy Configuration**
- JSON-based strategy configuration
- Multiple concurrent strategies
- Individual strategy enable/disable
- Strategy-specific parameters and risk controls

### ✅ **Real-time Monitoring**
- Web-based dashboard with Streamlit
- Live P&L tracking and position monitoring
- Performance analytics and metrics
- System logs and alerts

### ✅ **Paper Trading Mode**
- Test strategies without risking capital
- Full simulation with mock executions
- Performance tracking and analysis

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │    │  Trading Engine │    │   Kite API      │
│  (Streamlit)    │◄──►│                 │◄──►│   Integration   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
            ┌───────▼────┐ ┌────▼────┐ ┌────▼────────┐
            │Price Action│ │  Risk   │ │ Config      │
            │ Analyzer   │ │Manager  │ │ Manager     │
            └────────────┘ └─────────┘ └─────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Zerodha Kite Connect API credentials
- Active trading account with Zerodha

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd zerodha-options-trader
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API credentials
```

4. **Generate example strategies:**
```bash
python config.py
```

5. **Start the dashboard:**
```bash
streamlit run dashboard.py
```

6. **Access the dashboard:**
Open http://localhost:8501 in your browser

## 📋 Configuration

### Environment Variables (.env)

```bash
# Zerodha API Configuration
KITE_API_KEY=your_api_key_here
KITE_ACCESS_TOKEN=your_access_token_here

# Trading Configuration
TRADING_MODE=paper  # paper or live
MAX_DAILY_LOSS=5000  # Maximum daily loss in INR
MAX_POSITION_SIZE=50000  # Maximum position size per trade
RISK_PER_TRADE=2  # Risk per trade as % of capital

# Logging
LOG_LEVEL=INFO
LOG_FILE=trading.log
```

### Strategy Configuration (strategies.json)

Example strategy configuration:

```json
{
  "strategies": [
    {
      "strategy_name": "NIFTY_CALL_BREAKOUT",
      "enabled": true,
      "underlying": "NIFTY",
      "option_type": "CE",
      "expiry_preference": "current",
      "itm_depth": 2,
      "min_itm_amount": 20.0,
      "max_itm_amount": 150.0,
      "entry_time_start": "09:45",
      "entry_time_end": "14:00",
      "entry_trigger": "breakout",
      "lookback_periods": 15,
      "breakout_threshold": 0.6,
      "volume_confirmation": true,
      "position_type": "risk_based",
      "risk_percentage": 1.5,
      "stop_loss_type": "percentage",
      "stop_loss_value": 25.0,
      "profit_target_type": "risk_reward",
      "profit_target_value": 2.0,
      "exit_time": "15:15",
      "max_positions": 1,
      "cooldown_minutes": 45
    }
  ]
}
```

## 🎮 Usage

### Starting the System

1. **Configure your API credentials** in the `.env` file
2. **Start the dashboard**: `streamlit run dashboard.py`
3. **Configure strategies** using the web interface
4. **Start the trading engine** from the dashboard
5. **Monitor positions** and performance in real-time

### Strategy Configuration Parameters

#### **Basic Settings**
- `strategy_name`: Unique identifier for the strategy
- `enabled`: Whether the strategy is active
- `underlying`: NIFTY, BANKNIFTY, etc.
- `option_type`: CE (Call) or PE (Put)
- `expiry_preference`: current, next, or monthly

#### **ITM Configuration**
- `itm_depth`: How many strikes ITM (1=1st ITM, 2=2nd ITM)
- `min_itm_amount`: Minimum ITM amount in points
- `max_itm_amount`: Maximum ITM amount in points

#### **Entry Conditions**
- `entry_time_start/end`: Trading window
- `entry_trigger`: breakout, pullback, market_open, manual
- `lookback_periods`: Analysis period for price action
- `breakout_threshold`: Breakout sensitivity
- `volume_confirmation`: Require volume confirmation

#### **Position Sizing**
- `position_type`: fixed_amount, risk_based, percentage
- `position_size`: Fixed amount (for fixed_amount type)
- `risk_percentage`: Risk per trade as % of capital

#### **Risk Management**
- `stop_loss_type`: percentage, amount, atr_multiple
- `stop_loss_value`: Stop loss value
- `profit_target_type`: percentage, amount, risk_reward
- `profit_target_value`: Profit target value

#### **Time Management**
- `exit_time`: Mandatory exit time
- `max_positions`: Maximum concurrent positions
- `cooldown_minutes`: Cooldown between trades

## 🛡️ Risk Management

### Built-in Safety Features

- **Daily Loss Limits**: Automatic trading halt when daily loss limit is reached
- **Position Size Limits**: Maximum position size per trade
- **Risk Per Trade**: Percentage-based risk management
- **Circuit Breakers**: Emergency stops for extreme market conditions
- **Time-based Exits**: Mandatory exit before market close

### Risk Monitoring

- Real-time P&L tracking
- Portfolio risk assessment
- Daily and total drawdown monitoring
- Risk-reward ratio analysis

## 📊 Dashboard Features

### Main Dashboard Tabs

1. **Portfolio**: Overview of account balance, positions, and risk metrics
2. **Positions**: Detailed view of active positions with P&L
3. **Performance**: Performance analytics and trade history
4. **Strategies**: Strategy configuration and management
5. **Logs**: System logs and alerts

### Key Metrics

- Available margin and capital utilization
- Unrealized and daily P&L
- Active positions count
- Trading status and risk alerts
- Win rate and average profit/loss

## 🔧 Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with paper trading
export TRADING_MODE=paper

# Start the dashboard
streamlit run dashboard.py --server.port 8501

# Or run the engine directly
python trading_engine.py
```

### Testing

```bash
# Run unit tests (when available)
python -m pytest tests/

# Manual testing with paper trading
python config.py  # Generate test configuration
python trading_engine.py  # Run engine
```

### Customization

#### Adding New Strategies

1. **Define strategy parameters** in `config.py`
2. **Implement signal generation** in `price_action.py`
3. **Add strategy logic** to `trading_engine.py`
4. **Update dashboard** for new strategy visualization

#### Adding New Risk Controls

1. **Define risk parameters** in `risk_manager.py`
2. **Implement validation logic** in `RiskManager` class
3. **Integrate with trading engine** for real-time monitoring

## ⚠️ Important Notes

### Legal and Compliance
- **This system is for educational and personal use only**
- **Always comply with local regulations and broker terms**
- **Test thoroughly in paper trading mode before live trading**
- **Options trading involves significant risk of loss**

### Best Practices
- Start with small position sizes
- Use paper trading mode extensively
- Monitor system performance regularly
- Keep API credentials secure
- Maintain adequate account balance

### Limitations
- **Market data delays**: System uses real-time data but may have slight delays
- **Options liquidity**: ITM options may have lower liquidity
- **Network dependency**: Requires stable internet connection
- **Broker limitations**: Subject to Zerodha API rate limits

## 📈 Performance Optimization

### System Performance
- Use 5-minute intervals for analysis
- Cache frequently accessed data
- Optimize database queries (if using database logging)
- Monitor memory usage for long-running sessions

### Trading Performance
- Adjust parameters based on market conditions
- Regular backtesting and strategy validation
- Monitor slippage and execution quality
- Review and optimize risk parameters

## 🆘 Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify API key and access token
   - Check internet connection
   - Ensure account is active

2. **Strategy Not Executing**
   - Check strategy is enabled
   - Verify time windows
   - Check risk limits not exceeded
   - Review market conditions

3. **Dashboard Not Loading**
   - Check all dependencies installed
   - Verify port 8501 is available
   - Check system logs for errors

### Error Handling
- All errors are logged to the specified log file
- Dashboard displays error messages
- Trading engine has automatic recovery mechanisms
- Circuit breakers prevent cascading failures

## 📞 Support

For issues, questions, or contributions:
- Review the documentation
- Check system logs for error details
- Test in paper trading mode first
- Ensure all dependencies are correctly installed

---

**Disclaimer**: This software is provided for educational purposes only. Trading options involves substantial risk and may not be suitable for all investors. Past performance does not guarantee future results. Always trade at your own risk and never invest more than you can afford to lose.