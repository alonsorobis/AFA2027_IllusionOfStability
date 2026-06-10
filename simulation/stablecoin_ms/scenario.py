"""Scenario parameter container.

A `Scenario` instance freezes the parameter set that defines one Monte Carlo
experiment. It is constructed once per scenario (baseline, USDC-2023,
Brazil-ban, TerraUSD-falsification) and passed into the MC loop.

The parameter names map one-to-one to the symbols in `planning/MODEL.md`.

Implementation note: the skeleton uses plain `dataclasses` so the package
imports with zero non-stdlib dependencies. Stricter validation via pydantic
can be layered on top once the simulation is operational (requirements.txt
already lists pydantic as a recommended dependency).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


CLASS_KEYS = ("retail", "wholesale", "cross_border", "market_maker")


def _check_keys(d: Dict[str, float], name: str) -> None:
    missing = [k for k in CLASS_KEYS if k not in d]
    extra = [k for k in d if k not in CLASS_KEYS]
    if missing or extra:
        raise ValueError(
            f"{name}: keys must be exactly {CLASS_KEYS}; "
            f"missing={missing}, extra={extra}"
        )


@dataclass(frozen=True)
class ClassParameters:
    """Per-class parameters keyed by the four classes in `CLASS_KEYS`."""

    pi: Dict[str, float]       # population shares, sum to 1
    B: Dict[str, float]        # per-capita stablecoin balance
    sigma: Dict[str, float]    # signal noise sigma_k > 0
    omega: Dict[str, float]    # convenience yield of holding
    cq: Dict[str, float]       # congestion cost per unit queue

    def __post_init__(self) -> None:
        for name, d in (("pi", self.pi), ("B", self.B), ("sigma", self.sigma),
                        ("omega", self.omega), ("cq", self.cq)):
            _check_keys(d, name)
        if any(v <= 0 for v in self.sigma.values()):
            raise ValueError("sigma_k must be strictly positive")
        s = sum(self.pi.values())
        if abs(s - 1.0) > 1e-9:
            raise ValueError(f"pi must sum to 1, got {s}")


@dataclass(frozen=True)
class IssuerParameters:
    R: float            # liquid reserves at the issuer, >= 0
    A: float            # illiquid assets at the issuer, >= 0
    h: float            # issuer default hazard in [0,1]
    xi: float           # loss given default borne by the holder, >= 0

    def __post_init__(self) -> None:
        if self.R < 0 or self.A < 0 or self.xi < 0:
            raise ValueError("R, A, xi must be non-negative")
        if not 0.0 <= self.h <= 1.0:
            raise ValueError("h must be in [0,1]")


@dataclass(frozen=True)
class SecondaryParameters:
    M: float                 # baseline secondary market depth, > 0
    psi: float               # price-impact scale, >= 0
    nu: float                # price-impact convexity, > 0 (paper expects > 1)
    mu_q: float              # congestion penalty, >= 0
    zeta: float              # depth erosion coefficient, >= 0
    p_underbar: float        # floor on secondary price, in [0,1]

    def __post_init__(self) -> None:
        if self.M <= 0 or self.nu <= 0:
            raise ValueError("M and nu must be strictly positive")
        if min(self.psi, self.mu_q, self.zeta) < 0:
            raise ValueError("psi, mu_q, zeta must be non-negative")
        if not 0.0 <= self.p_underbar <= 1.0:
            raise ValueError("p_underbar must be in [0,1]")


@dataclass(frozen=True)
class RailParameters:
    """Rail-state parameters. Queue ratio q is a parameter at scenario level."""

    q: Dict[str, float]       # per-class queue ratio q_k in [0,1]

    def __post_init__(self) -> None:
        _check_keys(self.q, "q")
        if any(not 0.0 <= v <= 1.0 for v in self.q.values()):
            raise ValueError("q_k must be in [0,1]")


@dataclass(frozen=True)
class ThetaPrior:
    """Improper-uniform-prior limit is the default; mean/tau are book-keeping only."""

    mean: float = 0.0
    tau: float = 0.0   # tau=0 corresponds to the improper-prior limit

    def __post_init__(self) -> None:
        if self.tau < 0:
            raise ValueError("tau must be non-negative")


@dataclass(frozen=True)
class Scenario:
    """Top-level container."""

    name: str
    n_agents: int
    n_draws: int
    seed: int
    classes: ClassParameters
    issuer: IssuerParameters
    secondary: SecondaryParameters
    rails: RailParameters
    theta_prior: ThetaPrior = field(default_factory=ThetaPrior)
    redemption_fee: float = 0.0    # phi in V_R, >= 0

    def __post_init__(self) -> None:
        if self.n_agents <= 0 or self.n_draws <= 0:
            raise ValueError("n_agents and n_draws must be positive")
        if self.redemption_fee < 0:
            raise ValueError("redemption_fee must be non-negative")

    def total_stake(self) -> float:
        """W = sum_k pi_k * B_k (per-capita weighted)."""
        return sum(self.classes.pi[k] * self.classes.B[k] for k in CLASS_KEYS)


@dataclass(frozen=True)
class DrawResult:
    """Result of one Monte Carlo draw."""

    theta: float
    thresholds: Dict[str, float]            # s_star_k
    redemption_rate: Dict[str, float]       # Phi((s_star_k - theta) / sigma_k)
    aggregate_demand: float                 # D
    primary_paid: float                     # P
    unmet_demand: float                     # U
    secondary_price: float                  # p_sec
    converged: bool
    iterations: int
    metadata: Dict[str, float] = field(default_factory=dict)
