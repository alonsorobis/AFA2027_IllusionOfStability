"""Threshold (kink) test of the depeg channel.

The model: unmet redemption is U = max(D - R, 0), so the realised depeg is ~0
until conversions D exceed liquid reserves R and then rises convexly. With net
redemption outflow as the proxy for D, this implies a kinked relationship,

    depeg = a + b * max(0, outflow - gamma) [+ c * max(0, outflow - gamma)^2],

with a breakpoint gamma > 0 (the reserve buffer, in % of supply), a positive
slope b above it, and convexity c > 0. We estimate gamma by grid search
(minimising SSR of the linear-kink fit) and then test for convexity above it.

Output: data/processed/threshold_check.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "data" / "raw"
PROC = ROOT.parent / "data" / "processed"


def daily(coin):
    px = pd.read_parquet(RAW / f"cryptocompare_{coin}_usd_3600s_20260601.parquet")
    px["date"] = pd.to_datetime(px["time"]).dt.tz_localize(None).dt.normalize()
    g = px.groupby("date").agg(min_close=("close", "min")).reset_index()
    g["depeg"] = (1.0 - g["min_close"]).clip(lower=0) * 1e4              # bps
    sup = pd.read_csv(PROC / f"defillama_supply_{coin}_daily.csv")
    sup["date"] = pd.to_datetime(sup["date"]).dt.tz_localize(None).dt.normalize()
    sup = sup.sort_values("date")
    sup["outflow"] = (-sup["total_circulating"].pct_change()) * 100      # percent
    return g.merge(sup[["date", "outflow"]], on="date", how="inner").dropna()


def ols(y, X):
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ (X.T @ y)
    r = y - X @ b
    n, k = X.shape
    S = (X * r[:, None]).T @ (X * r[:, None])
    cov = (n / (n - k)) * XtXi @ S @ XtXi
    se = np.sqrt(np.diag(cov))
    ssr = float(r @ r)
    r2 = 1 - ssr / np.sum((y - y.mean()) ** 2)
    return b, se, r2, ssr


def fit(coin):
    m = daily(coin)
    sub = m[m["outflow"] > 0]
    x = sub["outflow"].to_numpy()
    y = sub["depeg"].to_numpy()
    # grid search breakpoint over interior outflow quantiles
    grid = np.quantile(x, np.linspace(0.30, 0.95, 40))
    best = None
    for g in grid:
        z = np.maximum(0.0, x - g)
        if np.count_nonzero(z) < 15:
            continue
        b, se, r2, ssr = ols(y, np.column_stack([np.ones(len(x)), z]))
        if best is None or ssr < best["ssr"]:
            best = {"gamma": float(g), "slope_above": float(b[1]),
                    "slope_t": float(b[1] / se[1]), "r2": float(r2), "ssr": ssr}
    # convexity above the estimated breakpoint
    g = best["gamma"]
    z = np.maximum(0.0, x - g)
    bq, seq, r2q, _ = ols(y, np.column_stack([np.ones(len(x)), z, z ** 2]))
    # linear (no kink) benchmark on the same sample
    bl, sel, r2l, _ = ols(y, np.column_stack([np.ones(len(x)), x]))
    return {
        "coin": coin, "n_redemption_days": int(len(x)),
        "breakpoint_gamma_pct": best["gamma"],
        "slope_above_bps_per_pct": best["slope_above"], "slope_above_t": best["slope_t"],
        "kink_r2": best["r2"], "linear_no_kink_r2": float(r2l),
        "convex_term_above": float(bq[2]), "convex_t": float(bq[2] / seq[2]),
        "kink_quadratic_r2": float(r2q),
        "n_days_above_breakpoint": int(np.count_nonzero(z)),
    }


def main():
    out = {c: fit(c) for c in ["USDC", "USDT"]}
    (PROC / "threshold_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
