"""Schwab GEX Puller — PKCE flow (robust input v2025‑06‑04)

• Authorize URL : https://api.schwabapi.com/v1/oauth/authorize
• Token URL     : https://api.schwabapi.com/v1/oauth2/token  (PKCE)
• Callback URI  : https://127.0.0.1      ← must match portal exactly

New in this version
===================
1.  **Safer redirect‑URL prompt**: if the pasted text doesn’t contain a `?code=`
    query param the script explains the problem and asks again instead of
    crashing with `KeyError: 'code'`.
2.  Minor: trims surrounding quotes/whitespace.

Usage
-----
1. Run the script → browser opens Schwab login → sign in, click *Allow*.
2. After the blank `127.0.0.1` page appears, copy the **entire** address from
   the browser’s URL bar (starts with https://127.0.0.1/?code=… ).
3. Paste it at the prompt.  Script stores tokens in `token.json` and prints the
   first rows of strike‑level GEX.
"""

import os, time, json, secrets, hashlib, base64, webbrowser, urllib.parse as up
import requests, pandas as pd

# ========= CONFIG =========
APP_KEY      = "9iY4fkoLKGMUoRgdWJgzM6bZuRMTwi84"   # ← replace with your key
REDIRECT_URI = "https://127.0.0.1"                   # must match portal
TOKEN_FILE   = "token.json"
SCOPE        = "MarketData"
SYMBOL       = "SPY"                                  # change ticker as needed

AUTH_URL  = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
# ==========================


# ---------------- helper functions ----------------

def _pkce_pair():
    v = secrets.token_urlsafe(64)[:128]
    c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
    return v, c


def _post_token(payload: dict):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Token endpoint {r.status_code}: {r.text}")
    tok = r.json()
    tok["expires_at"] = time.time() + tok["expires_in"]
    return tok


def _prompt_redirect() -> str:
    """Prompt until a string containing ?code= is entered."""
    while True:
        redirect = input("Paste entire redirect URL here: ").strip().strip("\"')")
        if "?code=" in redirect:
            return redirect
        print("\n❌  That doesn’t contain '?code='. Copy the *full* URL from the browser and try again.\n")


def _first_login():
    verifier, challenge = _pkce_pair()
    params = {
        "response_type": "code",
        "client_id": APP_KEY,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{AUTH_URL}?{up.urlencode(params)}"
    print("Opening browser…")
    webbrowser.open(url, new=2)
    redirect = _prompt_redirect()
    code = up.parse_qs(up.urlparse(redirect).query)["code"][0]
    return _post_token({
        "grant_type": "authorization_code",
        "client_id": APP_KEY,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    }) | {"code_verifier": verifier}


def _refresh(tok):
    if tok["expires_at"] > time.time() + 60:
        return tok
    return _post_token({
        "grant_type": "refresh_token",
        "client_id": APP_KEY,
        "refresh_token": tok["refresh_token"],
        "code_verifier": tok["code_verifier"],
    }) | {"code_verifier": tok["code_verifier"]}


def get_tokens():
    if os.path.exists(TOKEN_FILE):
        tok = json.load(open(TOKEN_FILE))
        tok = _refresh(tok)
    else:
        tok = _first_login()
    json.dump(tok, open(TOKEN_FILE, "w"))
    return tok


# -------------- GEX calc ----------------

def gex_snapshot(symbol: str, bearer: str):
    chain = requests.get(
        "https://api.schwabapi.com/marketdata/v1/chains",
        headers={"Authorization": f"Bearer {bearer}"},
        params={"symbol": symbol, "strategy": "SINGLE", "greeks": "TRUE"},
        timeout=30,
    ).json()
    spot = chain["underlyingPrice"]
    rows = []
    for opt in chain["options"]:
        g, oi = opt["greek"]["gamma"], opt["openInterest"]
        sign = 1 if opt["putCall"] == "CALL" else -1
        rows.append({"strike": opt["strikePrice"], "gex": g*oi*100*spot*sign})
    return pd.DataFrame(rows).groupby("strike", as_index=False)["gex"].sum()


# -------------- main ----------------

if __name__ == "__main__":
    print(f"Fetching GEX for {SYMBOL}…")
    try:
        tokens = get_tokens()
        df = gex_snapshot(SYMBOL, tokens["access_token"])
        print(df.head())
    except Exception as exc:
        print("\n❌", exc)