"""Per-class agent state and signal draws.

Each class k in CLASS_KEYS has population share pi_k, balance B_k, signal
noise sigma_k. The model is atomistic within class, so "agents.py" exposes
class-level aggregates rather than per-individual structs.

See `planning/MODEL.md` Sections 1-2.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from .scenario import CLASS_KEYS


def class_stake(scenario) -> Dict[str, float]:
    """W_k = pi_k * B_k for each class."""
    return {
        k: scenario.classes.pi[k] * scenario.classes.B[k] for k in CLASS_KEYS
    }


def total_stake(scenario) -> float:
    """W = sum_k W_k."""
    return sum(class_stake(scenario).values())


def draw_class_assignments(
    n_agents: int,
    pi: Dict[str, float],
    rng: np.random.Generator,
) -> np.ndarray:
    """Multinomial assignment of n_agents to the K classes.

    Returned array contains integer codes that index `CLASS_KEYS`.
    """
    keys = list(CLASS_KEYS)
    probs = np.array([pi[k] for k in keys], dtype=float)
    if not np.isclose(probs.sum(), 1.0):
        raise ValueError(f"pi must sum to 1, got {probs.sum()}")
    return rng.choice(len(keys), size=n_agents, p=probs)
