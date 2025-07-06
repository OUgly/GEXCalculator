import os
import logging
import time
from typing import Dict, Any, Optional
from functools import wraps
import httpx
from dotenv import load_dotenv
from schwab.auth import client_from_manual_flow, client_from_token_file

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('schwab_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
CLIENT_ID = os.environ["SCHWAB_CLIENT_ID"]
CLIENT_SECRET = os.environ["SCHWAB_CLIENT_SECRET"]
CALLBACK_URL = os.environ.get("SCHWAB_CALLBACK_URL", "https://127.0.0.1:8182")  # Must use HTTPS for Schwab
MAX_RETRIES = 3
RETRY_DELAY = 1  # Base delay in seconds
REQUIRED_RESPONSE_KEYS = {'symbol', 'status', 'underlyingPrice', 'putExpDateMap', 'callExpDateMap'}

class SchwabAPIError(Exception):
    """Custom exception for Schwab API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)

def retry_with_backoff(retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Decorator to implement retry logic with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            while retry_count < retries:
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in {429, 503, 504}:  # Rate limit or service unavailable
                        retry_count += 1
                        if retry_count < retries:
                            wait_time = delay * (2 ** (retry_count - 1))  # Exponential backoff
                            logger.warning(f"Request failed with {e.response.status_code}, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                    raise
                except Exception as e:
                    raise SchwabAPIError(f"Unexpected error: {str(e)}")
            raise SchwabAPIError("Maximum retry attempts reached")
        return wrapper
    return decorator


class SchwabClient:
    """Client for interacting with Schwab's API with improved error handling."""

    def __init__(self, clean_token: bool = False):
        """Initialize the Schwab API client.

        Args:
            clean_token: When ``True`` the cached token file is deleted and a
                new OAuth flow is forced. Defaults to ``False`` so the existing
                token is reused if present.
        """
        try:
            token_path = "schwab_token.json"

            if clean_token and os.path.exists(token_path):
                os.remove(token_path)
                logger.info("Removed existing token file")

            client = None

            if not clean_token and os.path.exists(token_path):
                try:
                    logger.info("Loading Schwab client from existing token")
                    client = client_from_token_file(
                        token_path, CLIENT_ID, CLIENT_SECRET
                    )
                    # If the token is older than 6.5 days, force a new login
                    if client.token_age() >= 60 * 60 * 24 * 6.5:
                        logger.info("Existing token is too old; initiating new OAuth flow")
                        client = None
                except Exception as e:
                    logger.warning(f"Failed to load token file: {e}; starting OAuth flow")

            if client is None:
                logger.info("Starting Schwab OAuth flow")
                client = client_from_manual_flow(
                    api_key=CLIENT_ID,
                    app_secret=CLIENT_SECRET,
                    callback_url=CALLBACK_URL,
                    token_path=token_path,
                )

            self.client = client
            logger.info("Successfully created Schwab client")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to create Schwab client: {error_msg}", exc_info=True)
            
            if hasattr(e, 'response'):
                logger.error(f"Response Status: {e.response.status_code}")
                logger.error(f"Response Headers: {dict(e.response.headers)}")
                logger.error(f"Response Body: {e.response.text}")
                raise SchwabAPIError("Authentication failed", 
                                   status_code=e.response.status_code,
                                   response_text=e.response.text)
            
            raise SchwabAPIError(f"Failed to initialize Schwab client: {error_msg}")
    
    def _validate_option_chain_response(self, data: dict) -> None:
        """
        Validate the structure of the option chain response.
        
        Args:
            data: The response data to validate
            
        Raises:
            SchwabAPIError: If the response is missing required keys or has invalid structure
        """
        missing_keys = REQUIRED_RESPONSE_KEYS - set(data.keys())
        if missing_keys:
            raise SchwabAPIError(f"Invalid response structure. Missing keys: {missing_keys}")
            
        try:
            # Additional validation of nested structures
            float(data['underlyingPrice'])  # Validate price is numeric
            
            # Validate option maps
            for map_key in ['putExpDateMap', 'callExpDateMap']:
                if not isinstance(data[map_key], dict):
                    raise ValueError(f"{map_key} is not a dictionary")
                
        except (ValueError, TypeError) as e:
            raise SchwabAPIError(f"Invalid data format in response: {str(e)}")
        
    @retry_with_backoff()
    def fetch_option_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch option chain data for a given symbol with improved error handling and retry logic.
        
        Args:
            symbol: The stock symbol to fetch options data for (e.g., 'AAPL')
            
        Returns:
            Dict containing the options chain data
            
        Raises:
            SchwabAPIError: If there's an error fetching or processing the data
        """
        try:
            logger.info(f"Fetching option chain for {symbol}")
            
            # Log pre-request details
            logger.debug("Making API request with following parameters:")
            logger.debug(f"Symbol: {symbol}")
            
            response = self.client.get_option_chain(symbol.upper())
            
            # Log complete request/response cycle
            logger.debug(f"Request URL: {response.request.url}")
            logger.debug(f"Request headers: {dict(response.request.headers)}")
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                self._validate_option_chain_response(data)
                
                logger.info(f"Successfully retrieved option chain for {symbol}")
                logger.debug(f"Response contains keys: {list(data.keys())}")
                return data
            else:
                logger.error(f"Failed to fetch option chain. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise SchwabAPIError(
                    f"Failed to fetch option chain. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text
                )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching option chain: {str(e)}", exc_info=True)
            raise SchwabAPIError(
                f"HTTP error fetching option chain: {str(e)}", 
                status_code=e.response.status_code,
                response_text=e.response.text
            )
            
        except Exception as e:
            logger.error(f"Error fetching option chain: {str(e)}", exc_info=True)
            if hasattr(e, 'response'):
                logger.error(f"Response Status: {e.response.status_code}")
                logger.error(f"Response Headers: {dict(e.response.headers)}")
                logger.error(f"Response Body: {e.response.text}")
            raise SchwabAPIError(f"Failed to fetch option chain: {str(e)}")
    
    def fetch_and_save_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch option chain data and save it to a JSON file.
        
        Args:
            symbol: The stock symbol to fetch options data for (e.g., 'AAPL')
            
        Returns:
            Dict containing the options chain data
            
        Raises:
            SchwabAPIError: If there's an error fetching or processing the data
        """
        import json
        from datetime import datetime
        import os
        
        # Fetch the chain data
        chain_data = self.fetch_option_chain(symbol)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{timestamp}.json"
        
        # Ensure chain_data directory exists
        chain_dir = os.path.join(os.path.dirname(__file__), "chain_data")
        os.makedirs(chain_dir, exist_ok=True)
        
        # Save to JSON file
        filepath = os.path.join(chain_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(chain_data, f, indent=2)
            
        logger.info(f"Saved chain data to {filepath}")
        return chain_data

# For backwards compatibility
def fetch_option_chain(symbol: str) -> Dict[str, Any]:
    """Legacy function for backwards compatibility."""
    client = SchwabClient(clean_token=True)  # Always clean token for legacy function
    return client.fetch_and_save_chain(symbol)  # Use new method that saves JSON
