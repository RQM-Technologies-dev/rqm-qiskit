"""
circuit.py – RQMCircuit: a thin wrapper around Qiskit QuantumCircuit.

RQMCircuit is intentionally kept small.  It exposes only the operations
needed for 1-qubit SU(2) demos: state preparation, gate application,
measurement, and text drawing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qiskit import QuantumCircuit

from rqm_qiskit.state import RQMState
from rqm_qiskit.gates import RQMGate

if TYPE_CHECKING:
    pass


class RQMCircuit:
    """A lightweight wrapper around :class:`qiskit.QuantumCircuit`.

    Provides a higher-level interface for building 1-qubit circuits
    using :class:`~rqm_qiskit.RQMState` and :class:`~rqm_qiskit.RQMGate`
    objects.

    Parameters
    ----------
    num_qubits:
        Number of qubits in the circuit (≥ 1).

    Examples
    --------
    >>> circ = RQMCircuit(1)
    >>> circ.prepare_state(RQMState.plus())
    >>> circ.apply_gate(RQMGate.ry(0.5))
    >>> circ.measure_all()
    >>> print(circ.draw_text())
    """

    def __init__(self, num_qubits: int) -> None:
        if num_qubits < 1:
            raise ValueError("num_qubits must be at least 1.")
        self._num_qubits = num_qubits
        # A matching classical register is created lazily when measure_all() is called.
        self._qc: QuantumCircuit = QuantumCircuit(num_qubits)

    # ------------------------------------------------------------------
    # Circuit-building methods
    # ------------------------------------------------------------------

    def prepare_state(self, state: RQMState, qubit: int = 0) -> None:
        """Initialize a qubit to the given RQMState.

        This uses Qiskit's ``initialize`` instruction, which prepares the
        qubit in the exact statevector ``[alpha, beta]``.

        Parameters
        ----------
        state:
            The 1-qubit state to prepare.
        qubit:
            Target qubit index (default 0).
        """
        self._check_qubit(qubit)
        alpha, beta = state.vector()
        self._qc.initialize([alpha, beta], qubit)

    def apply_gate(self, gate: RQMGate, qubit: int = 0) -> None:
        """Apply an RQMGate to a qubit.

        Parameters
        ----------
        gate:
            The rotation gate to apply.
        qubit:
            Target qubit index (default 0).
        """
        self._check_qubit(qubit)
        self._qc.append(gate.to_qiskit_gate(), [qubit])

    def measure_all(self) -> None:
        """Add measurement gates to all qubits.

        If the circuit does not yet have classical bits, they are added
        automatically.  Calling this method multiple times is safe – it
        will not add duplicate measurements.
        """
        if self._qc.num_clbits == 0:
            self._qc.add_register(*[])  # no-op; measurement adds bits below
            self._qc.measure_all()
        # If measurements already exist, do nothing.

    def to_qiskit(self) -> QuantumCircuit:
        """Return the underlying :class:`~qiskit.QuantumCircuit`."""
        return self._qc

    def draw_text(self) -> str:
        """Return a text-mode circuit diagram as a string."""
        return str(self._qc.draw(output="text"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_qubit(self, qubit: int) -> None:
        if not (0 <= qubit < self._num_qubits):
            raise ValueError(
                f"Qubit index {qubit} is out of range for a "
                f"{self._num_qubits}-qubit circuit."
            )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"RQMCircuit(num_qubits={self._num_qubits})"
