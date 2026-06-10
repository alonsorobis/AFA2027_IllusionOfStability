"""DiD estimation of MiCA Title V impact on the USDT/EUR basis using USDC/EUR as control.

Event: Markets in Crypto-Assets Regulation Title V applicable from 30 December 2024.
Title V prohibits crypto-asset service providers from offering services in
non-authorised electronic-money tokens to EEA public customers. USDT did not apply
for MiCA authorisation; USDC is MiCA-compliant. EU-licensed venues (Coinbase EU,
Crypto.com EU, Bitstamp) delisted USDT for EEA customers between December 2024 and
March 2025.

Design (within-stablecoin DiD):
    log_basis_{i,t} = alpha_i + delta_t + beta * Treated_i * Post_t + epsilon_{i,t}
where:
    log_basis_{i,t} = log(stablecoin_EUR_close_t / EUR_USD_official_FX_t)
    Treated = 1 if USDT (delisted in EU), 0 if USDC (MiCA-compliant)
    Post    = 1 if t >= 2024-12-30
    alpha_i = stablecoin fixed effect
    delta_t = day fixed effect

Identification: any differential in USDT/EUR basis vs USDC/EUR basis around the
event is attributable to the MiCA-induced reduction in USDT EU venue liquidity,
since both stablecoins share the same EUR/USD fundamentals.

Robustness:
- Alternative event dates: 2024-12-05 (Coinbase EU announcement), 2025-01-31 (Crypto.com EU deadline)
- Event study with monthly bins around Dec 2024
- Placebo on pre-event sample
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from io import StringIO

import numpy as np
import pandas as pd
import requests

PROJECT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT / "data" / "processed"

CC_DAY = "https://min-api.cryptocompare.com/data/v2/histoday"
USER_AGENT = "afa2027/0.1"

EVENT_DATE = pd.Timestamp("2024-12-30")  # MiCA Title V applicable


def fetch_cc_daily(fsym: str, tsym: str, to_ts: int, limit: int = 730) -> pd.DataFrame:
    r = requests.get(
        CC_DAY,
        params={"fsym": fsym, "tsym": tsym, "limit": limit, "toTs": to_ts},
        timeout=30,
        headers={"User-Agent": USER_AGENT},
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("Response") != "Success":
        raise RuntimeError(f"CC {fsym}-{tsym} failed: {payload.get('Message')}")
    rows = payload.get("Data", {}).get("Data", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for col in ("open", "high", "low", "close", "volumefrom", "volumeto"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df["close"] > 0].copy()
    df["fsym"] = fsym
    df["tsym"] = tsym
    return df


def fred_fx(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "rate"})
    df["date"] = pd.to_datetime(df["date"])
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    return df.dropna(subset=["rate"]).reset_index(drop=True)


def run() -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = PROCESSED / f"did_mica_usdt_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {out_dir}", flush=True)

    print("\n=== 1. Download USDT/EUR and USDC/EUR daily ===")
    to_ts = int(time.time())
    df_usdt = fetch_cc_daily("USDT", "EUR", to_ts)
    df_usdt["stablecoin"] = "USDT"
    print(f"  USDT/EUR: {len(df_usdt)} obs, {df_usdt['time'].min().date()} to {df_usdt['time'].max().date()}", flush=True)
    time.sleep(0.4)
    df_usdc = fetch_cc_daily("USDC", "EUR", to_ts)
    df_usdc["stablecoin"] = "USDC"
    print(f"  USDC/EUR: {len(df_usdc)} obs, {df_usdc['time'].min().date()} to {df_usdc['time'].max().date()}", flush=True)
    cc = pd.concat([df_usdt, df_usdc], ignore_index=True)
    cc["date"] = cc["time"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)

    print("\n=== 2. FRED EUR-USD (DEXUSEU is USD per EUR) ===")
    # DEXUSEU = USD per 1 EUR
    fx = fred_fx("DEXUSEU")
    print(f"  DEXUSEU: {len(fx)} obs, {fx['date'].min().date()} to {fx['date'].max().date()}", flush=True)
    # We need EUR-per-USD so we can compute basis = stablecoin_EUR_close / (EUR-per-USD)
    fx["eur_per_usd"] = 1.0 / fx["rate"]
    fx_lite = fx[["date", "eur_per_usd"]].copy()

    print("\n=== 3. Build panel ===")
    panel = cc.merge(fx_lite, on="date", how="inner")
    panel["log_basis"] = np.log(panel["close"] / panel["eur_per_usd"])
    panel["basis_bps"] = panel["log_basis"] * 1e4
    panel["treated"] = (panel["stablecoin"] == "USDT").astype(int)
    panel["post"] = (panel["date"] >= EVENT_DATE).astype(int)
    panel["did"] = panel["treated"] * panel["post"]
    panel = panel[["date", "stablecoin", "close", "eur_per_usd", "log_basis", "basis_bps", "treated", "post", "did", "volumeto"]].sort_values(["stablecoin", "date"])
    panel.to_parquet(out_dir / "panel_daily.parquet", index=False)
    print(f"  Panel: {len(panel)} rows, {panel['date'].min().date()} to {panel['date'].max().date()}")
    print()
    print("=== 4. Descriptive means ===")
    print(panel.groupby(["stablecoin", "post"])["basis_bps"].agg(["mean", "std", "count"]).round(2))

    print()
    print("=== 5. DiD with statsmodels ===")
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    df = panel.copy()
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")

    m_main = smf.ols("basis_bps ~ did + C(stablecoin) + C(date_str)", data=df).fit(cov_type="HC1")
    print(f"  MAIN: beta_did = {m_main.params['did']:.2f} bps, SE = {m_main.bse['did']:.2f}, t = {m_main.tvalues['did']:.2f}, p = {m_main.pvalues['did']:.4f}")
    print(f"        95% CI [{m_main.conf_int().loc['did', 0]:.2f}, {m_main.conf_int().loc['did', 1]:.2f}]")

    # Robustness 1: earlier event date (Coinbase EU announcement)
    df_r1 = df.copy()
    early = pd.Timestamp("2024-12-05")
    df_r1["post_r1"] = (df_r1["date"] >= early).astype(int)
    df_r1["did_r1"] = df_r1["treated"] * df_r1["post_r1"]
    m_r1 = smf.ols("basis_bps ~ did_r1 + C(stablecoin) + C(date_str)", data=df_r1).fit(cov_type="HC1")
    print(f"  R1 (event 2024-12-05): beta = {m_r1.params['did_r1']:.2f} bps, SE = {m_r1.bse['did_r1']:.2f}, t = {m_r1.tvalues['did_r1']:.2f}, p = {m_r1.pvalues['did_r1']:.4f}")

    # Robustness 2: later event date (Crypto.com EU deadline)
    df_r2 = df.copy()
    late = pd.Timestamp("2025-01-31")
    df_r2["post_r2"] = (df_r2["date"] >= late).astype(int)
    df_r2["did_r2"] = df_r2["treated"] * df_r2["post_r2"]
    m_r2 = smf.ols("basis_bps ~ did_r2 + C(stablecoin) + C(date_str)", data=df_r2).fit(cov_type="HC1")
    print(f"  R2 (event 2025-01-31): beta = {m_r2.params['did_r2']:.2f} bps, SE = {m_r2.bse['did_r2']:.2f}, t = {m_r2.tvalues['did_r2']:.2f}, p = {m_r2.pvalues['did_r2']:.4f}")

    # Placebo: pretend event was 2024-06-30 (6 months before), restrict to pre-2024-12-30
    df_pl = df[df["date"] < EVENT_DATE].copy()
    placebo = pd.Timestamp("2024-06-30")
    df_pl["post_pl"] = (df_pl["date"] >= placebo).astype(int)
    df_pl["did_pl"] = df_pl["treated"] * df_pl["post_pl"]
    m_pl = smf.ols("basis_bps ~ did_pl + C(stablecoin) + C(date_str)", data=df_pl).fit(cov_type="HC1")
    print(f"  Placebo (event 2024-06-30, pre-only): beta = {m_pl.params['did_pl']:.2f} bps, SE = {m_pl.bse['did_pl']:.2f}, t = {m_pl.tvalues['did_pl']:.2f}, p = {m_pl.pvalues['did_pl']:.4f}")

    # Event study: monthly bins around event
    print()
    print("=== 6. Event study (monthly bins, ref = -1) ===")
    df["m"] = ((df["date"] - EVENT_DATE).dt.days // 30).clip(-12, 12).astype(int)
    es_terms = []
    for m in sorted(df["m"].unique()):
        if m == -1:
            continue
        col = f"es_p{m}" if m >= 0 else f"es_m{abs(m)}"
        df[col] = ((df["m"] == m) & (df["treated"] == 1)).astype(int)
        es_terms.append((int(m), col))
    formula = "basis_bps ~ " + " + ".join(c for _, c in es_terms) + " + C(stablecoin) + C(date_str)"
    mes = smf.ols(formula, data=df).fit(cov_type="HC1")
    pre_terms = [c for m, c in es_terms if m < -1]
    post_terms = [c for m, c in es_terms if m >= 0]
    ftest_pre = mes.f_test(" = ".join(pre_terms) + " = 0") if len(pre_terms) > 1 else None
    ftest_post = mes.f_test(" = ".join(post_terms) + " = 0") if len(post_terms) > 1 else None
    print(f"  R^2 = {mes.rsquared:.3f}")
    print(f"  Joint F-test (pre-event = 0): F = {float(ftest_pre.fvalue) if ftest_pre else 'N/A':.2f}, p = {float(ftest_pre.pvalue) if ftest_pre else 'N/A':.4f}")
    print(f"  Joint F-test (post-event = 0): F = {float(ftest_post.fvalue):.2f}, p = {float(ftest_post.pvalue):.4f}")
    print()
    print(f"  {'rel_mo':>8s}  {'coef':>8s}  {'SE':>6s}  {'t':>6s}  {'p':>6s}")
    for m, col in es_terms:
        print(f"  {m:>8d}  {mes.params[col]:>8.2f}  {mes.bse[col]:>6.2f}  {mes.tvalues[col]:>6.2f}  {mes.pvalues[col]:>6.3f}")

    # Plots
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = {"USDT": "C3", "USDC": "C0"}
    for sc in ["USDT", "USDC"]:
        sub = panel[panel["stablecoin"] == sc].sort_values("date")
        smooth = sub.set_index("date")["basis_bps"].rolling(7, min_periods=3).mean()
        ax.plot(smooth.index, smooth.values, label=f"{sc}/EUR", color=colors[sc], lw=1.4)
    ax.axvline(EVENT_DATE, color="k", ls="--", lw=1, alpha=0.6, label="MiCA Title V (2024-12-30)")
    ax.axvline(pd.Timestamp("2024-12-05"), color="grey", ls=":", lw=0.8, alpha=0.5, label="Coinbase EU delisting announcement")
    ax.set_xlabel("Date")
    ax.set_ylabel("Stablecoin/EUR basis vs official EUR-USD FX (bps, 7-day rolling)")
    ax.set_title("Stablecoin/EUR basis: USDT (treated) vs USDC (control), 2024-2026")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_dir / "basis_usdt_vs_usdc.png", dpi=130)
    print(f"\n  Saved plot {out_dir / 'basis_usdt_vs_usdc.png'}")

    # Event study plot
    months = [m for m, _ in es_terms] + [-1]
    months.sort()
    coefs_full = []
    ci_lo_full = []
    ci_hi_full = []
    for m in months:
        if m == -1:
            coefs_full.append(0); ci_lo_full.append(0); ci_hi_full.append(0)
        else:
            col = next(c for mm, c in es_terms if mm == m)
            coefs_full.append(mes.params[col])
            ci = mes.conf_int().loc[col]
            ci_lo_full.append(ci[0]); ci_hi_full.append(ci[1])
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.errorbar(months, coefs_full,
                 yerr=[[c - lo for c, lo in zip(coefs_full, ci_lo_full)],
                       [hi - c for c, hi in zip(coefs_full, ci_hi_full)]],
                 fmt="o-", capsize=3, lw=1, color="C0", markersize=5)
    ax2.axhline(0, color="k", lw=0.5)
    ax2.axvline(0, color="r", ls="--", lw=1, alpha=0.6, label="MiCA Title V (2024-12-30)")
    ax2.set_xlabel("Months relative to event (ref = -1)")
    ax2.set_ylabel("USDT-EUR vs USDC-EUR differential basis (bps)")
    ax2.set_title("Event study: MiCA Title V and the USDT/EUR vs USDC/EUR basis")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=9)
    plt.tight_layout()
    fig2.savefig(out_dir / "event_study.png", dpi=130)
    print(f"  Saved plot {out_dir / 'event_study.png'}")

    # Save manifest
    manifest = {
        "event_date": "2024-12-30",
        "design": "within-stablecoin DiD: USDT (delisted) vs USDC (MiCA-compliant), EUR pair basis",
        "n_panel_obs": int(len(df)),
        "main_did_HC1": {
            "beta_bps": float(m_main.params["did"]),
            "se": float(m_main.bse["did"]),
            "t": float(m_main.tvalues["did"]),
            "p": float(m_main.pvalues["did"]),
            "ci_lo": float(m_main.conf_int().loc["did", 0]),
            "ci_hi": float(m_main.conf_int().loc["did", 1]),
        },
        "robust_2024_12_05": {
            "beta_bps": float(m_r1.params["did_r1"]),
            "se": float(m_r1.bse["did_r1"]),
            "p": float(m_r1.pvalues["did_r1"]),
        },
        "robust_2025_01_31": {
            "beta_bps": float(m_r2.params["did_r2"]),
            "se": float(m_r2.bse["did_r2"]),
            "p": float(m_r2.pvalues["did_r2"]),
        },
        "placebo_2024_06_30_pre_only": {
            "beta_bps": float(m_pl.params["did_pl"]),
            "se": float(m_pl.bse["did_pl"]),
            "p": float(m_pl.pvalues["did_pl"]),
        },
        "event_study": {
            "months": [m for m, _ in es_terms],
            "coefs_bps": [float(mes.params[c]) for _, c in es_terms],
            "p_values": [float(mes.pvalues[c]) for _, c in es_terms],
            "joint_F_pre": {"F": float(ftest_pre.fvalue), "p": float(ftest_pre.pvalue)} if ftest_pre else None,
            "joint_F_post": {"F": float(ftest_post.fvalue), "p": float(ftest_post.pvalue)} if ftest_post else None,
        },
        "descriptive_means": {
            "USDT_pre_event_mean_bps": float(panel[(panel.stablecoin == "USDT") & (panel.post == 0)].basis_bps.mean()),
            "USDT_post_event_mean_bps": float(panel[(panel.stablecoin == "USDT") & (panel.post == 1)].basis_bps.mean()),
            "USDC_pre_event_mean_bps": float(panel[(panel.stablecoin == "USDC") & (panel.post == 0)].basis_bps.mean()),
            "USDC_post_event_mean_bps": float(panel[(panel.stablecoin == "USDC") & (panel.post == 1)].basis_bps.mean()),
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n  Saved manifest {out_dir / 'manifest.json'}")
    return manifest


if __name__ == "__main__":
    run()
