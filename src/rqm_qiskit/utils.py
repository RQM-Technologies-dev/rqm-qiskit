"""
utils.py – Internal utility helpers for rqm_qiskit.

These are small, generic helpers used across the package.
They are not part of the public API and may change without notice.

Note: spinor normalization and other quantum-math utilities come from
``rqm_core`` (the canonical source of truth for shared math).
"""

from __future__ import annotations

import math


def rad_to_deg(radians: float) -> float:
    """Convert radians to degrees."""
    return math.degrees(radians)


def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians."""
    return math.radians(degrees)
