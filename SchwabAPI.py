from schwab.client import SchwabClient

# Replace with your actual values
api_key = "9iY4fkoLKGMUoRgdWJgzM6bZuRMTwi84"
api_secret = "YOUR_API_SECRET"
callback_url = "https://127.0.0.1"
token_path = "C:/Users/Louie/Downloads/token.json"  # Where you want to save the token

# Initialize the client
client = SchwabClient(
    api_key=api_key,
    api_secret=api_secret,
    callback_url=callback_url,
    token_path=token_path,
)


# Check if token is valid, if not, do login flow
if not client.is_token_valid():
    client.login_flow()

# Now you can use the client to make API calls
accounts = client.get_accounts()
print(accounts)

# Example of getting price history
price_history = client.get_price_history(symbol="SPY")
print(price_history)
