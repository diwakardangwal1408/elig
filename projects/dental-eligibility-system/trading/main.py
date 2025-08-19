#!/usr/bin/env python3
"""
Main entry point for Zerodha Options Trading System
"""
import sys
import os
import argparse
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import ConfigManager, create_example_strategies
from trading_engine import TradingEngine
import subprocess


def create_example_config():
    """Create example configuration files"""
    print("Creating example configuration...")
    
    # Create .env file if it doesn't exist
    env_path = Path(".env")
    if not env_path.exists():
        env_example = Path(".env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_path)
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env file with your API credentials")
        else:
            print("❌ .env.example not found")
    
    # Create strategies configuration
    config_manager = ConfigManager()
    if not config_manager.strategies:
        example_strategies = create_example_strategies()
        for strategy in example_strategies.values():
            config_manager.add_strategy(strategy)
        print("✅ Created example strategies configuration")
    else:
        print("✅ Strategies configuration already exists")


def check_requirements():
    """Check if all requirements are satisfied"""
    print("Checking requirements...")
    
    try:
        import kiteconnect
        print("✅ kiteconnect library found")
    except ImportError:
        print("❌ kiteconnect library not found. Install with: pip install kiteconnect")
        return False
    
    try:
        import streamlit
        print("✅ streamlit library found")
    except ImportError:
        print("❌ streamlit library not found. Install with: pip install streamlit")
        return False
    
    # Check .env file
    env_path = Path(".env")
    if env_path.exists():
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found")
    
    # Check strategies configuration
    strategies_path = Path("strategies.json")
    if strategies_path.exists():
        print("✅ strategies.json found")
    else:
        print("⚠️  strategies.json not found")
    
    return True


def run_trading_engine():
    """Run the trading engine directly"""
    print("Starting Zerodha Options Trading Engine...")
    
    try:
        engine = TradingEngine()
        engine.start()
        
        print("✅ Trading Engine started successfully")
        print("📊 Press Ctrl+C to stop the engine")
        
        # Keep running until interrupted
        import time
        while engine.is_running:
            time.sleep(60)
            # Print status every 5 minutes
            if hasattr(engine, 'get_portfolio_status'):
                status = engine.get_portfolio_status()
                print(f"📈 Active Positions: {status.get('active_positions_count', 0)}")
                print(f"💰 Unrealized P&L: ₹{status.get('total_unrealized_pnl', 0):.2f}")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping trading engine...")
        engine.stop()
        print("✅ Trading engine stopped")
    
    except Exception as e:
        print(f"❌ Error running trading engine: {e}")


def run_dashboard():
    """Launch the Streamlit dashboard"""
    print("Launching Zerodha Options Trading Dashboard...")
    
    try:
        # Run streamlit dashboard
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "dashboard.py",
            "--server.port", "8501",
            "--server.headless", "true"
        ])
    
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")
    
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")


def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Requirements installed successfully")
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
    
    except FileNotFoundError:
        print("❌ requirements.txt not found")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Zerodha Options Trading System")
    parser.add_argument(
        "command",
        choices=["setup", "check", "dashboard", "engine", "install"],
        help="Command to execute"
    )
    parser.add_argument(
        "--config",
        default="strategies.json",
        help="Path to strategies configuration file"
    )
    
    args = parser.parse_args()
    
    print("🎯 Zerodha Options Trading System")
    print("=" * 40)
    
    if args.command == "install":
        install_requirements()
    
    elif args.command == "setup":
        create_example_config()
        print("\n📋 Setup complete! Next steps:")
        print("1. Edit .env file with your API credentials")
        print("2. Review and modify strategies.json")
        print("3. Run: python main.py dashboard")
    
    elif args.command == "check":
        if check_requirements():
            print("\n✅ All requirements satisfied!")
        else:
            print("\n❌ Some requirements not met. Run: python main.py install")
    
    elif args.command == "dashboard":
        if check_requirements():
            run_dashboard()
        else:
            print("❌ Requirements not met. Run setup first.")
    
    elif args.command == "engine":
        if check_requirements():
            run_trading_engine()
        else:
            print("❌ Requirements not met. Run setup first.")
    
    print("\n👋 Thank you for using Zerodha Options Trading System!")


if __name__ == "__main__":
    main()