"""
Tests for RQMCircuit (src/rqm_qiskit/circuit.py).
"""

import math
import pytest

from qiskit import QuantumCircuit

from rqm_qiskit import RQMState, RQMGate, RQMCircuit


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_create_single_qubit_circuit():
    circ = RQMCircuit(1)
    assert repr(circ) == "RQMCircuit(num_qubits=1)"


def test_create_multi_qubit_circuit():
    circ = RQMCircuit(3)
    qc = circ.to_qiskit()
    assert qc.num_qubits == 3


def test_zero_qubits_raises():
    with pytest.raises(ValueError):
        RQMCircuit(0)


# ---------------------------------------------------------------------------
# prepare_state
# ---------------------------------------------------------------------------


def test_prepare_state_default_qubit():
    circ = RQMCircuit(1)
    circ.prepare_state(RQMState.plus())
    qc = circ.to_qiskit()
    assert qc.num_qubits == 1


def test_prepare_state_out_of_range_raises():
    circ = RQMCircuit(1)
    with pytest.raises(ValueError, match="out of range"):
        circ.prepare_state(RQMState.zero(), qubit=2)


# ---------------------------------------------------------------------------
# apply_gate
# ---------------------------------------------------------------------------


def test_apply_gate_default_qubit():
    circ = RQMCircuit(1)
    circ.prepare_state(RQMState.zero())
    circ.apply_gate(RQMGate.ry(math.pi / 2))
    qc = circ.to_qiskit()
    # Circuit should have operations
    assert len(qc.data) > 0


def test_apply_gate_out_of_range_raises():
    circ = RQMCircuit(1)
    with pytest.raises(ValueError, match="out of range"):
        circ.apply_gate(RQMGate.rx(1.0), qubit=5)


# ---------------------------------------------------------------------------
# measure_all
# ---------------------------------------------------------------------------


def test_measure_all_adds_classical_bits():
    circ = RQMCircuit(1)
    circ.prepare_state(RQMState.zero())
    circ.measure_all()
    qc = circ.to_qiskit()
    assert qc.num_clbits >= 1


def test_measure_all_idempotent():
    """Calling measure_all twice should not raise."""
    circ = RQMCircuit(1)
    circ.measure_all()
    circ.measure_all()  # second call should be a no-op


# ---------------------------------------------------------------------------
# to_qiskit
# ---------------------------------------------------------------------------


def test_to_qiskit_returns_quantum_circuit():
    circ = RQMCircuit(1)
    qc = circ.to_qiskit()
    assert isinstance(qc, QuantumCircuit)


# ---------------------------------------------------------------------------
# draw_text
# ---------------------------------------------------------------------------


def test_draw_text_returns_string():
    circ = RQMCircuit(1)
    circ.prepare_state(RQMState.plus())
    circ.apply_gate(RQMGate.ry(0.5))
    circ.measure_all()
    text = circ.draw_text()
    assert isinstance(text, str)
    assert len(text) > 0
