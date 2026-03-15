"""
convert.py – Helpers to convert RQM objects to Qiskit QuantumCircuits.

These functions are convenience wrappers for quick one-liner conversions
without creating an RQMCircuit manually.
"""

from __future__ import annotations

from qiskit import QuantumCircuit

from rqm_qiskit.state import RQMState
from rqm_qiskit.gates import RQMGate


def state_to_quantum_circuit(state: RQMState) -> QuantumCircuit:
    """Convert an :class:`~rqm_qiskit.RQMState` to a 1-qubit QuantumCircuit.

    The returned circuit uses Qiskit's ``initialize`` instruction to
    prepare the qubit in the given state.

    Parameters
    ----------
    state:
        The 1-qubit state to encode.

    Returns
    -------
    qiskit.QuantumCircuit
        A 1-qubit circuit that initializes the qubit to ``state``.

    Examples
    --------
    >>> from rqm_qiskit import RQMState, state_to_quantum_circuit
    >>> qc = state_to_quantum_circuit(RQMState.plus())
    >>> print(qc.draw(output="text"))
    """
    alpha, beta = state.vector()
    qc = QuantumCircuit(1)
    qc.initialize([alpha, beta], 0)
    return qc


def gate_to_quantum_circuit(gate: RQMGate) -> QuantumCircuit:
    """Convert an :class:`~rqm_qiskit.RQMGate` to a 1-qubit QuantumCircuit.

    The returned circuit applies the rotation gate to qubit 0.

    Parameters
    ----------
    gate:
        The rotation gate to apply.

    Returns
    -------
    qiskit.QuantumCircuit
        A 1-qubit circuit applying ``gate`` to qubit 0.

    Examples
    --------
    >>> from rqm_qiskit import RQMGate, gate_to_quantum_circuit
    >>> qc = gate_to_quantum_circuit(RQMGate.rx(1.57))
    >>> print(qc.draw(output="text"))
    """
    qc = QuantumCircuit(1)
    qc.append(gate.to_qiskit_gate(), [0])
    return qc
