"""
gates.py – RQMGate and named gate quaternion factories.

RQMGate operates in two modes:

* **Rotation mode** (backward-compatible): ``RQMGate("x", angle)``
  represents an axis-angle SU(2) rotation.  SU(2) matrix generation
  delegates to :func:`rqm_core.su2.axis_angle_to_su2`.

* **Named gate mode** (new): ``RQMGate("H", target=0)`` is a simple
  named-gate descriptor consumed by :class:`~rqm_qiskit.backend.QiskitBackend`
  and :class:`~rqm_qiskit.translator.QiskitTranslator`.

Named gate quaternion factories (``gate_h``, ``gate_s``, ``gate_t``,
``gate_rx``, ``gate_ry``, ``gate_rz``) and ``match_gate`` are re-exported
directly from :mod:`rqm_core.gates`.  No math is defined locally.

# NOTE:
# Primary input type is rqm-compiler CompiledProgram.
# RQMGate and dict support are transitional and may be removed in a future
# release.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from rqm_core.su2 import axis_angle_to_su2
from rqm_core.quaternion import Quaternion as _CoreQuaternion

# Named gate factories and gate recognition re-exported from rqm-core.
# These are the canonical implementations; no math is duplicated here.
from rqm_core.gates import (
    gate_h,
    gate_s,
    gate_t,
    gate_rx,
    gate_ry,
    gate_rz,
    match_gate,
)

if TYPE_CHECKING:
    from qiskit.circuit import Gate
    from rqm_compiler import Operation
    from rqm_qiskit.quaternion import Quaternion

_VALID_AXES = {"x", "y", "z"}

# ---------------------------------------------------------------------------
# Named gate → rqm-compiler gate name mapping
# ---------------------------------------------------------------------------

_NAMED_GATE_OPS: dict[str, str] = {
    "I": "i",
    "X": "x",
    "Y": "y",
    "Z": "z",
    "H": "h",
    "S": "s",
    "T": "t",
    "V": "h",  # V gate approximated as H for translation purposes
    "CX": "cx",
    "CNOT": "cx",
    "CY": "cy",
    "CZ": "cz",
    "SWAP": "swap",
    "ISWAP": "iswap",
    "RX": "rx",
    "RY": "ry",
    "RZ": "rz",
    "PHASE": "phaseshift",
}

# Controlled gates: one qubit is "control", one is "target".
_CONTROLLED_GATES: frozenset[str] = frozenset({"CX", "CNOT", "CY", "CZ"})

# Symmetric two-qubit gates: both qubits go in targets, no controls.
_SYMMETRIC_TWO_QUBIT_GATES: frozenset[str] = frozenset({"SWAP", "ISWAP"})

_TWO_QUBIT_GATES: frozenset[str] = _CONTROLLED_GATES | _SYMMETRIC_TWO_QUBIT_GATES


# ---------------------------------------------------------------------------
# RQMGate – dual-mode gate (rotation mode + named gate mode)
# ---------------------------------------------------------------------------


class RQMGate:
    """A quantum gate in either axis-angle rotation or named-gate form.

    **Rotation mode** (backward-compatible)::

        gate = RQMGate("x", math.pi / 2)   # R_x(π/2)
        gate = RQMGate.ry(0.5)

    **Named gate mode** (for use with QiskitBackend / QiskitTranslator)::

        gate = RQMGate("H", target=0)
        gate = RQMGate("CNOT", control=0, target=1)

    The mode is determined by the presence of the ``angle`` positional
    argument: if ``angle`` is provided the gate is in rotation mode;
    otherwise it is in named gate mode.

    # NOTE:
    # Primary input type is rqm-compiler CompiledProgram.
    # RQMGate support is transitional and may be removed in a future release.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        name_or_axis: str,
        angle: "float | None" = None,
        *,
        target: "int | None" = None,
        control: "int | None" = None,
        params: "dict | None" = None,
    ) -> None:
        if angle is not None:
            # ----------------------------------------------------------------
            # Rotation mode: RQMGate("x", angle)
            # ----------------------------------------------------------------
            axis = name_or_axis.lower()
            if axis not in _VALID_AXES:
                raise ValueError(
                    f"Invalid axis {name_or_axis!r}. Must be one of {sorted(_VALID_AXES)}."
                )
            self._mode: str = "rotation"
            self._axis: "str | None" = axis
            self._angle: "float | None" = float(angle)
            self._gate_name: "str | None" = None
            self._target: "int | None" = None
            self._control: "int | None" = None
            self._params: dict = {}
        else:
            # ----------------------------------------------------------------
            # Named gate mode: RQMGate("H", target=0)
            # ----------------------------------------------------------------
            name_upper = name_or_axis.upper()
            if name_upper not in _NAMED_GATE_OPS:
                raise ValueError(
                    f"Unknown gate name {name_or_axis!r}. "
                    f"Supported gates: {sorted(_NAMED_GATE_OPS)}."
                )
            self._mode = "named"
            self._gate_name = name_upper
            self._axis = None
            self._angle = None
            self._target = target if target is not None else 0
            self._control = control
            self._params = dict(params) if params else {}

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
    # Properties (rotation mode only)
    # ------------------------------------------------------------------

    @property
    def axis(self) -> str:
        """Rotation axis (``"x"``, ``"y"``, or ``"z"``).

        Only available in rotation mode.
        """
        if self._mode != "rotation":
            raise AttributeError(
                "axis is only defined for rotation-mode RQMGate (created with an angle)"
            )
        return self._axis  # type: ignore[return-value]

    @property
    def angle(self) -> float:
        """Rotation angle in radians.

        Only available in rotation mode.
        """
        if self._mode != "rotation":
            raise AttributeError(
                "angle is only defined for rotation-mode RQMGate (created with an angle)"
            )
        return self._angle  # type: ignore[return-value]

    @property
    def gate_name(self) -> str:
        """Named gate identifier (e.g. ``"H"``, ``"CNOT"``).

        Only available in named gate mode.
        """
        if self._mode != "named":
            raise AttributeError(
                "gate_name is only defined for named-mode RQMGate (created without an angle)"
            )
        return self._gate_name  # type: ignore[return-value]

    @property
    def quaternion(self) -> "Quaternion":
        """The unit quaternion representing this gate.

        Only available in rotation mode.

        Returns
        -------
        :class:`~rqm_qiskit.Quaternion`
            A unit quaternion.
        """
        from rqm_qiskit.quaternion import Quaternion

        return Quaternion.from_axis_angle(self.axis, self._angle)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def to_matrix(self) -> np.ndarray:
        """Return the 2×2 complex unitary rotation matrix.

        Only available in rotation mode.
        Delegates to :func:`rqm_core.su2.axis_angle_to_su2`.
        """
        if self._mode != "rotation":
            raise AttributeError("to_matrix() is only available for rotation-mode RQMGate")
        return axis_angle_to_su2(self._axis, self._angle)  # type: ignore[arg-type]

    def to_operation(self, qubit: int = 0) -> "Operation":
        """Return the corresponding :class:`~rqm_compiler.ops.Operation`.

        In rotation mode, delegates gate ownership to rqm-compiler
        (``"x"`` → ``"rx"``, ``"y"`` → ``"ry"``, ``"z"`` → ``"rz"``).

        In named gate mode, maps the gate name to the canonical
        rqm-compiler operation name.

        Parameters
        ----------
        qubit:
            Target qubit index (default 0, used in rotation mode only).

        Returns
        -------
        :class:`rqm_compiler.ops.Operation`
        """
        from rqm_compiler import Operation

        if self._mode == "rotation":
            return Operation(
                gate=f"r{self._axis}",
                targets=[qubit],
                params={"angle": self._angle},
            )
        else:
            # Named gate mode
            op_name = _NAMED_GATE_OPS[self._gate_name]  # type: ignore[index]
            if self._gate_name in _SYMMETRIC_TWO_QUBIT_GATES:
                # SWAP, ISWAP: both qubits are targets (no control qubit)
                t1 = self._target if self._target is not None else 0
                t2 = self._control if self._control is not None else 1
                return Operation(
                    gate=op_name,
                    targets=[t1, t2],
                    controls=[],
                )
            elif self._gate_name in _CONTROLLED_GATES:
                return Operation(
                    gate=op_name,
                    targets=[self._target],
                    controls=[self._control] if self._control is not None else [],
                )
            else:
                extra: dict = {}
                if self._params.get("angle") is not None:
                    extra["angle"] = self._params["angle"]
                return Operation(
                    gate=op_name,
                    targets=[self._target],
                    params=extra,
                )

    def to_qiskit_gate(self) -> "Gate":
        """Return the corresponding Qiskit gate object.

        Only available in rotation mode.

        Returns
        -------
        qiskit.circuit.Gate
            One of :class:`~qiskit.circuit.library.RXGate`,
            :class:`~qiskit.circuit.library.RYGate`, or
            :class:`~qiskit.circuit.library.RZGate`.
        """
        if self._mode != "rotation":
            raise AttributeError("to_qiskit_gate() is only available for rotation-mode RQMGate")
        from qiskit.circuit.library import RXGate, RYGate, RZGate

        mapping = {"x": RXGate, "y": RYGate, "z": RZGate}
        return mapping[self._axis](self._angle)  # type: ignore[index]

    def pretty(self) -> str:
        """Return a human-readable description of the gate."""
        if self._mode == "rotation":
            return (
                f"RQMGate R{self._axis.upper()}(θ={self._angle:.4f} rad"  # type: ignore[union-attr]
                f" ≈ {math.degrees(self._angle):.2f}°)"  # type: ignore[arg-type]
            )
        else:
            extras = []
            if self._target is not None:
                extras.append(f"target={self._target}")
            if self._control is not None:
                extras.append(f"control={self._control}")
            return f"RQMGate({self._gate_name}, {', '.join(extras)})"

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        if self._mode == "rotation":
            return f"RQMGate(axis={self._axis!r}, angle={self._angle!r})"
        else:
            extras = []
            if self._target is not None:
                extras.append(f"target={self._target!r}")
            if self._control is not None:
                extras.append(f"control={self._control!r}")
            return f"RQMGate({self._gate_name!r}, {', '.join(extras)})"
