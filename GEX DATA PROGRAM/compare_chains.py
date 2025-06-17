import json
from schwab_api import SchwabClient
import pandas as pd

def load_manual_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def extract_option_data(chain_data, expiry_month="2025-06"):
    rows = []
    
    for opt_type, exp_map in [("CALL", chain_data.get("callExpDateMap", {})),
                             ("PUT", chain_data.get("putExpDateMap", {}))]:
        for expiry_key, strikes in exp_map.items():
            if not expiry_key.startswith(expiry_month):
                continue
                
            for strike_str, contracts in strikes.items():
                for contract in (contracts if isinstance(contracts, list) else [contracts]):
                    gamma = (contract.get("gamma") or 
                            contract.get("greek", {}).get("gamma") or 
                            contract.get("greeks", {}).get("gamma"))
                    
                    if gamma is not None:
                        rows.append({
                            "Type": opt_type,
                            "Strike": float(strike_str),
                            "Gamma": float(gamma),
                            "OI": contract.get("openInterest", 0),
                            "IV": contract.get("volatility", 0),
                        })
    
    return pd.DataFrame(rows)

def main():
    # Load manual JSON
    manual_data = load_manual_json('c:\\Users\\Louie\\Downloads\\response_1749926300496.json')
    manual_df = extract_option_data(manual_data)
    
    # Get API data
    client = SchwabClient(clean_token=True)
    api_data = client.fetch_option_chain("SOXL")
    api_df = extract_option_data(api_data)
    
    # Sort both dataframes
    manual_df = manual_df.sort_values(['Type', 'Strike']).reset_index(drop=True)
    api_df = api_df.sort_values(['Type', 'Strike']).reset_index(drop=True)
    
    print("\n=== Manual JSON Data ===")
    print(manual_df)
    
    print("\n=== API Data ===")
    print(api_df)
    
    # Compare key statistics
    print("\n=== Comparison ===")
    print(f"Manual JSON - Total Contracts: {len(manual_df)}")
    print(f"API Data - Total Contracts: {len(api_df)}")
    
    print("\nManual JSON Stats:")
    print(manual_df.groupby('Type')['Gamma'].describe())
    
    print("\nAPI Stats:")
    print(api_df.groupby('Type')['Gamma'].describe())
    
    # Check for differences
    if len(manual_df) == len(api_df):
        gamma_diff = (manual_df['Gamma'] - api_df['Gamma']).abs().mean()
        oi_diff = (manual_df['OI'] - api_df['OI']).abs().mean()
        print(f"\nAverage differences:")
        print(f"Gamma: {gamma_diff:.6f}")
        print(f"Open Interest: {oi_diff:.2f}")

if __name__ == "__main__":
    main()
