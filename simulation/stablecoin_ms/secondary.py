"""Secondary-market block.

p_sec(D) = min(1, max(p_underbar, 1 - psi*(U/Mtilde)^nu - mu_q*q - xi*h))
Mtilde   = M / (1 + zeta * U / M)

See `planning/MODEL.md` Section 3.
"""

from __future__ import annotations


def effective_depth(U: float, M: float, zeta: float) -> float:
    """Mtilde = M / (1 + zeta * U / M).

    Depth erodes monotonically with unmet primary demand U.
    """
    if M <= 0:
        raise ValueError("M must be positive")
    if U < 0:
        raise ValueError("U must be non-negative")
    if zeta < 0:
        raise ValueError("zeta must be non-negative")
    return float(M / (1.0 + zeta * U / M))


def secondary_price(
    U: float,
    M: float,
    psi: float,
    nu: float,
    mu_q: float,
    q: float,
    xi: float,
    h: float,
    p_underbar: float,
    zeta: float,
    noise: float = 0.0,
) -> float:
    """Realised secondary-market price.

    Bounded in [p_underbar, 1]. The raw formula is

        1 - psi * (U / Mtilde)^nu - mu_q * q - xi * h + noise

    capped above at 1 and floored at p_underbar. See MODEL.md eq. for p_sec(D).
    """
    if not 0.0 <= p_underbar <= 1.0:
        raise ValueError("p_underbar must be in [0,1]")
    Mtilde = effective_depth(U, M, zeta)
    impact = (U / Mtilde) ** nu if U > 0 else 0.0
    # Counterparty risk (xi, h) no longer marks down the realised secondary
    # price; it is priced through the holder's value of holding in payoffs.V_H.
    # xi and h are retained in the signature for backward compatibility.
    raw = 1.0 - psi * impact - mu_q * q + noise
    return float(min(1.0, max(p_underbar, raw)))
