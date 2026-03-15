"""
quaternion.py – A lightweight Quaternion class for SU(2) / quantum-state geometry.

A unit quaternion q = w + x·i + y·j + z·k represents an SU(2) rotation
in the same mathematical structure as a single-qubit gate.

The isomorphism is:
    Quaternion basis element  →  SU(2) generator
    i  ↔  -i·σ_x
    j  ↔  -i·σ_y
    k  ↔  -i·σ_z

So a rotation by angle θ around unit-vector axis n̂ = (n_x, n_y, n_z) maps to:
    q   = cos(θ/2) + sin(θ/2)·(n_x·i + n_y·j + n_z·k)
    U   = cos(θ/2)·I − i·sin(θ/2)·(n_x·σ_x + n_y·σ_y + n_z·σ_z)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


class Quaternion:
    """A quaternion q = w + x·i + y·j + z·k.

    Used here to represent SU(2) rotations.  ``w``, ``x``, ``y``, and ``z``
    are real floating-point numbers.

    Unit quaternions (those with ``norm() == 1``) correspond exactly to
    elements of SU(2) and therefore to single-qubit rotation gates.

    Parameters
    ----------
    w, x, y, z:
        Real components of the quaternion.
    """

    def __init__(self, w: float, x: float, y: float, z: float) -> None:
        self._w = float(w)
        self._x = float(x)
        self._y = float(y)
        self._z = float(z)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def w(self) -> float:
        """Scalar (real) component."""
        return self._w

    @property
    def x(self) -> float:
        """Coefficient of i."""
        return self._x

    @property
    def y(self) -> float:
        """Coefficient of j."""
        return self._y

    @property
    def z(self) -> float:
        """Coefficient of k."""
        return self._z

    # ------------------------------------------------------------------
    # Named constructors
    # ------------------------------------------------------------------

    @classmethod
    def identity(cls) -> "Quaternion":
        """Return the identity quaternion (1, 0, 0, 0).

        Corresponds to the identity SU(2) matrix (no rotation).
        """
        return cls(1.0, 0.0, 0.0, 0.0)

    @classmethod
    def from_axis_angle(cls, axis: str, angle: float) -> "Quaternion":
        """Return a unit quaternion for a rotation around a Cartesian axis.

        The rotation is by ``angle`` radians around the given axis.  The
        formula is:
            q = cos(θ/2) + sin(θ/2)·(axis_vector)

        Parameters
        ----------
        axis:
            One of ``"x"``, ``"y"``, ``"z"``.
        angle:
            Rotation angle in radians.

        Returns
        -------
        Quaternion
            A unit quaternion.

        Raises
        ------
        ValueError
            If ``axis`` is not one of the allowed values.
        """
        axis = axis.lower()
        if axis not in {"x", "y", "z"}:
            raise ValueError(
                f"Invalid axis {axis!r}. Must be one of ['x', 'y', 'z']."
            )
        half = angle / 2.0
        c = math.cos(half)
        s = math.sin(half)

        if axis == "x":
            return cls(c, s, 0.0, 0.0)
        if axis == "y":
            return cls(c, 0.0, s, 0.0)
        # axis == "z"
        return cls(c, 0.0, 0.0, s)

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    def __mul__(self, other: "Quaternion") -> "Quaternion":
        """Quaternion (Hamilton) product.

        Represents composition of rotations.

        Parameters
        ----------
        other:
            The right-hand quaternion.
        """
        if not isinstance(other, Quaternion):
            return NotImplemented  # type: ignore[return-value]

        w1, x1, y1, z1 = self._w, self._x, self._y, self._z
        w2, x2, y2, z2 = other._w, other._x, other._y, other._z

        return Quaternion(
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )

    def conjugate(self) -> "Quaternion":
        """Return the conjugate  q* = w − x·i − y·j − z·k."""
        return Quaternion(self._w, -self._x, -self._y, -self._z)

    # ------------------------------------------------------------------
    # Norm and normalization
    # ------------------------------------------------------------------

    def norm(self) -> float:
        """Return the Euclidean norm |q| = sqrt(w² + x² + y² + z²)."""
        return math.sqrt(
            self._w ** 2 + self._x ** 2 + self._y ** 2 + self._z ** 2
        )

    def normalize(self) -> "Quaternion":
        """Return a unit quaternion in the same direction.

        Raises
        ------
        ValueError
            If the quaternion has zero norm.
        """
        n = self.norm()
        if n < 1e-10:
            raise ValueError(
                "Cannot normalize a zero quaternion. "
                "At least one component must be non-zero."
            )
        return Quaternion(self._w / n, self._x / n, self._y / n, self._z / n)

    def is_unit(self, tol: float = 1e-10) -> bool:
        """Return ``True`` if this is a unit quaternion within tolerance."""
        return abs(self.norm() - 1.0) < tol

    # ------------------------------------------------------------------
    # Conversion to SU(2)
    # ------------------------------------------------------------------

    def to_su2_matrix(self) -> np.ndarray:
        """Return the 2×2 complex SU(2) matrix for this (unit) quaternion.

        The mapping is:
            U = [[w − i·z,  −(y + i·x)],
                 [y − i·x,   w + i·z  ]]

        This corresponds to the standard identification:
            i (quat)  ↔  −i·σ_x
            j (quat)  ↔  −i·σ_y
            k (quat)  ↔  −i·σ_z

        Returns
        -------
        numpy.ndarray
            Shape ``(2, 2)``, dtype ``complex128``.
        """
        w, x, y, z = self._w, self._x, self._y, self._z
        return np.array(
            [[w - 1j * z,  -(y + 1j * x)],
             [y - 1j * x,   w + 1j * z  ]],
            dtype=complex,
        )

    # ------------------------------------------------------------------
    # Pretty printing
    # ------------------------------------------------------------------

    def pretty(self) -> str:
        """Return a human-readable representation."""
        parts = [f"{self._w:.4f}"]
        for coeff, label in [(self._x, "i"), (self._y, "j"), (self._z, "k")]:
            parts.append(f"{coeff:+.4f}{label}")
        return "Quaternion(" + " ".join(parts) + f")  |q| = {self.norm():.6f}"

    def __repr__(self) -> str:
        return (
            f"Quaternion(w={self._w!r}, x={self._x!r}, "
            f"y={self._y!r}, z={self._z!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quaternion):
            return NotImplemented
        return np.allclose(
            [self._w, self._x, self._y, self._z],
            [other._w, other._x, other._y, other._z],
        )
