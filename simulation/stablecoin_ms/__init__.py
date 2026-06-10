"""Stablecoin microstructure ABM with endogenous Morris-Shin redemption.

This package implements the model stated in `planning/MODEL.md` of the
AFA 2027 *Illusion of Stability* submission. It is built from scratch
on 2026-06-01 inside AI-supervised sessions, per the AFA timing rule.
"""

__version__ = "0.1.0.dev0"
__project__ = "afa2027-illusion-of-stability"
__build_date__ = "2026-06-01"

__all__ = [
    "agents",
    "issuer",
    "secondary",
    "signals",
    "fixed_point",
    "payoffs",
    "scenario",
    "montecarlo",
    "calibration",
    "cost_benefit",
]
