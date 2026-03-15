"""
Tests for conversion helpers (src/rqm_qiskit/convert.py).
"""

from qiskit import QuantumCircuit

from rqm_qiskit import RQMState, RQMGate
from rqm_qiskit import state_to_quantum_circuit, gate_to_quantum_circuit


def test_state_to_quantum_circuit_type():
    qc = state_to_quantum_circuit(RQMState.plus())
    assert isinstance(qc, QuantumCircuit)


def test_state_to_quantum_circuit_one_qubit():
    qc = state_to_quantum_circuit(RQMState.zero())
    assert qc.num_qubits == 1


def test_state_to_quantum_circuit_has_operations():
    qc = state_to_quantum_circuit(RQMState.minus())
    assert len(qc.data) > 0


def test_gate_to_quantum_circuit_type():
    qc = gate_to_quantum_circuit(RQMGate.ry(1.0))
    assert isinstance(qc, QuantumCircuit)


def test_gate_to_quantum_circuit_one_qubit():
    qc = gate_to_quantum_circuit(RQMGate.rx(0.5))
    assert qc.num_qubits == 1


def test_gate_to_quantum_circuit_has_operations():
    qc = gate_to_quantum_circuit(RQMGate.rz(0.5))
    assert len(qc.data) > 0


def test_all_axes_convert():
    for axis in ("x", "y", "z"):
        qc = gate_to_quantum_circuit(RQMGate(axis, 1.0))
        assert qc.num_qubits == 1
