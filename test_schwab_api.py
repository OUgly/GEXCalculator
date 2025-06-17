from schwab_api import SchwabClient

# Create a client instance
client = SchwabClient()

# Fetch option chain data
json_data = client.fetch_option_chain("SOXL")  # Replace with any symbol
print(json_data.keys())