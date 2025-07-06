# GEX Calculator

This project provides a small Dash dashboard for exploring gamma exposure metrics using data from the Schwab API.

## Usage

Install the requirements and run the application:

```bash
pip install -r requirements.txt
python -m gex.app
```

The app will start a local server where you can upload option chain JSON files or fetch chains directly from Schwab.

## Environment variables

The Schwab API credentials must be provided through environment variables or a `.env` file:

- `SCHWAB_CLIENT_ID` – your Schwab API client ID
- `SCHWAB_CLIENT_SECRET` – your Schwab API client secret
- `SCHWAB_CALLBACK_URL` – optional override for the OAuth callback URL (defaults to `https://127.0.0.1:8182`)

An example `.env.example` file is included. Copy it to `.env` and fill in your credentials before running the app.
