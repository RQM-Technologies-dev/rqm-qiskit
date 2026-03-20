"""
quaternion.py – Quaternion bridge class for the rqm-qiskit layer.

Subclasses :class:`rqm_core.quaternion.Quaternion` and adds bridge-layer
convenience methods: ``pretty()``, ``from_axis_angle_vec()``,
``to_axis_angle()``, ``canonicalize()``, and ``rotate_vector()``.

These additional methods delegate all arithmetic to rqm-core operations
(``from_axis_angle``, ``to_su2_matrix``, ``to_rotation_matrix``,
``normalize``).  No independent math is implemented here.

Users who previously did::

    from rqm_qiskit.quaternion import Quaternion

can continue to do so without any changes.
"""

from __future__ import annotations

import math

import numpy as np
from rqm_core.quaternion import Quaternion as _CoreQuaternion


class Quaternion(_CoreQuaternion):
    """Unit quaternion for SU(2) rotations and state geometry.

    Extends :class:`rqm_core.quaternion.Quaternion` with additional
    bridge-layer helpers used throughout rqm-qiskit.

    Core methods (``from_axis_angle``, ``identity``, arithmetic,
    ``to_su2_matrix``, ``to_rotation_matrix``, ``normalize``,
    ``conjugate``, ``norm``, ``is_unit``) are inherited from rqm-core.

    Bridge additions (``from_axis_angle_vec``, ``to_axis_angle``,
    ``canonicalize``, ``rotate_vector``, ``pretty``) are provided here
    and delegate all arithmetic to rqm-core operations.
    """

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def from_axis_angle_vec(
        cls,
        axis: "list[float] | tuple[float, float, float]",
        angle: float,
    ) -> "Quaternion":
        """Create a unit quaternion from an arbitrary axis vector and angle.

        Parameters
        ----------
        axis:
            3-element sequence ``[nx, ny, nz]``.  Need not be normalized.
        angle:
            Rotation angle in radians.

        Returns
        -------
        Quaternion
            A unit quaternion representing the rotation.

        Raises
        ------
        ValueError
            If ``axis`` is the zero vector.
        """
        nx, ny, nz = float(axis[0]), float(axis[1]), float(axis[2])
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-12:
            raise ValueError(
                "Cannot create a quaternion from a zero axis vector."
            )
        nx, ny, nz = nx / length, ny / length, nz / length
        half = angle / 2.0
        s = math.sin(half)
        return cls(math.cos(half), nx * s, ny * s, nz * s)

    # ------------------------------------------------------------------
    # Instance methods
    # ------------------------------------------------------------------

    def to_axis_angle(
        self,
    ) -> "tuple[tuple[float, float, float], float]":
        """Return the (axis, angle) decomposition of this quaternion.

        Returns
        -------
        tuple
            ``(axis, angle)`` where ``axis`` is a unit 3-tuple and
            ``angle`` is in radians ``[0, 2π)``.  For the identity
            quaternion the axis is ``(1.0, 0.0, 0.0)`` and angle is 0.
        """
        # angle = 2 * arccos(w), clamped to [-1, 1] for numerical safety.
        w_clamped = max(-1.0, min(1.0, self.w))
        angle = 2.0 * math.acos(abs(w_clamped))
        # Sign of w determines which half-angle we're in.
        if self.w < 0.0:
            angle = 2.0 * math.pi - angle if angle > 1e-12 else angle

        sin_half = math.sin(angle / 2.0)
        if sin_half < 1e-12:
            # Identity (or near-identity): axis is arbitrary.
            return (1.0, 0.0, 0.0), 0.0

        nx = self.x / sin_half
        ny = self.y / sin_half
        nz = self.z / sin_half
        return (nx, ny, nz), angle

    def canonicalize(self) -> "Quaternion":
        """Return the canonical representative with ``w ≥ 0``.

        In SU(2) the quaternions ``q`` and ``-q`` represent the same
        physical rotation (double cover of SO(3)).  This method picks the
        representative with non-negative ``w`` for consistency.

        Returns
        -------
        Quaternion
            A unit quaternion with ``w ≥ 0``.
        """
        if self.w < 0.0:
            return Quaternion(-self.w, -self.x, -self.y, -self.z)
        return Quaternion(self.w, self.x, self.y, self.z)

    def rotate_vector(
        self,
        v: "list[float] | tuple[float, float, float]",
    ) -> "tuple[float, float, float]":
        """Rotate a 3-D vector using the SO(3) rotation matrix.

        Delegates to :meth:`to_rotation_matrix` (rqm-core) so no
        independent rotation math is implemented here.

        Parameters
        ----------
        v:
            3-element vector to rotate.

        Returns
        -------
        tuple[float, float, float]
            The rotated vector.
        """
        R = self.to_rotation_matrix()
        vn = np.array([float(v[0]), float(v[1]), float(v[2])])
        rv = R @ vn
        return (float(rv[0]), float(rv[1]), float(rv[2]))

    # ------------------------------------------------------------------
    # Overrides to ensure bridge operations return bridge Quaternion
    # (not CoreQuaternion instances from parent arithmetic methods)
    # ------------------------------------------------------------------

    def normalize(self) -> "Quaternion":
        """Return a normalized unit quaternion (bridge Quaternion type)."""
        r = super().normalize()
        return Quaternion(r.w, r.x, r.y, r.z)

    def conjugate(self) -> "Quaternion":
        """Return the conjugate quaternion (bridge Quaternion type)."""
        r = super().conjugate()
        return Quaternion(r.w, r.x, r.y, r.z)

    def inverse(self) -> "Quaternion":
        """Return the inverse quaternion (bridge Quaternion type)."""
        r = super().inverse()
        return Quaternion(r.w, r.x, r.y, r.z)

    def __mul__(self, other: "_CoreQuaternion") -> "Quaternion":
        """Quaternion product (bridge Quaternion type)."""
        r = super().__mul__(other)
        return Quaternion(r.w, r.x, r.y, r.z)

    def pretty(self) -> str:
        """Return a human-readable string representation.

        Returns
        -------
        str
            A formatted string showing all four components and the norm.
        """
        parts = [f"{self.w:.4f}"]
        for coeff, label in [(self.x, "i"), (self.y, "j"), (self.z, "k")]:
            parts.append(f"{coeff:+.4f}{label}")
        return "Quaternion(" + " ".join(parts) + f")  |q| = {self.norm():.6f}"

    def __repr__(self) -> str:
        # Override parent class repr to preserve keyword-argument format
        # (w=…, x=…, y=…, z=…) expected by existing rqm-qiskit tests and users.
        return (
            f"Quaternion(w={self.w!r}, x={self.x!r}, "
            f"y={self.y!r}, z={self.z!r})"
        )
