from authlib.integrations.httpx_client import OAuth2Client
import json
import os
import time
import logging
import webbrowser
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchwartzAuthManager:
    """Manages Schwartz API authentication using OAuth2."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_path: str = "schwab_token.json",
        callback_url: str = "https://127.0.0.1",  # Must match Schwab configuration
        auth_url: str = "https://api.schwabapi.com/v1/oauth/authorize",
        token_url: str = "https://api.schwabapi.com/v1/oauth/token"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path
        self.callback_url = callback_url
        self.auth_url = auth_url
        self.token_url = token_url
        self.token = self._load_token()
        
    def _load_token(self) -> dict:
        """Load token from file if it exists and is not expired."""
        if not os.path.exists(self.token_path):
            return None
            
        try:
            with open(self.token_path, 'r') as f:
                token = json.load(f)
                
            # Check if token is expired (7 days max lifetime)
            if 'created_at' in token:
                age = time.time() - token['created_at']
                if age > 60 * 60 * 24 * 6.5:  # 6.5 days to be safe
                    logger.info("Token is too old, will need to create new one")
                    return None
                    
            return token
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return None
            
    def _save_token(self, token: dict):
        """Save token to file with creation timestamp."""
        token['created_at'] = time.time()
        with open(self.token_path, 'w') as f:
            json.dump(token, f)
        logger.info(f"Token saved to {self.token_path}")

    def get_oauth_client(self) -> OAuth2Client:
        """Get an OAuth2 client, either from cached token or new auth flow."""
        if self.token:
            logger.info("Using existing token")
            client = OAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
                token=self.token,
                update_token=self._save_token,  # Auto-save refreshed tokens
                token_endpoint=self.token_url
            )
            return client
            
        logger.info("No valid token found, starting new OAuth flow")
        return self._create_new_token()
        
    def _create_new_token(self) -> OAuth2Client:
        """Create a new token through the OAuth2 flow."""
        client = OAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.callback_url
        )

        # Define required scopes for Schwab API
        scopes = ['market_data']  # Add other scopes as needed
        
        # Get the authorization URL with scopes
        auth_url, state = client.create_authorization_url(
            self.auth_url,
            scope=' '.join(scopes)
        )
        
        print("\n=================================================================")
        print("Starting Schwab OAuth authentication flow")
        print("\nDebug: Authorization URL generated:")
        print(auth_url)
        print("\n1. Opening your default browser to authorize application...")
        print("2. Log in with your Schwab credentials if prompted")
        print("3. Approve the application access request")
        print("\nThe browser will attempt to redirect to http://127.0.0.1")
        print("You may see a 'connection refused' error - this is expected.")
        print("\nIMPORTANT: When copying the callback URL:")
        print("- Copy the ENTIRE URL from your browser's address bar")
        print("- Make sure no extra characters are included")
        print("- The URL should start with 'http://127.0.0.1/?code='")
        print("=================================================================\n")
        
        # Open in default browser
        webbrowser.open(auth_url)
        
        callback_url = input("\nAfter approving, paste the FULL callback URL here: ")
        
        try:
            # Parse the callback URL
            parsed = urlparse(callback_url)
            if not parsed.query or 'code' not in dict(param.split('=') for param in parsed.query.split('&')):
                raise ValueError("Invalid callback URL - missing authorization code")

            # Set up headers required by Schwab API
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            # Exchange the authorization code for tokens
            token = client.fetch_token(
                self.token_url,
                authorization_response=callback_url,
                grant_type='authorization_code',
                include_client_id=True
            )
            
            self._save_token(token)
            logger.info("New token created and saved")
            
            return OAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
                token=token,
                update_token=self._save_token,
                token_endpoint=self.token_url
            )
            
        except Exception as e:
            logger.error(f"Error during token exchange: {str(e)}")
            raise Exception(f"Failed to complete OAuth flow: {str(e)}")

    def clear_token(self):
        """Clear the saved token file."""
        if os.path.exists(self.token_path):
            os.remove(self.token_path)
            logger.info("Token file cleared")
