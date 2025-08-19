"""
Streamlit authentication page for Zerodha login
"""
import streamlit as st
import os
from pathlib import Path
from config import SystemSettings
from kite_api import ZerodhaAPI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_system_settings():
    """Load system settings"""
    try:
        return SystemSettings()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        st.info("Please make sure you have a .env file with KITE_API_KEY and KITE_API_SECRET")
        return None

def main():
    """Main authentication page"""
    st.set_page_config(
        page_title="Zerodha Authentication",
        page_icon="🔐",
        layout="wide"
    )
    
    st.title("🔐 Zerodha Authentication")
    st.write("Authenticate with your Zerodha account to start trading")
    
    # Load configuration
    settings = load_system_settings()
    if not settings:
        st.stop()
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'api_instance' not in st.session_state:
        st.session_state.api_instance = None
    
    try:
        # Try to create API instance and check if already authenticated
        api = ZerodhaAPI(settings.kite_api_key, settings.kite_api_secret)
        if api.is_authenticated():
            st.session_state.authenticated = True
            st.session_state.api_instance = api
    except ValueError as e:
        # Not authenticated yet, which is expected
        st.session_state.authenticated = False
        logger.info("No valid authentication found, user needs to login")
    except Exception as e:
        st.error(f"Error initializing API: {e}")
        st.stop()
    
    if st.session_state.authenticated:
        show_authenticated_page()
    else:
        show_login_page(settings)

def show_login_page(settings):
    """Show login page for authentication"""
    st.header("Step 1: Get Login URL")
    
    # Create temporary API instance to get login URL
    try:
        temp_api = ZerodhaAPI.__new__(ZerodhaAPI)
        temp_api.auth_handler = temp_api.__class__.__dict__['__init__'].__defaults__
        from auth_handler import ZerodhaAuthHandler
        auth_handler = ZerodhaAuthHandler(settings.kite_api_key, settings.kite_api_secret)
        login_url = auth_handler.get_login_url()
        
        st.write("1. Click the link below to login to your Zerodha account:")
        st.markdown(f"**[Zerodha Login URL]({login_url})**")
        st.write("2. After login, you'll be redirected to a URL containing a 'request_token'")
        st.write("3. Copy the 'request_token' from the redirect URL and paste it below")
        
        st.header("Step 2: Enter Request Token")
        request_token = st.text_input(
            "Request Token",
            placeholder="Enter the request_token from the redirect URL",
            help="The request_token appears in the URL after successful login"
        )
        
        if st.button("Authenticate", type="primary"):
            if request_token:
                authenticate_user(settings, request_token)
            else:
                st.error("Please enter the request token")
        
        # Show example redirect URL
        with st.expander("ℹ️ How to find the request token"):
            st.write("""
            After clicking the login URL and completing authentication, you'll be redirected to a URL like:
            
            `http://127.0.0.1:8080/?request_token=XXXXXXXXXXXXXXXXXXXXXX&action=login&status=success`
            
            Copy the value after `request_token=` (the X's in the example above).
            
            **Note:** You need to configure the redirect URL in your Zerodha app settings to `http://127.0.0.1:8080/`
            """)
    
    except Exception as e:
        st.error(f"Error getting login URL: {e}")

def authenticate_user(settings, request_token):
    """Authenticate user with request token"""
    try:
        with st.spinner("Authenticating..."):
            # Create API instance without existing authentication
            from auth_handler import ZerodhaAuthHandler
            auth_handler = ZerodhaAuthHandler(settings.kite_api_key, settings.kite_api_secret)
            
            # Generate session
            session_data = auth_handler.generate_session(request_token)
            
            # Create authenticated API instance
            api = ZerodhaAPI(settings.kite_api_key, settings.kite_api_secret)
            
            st.session_state.authenticated = True
            st.session_state.api_instance = api
            
            st.success("✅ Authentication successful!")
            st.rerun()
    
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        logger.error(f"Authentication error: {e}")

def show_authenticated_page():
    """Show authenticated user page"""
    st.success("✅ You are authenticated!")
    
    api = st.session_state.api_instance
    
    # Show user info
    user_info = api.get_user_info()
    if user_info:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 User Information")
            st.write(f"**Name:** {user_info.get('user_name', 'N/A')}")
            st.write(f"**User ID:** {user_info.get('user_id', 'N/A')}")
            st.write(f"**Email:** {user_info.get('email', 'N/A')}")
            st.write(f"**Broker:** {user_info.get('broker', 'N/A')}")
        
        with col2:
            st.subheader("🔗 Quick Actions")
            if st.button("🚀 Launch Trading Dashboard"):
                st.write("Run this command in your terminal:")
                st.code("python main.py dashboard")
            
            if st.button("⚙️ Run Trading Engine"):
                st.write("Run this command in your terminal:")
                st.code("python main.py engine")
    
    # Logout option
    if st.button("🚪 Logout"):
        api.auth_handler.logout()
        st.session_state.authenticated = False
        st.session_state.api_instance = None
        st.rerun()
    
    # Show market status
    st.subheader("📈 Market Status")
    if api.is_market_open():
        st.success("🟢 Market is OPEN")
    else:
        st.warning("🔴 Market is CLOSED")

if __name__ == "__main__":
    main()