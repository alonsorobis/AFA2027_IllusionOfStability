"""Reduced-form mechanism check for the depeg channel.

The structural secondary price is p^sec = 1 - psi*(U/Mtilde)^nu - ..., so the
realised depeg d = 1 - p rises in unmet redemption pressure U and, because the
impact is convex (nu > 1) and scaled by depth Mtilde, the rise is steeper and
more convex the thinner the secondary market. We proxy redemption pressure by
the daily NET outflow of circulating supply (mint/burn, DefiLlama) -- the model's
conversion mass, not gross trading volume -- and the realised depeg by the daily
maximum below-par deviation of the hourly secondary price (CryptoCompare).

Test: regress daily depeg (bps) on net outflow (%), with a quadratic term, per
issuer. The model predicts a positive slope (depeg rises with redemptions) and,
for the thinner USDC market, a convex (positive quadratic) response; the deeper
USDT market should respond more nearly linearly. Descriptive, not causal: depeg
and outflow are jointly determined within a run.

Output: data/processed/mechanism_check.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "data" / "raw"
PROC = ROOT.parent / "data" / "processed"


def ols(y, X):
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ (X.T @ y)
    r = y - X @ b
    n, k = X.shape
    S = (X * r[:, None]).T @ (X * r[:, None])
    cov = (n / (n - k)) * XtXi @ S @ XtXi          # HC1 robust
    se = np.sqrt(np.diag(cov))
    r2 = 1 - np.sum(r ** 2) / np.sum((y - y.mean()) ** 2)
    return b, se, r2, n


def daily(coin):
    px = pd.read_parquet(RAW / f"cryptocompare_{coin}_usd_3600s_20260601.parquet")
    px["date"] = pd.to_datetime(px["time"]).dt.tz_localize(None).dt.normalize()
    g = px.groupby("date").agg(min_close=("close", "min")).reset_index()
    g["depeg"] = (1.0 - g["min_close"]).clip(lower=0)          # daily max below-par deviation
    sup = pd.read_csv(PROC / f"defillama_supply_{coin}_daily.csv")
    sup["date"] = pd.to_datetime(sup["date"]).dt.tz_localize(None).dt.normalize()
    sup = sup.sort_values("date")
    sup["outflow"] = -sup["total_circulating"].pct_change()    # positive = net redemption
    return g.merge(sup[["date", "outflow"]], on="date", how="inner").dropna()


def per_coin(coin):
    m = daily(coin)
    sub = m[m["outflow"] > 0]                                  # redemption days
    y = sub["depeg"].to_numpy() * 1e4                          # bps
    o = sub["outflow"].to_numpy() * 100                        # percent
    bl, sel, r2l, n = ols(y, np.column_stack([np.ones(len(o)), o]))
    bq, seq, r2q, _ = ols(y, np.column_stack([np.ones(len(o)), o, o ** 2]))
    return {
        "coin": coin, "n_redemption_days": int(n),
        "linear_slope_bps_per_pct": float(bl[1]), "linear_slope_t": float(bl[1] / sel[1]),
        "linear_r2": float(r2l),
        "quad_term": float(bq[2]), "quad_t": float(bq[2] / seq[2]),
        "quad_linear_term": float(bq[1]), "quad_r2": float(r2q),
        "convex": bool(bq[2] > 0 and bq[2] / seq[2] > 1.64),
        "max_outflow_pct": float(m["outflow"].max() * 100),
        "max_depeg_bps": float(m["depeg"].max() * 1e4),
        "corr_depeg_outflow_full": float(np.corrcoef(m["depeg"], m["outflow"].fillna(0))[0, 1]),
    }


def main():
    out = {c: per_coin(c) for c in ["USDC", "USDT"]}
    (PROC / "mechanism_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
