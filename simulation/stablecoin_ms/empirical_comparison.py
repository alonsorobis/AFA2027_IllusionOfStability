"""Empirical cost-benefit comparison framework for the IJCB submission.

The Morris-Shin model (in `simple_calibration.py`) gives us the
stablecoin-specific risk premium decomposed into counterparty (constant)
and depeg (regime-weighted) components. The empirical comparison module
takes that risk premium plus observable rail-specific fees and latencies
and produces per-use-case net costs.

Three use cases cover the policy space:

  1. BR→BR domestic retail: PIX (upgraded public rail) versus bank transfer
     (incumbent) versus USDT-on-Tron (stablecoin).
  2. US→MX cross-border retail: SWIFT correspondent versus Wise (fintech
     upgraded) versus USDT-on-Tron.
  3. EU→BR cross-border with the November 2025 BCB regulatory package:
     SWIFT correspondent versus USDT-on-Tron at pre- and post-package
     friction.

For each cell the net cost (basis points of transaction value) is
fee + settlement working-capital cost + risk premium. The risk premium
is zero for traditional and upgraded rails (counterparty risk is borne by
the central bank or RTGS operator; no depeg risk because the unit of
account matches the settlement asset). Operational risk (queues from
public-sector outages, blackouts) exists for every rail and we treat it
as a common term that drops out of the comparison.

The framework is reused in Section 7 to overlay a Nexus projection on the
two cross-border use cases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Rail catalog
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RailSpec:
    name: str
    rail_type: str
    fee_bps_at_400usd: float
    fee_bps_at_1000usd: float
    settlement_delay_days: float
    counterparty_risk_bps: float
    depeg_risk_bps: float
    description: str
    source: str


# Reference rates for working-capital cost (SOFR proxy)
SOFR_REFERENCE_PCT = 4.5    # annualised, basis-point rate for working-capital cost
EURO_RATE_PCT = 2.5         # ECB MRO proxy

# Tron USDT transfer fee (USD). The Tron network ratified proposal #104 on
# 2025-08-29 cutting the energy unit price from 210 sun to 100 sun. After
# the cut, the headline costs at the TRX price prevailing in Q1 2026 are:
#   - first transfer to a new wallet:    ~13.14 TRX  ≈ $1.92
#   - repeat transfer to existing wallet: ~6.57 TRX  ≈ $1.42
#   - with energy rental (TronSave etc.): ~4.66 TRX  ≈ $0.50
# We use the repeat-transfer cost as the headline number because the use
# cases below presume an established sender-receiver pair (remittance
# corridor, retail merchant); a sensitivity panel is in Appendix A2 of the
# paper. Sources:
#   https://blog.tronsave.io/how-much-does-it-cost-to-send-usdt-trc20/
#   https://gasfeesnow.com/tron/
USDT_TRON_FEE_USD = 1.50
USDT_TRON_FEE_USD_FIRST = 1.92
USDT_TRON_FEE_USD_REPEAT = 1.42
USDT_TRON_FEE_USD_RENTED = 0.50

# Stablecoin risk premium components, filled from simple_calibration output.
# Defaults below are the 7-parameter calibration manifest
# data/processed/simple_calibration_20260602T092829Z/manifest.json
# Total weighted premium at p_stress=0.01084 is 61.4 bps.
STABLECOIN_COUNTERPARTY_BPS = 20.0
STABLECOIN_DEPEG_BASELINE_BPS = 39.29
STABLECOIN_DEPEG_STRESS_BPS = 235.02
STABLECOIN_P_STRESS = 96.0 / 8856.0    # empirical fraction of stress hours in 2022-2023 window


def load_stablecoin_risk(manifest_path: Path | str | None = None) -> Dict[str, float]:
    """Load the latest simple_calibration (USDC) risk components into module globals."""
    global STABLECOIN_COUNTERPARTY_BPS, STABLECOIN_DEPEG_BASELINE_BPS, STABLECOIN_DEPEG_STRESS_BPS
    if manifest_path is None:
        cands = sorted((PROJECT_ROOT / "data" / "processed").glob("simple_calibration_*/manifest.json"))
        if not cands:
            return {
                "counterparty_loss_bps": STABLECOIN_COUNTERPARTY_BPS,
                "depeg_loss_baseline_bps": STABLECOIN_DEPEG_BASELINE_BPS,
                "depeg_loss_stress_bps": STABLECOIN_DEPEG_STRESS_BPS,
            }
        manifest_path = cands[-1]
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    risk = manifest["risk_components"]
    STABLECOIN_COUNTERPARTY_BPS = float(risk["counterparty_loss_bps"])
    STABLECOIN_DEPEG_BASELINE_BPS = float(risk["depeg_loss_baseline_bps"])
    STABLECOIN_DEPEG_STRESS_BPS = float(risk["depeg_loss_stress_bps"])
    return risk


def load_usdt_risk(manifest_path: Path | str | None = None) -> Dict[str, float]:
    """Load the latest usdt_calibration risk components. Returns a dict; does not
    overwrite the USDC module globals."""
    if manifest_path is None:
        cands = sorted((PROJECT_ROOT / "data" / "processed").glob("usdt_calibration_*/manifest.json"))
        if not cands:
            raise FileNotFoundError("No usdt_calibration manifest found")
        manifest_path = cands[-1]
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return manifest["risk_components"]


def total_risk_bps(rc: Dict[str, float], p_stress: float = None) -> float:
    """Probability-weighted total stablecoin risk premium given a components dict."""
    if p_stress is None:
        p_stress = STABLECOIN_P_STRESS
    depeg = (1 - p_stress) * rc["depeg_loss_baseline_bps"] + p_stress * rc["depeg_loss_stress_bps"]
    return rc["counterparty_loss_bps"] + depeg


def stablecoin_total_risk_bps(p_stress: float = STABLECOIN_P_STRESS) -> float:
    """Probability-weighted total stablecoin-specific risk premium in basis
    points. The two components do not double-count: the counterparty term
    measures issuer-default loss; the depeg term measures the haircut on a
    successfully-redeeming holder net of the issuer-default markdown.
    """
    depeg = (1 - p_stress) * STABLECOIN_DEPEG_BASELINE_BPS + p_stress * STABLECOIN_DEPEG_STRESS_BPS
    return STABLECOIN_COUNTERPARTY_BPS + depeg


# ---------------------------------------------------------------------------
# Working-capital cost helper
# ---------------------------------------------------------------------------


def working_capital_bps(settlement_delay_days: float, annual_rate_pct: float = SOFR_REFERENCE_PCT) -> float:
    """Basis points of transaction value tied up over the settlement window.

    For example, a 2-day settlement delay at a 4.5% annualised rate costs
    2/365 × 4.5% × 1e4 ≈ 25 basis points of transaction value.
    """
    return float(settlement_delay_days / 365.0 * annual_rate_pct * 1e2)


# ---------------------------------------------------------------------------
# Per-use-case definitions
# ---------------------------------------------------------------------------


def fee_bps_for_usdt_tron(tx_value_usd: float) -> float:
    return USDT_TRON_FEE_USD / tx_value_usd * 1e4


@dataclass(frozen=True)
class Comparison:
    use_case: str
    tx_value_usd: float
    p_stress: float
    rails: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add_rail(self, name: str, fee_bps: float, settlement_delay_days: float,
                 rail_class: str, risk_bps: float, regulatory_shock_bps: float = 0.0,
                 source: str = "") -> "Comparison":
        wc = working_capital_bps(settlement_delay_days)
        total = fee_bps + wc + risk_bps + regulatory_shock_bps
        self.rails[name] = {
            "rail_class": rail_class,
            "fee_bps": fee_bps,
            "settlement_delay_days": settlement_delay_days,
            "working_capital_bps": wc,
            "risk_bps": risk_bps,
            "regulatory_shock_bps": regulatory_shock_bps,
            "total_bps": total,
            "source": source,
        }
        return self

    def to_dict(self) -> Dict:
        return {
            "use_case": self.use_case,
            "tx_value_usd": self.tx_value_usd,
            "p_stress": self.p_stress,
            "rails": self.rails,
        }


def usdt_total_risk_bps(p_stress: float = STABLECOIN_P_STRESS,
                          manifest_path: Path | str | None = None) -> float:
    """Probability-weighted USDT risk premium, loaded fresh from manifest."""
    rc = load_usdt_risk(manifest_path)
    return total_risk_bps(rc, p_stress)


def br_domestic_retail(tx_value_usd: float = 40.0,
                        p_stress: float = STABLECOIN_P_STRESS) -> Comparison:
    """Use case 1: a Brazilian household pays a small amount to another
    Brazilian household. The realistic stablecoin in LATAM retail flows is
    USDT (~80% of LATAM stablecoin volume) so we apply the USDT premium."""
    risk_usdt = usdt_total_risk_bps(p_stress)
    c = Comparison(use_case="BR domestic retail (tx ≈ R$200 / $40)",
                   tx_value_usd=tx_value_usd, p_stress=p_stress)
    c.add_rail("PIX (BCB instant payment system)", fee_bps=0.0,
               settlement_delay_days=0.0, rail_class="upgraded_public", risk_bps=0.0,
               source="BCB SPI Annual Report 2024")
    c.add_rail("Bank transfer (TED/DOC)", fee_bps=200.0,
               settlement_delay_days=0.5, rail_class="traditional_incumbent", risk_bps=0.0,
               source="Author benchmark from Brazilian retail banking fee schedules")
    c.add_rail("USDT on Tron", fee_bps=fee_bps_for_usdt_tron(tx_value_usd),
               settlement_delay_days=0.0, rail_class="stablecoin_usdt",
               risk_bps=risk_usdt,
               source="Tron Bandwidth and Energy; USDT risk premium from this paper's USDT calibration (may-2022 anchor)")
    return c


def us_mx_remittance(tx_value_usd: float = 400.0,
                      p_stress: float = STABLECOIN_P_STRESS) -> Comparison:
    """Use case 2: a US household sends a remittance to Mexico. USDT on Tron
    is the dominant real-world stablecoin in this corridor (90%+ of LATAM
    stablecoin remittance flow), so we apply the USDT premium."""
    risk_usdt = usdt_total_risk_bps(p_stress)
    c = Comparison(use_case="US→MX retail remittance (tx ≈ $400)",
                   tx_value_usd=tx_value_usd, p_stress=p_stress)
    c.add_rail("SWIFT correspondent (Bank avg)", fee_bps=331.0,
               settlement_delay_days=2.0, rail_class="traditional_incumbent", risk_bps=0.0,
               source="World Bank RPW Q3 2025, USA→MEX Bank-firmtype mean cost at $500 tier; range [222, 700]")
    c.add_rail("Wise (fintech remittance)", fee_bps=250.0,
               settlement_delay_days=1.0, rail_class="fintech_upgraded_incumbent", risk_bps=0.0,
               source="World Bank RPW Q3 2025, USA→MEX Wise observations at $500 tier (3 obs, range [96, 692])")
    c.add_rail("USDT on Tron", fee_bps=fee_bps_for_usdt_tron(tx_value_usd),
               settlement_delay_days=0.0, rail_class="stablecoin_usdt",
               risk_bps=risk_usdt,
               source="Tron fee + USDT risk premium from this paper's USDT calibration")
    return c


def eu_br_cross_border(tx_value_usd: float = 1000.0,
                        p_stress: float = STABLECOIN_P_STRESS,
                        post_bcb_package: bool = False,
                        asset: str = "USDC") -> Comparison:
    """Use case 3: an EU resident sends value to Brazil. We default to USDC
    because EU-originated cross-border flows are more likely to use the
    EU-regulated MiCA-compliant alternative; USDT is the alternative when
    asset='USDT'. The November 2025 BCB regulatory package adds a friction."""
    if asset.upper() == "USDC":
        risk_premium = stablecoin_total_risk_bps(p_stress)
        risk_source = "USDC risk premium from this paper's USDC calibration (march-2023 anchor)"
        rail_label = "USDC cross-border"
        rail_class = "stablecoin_usdc"
    else:
        risk_premium = usdt_total_risk_bps(p_stress)
        risk_source = "USDT risk premium from this paper's USDT calibration (may-2022 anchor)"
        rail_label = "USDT cross-border"
        rail_class = "stablecoin_usdt"
    label = f"EU→BR cross-border with {asset} (post-BCB package)" if post_bcb_package else \
            f"EU→BR cross-border with {asset} (pre-BCB package)"
    c = Comparison(use_case=f"{label} (tx ≈ $1000)",
                   tx_value_usd=tx_value_usd, p_stress=p_stress)
    c.add_rail("SWIFT correspondent (EUR→BR via USD)", fee_bps=487.0,
               settlement_delay_days=2.0, rail_class="traditional_incumbent", risk_bps=0.0,
               source="World Bank RPW Q3 2025: no ESP→BR Bank observation, ITA→BR Bank mean 1112 bps (n=3, range [864, 1608]); 487 bps used as cautious midpoint")
    c.add_rail("Wise (fintech remittance) EUR→BR", fee_bps=204.0,
               settlement_delay_days=1.0, rail_class="fintech_upgraded_incumbent", risk_bps=0.0,
               source="World Bank RPW Q3 2025, ESP→BR Wise observations at $500 tier (3 obs, range [131, 270])")
    bcb_shock = 150.0 if post_bcb_package else 0.0
    c.add_rail(rail_label, fee_bps=fee_bps_for_usdt_tron(tx_value_usd),
               settlement_delay_days=0.0, rail_class=rail_class,
               risk_bps=risk_premium, regulatory_shock_bps=bcb_shock,
               source=risk_source)
    return c


def nexus_projection_on(comparison: Comparison) -> Comparison:
    """Overlay a projected Nexus rail on a cross-border comparison.

    Nexus assumptions follow the BIS Project Nexus blueprint (July 2024):
    - target settlement latency < 60 seconds (treated as 0 working-capital cost)
    - fee structure compatible with the linked domestic instant payment
      systems; we model it as a flat $0.20 per transaction, in line with the
      SEPA Instant Payments Regulation upper bound of "no more expensive
      than a regular SEPA credit transfer"
    - zero counterparty risk: settlement is via central-bank-backed RTGS
      bridges, no privately-issued claim is held by the user
    """
    nexus_fee_bps = 0.20 / comparison.tx_value_usd * 1e4
    comparison.add_rail("BIS Nexus (projected)", fee_bps=nexus_fee_bps,
               settlement_delay_days=0.0, rail_class="upgraded_public_cross_border",
               risk_bps=0.0,
               source="BIS Project Nexus blueprint July 2024 (bis.org/publ/othp86.pdf); fee projection by authors using SEPA Instant ceiling")
    return comparison


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------


def all_comparisons(p_stress: float = STABLECOIN_P_STRESS,
                     include_nexus: bool = False) -> Dict[str, Comparison]:
    """Build and return the three headline comparisons. Optionally include
    a Nexus projection layer on the two cross-border use cases. Use case 3
    is reported with both USDC and USDT to highlight the divergent risk
    profiles of the two largest stablecoins."""
    out = {
        "use_case_1_br_domestic": br_domestic_retail(p_stress=p_stress),
        "use_case_2_us_mx_remittance": us_mx_remittance(p_stress=p_stress),
        "use_case_3a_eu_br_usdc_pre_package": eu_br_cross_border(p_stress=p_stress, post_bcb_package=False, asset="USDC"),
        "use_case_3a_eu_br_usdc_post_package": eu_br_cross_border(p_stress=p_stress, post_bcb_package=True, asset="USDC"),
        "use_case_3b_eu_br_usdt_pre_package": eu_br_cross_border(p_stress=p_stress, post_bcb_package=False, asset="USDT"),
        "use_case_3b_eu_br_usdt_post_package": eu_br_cross_border(p_stress=p_stress, post_bcb_package=True, asset="USDT"),
    }
    if include_nexus:
        out["use_case_2_us_mx_remittance_with_nexus"] = nexus_projection_on(
            us_mx_remittance(p_stress=p_stress))
        out["use_case_3a_eu_br_usdc_pre_package_with_nexus"] = nexus_projection_on(
            eu_br_cross_border(p_stress=p_stress, post_bcb_package=False, asset="USDC"))
        out["use_case_3b_eu_br_usdt_pre_package_with_nexus"] = nexus_projection_on(
            eu_br_cross_border(p_stress=p_stress, post_bcb_package=False, asset="USDT"))
    return out
