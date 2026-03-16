"""
quaternion.py – Compatibility shim that re-exports Quaternion from rqm-core.

The canonical quaternion / SU(2) mathematics now lives in rqm-core.  This
module re-exports ``Quaternion`` for backward compatibility and adds a
``pretty()`` method that is specific to the rqm-qiskit bridge layer.

Users who previously did::

    from rqm_qiskit.quaternion import Quaternion

can continue to do so without any changes.
"""

from __future__ import annotations

from rqm_core.quaternion import Quaternion as _CoreQuaternion


class Quaternion(_CoreQuaternion):
    """Unit quaternion for SU(2) rotations and state geometry.

    Re-exports all mathematics from :class:`rqm_core.quaternion.Quaternion`.
    Adds :meth:`pretty` for human-readable bridge-layer output.

    All core methods (``from_axis_angle``, ``identity``, arithmetic,
    ``to_su2_matrix``, etc.) are inherited unchanged from rqm-core.
    """

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
