import json
from gex_backend import run_gex_analysis

# Change this to the actual path of your downloaded Schwab JSON
json_path = "c:\\Users\\Louie\\Desktop\\GAMMA EXPOSURE\\JUNE 2025\\QBTS  --  JUN 9-13\\QBTS_THURSDAY6-12_3PM.json"  # e.g. "soxl_chain.json"
ticker = "QBTS"

with open(json_path, "r") as f:
    chain_data = json.load(f)

df, spot, zero, levels, profile = run_gex_analysis(chain_data, ticker)

print(f"✅ Spot: {spot:.2f}")
print(f"✅ Zero Gamma: {zero:.2f}" if zero else "⚠️ Zero Gamma not found")
print(f"✅ Total Gamma: {df['TotalGEX'].sum():.2f} Bn")
print(f"✅ Data shape: {df.shape}")
