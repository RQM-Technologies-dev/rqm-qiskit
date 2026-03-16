"""
Tests for conversion helpers (src/rqm_qiskit/convert.py).
"""

import math

import numpy as np
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


# ---------------------------------------------------------------------------
# Single lowering path: gate_to_quantum_circuit routes through
# compiled_circuit_to_qiskit (no parallel mini-lowering path)
# ---------------------------------------------------------------------------


def test_gate_to_quantum_circuit_routes_through_compiled_circuit_to_qiskit():
    """gate_to_quantum_circuit must produce the same result as routing manually
    through compiled_circuit_to_qiskit — confirming it uses the single lowering path.
    """
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit

    for axis, angle in [("x", 1.2), ("y", 0.8), ("z", 2.1)]:
        gate = RQMGate(axis, angle)

        # Reference: manual route through compiled_circuit_to_qiskit
        c = Circuit(1)
        c.add(gate.to_operation(qubit=0))
        qc_ref = compiled_circuit_to_qiskit(c)

        # Under test: convenience wrapper
        qc = gate_to_quantum_circuit(gate)

        # Both paths must yield circuits with identical gate names and angles.
        assert qc.num_qubits == qc_ref.num_qubits
        assert len(qc.data) == len(qc_ref.data)
        for instr, instr_ref in zip(qc.data, qc_ref.data):
            assert instr.operation.name == instr_ref.operation.name, (
                f"gate name mismatch for axis={axis}: "
                f"{instr.operation.name!r} != {instr_ref.operation.name!r}"
            )
            assert np.allclose(
                instr.operation.params, instr_ref.operation.params, atol=1e-14
            ), (
                f"gate params mismatch for axis={axis}: "
                f"{instr.operation.params} != {instr_ref.operation.params}"
            )
