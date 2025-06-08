import json
import pandas as pd

# === USER INPUT ===
json_file_path = "response_1749418418599.json"
spot_price = float(input("Enter current spot price (e.g. 19.18): "))

# === Load and parse JSON ===
with open(json_file_path, "r") as f:
    data = json.load(f)

flattened = []

# Extract both CALLs and PUTs if present
for side_key in ["callExpDateMap", "putExpDateMap"]:
    if side_key in data:
        exp_map = data[side_key]
        for expiry, strikes in exp_map.items():
            for strike_str, options in strikes.items():
                for option in options:
                    flattened.append({
                        "strike": float(strike_str),
                        "type": option.get("putCall", ""),
                        "openInterest": option.get("openInterest", 0),
                        "gamma": option.get("gamma", 0)
                    })

# === Create DataFrame ===
df = pd.DataFrame(flattened)

# === Calculate signed GEX ===
def compute_signed_gex(row):
    direction = 1
    if row["type"] == "CALL" and row["strike"] > spot_price:
        direction = -1
    elif row["type"] == "PUT" and row["strike"] < spot_price:
        direction = -1
    return row["openInterest"] * row["gamma"] * 100 * direction

df["gex"] = df.apply(compute_signed_gex, axis=1)

# === Compute cumulative GEX by sorted strike ===
df = df.sort_values("strike")
df["cumulative_gex"] = df["gex"].cumsum()

# === Find zero gamma level ===
zero_gamma_idx = df["cumulative_gex"].abs().idxmin()
zero_gamma_strike = df.loc[zero_gamma_idx, "strike"]

# === Output ===
print(f"\nZero Gamma Strike Level: {zero_gamma_strike}")
print(df[["strike", "type", "gex", "cumulative_gex"]])
