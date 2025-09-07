# GEX Calculator

Dash dashboard for professional exploration of Gamma Exposure (GEX) using Schwab option chain data. Includes caching, notes, CSV export, and a clean trading‑desk UI.

## Quick Start

Install dependencies and run the app:

```
pip install -r requirements.txt
python -m gex.app
```

Open http://localhost:8050 to use the dashboard.

## Controls

- Upload JSON: Load a local option chain JSON file.
- Ticker: Enter a symbol (e.g., SPY) to fetch from Schwab.
- Fetch Chain: Retrieves and caches the latest chain (30‑min cache).
- Refresh: Re-fetches the chain (respects cache freshness).
- Auto Refresh (60s): Periodic refresh during market hours.
- Expiry / Month: Focus on specific weeks or months.
- Run Analysis: Rebuild charts after uploads/changes.
- Theme: Toggle Plotly theme (dark/light).
- Download CSV: Export the processed table for analysis.

Notes are saved per-symbol in the local SQLite DB and appear in the Notes panel.

## Database

An SQLite database `gex.db` is created in the project root on first run. Tables are created automatically using SQLAlchemy in `gex/gex_backend.py`.

## Configuration

Environment variables are loaded from `.env` if present:

```
SCHWAB_CLIENT_ID=your_client_id
SCHWAB_CLIENT_SECRET=your_client_secret
DEBUG=false
LOG_LEVEL=INFO
```

Set `LOG_LEVEL=DEBUG` for detailed computation logs. Set `DEBUG=true` to enable Dash’s debug server in development.

## Notes

- API tokens are cached in `schwab_token.json`. If authentication fails, delete the file and restart.
- Chain data is cached in the DB for 30 minutes to avoid excessive API calls.
