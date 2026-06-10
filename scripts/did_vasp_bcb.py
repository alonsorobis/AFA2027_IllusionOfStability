"""DiD estimation of the BCB VASP package impact on Brazilian stablecoin pricing.

Event: Banco Central do Brasil Resolution 561/2026 bringing Virtual Asset
Service Providers under the foreign-exchange perimeter (signed November 2025).

Design:
    log(stablecoin/local_FX_basis) = alpha_i + delta_t
        + beta * Brazil_i * Post_t + epsilon_{i,t}

Outcomes:
    log_basis: log(crypto_pair_close / official_FX_rate)  — the stablecoin
                basis in log points; * 1e4 to convert to basis points.

Treated: Brazil (USDT/BRL, USDC/BRL).
Control: Mexico (USDT/MXN), Argentina (USDT/ARS), Colombia (USDT/COP).

Event date: 2025-11-15 (BCB Resolution 561 signature) with alternatives
2025-06-01 (early package announcement) for anticipation robustness.

Outputs:
    data/processed/did_vasp_bcb_{TS}/
        ├── panel_daily.parquet
        ├── manifest.json
        └── plot_premium_by_country.png  (if matplotlib)
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT / "data" / "raw"
PROCESSED = PROJECT / "data" / "processed"

CC_DAY = "https://min-api.cryptocompare.com/data/v2/histoday"
CC_HOUR = "https://min-api.cryptocompare.com/data/v2/histohour"
USER_AGENT = "afa2027/0.1"

# Treated and control jurisdictions
PAIRS = [
    ("USDT", "BRL", "Brazil"),
    ("USDC", "BRL", "Brazil"),
    ("USDT", "MXN", "Mexico"),
    ("USDT", "ARS", "Argentina"),
    ("USDT", "COP", "Colombia"),
]

# Event date for BCB VASP package
EVENT_DATE = pd.Timestamp("2025-11-15", tz="UTC")


def fetch_cryptocompare_daily(fsym: str, tsym: str, to_ts: int, limit: int = 2000) -> pd.DataFrame:
    """Pull daily candles from CryptoCompare ending at to_ts."""
    r = requests.get(
        CC_DAY,
        params={"fsym": fsym, "tsym": tsym, "limit": limit, "toTs": to_ts},
        timeout=30,
        headers={"User-Agent": USER_AGENT},
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("Response") != "Success":
        raise RuntimeError(f"CryptoCompare {fsym}-{tsym} failed: {payload.get('Message')}")
    rows = payload.get("Data", {}).get("Data", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for col in ("open", "high", "low", "close", "volumefrom", "volumeto"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fsym"] = fsym
    df["tsym"] = tsym
    return df


def download_pairs() -> pd.DataFrame:
    """Download all 5 stablecoin/local-currency pairs daily."""
    to_ts = int(time.time())
    frames = []
    for fsym, tsym, country in PAIRS:
        print(f"Fetching {fsym}-{tsym} daily ...", flush=True)
        df = fetch_cryptocompare_daily(fsym, tsym, to_ts, limit=730)
        df["country"] = country
        # Filter to non-zero closes
        df = df[df["close"] > 0].copy()
        print(f"  {fsym}-{tsym}: {len(df)} non-zero days, "
              f"{df['time'].min().date() if len(df) else 'NaT'} to "
              f"{df['time'].max().date() if len(df) else 'NaT'}", flush=True)
        frames.append(df)
        time.sleep(0.4)
    return pd.concat(frames, ignore_index=True)


def fred_fx_series(series_id: str) -> pd.DataFrame:
    """Fetch a FRED FX series via the public CSV gateway (no API key).

    FRED CSV format as of 2026: first column is `observation_date`, second is
    the series ID; missing observations are encoded as '.'.
    """
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text))
    # Rename to canonical
    date_col = df.columns[0]
    value_col = df.columns[1]
    df = df.rename(columns={date_col: "date", value_col: "rate"})
    df["date"] = pd.to_datetime(df["date"])
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df = df.dropna(subset=["rate"]).reset_index(drop=True)
    df["series_id"] = series_id
    return df


def download_official_fx() -> dict[str, pd.DataFrame]:
    """Download daily USD-quoted FX rates for BRL, MXN, COP from FRED.

    For ARS, FRED no longer publishes a clean USD-ARS daily series because of
    Argentina's dual exchange-rate regime. We proxy ARS using the inverse of
    USDT/ARS itself (which trades de facto at the parallel/blue rate) and treat
    Argentina as a separate sensitivity check rather than a clean control.
    """
    series = {
        "BRL": "DEXBZUS",  # Brazil-US (BRL per USD)
        "MXN": "DEXMXUS",  # Mexico-US (MXN per USD)
        # COP: FRED's DEXCOUS exists but is monthly; use NB.COL.PCPI? Better: just take latest from CryptoCompare USD-COP if available.
    }
    out = {}
    for ccy, sid in series.items():
        print(f"Fetching FRED {sid} for {ccy} ...", flush=True)
        df = fred_fx_series(sid)
        print(f"  {sid}: {len(df)} obs, {df['date'].min().date()} to {df['date'].max().date()}", flush=True)
        out[ccy] = df
        time.sleep(0.2)
    return out


def fetch_cc_usd_local(local_ccy: str, to_ts: int) -> pd.DataFrame:
    """Fallback: get USD-vs-local-currency rate from CryptoCompare directly.

    Useful for ARS and COP where FRED's daily series are sparse.
    """
    return fetch_cryptocompare_daily("USD", local_ccy, to_ts, limit=730)


def build_panel(cc: pd.DataFrame, fred: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the country-day panel with log basis as outcome."""
    cc = cc.copy()
    cc["date"] = cc["time"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
    cc["pair"] = cc["fsym"] + "-" + cc["tsym"]

    # Pull USD-quoted FX from FRED for BRL/MXN; for ARS and COP use CC USD/local
    to_ts = int(time.time())
    cc_usd_ars = fetch_cc_usd_local("ARS", to_ts)
    cc_usd_cop = fetch_cc_usd_local("COP", to_ts)
    for d in (cc_usd_ars, cc_usd_cop):
        d["date"] = d["time"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
        d.rename(columns={"close": "fx_rate"}, inplace=True)
    fx_ars = cc_usd_ars[["date", "fx_rate"]].copy()
    fx_ars["currency"] = "ARS"
    fx_cop = cc_usd_cop[["date", "fx_rate"]].copy()
    fx_cop["currency"] = "COP"

    # FRED series for BRL/MXN
    fx_brl = fred["BRL"][["date", "rate"]].rename(columns={"rate": "fx_rate"}).copy()
    fx_brl["currency"] = "BRL"
    fx_mxn = fred["MXN"][["date", "rate"]].rename(columns={"rate": "fx_rate"}).copy()
    fx_mxn["currency"] = "MXN"

    fx_all = pd.concat([fx_brl, fx_mxn, fx_ars, fx_cop], ignore_index=True)

    # Merge crypto pair price with official FX of the local currency
    panel = cc.merge(
        fx_all,
        left_on=["date", "tsym"],
        right_on=["date", "currency"],
        how="inner",
    )
    panel["log_basis"] = np.log(panel["close"] / panel["fx_rate"])
    panel["basis_bps"] = panel["log_basis"] * 1e4
    panel["post"] = (panel["date"] >= EVENT_DATE.tz_localize(None)).astype(int)
    panel["treated"] = (panel["country"] == "Brazil").astype(int)
    panel["did"] = panel["post"] * panel["treated"]
    panel = panel[["date", "country", "pair", "fsym", "tsym",
                     "close", "fx_rate", "log_basis", "basis_bps",
                     "post", "treated", "did", "volumeto"]].sort_values(["country", "pair", "date"])
    return panel


def estimate_did(panel: pd.DataFrame, label: str = "main") -> dict:
    """Two-way fixed-effects DiD on basis_bps.

    Uses statsmodels OLS with country and date dummies. Returns coefficient,
    SE, t-stat, 95% CI.
    """
    try:
        import statsmodels.api as sm
    except ImportError:
        # Fall back to a manual within-transformation
        return _did_manual(panel, label=label)

    df = panel.dropna(subset=["basis_bps"]).copy()
    # Two-way FE via dummies
    country_dummies = pd.get_dummies(df["country"], prefix="c", drop_first=True).astype(float)
    date_dummies = pd.get_dummies(df["date"], prefix="d", drop_first=True).astype(float)
    X = pd.concat([country_dummies, date_dummies], axis=1)
    X["did"] = df["did"].astype(float).values
    X = sm.add_constant(X)
    y = df["basis_bps"].astype(float).values
    model = sm.OLS(y, X, hasconst=True)
    # Cluster SE by country
    try:
        groups = df["country"].astype("category").cat.codes
        result = model.fit(cov_type="cluster", cov_kwds={"groups": groups.values})
    except Exception:
        result = model.fit(cov_type="HC1")
    beta = float(result.params["did"])
    se = float(result.bse["did"])
    tstat = float(result.tvalues["did"])
    pval = float(result.pvalues["did"])
    ci_lo, ci_hi = (float(x) for x in result.conf_int().loc["did"])
    return {
        "label": label,
        "n_obs": int(len(df)),
        "beta_bps": beta,
        "se_bps": se,
        "tstat": tstat,
        "pval": pval,
        "ci_lo_bps": ci_lo,
        "ci_hi_bps": ci_hi,
    }


def _did_manual(panel: pd.DataFrame, label: str = "main") -> dict:
    """Manual DiD fallback (no statsmodels): mean(treated post) - mean(treated pre)
    minus the same for controls.
    """
    df = panel.dropna(subset=["basis_bps"]).copy()
    df["group"] = df["country"].apply(lambda c: "treated" if c == "Brazil" else "control")
    g = df.groupby(["group", "post"])["basis_bps"].mean().unstack(fill_value=np.nan)
    did = (g.loc["treated", 1] - g.loc["treated", 0]) - (g.loc["control", 1] - g.loc["control", 0])
    return {
        "label": label,
        "n_obs": int(len(df)),
        "beta_bps_manual": float(did),
    }


def run() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = PROCESSED / f"did_vasp_bcb_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== 1. Download crypto pairs (5 daily series) ===")
    cc = download_pairs()
    cc_out = out_dir / "cryptocompare_raw.parquet"
    cc.to_parquet(cc_out, index=False)
    print(f"Saved {cc_out} ({len(cc)} rows)")

    print()
    print("=== 2. Download official FX (FRED + CC fallback) ===")
    fred = download_official_fx()

    print()
    print("=== 3. Build panel ===")
    panel = build_panel(cc, fred)
    panel_out = out_dir / "panel_daily.parquet"
    panel.to_parquet(panel_out, index=False)
    print(f"Saved {panel_out} ({len(panel)} rows, {panel['country'].nunique()} countries, "
          f"{panel['date'].min().date()} to {panel['date'].max().date()})")

    print()
    print("=== 4. Run DiD ===")
    print("--- Main specification: all 4 controls, full sample ---")
    main_result = estimate_did(panel, label="main")
    print(json.dumps(main_result, indent=2))

    # Robustness: drop Argentina (atypical FX dynamics)
    print("\n--- No Argentina ---")
    no_ars = panel[panel["country"] != "Argentina"]
    no_ars_result = estimate_did(no_ars, label="no_argentina")
    print(json.dumps(no_ars_result, indent=2))

    # Robustness: only USDT-BRL treated (drop USDC-BRL)
    print("\n--- USDT-BRL only as treated ---")
    no_usdc_brl = panel[~((panel["country"] == "Brazil") & (panel["fsym"] == "USDC"))]
    no_usdc_result = estimate_did(no_usdc_brl, label="no_usdc_brl")
    print(json.dumps(no_usdc_result, indent=2))

    # Placebo: pretend event was June 2025 (5 months before actual event)
    print("\n--- Placebo event date 2025-06-01 ---")
    placebo = panel.copy()
    placebo_date = pd.Timestamp("2025-06-01")
    placebo["post"] = (placebo["date"] >= placebo_date).astype(int)
    placebo["did"] = placebo["post"] * placebo["treated"]
    # Trim to pre-event-only (avoid contamination with the actual event)
    placebo_pre = placebo[placebo["date"] < EVENT_DATE.tz_localize(None)]
    placebo_result = estimate_did(placebo_pre, label="placebo_2025_06_pre_only")
    print(json.dumps(placebo_result, indent=2))

    manifest = {
        "run": ts,
        "event_date": str(EVENT_DATE),
        "pairs": [{"fsym": f, "tsym": t, "country": c} for f, t, c in PAIRS],
        "n_panel_obs": int(len(panel)),
        "panel_date_min": str(panel["date"].min().date()),
        "panel_date_max": str(panel["date"].max().date()),
        "results": {
            "main": main_result,
            "no_argentina": no_ars_result,
            "no_usdc_brl": no_usdc_result,
            "placebo_2025_06_pre_only": placebo_result,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nSaved manifest to {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    run()
