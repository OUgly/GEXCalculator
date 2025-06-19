#!/usr/bin/env python3
import pathlib
from gex.schwab_api import SchwabClient

token = pathlib.Path(__file__).resolve().parent.parent / "schwab_token.json"
if token.exists():
    token.unlink()
    print("✅  Old token deleted.")

print("👉  Follow the browser flow one last time…")
SchwabClient(clean_token=True)  # will create a fresh token & quit
