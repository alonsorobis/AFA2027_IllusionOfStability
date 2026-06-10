"""Smoke tests for the package skeleton.

Verifies that imports work and that the unimplemented functions raise
NotImplementedError instead of crashing silently. Replaced by real unit
tests as each module is implemented.
"""

from __future__ import annotations

import pytest


def test_import_top_level():
    import stablecoin_ms

    assert stablecoin_ms.__version__ == "0.1.0.dev0"


def test_class_keys_consistent():
    from stablecoin_ms.scenario import CLASS_KEYS

    assert CLASS_KEYS == ("retail", "wholesale", "cross_border", "market_maker")


def test_corridor_map_consistent():
    from stablecoin_ms.cost_benefit import (
        CORRIDORS,
        CORRIDOR_TO_CLASS,
        CORRIDOR_TO_INCUMBENT,
    )

    assert set(CORRIDORS) == set(CORRIDOR_TO_CLASS)
    assert set(CORRIDORS) == set(CORRIDOR_TO_INCUMBENT)


def test_issuer_primary_payment_simple():
    from stablecoin_ms.issuer import primary_payment, unmet_demand, primary_share

    assert primary_payment(D=10, R=4) == 4
    assert unmet_demand(D=10, R=4) == 6
    assert primary_share(D=10, R=4) == pytest.approx(0.4)
    assert primary_share(D=4, R=10) == 1.0


def test_remaining_stubs_raise_not_implemented():
    """Stubs that are still placeholders as of session 06.

    signals, secondary, payoffs, fixed_point, montecarlo and calibration are
    implemented. The remaining placeholders live in cost_benefit (the §6
    metric is wired in a later session once the calibrated scenarios exist).
    """
    from stablecoin_ms import cost_benefit

    with pytest.raises(NotImplementedError):
        cost_benefit.compute_cec_stablecoin(
            draws=None, klass="retail", fee_stablecoin_per_unit=0.0,
            cq=0.0, q=0.0, hazard_lgd_product=0.0, gamma_k=0.0,
        )
    with pytest.raises(NotImplementedError):
        cost_benefit.breakeven_theta(scenario=None, klass="retail", rail=None)
