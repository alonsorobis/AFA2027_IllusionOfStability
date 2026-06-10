"""Issuer balance-sheet block.

Maps aggregate redemption demand D into primary payments P and unmet demand U.
See `planning/MODEL.md` Section 3.
"""

from __future__ import annotations


def primary_payment(D: float, R: float) -> float:
    """P = min(D, R)."""
    if D < 0 or R < 0:
        raise ValueError("D and R must be non-negative")
    return min(D, R)


def unmet_demand(D: float, R: float) -> float:
    """U = max(D - R, 0)."""
    return max(D - R, 0.0)


def primary_share(D: float, R: float) -> float:
    """Per-redeeming-agent share that gets paid at par."""
    if D <= 0:
        return 1.0
    return min(1.0, R / D)
