"""
quaternion.py – Quaternion bridge class for the rqm-qiskit layer.

Re-exports :class:`rqm_core.quaternion.Quaternion` as a thin subclass that
adds a ``pretty()`` convenience method and overrides arithmetic operators
to return the bridge type for consistency.

All canonical quaternion math (``from_axis_angle``, ``from_axis_angle_vec``,
``to_axis_angle``, ``canonicalize``, ``rotate_vector``, ``to_su2_matrix``,
``to_rotation_matrix``) is inherited unchanged from rqm-core.

Users who previously did::

    from rqm_qiskit.quaternion import Quaternion

can continue to do so without any changes.
"""

from __future__ import annotations

from rqm_core.quaternion import Quaternion as _CoreQuaternion


class Quaternion(_CoreQuaternion):
    """Unit quaternion for SU(2) rotations and state geometry.

    Inherits all mathematics from :class:`rqm_core.quaternion.Quaternion`.

    Canonical methods inherited from rqm-core (NOT redefined here):
    ``from_axis_angle``, ``from_axis_angle_vec``, ``to_axis_angle``,
    ``canonicalize``, ``rotate_vector``, ``identity``, ``to_su2_matrix``,
    ``to_rotation_matrix``, ``norm``, ``is_unit``.

    Bridge additions:
    - ``pretty()`` – human-readable formatted string.
    - ``normalize``, ``conjugate``, ``inverse``, ``__mul__`` – thin wrappers
      that ensure the bridge type is returned for arithmetic operations.
    """

    # ------------------------------------------------------------------
    # Overrides to ensure bridge operations return bridge Quaternion type
    # (rqm-core arithmetic methods return CoreQuaternion instances)
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
