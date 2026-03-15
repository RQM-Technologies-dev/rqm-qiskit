"""
utils.py – Internal utility helpers for rqm_qiskit.

These are small, generic helpers used across the package.
They are not part of the public API and may change without notice.
"""

from __future__ import annotations

import math


def normalize(alpha: complex, beta: complex) -> tuple[complex, complex]:
    """Normalize a 2-component complex vector.

    Parameters
    ----------
    alpha, beta:
        Raw amplitudes.

    Returns
    -------
    tuple[complex, complex]
        Normalized (alpha, beta) such that |alpha|² + |beta|² = 1.

    Raises
    ------
    ValueError
        If the norm is effectively zero.
    """
    norm = math.sqrt(abs(alpha) ** 2 + abs(beta) ** 2)
    if norm < 1e-10:
        raise ValueError(
            "Cannot normalize a zero vector. "
            "At least one amplitude must be non-zero."
        )
    return (alpha / norm, beta / norm)


def rad_to_deg(radians: float) -> float:
    """Convert radians to degrees."""
    return math.degrees(radians)


def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians."""
    return math.radians(degrees)
