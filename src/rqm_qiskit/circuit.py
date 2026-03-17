"""
circuit.py – RQMCircuit: a thin Qiskit-bridge façade over rqm-compiler.Circuit.

RQMCircuit delegates canonical circuit ownership to
:class:`rqm_compiler.Circuit` (the backend-neutral IR layer) and converts
to a Qiskit :class:`~qiskit.QuantumCircuit` on demand.  It is intentionally
kept small: only operations needed for 1-qubit SU(2) demos are exposed
(state preparation, gate application, measurement, and text drawing).

Architecture note
-----------------
- Gate operations are stored in the rqm-compiler canonical circuit.
- State preparation (``initialize``) is Qiskit-specific and is stored
  separately; it is prepended when building the final QuantumCircuit.
- The Qiskit circuit is built fresh on each call to :meth:`to_qiskit`,
  keeping rqm-compiler as the single source of truth for gate structure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qiskit import QuantumCircuit
from rqm_compiler import Circuit as CompilerCircuit

from rqm_qiskit.state import RQMState
from rqm_qiskit.gates import RQMGate

if TYPE_CHECKING:
    pass


class RQMCircuit:
    """A lightweight Qiskit-bridge façade over :class:`rqm_compiler.Circuit`.

    Stores the gate sequence in an rqm-compiler canonical circuit and
    converts to a :class:`~qiskit.QuantumCircuit` on demand.  State
    preparation (Qiskit's ``initialize``) is handled separately since it is
    not part of the rqm-compiler IR.

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
        # Canonical gate/circuit ownership delegated to rqm-compiler.
        self._compiler_circuit: CompilerCircuit = CompilerCircuit(num_qubits)
        # State preps are Qiskit-specific (initialize instruction) and are
        # stored here until to_qiskit() is called.
        self._state_preps: dict[int, RQMState] = {}
        # Track whether measure_all() has been called (for idempotency).
        self._measured: bool = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def compiler_circuit(self) -> CompilerCircuit:
        """The underlying :class:`rqm_compiler.Circuit` (canonical IR).

        Expose the compiler circuit for callers that need to work with
        the backend-neutral IR directly (e.g., for further compilation or
        inspection).
        """
        return self._compiler_circuit

    # ------------------------------------------------------------------
    # Circuit-building methods
    # ------------------------------------------------------------------

    def prepare_state(self, state: RQMState, qubit: int = 0) -> None:
        """Initialize a qubit to the given RQMState.

        State preparation uses Qiskit's ``initialize`` instruction, which
        is not part of the rqm-compiler IR.  The state is stored and
        prepended when :meth:`to_qiskit` builds the final circuit.

        Parameters
        ----------
        state:
            The 1-qubit state to prepare.
        qubit:
            Target qubit index (default 0).
        """
        self._check_qubit(qubit)
        self._state_preps[qubit] = state

    def apply_gate(self, gate: RQMGate, qubit: int = 0) -> None:
        """Apply an RQMGate to a qubit.

        Delegates to the rqm-compiler circuit via
        :meth:`~rqm_qiskit.RQMGate.to_operation`.

        Parameters
        ----------
        gate:
            The rotation gate to apply.
        qubit:
            Target qubit index (default 0).
        """
        self._check_qubit(qubit)
        self._compiler_circuit.add(gate.to_operation(qubit))

    def measure_all(self) -> None:
        """Add measurement gates to all qubits (idempotent).

        Measurement operations are stored in the rqm-compiler circuit.
        Calling this method multiple times is safe — subsequent calls are
        no-ops.
        """
        if not self._measured:
            for q in range(self._num_qubits):
                self._compiler_circuit.measure(q, key=f"m{q}")
            self._measured = True

    def to_qiskit(self) -> QuantumCircuit:
        """Build and return a Qiskit :class:`~qiskit.QuantumCircuit`.

        The circuit is constructed fresh on each call:

        1. The rqm-compiler circuit is lowered to Qiskit via
           :func:`~rqm_qiskit.convert.compiled_circuit_to_qiskit`.
        2. If state preparations were registered, they are prepended
           (Qiskit ``initialize`` instructions).
        """
        from rqm_qiskit.convert import compiled_circuit_to_qiskit

        qc = compiled_circuit_to_qiskit(self._compiler_circuit)

        if not self._state_preps:
            return qc

        # Prepend state initializations.  Both circuits share the same
        # register objects so qubit/clbit references remain valid.
        init_qc = QuantumCircuit(*qc.qregs, *qc.cregs)
        for qubit_idx, state in sorted(self._state_preps.items()):
            alpha, beta = state.vector()
            init_qc.initialize([alpha, beta], qubit_idx)
        for instr in qc.data:
            init_qc.append(instr.operation, instr.qubits, instr.clbits)
        return init_qc

    def draw_text(self) -> str:
        """Return a text-mode circuit diagram as a string."""
        return str(self.to_qiskit().draw(output="text"))

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
