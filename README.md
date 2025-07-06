# GEX Calculator

This project provides a small Dash dashboard for exploring gamma exposure metrics using data from the Schwab API.

## Usage

Install the requirements and run the application:

```bash
pip install -r requirements.txt
python -m gex.app
```

The app will start a local server where you can upload option chain JSON files or fetch chains directly from Schwab.

## Database

On first run the application creates an SQLite database file named `gex.db` in
the project root. The tables are created automatically by SQLAlchemy via the
`Base.metadata.create_all` call in `gex/gex_backend.py`. No manual steps are
required—simply run the app and the database will be initialized if it does not
already exist.
