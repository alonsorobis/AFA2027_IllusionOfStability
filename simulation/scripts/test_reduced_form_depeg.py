"""Referee test (b): reduced-form expected depeg loss vs the model-based one.

Computes the expected below-par conversion loss directly from the hourly
secondary price, with no global game, and lays it next to the calibrated
model output. Also estimates a per-coin stress probability p_s (Klee-style,
but empirical) instead of the shared 96/8856 figure.

Object priced (both approaches): the expected per-unit loss from converting
the stablecoin's USD claim below par, in basis points,
    ell_D = E[ max(1 - p, 0) ] * 1e4
decomposed by regime as (1-p_s)*ell_D_baseline + p_s*ell_D_stress.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"

COINS = {
    "USDC": ("cryptocompare_usdc_usd_3600s_20260601.parquet",
             ("2023-03-10", "2023-03-13 23:00")),   # SVB stress window
    "USDT": ("cryptocompare_usdt_usd_3600s_20260601.parquet",
             ("2022-05-11", "2022-05-15 00:00")),   # Terra stress window
}
# model-based numbers (current calibration, conditional and weighted)
MODEL = {
    "USDC": {"ell_Db_w": 26.4, "ell_Ds_w": 2.6, "ell_Ds_cond": 238.7},
    "USDT": {"ell_Db_w": 10.9, "ell_Ds_w": 0.3, "ell_Ds_cond": 27.7},
}
P_S_MODEL = 0.0108
THRESHOLDS = [0.999, 0.995, 0.99, 0.975]


def load(coin):
    f, _ = COINS[coin]
    df = pd.read_parquet(RAW / f)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)


def below_par_bps(p):
    return np.maximum(1.0 - p, 0.0) * 1e4


out = {}
for coin, (f, (t0, t1)) in COINS.items():
    df = load(coin)
    p = df["close"].to_numpy(float)
    t = df["time"]
    n = len(p)
    span = f"{t.iloc[0].date()} to {t.iloc[-1].date()} ({n} hours)"

    # (1) unconditional expected depeg loss at the USD-pair mid, whole history
    ell_uncond = float(below_par_bps(p).mean())

    # (2) per-coin empirical p_s and conditional depths over the whole history
    rows = []
    for thr in THRESHOLDS:
        stress = p < thr
        p_s = float(stress.mean())
        depth_s = float(below_par_bps(p[stress]).mean()) if stress.any() else 0.0
        depth_b = float(below_par_bps(p[~stress]).mean())
        ell_recon = (1 - p_s) * depth_b + p_s * depth_s
        rows.append({"thr": thr, "p_s": p_s, "n_stress": int(stress.sum()),
                     "depth_stress_bps": depth_s, "depth_base_bps": depth_b,
                     "ell_D_emp_bps": ell_recon})

    # (3) depth inside the named stress episode only (the calibration window)
    win = df[(t >= t0) & (t <= t1)]["close"].to_numpy(float)
    depth_episode = float(below_par_bps(win).mean())
    min_episode = float(win.min())

    out[coin] = {"span": span, "ell_uncond_mid_bps": ell_uncond,
                 "episode_mean_depth_bps": depth_episode, "episode_min": min_episode,
                 "by_threshold": rows}

    print(f"\n===== {coin}  [{span}] =====")
    print(f"  Unconditional E[max(1-p,0)] at the USD-pair mid : {ell_uncond:6.2f} bps")
    print(f"  Named episode mean below-par depth              : {depth_episode:6.2f} bps  (min {min_episode:.4f})")
    print(f"  {'thr':>6} {'p_s':>8} {'n_str':>6} {'depth_stress':>13} {'depth_base':>11} {'ell_D_emp':>10}")
    for r in rows:
        print(f"  {r['thr']:>6.3f} {r['p_s']:>8.4f} {r['n_stress']:>6d} "
              f"{r['depth_stress_bps']:>13.1f} {r['depth_base_bps']:>11.3f} {r['ell_D_emp_bps']:>10.2f}")
    m = MODEL[coin]
    print(f"  MODEL: ell_D,b(w)={m['ell_Db_w']}  ell_D,s(w)={m['ell_Ds_w']}  "
          f"-> ell_D total = {m['ell_Db_w']+m['ell_Ds_w']:.1f} bps  "
          f"(stress conditional {m['ell_Ds_cond']} at p_s={P_S_MODEL})")

(ROOT / "data" / "processed" / "reduced_form_depeg_test.json").write_text(json.dumps(out, indent=2))
print("\nWrote reduced_form_depeg_test.json")
