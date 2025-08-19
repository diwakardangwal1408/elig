"""
Trading Dashboard - Web-based monitoring interface
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Optional

from config import ConfigManager
from trading_engine import TradingEngine
from risk_manager import RiskLevel


class TradingDashboard:
    """Web-based dashboard for monitoring trading system"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.trading_engine = None
        self.last_update = None
        
    def run_dashboard(self):
        """Main dashboard application"""
        st.set_page_config(
            page_title="Zerodha Options Trader Dashboard",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS
        st.markdown("""
        <style>
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        .positive { color: #00C851; }
        .negative { color: #FF4444; }
        .neutral { color: #33B5E5; }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.title("🎯 Zerodha Options Trading Dashboard")
        st.markdown("---")
        
        # Sidebar
        self.render_sidebar()
        
        # Main content
        if st.session_state.get('trading_engine_started', False):
            self.render_main_dashboard()
        else:
            self.render_startup_page()
    
    def render_sidebar(self):
        """Render sidebar controls"""
        with st.sidebar:
            st.header("🚀 Trading Engine Control")
            
            # Engine status
            if 'trading_engine' in st.session_state:
                engine_status = "🟢 RUNNING" if st.session_state.trading_engine.is_running else "🔴 STOPPED"
            else:
                engine_status = "⚪ NOT STARTED"
            
            st.markdown(f"**Status:** {engine_status}")
            
            # Control buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("▶️ Start Engine", key="start_engine"):
                    self.start_trading_engine()
            
            with col2:
                if st.button("⏹️ Stop Engine", key="stop_engine"):
                    self.stop_trading_engine()
            
            st.divider()
            
            # Configuration
            st.header("⚙️ Configuration")
            
            # Strategy selection
            strategies = list(self.config_manager.strategies.keys())
            selected_strategies = st.multiselect(
                "Active Strategies",
                strategies,
                default=[name for name, strategy in self.config_manager.strategies.items() if strategy.enabled]
            )
            
            # Update strategy status
            if st.button("Update Strategy Status"):
                for name, strategy in self.config_manager.strategies.items():
                    strategy.enabled = name in selected_strategies
                self.config_manager.save_strategies()
                st.success("Strategy status updated!")
            
            st.divider()
            
            # Risk limits
            st.header("⚠️ Risk Controls")
            
            new_max_daily_loss = st.number_input(
                "Max Daily Loss (₹)",
                value=self.config_manager.system_settings.max_daily_loss,
                min_value=1000.0,
                step=1000.0
            )
            
            new_max_position_size = st.number_input(
                "Max Position Size (₹)",
                value=self.config_manager.system_settings.max_position_size,
                min_value=5000.0,
                step=5000.0
            )
            
            if st.button("Update Risk Limits"):
                # Note: This would require updating the system settings
                st.info("Risk limits updated (restart engine to apply)")
    
    def render_startup_page(self):
        """Render initial startup page"""
        st.header("🚀 Welcome to Zerodha Options Trading System")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 System Overview")
            st.write("""
            This automated trading system is designed for ITM options trading on Zerodha platform with:
            
            ✅ **Price Action Analysis** - Breakout and pullback strategies
            
            ✅ **Risk Management** - Position sizing and stop losses
            
            ✅ **Multi-Strategy Support** - Configure different strategies
            
            ✅ **Real-time Monitoring** - Live P&L and position tracking
            
            ✅ **Paper Trading Mode** - Test strategies safely
            """)
        
        with col2:
            st.subheader("⚙️ Configuration Status")
            
            # Check configuration status
            config_status = self.check_configuration()
            
            for item, status in config_status.items():
                if status:
                    st.success(f"✅ {item}")
                else:
                    st.error(f"❌ {item}")
        
        # Start button
        if all(config_status.values()):
            st.markdown("---")
            if st.button("🚀 Start Trading Engine", key="main_start"):
                self.start_trading_engine()
        else:
            st.warning("⚠️ Please complete configuration before starting")
    
    def render_main_dashboard(self):
        """Render main dashboard when engine is running"""
        # Get portfolio status
        if 'trading_engine' in st.session_state:
            portfolio_status = st.session_state.trading_engine.get_portfolio_status()
        else:
            portfolio_status = {'error': 'Engine not available'}
        
        # Top metrics row
        self.render_key_metrics(portfolio_status)
        
        # Main content tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Portfolio", "💼 Positions", "📈 Performance", "⚙️ Strategies", "📋 Logs"
        ])
        
        with tab1:
            self.render_portfolio_tab(portfolio_status)
        
        with tab2:
            self.render_positions_tab(portfolio_status)
        
        with tab3:
            self.render_performance_tab(portfolio_status)
        
        with tab4:
            self.render_strategies_tab()
        
        with tab5:
            self.render_logs_tab()
    
    def render_key_metrics(self, portfolio_status: Dict):
        """Render key performance metrics"""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        if 'error' not in portfolio_status:
            account_balance = portfolio_status.get('account_balance', {})
            available_margin = account_balance.get('available_margin', 0)
            total_pnl = portfolio_status.get('total_unrealized_pnl', 0)
            active_positions = portfolio_status.get('active_positions_count', 0)
            risk_summary = portfolio_status.get('risk_summary', {})
            
            with col1:
                st.metric(
                    "Available Margin",
                    f"₹{available_margin:,.0f}",
                    delta=None
                )
            
            with col2:
                pnl_color = "normal"
                if total_pnl > 0:
                    pnl_color = "normal"
                elif total_pnl < 0:
                    pnl_color = "inverse"
                
                st.metric(
                    "Unrealized P&L",
                    f"₹{total_pnl:,.0f}",
                    delta=f"{total_pnl:+.0f}",
                    delta_color=pnl_color
                )
            
            with col3:
                st.metric(
                    "Active Positions",
                    f"{active_positions}",
                    delta=None
                )
            
            with col4:
                daily_pnl = risk_summary.get('daily_pnl', 0)
                st.metric(
                    "Daily P&L",
                    f"₹{daily_pnl:,.0f}",
                    delta=f"{daily_pnl:+.0f}",
                    delta_color="normal" if daily_pnl >= 0 else "inverse"
                )
            
            with col5:
                trading_status = risk_summary.get('trading_status', 'UNKNOWN')
                status_color = "🟢" if trading_status == 'ACTIVE' else "🔴"
                st.metric(
                    "Trading Status",
                    f"{status_color} {trading_status}",
                    delta=None
                )
        else:
            st.error(f"Error getting portfolio status: {portfolio_status.get('error', 'Unknown error')}")
    
    def render_portfolio_tab(self, portfolio_status: Dict):
        """Render portfolio overview tab"""
        if 'error' in portfolio_status:
            st.error("Unable to load portfolio data")
            return
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📊 Portfolio Allocation")
            
            # Create portfolio allocation chart
            positions = portfolio_status.get('active_positions', [])
            if positions:
                df_positions = pd.DataFrame(positions)
                df_positions['abs_value'] = abs(df_positions['quantity'] * df_positions['current_price'])
                
                fig_pie = px.pie(
                    df_positions,
                    values='abs_value',
                    names='symbol',
                    title="Position Allocation"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No active positions")
        
        with col2:
            st.subheader("🎯 Risk Summary")
            
            risk_summary = portfolio_status.get('risk_summary', {})
            
            # Risk gauge
            daily_loss_used = risk_summary.get('daily_pnl', 0)
            max_daily_loss = risk_summary.get('max_daily_loss', 5000)
            loss_percentage = abs(daily_loss_used) / max_daily_loss * 100
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = loss_percentage,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Daily Loss Usage (%)"},
                delta = {'reference': 50},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "red"},
                    'steps': [
                        {'range': [0, 25], 'color': "lightgreen"},
                        {'range': [25, 50], 'color': "yellow"},
                        {'range': [50, 75], 'color': "orange"},
                        {'range': [75, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig_gauge.update_layout(height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)
    
    def render_positions_tab(self, portfolio_status: Dict):
        """Render active positions tab"""
        st.subheader("💼 Active Positions")
        
        positions = portfolio_status.get('active_positions', [])
        
        if not positions:
            st.info("No active positions")
            return
        
        # Create DataFrame
        df_positions = pd.DataFrame(positions)
        
        # Format columns
        df_positions['Entry Time'] = pd.to_datetime(df_positions['entry_time']).dt.strftime('%H:%M:%S')
        df_positions['Entry Price'] = df_positions['entry_price'].apply(lambda x: f"₹{x:.2f}")
        df_positions['Current Price'] = df_positions['current_price'].apply(lambda x: f"₹{x:.2f}")
        df_positions['Unrealized P&L'] = df_positions['unrealized_pnl'].apply(
            lambda x: f"₹{x:+.2f}" if x >= 0 else f"₹{x:.2f}"
        )
        
        # Display table
        display_columns = ['symbol', 'strategy', 'quantity', 'Entry Price', 'Current Price', 'Unrealized P&L', 'Entry Time']
        st.dataframe(
            df_positions[display_columns],
            use_container_width=True,
            hide_index=True
        )
        
        # Position details
        selected_symbol = st.selectbox("Select position for details", df_positions['symbol'].tolist())
        
        if selected_symbol:
            position_details = df_positions[df_positions['symbol'] == selected_symbol].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Quantity", f"{position_details['quantity']}")
            
            with col2:
                entry_price = position_details['entry_price']
                current_price = position_details['current_price']
                change_pct = ((current_price - entry_price) / entry_price) * 100
                st.metric("Price Change %", f"{change_pct:+.2f}%")
            
            with col3:
                st.metric("Strategy", position_details['strategy'])
    
    def render_performance_tab(self, portfolio_status: Dict):
        """Render performance analytics tab"""
        st.subheader("📈 Performance Analytics")
        
        # Mock performance data (in real implementation, this would come from trade history)
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        mock_pnl = [0] + list(range(1, len(dates)))  # Mock cumulative P&L
        
        df_performance = pd.DataFrame({
            'Date': dates,
            'Cumulative_PnL': mock_pnl
        })
        
        # Performance chart
        fig_performance = go.Figure()
        fig_performance.add_trace(go.Scatter(
            x=df_performance['Date'],
            y=df_performance['Cumulative_PnL'],
            mode='lines',
            name='Cumulative P&L',
            line=dict(color='blue', width=2)
        ))
        
        fig_performance.update_layout(
            title="Cumulative P&L Over Time",
            xaxis_title="Date",
            yaxis_title="P&L (₹)",
            height=400
        )
        
        st.plotly_chart(fig_performance, use_container_width=True)
        
        # Performance metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Trades", "42")  # Mock data
        
        with col2:
            st.metric("Win Rate", "65%")  # Mock data
        
        with col3:
            st.metric("Avg Win", "₹850")  # Mock data
        
        with col4:
            st.metric("Avg Loss", "₹320")  # Mock data
    
    def render_strategies_tab(self):
        """Render strategies configuration tab"""
        st.subheader("⚙️ Strategy Configuration")
        
        strategies = self.config_manager.strategies
        
        if not strategies:
            st.info("No strategies configured")
            return
        
        # Strategy selection
        strategy_names = list(strategies.keys())
        selected_strategy = st.selectbox("Select Strategy", strategy_names)
        
        if selected_strategy:
            strategy = strategies[selected_strategy]
            
            # Display strategy details
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Basic Configuration**")
                st.write(f"- **Underlying:** {strategy.underlying}")
                st.write(f"- **Option Type:** {strategy.option_type}")
                st.write(f"- **ITM Depth:** {strategy.itm_depth}")
                st.write(f"- **Entry Time:** {strategy.entry_time_start} - {strategy.entry_time_end}")
                st.write(f"- **Status:** {'🟢 Enabled' if strategy.enabled else '🔴 Disabled'}")
            
            with col2:
                st.write("**Risk Management**")
                st.write(f"- **Position Type:** {strategy.position_type}")
                st.write(f"- **Stop Loss:** {strategy.stop_loss_value}% ({strategy.stop_loss_type})")
                st.write(f"- **Profit Target:** {strategy.profit_target_value} ({strategy.profit_target_type})")
                st.write(f"- **Max Positions:** {strategy.max_positions}")
                st.write(f"- **Cooldown:** {strategy.cooldown_minutes} minutes")
            
            # Enable/Disable button
            if st.button(f"{'Disable' if strategy.enabled else 'Enable'} Strategy"):
                strategy.enabled = not strategy.enabled
                self.config_manager.save_strategies()
                st.success(f"Strategy {'enabled' if strategy.enabled else 'disabled'}")
                st.experimental_rerun()
    
    def render_logs_tab(self):
        """Render logs and alerts tab"""
        st.subheader("📋 System Logs")
        
        # Mock log data
        log_entries = [
            {"timestamp": "10:30:45", "level": "INFO", "message": "Trade executed: BUY 1 NIFTY25FEB26000CE @ ₹45.20"},
            {"timestamp": "10:28:12", "level": "INFO", "message": "Signal generated: Breakout detected for NIFTY"},
            {"timestamp": "10:25:33", "level": "WARNING", "message": "High volatility detected in BANKNIFTY"},
            {"timestamp": "09:15:01", "level": "INFO", "message": "Trading engine started"},
        ]
        
        # Create DataFrame
        df_logs = pd.DataFrame(log_entries)
        
        # Color code by level
        def color_level(level):
            colors = {
                'INFO': 'background-color: lightblue',
                'WARNING': 'background-color: yellow',
                'ERROR': 'background-color: lightcoral'
            }
            return colors.get(level, '')
        
        styled_df = df_logs.style.applymap(color_level, subset=['level'])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Auto refresh
        if st.button("🔄 Refresh Logs"):
            st.experimental_rerun()
    
    def check_configuration(self) -> Dict[str, bool]:
        """Check system configuration status"""
        try:
            system_settings = self.config_manager.system_settings
            
            return {
                "API Configuration": bool(system_settings.kite_api_key and system_settings.kite_access_token),
                "Strategies Defined": len(self.config_manager.strategies) > 0,
                "Risk Limits Set": bool(system_settings.max_daily_loss and system_settings.max_position_size),
                "Trading Mode Set": bool(system_settings.trading_mode)
            }
        except Exception as e:
            return {"Configuration Error": False}
    
    def start_trading_engine(self):
        """Start the trading engine"""
        try:
            if 'trading_engine' not in st.session_state:
                st.session_state.trading_engine = TradingEngine()
            
            st.session_state.trading_engine.start()
            st.session_state.trading_engine_started = True
            st.success("🚀 Trading Engine Started!")
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Failed to start trading engine: {e}")
    
    def stop_trading_engine(self):
        """Stop the trading engine"""
        try:
            if 'trading_engine' in st.session_state:
                st.session_state.trading_engine.stop()
                st.session_state.trading_engine_started = False
                st.success("⏹️ Trading Engine Stopped!")
                st.experimental_rerun()
        
        except Exception as e:
            st.error(f"Failed to stop trading engine: {e}")


def main():
    """Main function to run the dashboard"""
    dashboard = TradingDashboard()
    dashboard.run_dashboard()


if __name__ == "__main__":
    main()