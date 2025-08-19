"""
Zerodha Authentication Handler
Handles OAuth flow with request_token and access_token generation
"""
import hashlib
import logging
from typing import Optional, Dict, Any
from kiteconnect import KiteConnect
import json
from pathlib import Path


class ZerodhaAuthHandler:
    """Handles Zerodha authentication and token management"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)
        self.access_token: Optional[str] = None
        self.tokens_file = Path("zerodha_tokens.json")
        self.logger = logging.getLogger(__name__)
    
    def get_login_url(self) -> str:
        """Get the login URL for Zerodha authentication"""
        return self.kite.login_url()
    
    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """Generate access token from request token"""
        try:
            # Generate checksum
            checksum = hashlib.sha256(
                (self.api_key + request_token + self.api_secret).encode("utf-8")
            ).hexdigest()
            
            # Generate session
            session_data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            
            self.access_token = session_data["access_token"]
            
            # Save tokens to file for future use
            self._save_tokens(session_data)
            
            self.logger.info("Successfully generated access token")
            return session_data
            
        except Exception as e:
            self.logger.error(f"Error generating session: {e}")
            raise
    
    def load_saved_tokens(self) -> bool:
        """Load previously saved tokens"""
        try:
            if self.tokens_file.exists():
                with open(self.tokens_file, 'r') as f:
                    token_data = json.load(f)
                    
                self.access_token = token_data.get("access_token")
                
                # Validate token by making a test API call
                if self.access_token and self._validate_token():
                    self.logger.info("Loaded valid access token from file")
                    return True
                else:
                    self.logger.warning("Saved token is invalid")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error loading saved tokens: {e}")
            return False
    
    def _validate_token(self) -> bool:
        """Validate if the current access token is valid"""
        try:
            if not self.access_token:
                return False
                
            # Set token and try to get profile
            self.kite.set_access_token(self.access_token)
            profile = self.kite.profile()
            
            return profile is not None
            
        except Exception as e:
            self.logger.debug(f"Token validation failed: {e}")
            return False
    
    def _save_tokens(self, session_data: Dict[str, Any]) -> None:
        """Save tokens to file"""
        try:
            token_info = {
                "access_token": session_data.get("access_token"),
                "user_name": session_data.get("user_name"),
                "user_id": session_data.get("user_id"),
                "user_shortname": session_data.get("user_shortname"),
                "email": session_data.get("email"),
                "user_type": session_data.get("user_type"),
                "broker": session_data.get("broker"),
                "exchanges": session_data.get("exchanges", []),
                "products": session_data.get("products", []),
                "order_types": session_data.get("order_types", []),
                "avatar_url": session_data.get("avatar_url"),
                "public_token": session_data.get("public_token"),
                "refresh_token": session_data.get("refresh_token"),
                "silo": session_data.get("silo"),
                "api_key": session_data.get("api_key"),
                "login_time": session_data.get("login_time"),
                "meta": session_data.get("meta", {})
            }
            
            with open(self.tokens_file, 'w') as f:
                json.dump(token_info, f, indent=2, default=str)
                
            self.logger.info("Tokens saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving tokens: {e}")
    
    def get_authenticated_kite(self) -> Optional[KiteConnect]:
        """Get authenticated KiteConnect instance"""
        if self.access_token:
            self.kite.set_access_token(self.access_token)
            return self.kite
        return None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.access_token is not None and self._validate_token()
    
    def logout(self) -> None:
        """Clear authentication tokens"""
        self.access_token = None
        if self.tokens_file.exists():
            self.tokens_file.unlink()
        self.logger.info("Logged out successfully")
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get user information if authenticated"""
        try:
            if self.is_authenticated():
                return self.kite.profile()
            return None
        except Exception as e:
            self.logger.error(f"Error fetching user info: {e}")
            return None