"""
gates.py – RQMGate: a 1-qubit SU(2) rotation gate.

SU(2) matrix generation delegates to rqm-core so that the math lives in
one canonical place.  The Qiskit gate objects are built directly from
Qiskit's rotation-gate library.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from rqm_core.su2 import axis_angle_to_su2

import numpy as np

if TYPE_CHECKING:
    from qiskit.circuit import Gate
    from rqm_compiler import Operation
    from rqm_qiskit.quaternion import Quaternion

_VALID_AXES = {"x", "y", "z"}


class RQMGate:
    """A 1-qubit SU(2) rotation gate defined by an axis and angle.

    The gate represents a rotation of ``angle`` radians around the
    specified Bloch-sphere axis (``"x"``, ``"y"``, or ``"z"``).

    Examples
    --------
    >>> gate = RQMGate.ry(math.pi / 2)
    >>> gate.to_matrix()
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, axis: str, angle: float) -> None:
        """Create an RQMGate.

        Parameters
        ----------
        axis:
            Rotation axis – one of ``"x"``, ``"y"``, ``"z"``.
        angle:
            Rotation angle in radians.

        Raises
        ------
        ValueError
            If ``axis`` is not one of the supported values.
        """
        axis = axis.lower()
        if axis not in _VALID_AXES:
            raise ValueError(
                f"Invalid axis {axis!r}. Must be one of {sorted(_VALID_AXES)}."
            )
        self._axis: str = axis
        self._angle: float = float(angle)

    @classmethod
    def rx(cls, angle: float) -> "RQMGate":
        """Create an R_x rotation gate."""
        return cls("x", angle)

    @classmethod
    def ry(cls, angle: float) -> "RQMGate":
        """Create an R_y rotation gate."""
        return cls("y", angle)

    @classmethod
    def rz(cls, angle: float) -> "RQMGate":
        """Create an R_z rotation gate."""
        return cls("z", angle)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def axis(self) -> str:
        """Rotation axis (``"x"``, ``"y"``, or ``"z"``)."""
        return self._axis

    @property
    def angle(self) -> float:
        """Rotation angle in radians."""
        return self._angle

    @property
    def quaternion(self) -> "Quaternion":
        """The unit quaternion representing this gate.

        Uses :meth:`~rqm_qiskit.Quaternion.from_axis_angle` so that the
        quaternion's SU(2) matrix matches :meth:`to_matrix` exactly.

        Returns
        -------
        :class:`~rqm_qiskit.Quaternion`
            A unit quaternion.
        """
        from rqm_qiskit.quaternion import Quaternion

        return Quaternion.from_axis_angle(self._axis, self._angle)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def to_matrix(self) -> np.ndarray:
        """Return the 2×2 complex unitary rotation matrix.

        Delegates to :func:`rqm_core.su2.axis_angle_to_su2`.

        Returns
        -------
        numpy.ndarray
            Shape ``(2, 2)``, dtype ``complex128``.
        """
        return axis_angle_to_su2(self._axis, self._angle)

    def to_operation(self, qubit: int = 0) -> "Operation":
        """Return the corresponding :class:`~rqm_compiler.ops.Operation`.

        Delegates gate ownership to rqm-compiler, the canonical gate/circuit
        layer.  The axis maps to the rqm-compiler canonical gate name:
        ``"x"`` → ``"rx"``, ``"y"`` → ``"ry"``, ``"z"`` → ``"rz"``.

        Parameters
        ----------
        qubit:
            Target qubit index (default 0).

        Returns
        -------
        :class:`rqm_compiler.ops.Operation`
            A canonical rqm-compiler operation descriptor.
        """
        from rqm_compiler import Operation

        return Operation(
            gate=f"r{self._axis}",
            targets=[qubit],
            params={"angle": self._angle},
        )

    def to_qiskit_gate(self) -> "Gate":
        """Return the corresponding Qiskit gate object.

        Returns
        -------
        qiskit.circuit.Gate
            One of :class:`~qiskit.circuit.library.RXGate`,
            :class:`~qiskit.circuit.library.RYGate`, or
            :class:`~qiskit.circuit.library.RZGate`.
        """
        from qiskit.circuit.library import RXGate, RYGate, RZGate

        mapping = {"x": RXGate, "y": RYGate, "z": RZGate}
        return mapping[self._axis](self._angle)

    def pretty(self) -> str:
        """Return a human-readable description of the gate."""
        return (
            f"RQMGate R{self._axis.upper()}(θ={self._angle:.4f} rad"
            f" ≈ {math.degrees(self._angle):.2f}°)"
        )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"RQMGate(axis={self._axis!r}, angle={self._angle!r})"
