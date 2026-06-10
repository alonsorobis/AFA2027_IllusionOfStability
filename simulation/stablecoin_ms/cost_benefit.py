"""Certainty-equivalent cost-benefit metric vs incumbent rail.

See `planning/MODEL.md` Section 6.

For corridor c with stablecoin class k and incumbent rail i:

    CEC_stbl_c = E_theta[ fee_stbl_c
                          + (1 - p_sec(D)) * 1{s_i < s*_k}
                          + c_q * q
                          + h * LGD ]
                 + gamma_k * Var_theta(p_sec(D))

    CEC_inc_c  = fee_inc_c + c_settle_inc_c + rho_inc_c

The net metric  CEC_stbl_c - CEC_inc_c  is the headline number.
"""

from __future__ import annotations

from dataclasses import dataclass


CORRIDORS = ("US_to_MX", "US_to_PHL", "EU_to_BR")
CORRIDOR_TO_CLASS = {
    "US_to_MX": "retail",
    "US_to_PHL": "cross_border",
    "EU_to_BR": "wholesale",
}
CORRIDOR_TO_INCUMBENT = {
    "US_to_MX": "Wise",
    "US_to_PHL": "fintech_remittance_benchmark",
    "EU_to_BR": "TARGET2_to_BR_RTGS_via_correspondent",
}


@dataclass(frozen=True)
class IncumbentRail:
    name: str
    fee_per_unit: float
    settle_cost_per_unit: float
    risk_premium_per_unit: float


@dataclass(frozen=True)
class CECResult:
    corridor: str
    klass: str
    incumbent: str
    cec_stablecoin: float
    cec_incumbent: float
    net: float                  # cec_stablecoin - cec_incumbent
    expected_haircut: float
    expected_default_loss: float
    variance_p_sec: float


def compute_cec_stablecoin(
    draws,
    klass: str,
    fee_stablecoin_per_unit: float,
    cq: float,
    q: float,
    hazard_lgd_product: float,
    gamma_k: float,
) -> float:
    """Compute CEC for the stablecoin in one corridor from a list of DrawResult."""
    raise NotImplementedError("implement the expectation from MODEL.md §6")


def compute_cec_incumbent(rail: IncumbentRail) -> float:
    """Compute CEC for the incumbent rail. Linear in observed components."""
    return rail.fee_per_unit + rail.settle_cost_per_unit + rail.risk_premium_per_unit


def breakeven_theta(scenario, klass: str, rail: IncumbentRail) -> float:
    """The theta at which CEC_stablecoin = CEC_incumbent.

    Reported in §6 of the paper for each of the three corridors.
    """
    raise NotImplementedError("root-find over theta with scipy.optimize.brentq")
