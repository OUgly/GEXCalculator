import numpy as np
import pandas as pd
import json
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from scipy.stats import norm
from .schwab_api import SchwabClient  # Add this import
from db import SessionLocal, OptionChain, Base, engine

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Initialize Schwab client (will be created when needed)
_schwab_client = None

def get_chain_data(ticker: str, force_refresh: bool = False) -> dict:
    """Fetch option chain data from the Schwab API."""
    global _schwab_client
    try:
        if force_refresh:
            _schwab_client = SchwabClient(clean_token=True)
        elif _schwab_client is None:
            _schwab_client = SchwabClient(clean_token=False)
        return _schwab_client.fetch_option_chain(ticker)
    except Exception as e:
        raise ValueError(f"Failed to fetch option chain data: {str(e)}")


def save_chain_to_db(session: Session, symbol: str, fetched_at: datetime, raw_json: dict) -> None:
    """Persist fetched chain data to the database."""
    record = OptionChain(symbol=symbol, fetched_at=fetched_at, raw_json=json.dumps(raw_json))
    session.add(record)
    session.commit()


def load_latest_chain(session: Session, symbol: str):
    """Retrieve the most recently fetched chain for a symbol."""
    return (
        session.query(OptionChain)
        .filter(OptionChain.symbol == symbol)
        .order_by(OptionChain.fetched_at.desc())
        .first()
    )


def fetch_and_save_chain(ticker: str, force_refresh: bool = False) -> dict:
    """Fetch option chain data and cache it in the database."""
    with SessionLocal() as session:
        row = load_latest_chain(session, ticker)
        if row and not force_refresh:
            age = datetime.utcnow() - row.fetched_at
            if age <= timedelta(minutes=30):
                return json.loads(row.raw_json)

        data = get_chain_data(ticker, force_refresh=force_refresh)
        save_chain_to_db(session, ticker, datetime.utcnow(), data)
        return data

def load_chain_data(ticker: str) -> dict:
    """Load cached chain data, fetching from the API when stale."""
    print(f"\n=== Loading Chain Data for {ticker} ===")
    data = fetch_and_save_chain(ticker)
    print("Successfully loaded data:")
    print(f"- Call expirations: {len(data.get('callExpDateMap', {}))}")
    print(f"- Put expirations: {len(data.get('putExpDateMap', {}))}")
    return data

def _bs_unit_gamma(S, K, vol, T, r=0.0, q=0.0):
    """Compute Black-Scholes unit gamma for given parameters."""
    if T <= 0 or vol <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r - q + 0.5 * vol ** 2) * T) / (vol * np.sqrt(T))
    gamma = np.exp(-q * T) * norm.pdf(d1) / (S * vol * np.sqrt(T))
    print(f"Black-Scholes gamma calculation:")
    print(f"  S={S}, K={K}, vol={vol}, T={T}")
    print(f"  d1={d1}, gamma={gamma}")
    return gamma

def _dollar_gamma(unit_gamma, S, OI):
    """Convert unit gamma to dollar gamma value."""
    result = unit_gamma * OI * 100 * S * S * 0.01
    print(f"Dollar gamma calculation:")
    print(f"  unit_gamma={unit_gamma}, S={S}, OI={OI}")
    print(f"  result={result}")
    return result

def run_gex_analysis(chain_json: dict, ticker: str, spot: float = None, selected_expiry: str = None):
    """
    Run GEX analysis on option chain data.
    
    Args:
        chain_json: The option chain data
        ticker: The ticker symbol
        spot: Optional spot price override
        selected_expiry: Optional specific expiration date to analyze
    """
    print("\n=== Starting GEX Analysis ===")
    print("Data source structure:")
    print(f"Keys in chain_json: {list(chain_json.keys())}")
    
    # Get maps and prepare date handling
    call_map = chain_json.get('callExpDateMap', {})
    put_map = chain_json.get('putExpDateMap', {})
    from datetime import datetime, timedelta

    def normalize_expiry(expiry: str) -> str:
        """Normalize expiration date format by removing the :1 suffix if present."""
        return expiry.split(':')[0] if ':' in expiry else expiry

    def parse_exp_date(exp_str: str) -> date:
        """Parse an expiration date string into a date object."""
        exp_str = normalize_expiry(exp_str)  # Remove :1 suffix if present
        return datetime.strptime(exp_str, '%Y-%m-%d').date()

    # Get all available expirations
    all_expirations = sorted(set(call_map.keys()) | set(put_map.keys()))
    if not all_expirations:
        raise ValueError("No expiration dates found in chain data")
    
    # Get current date and look ahead 45 days for available expirations
    current_date = datetime.now().date()
    cutoff_date = current_date + timedelta(days=45)
    
    # Filter for next available expirations within 45 days
    valid_exps = [
        exp for exp in all_expirations 
        if current_date <= parse_exp_date(exp) <= cutoff_date
    ]
    
    print("\n=== Expiration Analysis ===")
    print(f"All available expirations: {len(all_expirations)}")
    print(f"Valid upcoming expirations: {valid_exps}")
    
    if not valid_exps:
        raise ValueError(f"No valid expirations found in the next 45 days")
      # If a specific expiry is selected, use it if it's available
    if selected_expiry:
        normalized_selected = normalize_expiry(selected_expiry)
        # Find the matching expiration, whether it has :1 suffix or not
        matching_exp = next((exp for exp in all_expirations 
                           if normalize_expiry(exp) == normalized_selected), None)
        if matching_exp:
            active_expirations = [matching_exp]
        else:
            raise ValueError(f"Selected expiration {selected_expiry} not found in available expirations")
    else:
        active_expirations = valid_exps
    
    # Process chain data
    rows = []
    spot = spot or chain_json.get("underlyingPrice")
    spot = float(spot)
    print(f"\nUnderlying price: {spot}")
    
    # Process all active expirations
    for expiry in active_expirations:
        for opt_type, exp_map in (("CALL", call_map), ("PUT", put_map)):
            if expiry not in exp_map:
                continue
                
            strikes = exp_map[expiry]
            for strike_str, contracts in strikes.items():
                for contract in (contracts if isinstance(contracts, list) else [contracts]):
                    gamma = None
                    if "gamma" in contract:
                        gamma = float(contract["gamma"])
                    elif "greek" in contract and isinstance(contract["greek"], dict):
                        gamma = float(contract["greek"].get("gamma", 0))
                    elif "greeks" in contract and isinstance(contract["greeks"], dict):
                        gamma = float(contract["greeks"].get("gamma", 0))
                    
                    oi = contract.get("openInterest")
                    iv = contract.get("volatility", contract.get("theoreticalVolatility"))
                    
                    if any(x is None for x in [gamma, oi, iv]):
                        continue
                        
                    rows.append({
                        "Expiry": expiry.split(":")[0],
                        "Strike": float(strike_str),
                        "Type": opt_type,
                        "GammaUnit": float(gamma),
                        "OI": int(oi),
                        "IV": float(iv) / 100,
                        "DTE": contract.get("daysToExpiration", 0) / 365,
                    })

    if not rows:
        raise ValueError("No valid option rows parsed")

    df = pd.DataFrame(rows)

    g_agg = df.groupby(["Strike", "Expiry"]).agg(
        CallOI=("OI", lambda x: x[df.Type == "CALL"].sum()),
        CallGammaUnit=("GammaUnit", lambda x: x[df.Type == "CALL"].sum()),
        CallIV=("IV", lambda x: x[df.Type == "CALL"].mean()),
        CallDTE=("DTE", lambda x: x[df.Type == "CALL"].mean()),
        PutOI=("OI", lambda x: x[df.Type == "PUT"].sum()),
        PutGammaUnit=("GammaUnit", lambda x: x[df.Type == "PUT"].sum()),
        PutIV=("IV", lambda x: x[df.Type == "PUT"].mean()),
        PutDTE=("DTE", lambda x: x[df.Type == "PUT"].mean())
    ).fillna(0)

    spot = spot or chain_json.get("underlyingPrice")
    spot = float(spot)

    g_agg["CallGEX"] = _dollar_gamma(g_agg.CallGammaUnit, spot, g_agg.CallOI)
    g_agg["PutGEX"] = -_dollar_gamma(g_agg.PutGammaUnit, spot, g_agg.PutOI)
    g_agg["TotalGEX"] = (g_agg.CallGEX + g_agg.PutGEX) / 1e9  # billions

    print("\n=== GEX Calculations ===")
    print(f"Total Call GEX: {g_agg['CallGEX'].sum() / 1e9:+.6f}Bn")
    print(f"Total Put GEX: {g_agg['PutGEX'].sum() / 1e9:+.6f}Bn")
    print(f"Net Total GEX: {g_agg['TotalGEX'].sum():+.6f}Bn")

    agg = g_agg.reset_index()    # Calculate profile using the latest expiry data for each strike
    latest_exp_data = g_agg.groupby("Strike").last()
    print("\n=== Profile Calculation ===")
    print(f"Number of unique strikes: {len(latest_exp_data)}")
    print(f"Strike range: {latest_exp_data.index.min():.2f} to {latest_exp_data.index.max():.2f}")
    
    levels = np.linspace(0.5 * spot, 1.5 * spot, 40)
    print(f"Price levels for analysis: {levels[0]:.2f} to {levels[-1]:.2f}")
    print("\n=== Starting Gamma Profile Calculation ===")
    profile = []
    print("First few rows of latest_exp_data:")
    print(latest_exp_data.head())
    
    profile = []
    print("\nCalculating profile for each price level:")
    for i, lvl in enumerate(levels):
        unit_sum = 0
        if i < 2:  # Print detailed calculation for first two levels only
            print(f"\nPrice level {lvl:.2f}:")
            
        for strike, row in latest_exp_data.iterrows():                # Calculate call and put gammas with detailed debugging
            print(f"\nProcessing strike {strike} at price level {lvl}:")
            print(f"Call data - IV: {row.CallIV}, DTE: {row.CallDTE}, OI: {row.CallOI}")
            print(f"Put data - IV: {row.PutIV}, DTE: {row.PutDTE}, OI: {row.PutOI}")
            
            g_c = _bs_unit_gamma(lvl, strike, row.CallIV or 0.3, row.CallDTE or 30 / 365)
            g_p = _bs_unit_gamma(lvl, strike, row.PutIV or 0.3, row.PutDTE or 30 / 365)
            
            print(f"Unit gammas - Call: {g_c}, Put: {g_p}")
            
            # Calculate dollar gamma contributions
            call_contribution = _dollar_gamma(g_c, lvl, row.CallOI)
            put_contribution = -_dollar_gamma(g_p, lvl, row.PutOI)  # Note the negative sign
            
            print(f"Dollar gamma - Call: {call_contribution}, Put: {put_contribution}")
            
            contribution = call_contribution + put_contribution
            print(f"Total contribution: {contribution}")
            
            unit_sum += contribution
            
            if i < 2 and abs(contribution) > 0.0001:  # Print significant contributions for first two levels
                print(f"  Strike {strike:.1f}: Call(gamma={g_c:.6f} * OI={row.CallOI}) + (-Put(gamma={g_p:.6f} * OI={row.PutOI})) = {contribution:.6f}")
          # Scale to billions here, once all contributions are summed
        gamma_dollar = unit_sum / 1e9
        profile.append(gamma_dollar)
        
        if i < 2:
            print(f"  Level {lvl:.2f} total: {gamma_dollar:.6f}")
    
    profile = np.array(profile)
    zero_gamma = None
    
    print("\n=== Zero Gamma Search ===")
    print(f"Profile shape: {profile.shape}")
    print("\nProfile values at each price level:")
    for lvl, prof in zip(levels, profile):
        print(f"Price: {lvl:.2f}, Gamma: {prof:.6f}")
    
    # Calculate the range excluding very small values
    threshold = 1e-6
    significant_profile = profile[np.abs(profile) > threshold]
    if len(significant_profile) > 0:
        print(f"Significant profile min/max: {significant_profile.min():.6f}/{significant_profile.max():.6f}")
    else:
        print("No significant gamma values found")
    
    # Check if profile contains both positive and negative values with significance
    has_positive = any(p > threshold for p in profile)
    has_negative = any(p < -threshold for p in profile)
    print(f"Profile contains positive values: {has_positive}")
    print(f"Profile contains negative values: {has_negative}")
    
    # Check for sign changes
    sign_changes = np.where(np.diff(np.sign(profile)) != 0)[0]
    print(f"Number of sign changes found: {len(sign_changes)}")
    
    if sign_changes.size:
        i = sign_changes[0]
        zero_gamma = levels[i] - profile[i] * (levels[i + 1] - levels[i]) / (profile[i + 1] - profile[i])
        print(f"Zero gamma calculated at: {zero_gamma:.2f}")
    else:
        print("No zero gamma found - no sign changes in profile")
        
    # Verify the calculated zero gamma is reasonable
    if zero_gamma is not None:
        if not (0.5 * spot <= zero_gamma <= 1.5 * spot):
            print(f"Warning: Zero gamma {zero_gamma:.2f} outside expected range [{0.5 * spot:.2f}, {1.5 * spot:.2f}]")
            zero_gamma = None

    return agg, spot, zero_gamma, levels, profile
