"""Recompute every derived number for the corrected model and regenerate
fig_risk_decomposition.pdf. Reads phi* (constant spec) from the recalibration
results; prints all numbers for the paper and writes a JSON snapshot.
"""
from __future__ import annotations
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stablecoin_ms.simple_calibration import build_scenario
from stablecoin_ms.usdt_calibration import build_scenario_usdt
from stablecoin_ms.montecarlo import run_scenario

PROOT = ROOT.parent
P_S = 0.0108
res = json.loads((PROOT / "data" / "processed" / "h1_recalibration_results.json").read_text())
PHI = {"USDC": np.array(res["USDC | constant_h1=0"]["phi"]),
       "USDT": np.array(res["USDT | constant_h1=0"]["phi"])}
BUILD = {"USDC": build_scenario, "USDT": build_scenario_usdt}
H0 = {"USDC": 0.01, "USDT": 0.02}
XI0 = {"USDC": 0.20, "USDT": 0.30}

def depeg(asset, phi, h=None, xi=None, n=800):
    """Return (depeg_b, depeg_s) conditional, in bps, optionally overriding (h,xi)."""
    out = []
    for regime, seed in (("baseline", 42), ("stress", 84)):
        sc = BUILD[asset](f"u_{asset}_{regime}", phi, regime, n_draws=n, seed=seed)
        if h is not None or xi is not None:
            sc = replace(sc, issuer=replace(sc.issuer, h=h if h is not None else sc.issuer.h,
                                            xi=xi if xi is not None else sc.issuer.xi))
        d = run_scenario(sc)
        p = np.array([x.secondary_price for x in d]); r = np.array([x.redemption_rate["retail"] for x in d])
        out.append(float(np.mean(r * (1 - p)) * 1e4))
    return out

def premium(cp, db, ds, ps=P_S):
    return cp + (1 - ps) * db + ps * ds

snap = {}
print("="*72, "\nCENTRAL DECOMPOSITION")
for a in ("USDC", "USDT"):
    db, ds = depeg(a, PHI[a])
    cp = H0[a] * XI0[a] * 1e4
    dbw, dsw = (1 - P_S) * db, P_S * ds
    Pi = cp + dbw + dsw
    snap[a] = {"cp": cp, "db_cond": db, "ds_cond": ds, "db_w": dbw, "ds_w": dsw, "Pi": Pi}
    print(f"  {a}: Pi={Pi:.1f}  cp={cp:.1f}({100*cp/Pi:.0f}%)  dbw={dbw:.1f}({100*dbw/Pi:.0f}%)  dsw={dsw:.2f}({100*dsw/Pi:.0f}%)")

# Use cases. The stablecoin path prices the full payment circuit:
#   on-ramp (fiat->stablecoin) + on-chain transfer fee + expected loss while
#   held + destination basis + off-ramp (stablecoin->local fiat).
# F_ON and F_OFF are the on- and off-ramp platform fees, central values within
# the 10-50 bps/leg retail range documented in Appendix D.
F_ON = 25.0
F_OFF = 25.0
RAMP = F_ON + F_OFF
snap["ramp"] = {"f_on": F_ON, "f_off": F_OFF, "total": RAMP}
uc = {
  "UC1_BR_USDT_40":   375.0 + RAMP + 21.0 + snap["USDT"]["Pi"],
  "UC2_USMX_USDT_400":  37.5 + RAMP + 12.0 + snap["USDT"]["Pi"],
  "UC3_EUBR_USDC_1000": 15.0 + RAMP + 21.0 + snap["USDC"]["Pi"],
  "UC3_EUBR_USDT_1000": 15.0 + RAMP + 21.0 + snap["USDT"]["Pi"],
}
snap["use_cases"] = uc
print(f"USE CASES (total bps, incl. {RAMP:.0f} bps on+off ramp):", {k: round(v,1) for k,v in uc.items()})
print(f"  UC2 USDT {uc['UC2_USMX_USDT_400']:.1f}: vs Wise 251.2 by {251.2-uc['UC2_USMX_USDT_400']:.1f}; vs SWIFT 333.5 by {333.5-uc['UC2_USMX_USDT_400']:.1f}")
print(f"  UC3 USDC {uc['UC3_EUBR_USDC_1000']:.1f}: vs Wise 205.2 by {205.2-uc['UC3_EUBR_USDC_1000']:.1f}; vs SWIFT 489.5 by {489.5-uc['UC3_EUBR_USDC_1000']:.1f}")
print(f"  UC3 USDT {uc['UC3_EUBR_USDT_1000']:.1f}: vs Wise 205.2 by {205.2-uc['UC3_EUBR_USDT_1000']:.1f}")

# Regulatory band (hold conditional depeg fixed; vary h and p_s) -- matches old methodology
print("="*72, "\nREGULATORY BAND")
band = {}
for a, hs, pss in (("USDC", (0.015,0.020), (0.02,0.03)), ("USDT", (0.025,0.035), (0.02,0.03))):
    db, ds = snap[a]["db_cond"], snap[a]["ds_cond"]
    lo = hs[0]*XI0[a]*1e4 + (1-pss[0])*db + pss[0]*ds
    hi = hs[1]*XI0[a]*1e4 + (1-pss[1])*db + pss[1]*ds
    band[a] = (lo, hi, hs[0]*XI0[a]*1e4, hs[1]*XI0[a]*1e4)
    print(f"  {a}: central {snap[a]['Pi']:.1f} -> adverse [{lo:.1f}, {hi:.1f}]  (ell_C adverse {hs[0]*XI0[a]*1e4:.0f}-{hs[1]*XI0[a]*1e4:.0f})")
snap["band"] = band

# Counterparty-parameter sensitivity (re-solve depeg at each (h,xi))
print("="*72, "\nCOUNTERPARTY SENSITIVITY")
sens = {}
grids = {"USDC": [(0.005,0.15),(0.010,0.20),(0.015,0.25)], "USDT": [(0.015,0.25),(0.020,0.30),(0.025,0.35)]}
for a in ("USDC","USDT"):
    sens[a]=[]
    for h,xi in grids[a]:
        db,ds = depeg(a, PHI[a], h=h, xi=xi, n=600)
        Pi = premium(h*xi*1e4, db, ds)
        sens[a].append((h,xi,Pi)); print(f"  {a} (h={h},xi={xi}): Pi={Pi:.1f}")
snap["sens"]=sens

# Regenerate figure
fig, ax = plt.subplots(figsize=(7.0, 3.6))
comps = ["counterparty\n$\\ell_C$", "depeg baseline\n$(1-p_s)\\,\\ell_{D,b}$", "depeg stress\n$p_s\\,\\ell_{D,s}$"]
uvals=[snap["USDC"]["cp"], snap["USDC"]["db_w"], snap["USDC"]["ds_w"]]
tvals=[snap["USDT"]["cp"], snap["USDT"]["db_w"], snap["USDT"]["ds_w"]]
y=np.arange(3); bh=0.36
bu=ax.barh(y+bh/2, uvals, height=bh, color="#2e6fb7", label="USDC", edgecolor="black", linewidth=0.4)
bt=ax.barh(y-bh/2, tvals, height=bh, color="#c75b4a", label="USDT", edgecolor="black", linewidth=0.4)
for bar,v in list(zip(bu,uvals))+list(zip(bt,tvals)):
    ax.text(v+0.6, bar.get_y()+bar.get_height()/2, f"{v:.1f}", va="center", ha="left", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(comps, fontsize=9); ax.set_xlabel("Basis points", fontsize=10)
ax.set_xlim(0, max(uvals+tvals)*1.18); ax.invert_yaxis()
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.legend(loc="lower right", fontsize=9, frameon=False)
def pcts(d): t=d["Pi"]; return f"{100*d['cp']/t:.0f}% / {100*d['db_w']/t:.0f}% / {100*d['ds_w']/t:.0f}%"
fig.text(0.5,-0.04, f"USDC total: {snap['USDC']['Pi']:.1f} bps   ({pcts(snap['USDC'])})        "
                    f"USDT total: {snap['USDT']['Pi']:.1f} bps   ({pcts(snap['USDT'])})",
         ha="center", va="top", fontsize=9, color="#333333")
plt.tight_layout()
figpath = PROOT/"paper"/"figures"/"fig_risk_decomposition.pdf"
fig.savefig(figpath, format="pdf", bbox_inches="tight"); plt.close(fig)
print("Wrote", figpath)
(PROOT/"data"/"processed"/"paper_numbers_corrected.json").write_text(json.dumps(snap, indent=2))
print("Wrote paper_numbers_corrected.json")
