import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# -----------------------------------------------------------------------------
# Optional GUI file‑picker (only used if the user didn’t pass a JSON path)
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None  # headless / minimal env – fallback to CLI prompts

# ---------------------------- Helpers ----------------------------------------

def _parse_side(exp_map: dict, multiplier: int, rows: list) -> None:
    """Extract option rows from Schwab /chains maps and append to *rows*."""
    for expiry_key, strikes in exp_map.items():
        expiry = expiry_key.split(":")[0]  # "2025‑01‑17: 220" → "2025‑01‑17"
        for strike_str, contracts in strikes.items():
            contract = contracts[0] if isinstance(contracts, list) else contracts
            gamma = contract.get("gamma") or contract.get("greek", {}).get("gamma")
            oi = contract.get("openInterest")
            if gamma is None or oi is None:
                continue

            rows.append(
                {
                    "expiry": expiry,
                    "strike": float(strike_str),
                    "type": "CALL" if multiplier > 0 else "PUT",
                    "openInterest": oi,
                    "gamma": gamma,
                    # contract gamma exposure in shares (ΔΓ * OI * 100)
                    "gex": multiplier * gamma * oi * 100,
                }
            )


# ------------------------- Interactive prompts ------------------------------

def _prompt_for_file() -> Path:
    """Ask the user for a JSON file (GUI picker if Tkinter is available)."""
    if tk is not None:
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select Schwab /chains JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        root.destroy()
        if file_path:
            return Path(file_path)

    # Fallback to plain CLI prompt
    while True:
        p = input("Path to /chains JSON file: ").strip()
        path = Path(p)
        if path.exists():
            return path
        print("✖ File not found – try again.")


def _prompt_for_ticker() -> str:
    return input("Ticker symbol (e.g., SOXL): ").strip().upper()


def _prompt_for_spot() -> float:
    while True:
        val = input("Underlying spot price: ").strip()
        try:
            return float(val)
        except ValueError:
            print("✖ Enter a numeric spot price (e.g., 258.75).")


# ------------------------------ Main -----------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Visualise strike‑level Gamma Exposure (GEX) from a Schwab /chains JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("json_path", nargs="?", type=Path, help="/chains JSON file")
    parser.add_argument("--ticker", default=None, help="Ticker used for plot title")
    parser.add_argument("--spot", type=float, default=None, help="Underlying spot price")

    args = parser.parse_args(argv)

    # ---- Interactive fallbacks --------------------------------------------
    if args.json_path is None:
        args.json_path = _prompt_for_file()
    if args.ticker is None:
        args.ticker = _prompt_for_ticker()
    if args.spot is None:
        args.spot = _prompt_for_spot()

    # ---- Load JSON ---------------------------------------------------------
    try:
        chain = json.loads(args.json_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        sys.exit(f"✖ Failed reading JSON: {e}")

    # ---- Build DataFrame ---------------------------------------------------
    rows: list[dict] = []
    _parse_side(chain.get("callExpDateMap", {}) or {}, +1, rows)
    _parse_side(chain.get("putExpDateMap", {}) or {}, -1, rows)

    if not rows:
        sys.exit("✖ No option rows parsed – JSON structure may have changed.")

    df = pd.DataFrame(rows)

    # Separate calls and puts for colour‑coding / width control
    calls = df[df["type"] == "CALL"].groupby("strike")["gex"].sum()
    puts = df[df["type"] == "PUT"].groupby("strike")["gex"].sum()

    # All strikes (show everything)
    strikes = pd.Index(sorted(set(calls.index).union(puts.index)))
    calls = calls.reindex(strikes, fill_value=0)
    puts = puts.reindex(strikes, fill_value=0)

    # Aggregate net GEX (calls + puts)
    net_gex_by_strike = calls + puts
    total_gex = net_gex_by_strike.sum()

    # ----- Zero‑Gamma calculation (centre‑of‑mass approach) -----------------
    if total_gex != 0:
        zero_gamma_price = (net_gex_by_strike * strikes).sum() / total_gex
    else:
        zero_gamma_price = args.spot  # fallback if total gamma is neutral

    # Highest positive & most negative strike (dealer zones)
    selling_strike = net_gex_by_strike.idxmax()
    buying_strike = net_gex_by_strike.idxmin()

    # ---- Dynamic figure height so all strike labels are visible ------------
    # Allocate ~0.25 inches per strike, with a sensible minimum figure height.
    fig_height = max(6, len(strikes) * 0.25)

    plt.style.use("ggplot")
    fig, ax = plt.subplots(figsize=(11, fig_height))

    bar_h = 0.3  # bar thickness

    # Calls (royal blue)
    ax.barh(
        strikes + bar_h / 2,
        calls.values,
        height=bar_h,
        color="royalblue",
        label="Calls (blue)",
    )

    # Puts (black)
    ax.barh(
        strikes - bar_h / 2,
        puts.values,
        height=bar_h,
        color="black",
        label="Puts (black)",
    )

    # Zero line
    ax.axvline(0, color="white", linewidth=0.8, linestyle="--")

    # Dealer zone lines (deeper colours)
    ax.axhline(selling_strike, color="#8B0000", linewidth=1.4, alpha=0.85)
    ax.axhline(zero_gamma_price, color="gold", linewidth=1.4, alpha=0.9)
    ax.axhline(buying_strike, color="#006400", linewidth=1.4, alpha=0.85)

    # Labels offset a bit from y‑axis to avoid overlap
    x_text = ax.get_xlim()[1] * 0.015
    ax.text(x_text, selling_strike, "Dealers likely Selling", va="center", ha="left", color="#8B0000", weight="bold")
    ax.text(x_text, zero_gamma_price, "Zero Gamma Level", va="center", ha="left", color="gold", weight="bold")
    ax.text(x_text, buying_strike, "Dealers likely Buying", va="center", ha="left", color="#006400", weight="bold")

    # Axis labels & title
    ax.set_xlabel("Gamma Exposure (shares)")
    ax.set_ylabel("Strike")
    ax.set_title(
        f"{args.ticker} Net GEX by Strike\nSpot: {args.spot}   Total Net Gamma: {total_gex:,.0f} shares",
        fontsize=14,
        weight="bold",
    )

    # Ensure every strike shows as a tick label; shrink font if there are many.
    ax.set_yticks(strikes)
    label_fontsize = 8 if len(strikes) > 40 else 10
    ax.tick_params(axis="y", labelsize=label_fontsize)

    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
