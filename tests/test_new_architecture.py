"""
Tests for the new architecture components added in the refactoring:

- QiskitBackend (compiler-first unified entry point)
- QiskitTranslator (IR → QuantumCircuit)
- compile_to_qiskit_circuit (convenience function)
- run_local / run_backend (execution functions)
- QiskitResult (structured result wrapper)
- spinor_to_circuit / bloch_to_circuit (bridge functions)
- Quaternion re-export identity
"""

import math
import pytest
import numpy as np
from qiskit import QuantumCircuit


# ---------------------------------------------------------------------------
# Quaternion re-export identity
# ---------------------------------------------------------------------------


def test_quaternion_is_rqm_core_subclass():
    """Quaternion from rqm_qiskit must be a subclass of rqm_core.Quaternion."""
    from rqm_qiskit import Quaternion
    import rqm_core

    assert issubclass(Quaternion, rqm_core.Quaternion)


# ---------------------------------------------------------------------------
# rqm-core bridge: spinor tests
# ---------------------------------------------------------------------------


def test_spinor_to_circuit_zero_state():
    """|0⟩ spinor should produce a circuit (no assertion on gates, just type)."""
    from rqm_qiskit import spinor_to_circuit

    qc = spinor_to_circuit(1.0 + 0j, 0.0 + 0j)
    assert isinstance(qc, QuantumCircuit)
    assert qc.num_qubits == 1


def test_spinor_to_circuit_one_state():
    """|1⟩ spinor should produce a circuit."""
    from rqm_qiskit import spinor_to_circuit

    qc = spinor_to_circuit(0.0 + 0j, 1.0 + 0j)
    assert isinstance(qc, QuantumCircuit)


def test_spinor_to_circuit_plus_state():
    """|+⟩ spinor produces a circuit with RY(π/2) ≈ rotation."""
    from rqm_qiskit import spinor_to_circuit

    s = 1.0 / math.sqrt(2)
    qc = spinor_to_circuit(s + 0j, s + 0j)
    assert isinstance(qc, QuantumCircuit)
    assert len(qc.data) > 0


def test_spinor_to_circuit_normalization():
    """Unnormalized and normalized spinors should produce the same circuit."""
    from rqm_qiskit import spinor_to_circuit

    qc1 = spinor_to_circuit(3.0 + 0j, 4.0 + 0j)  # norm=5, unnormalized
    qc2 = spinor_to_circuit(0.6 + 0j, 0.8 + 0j)  # normalized

    # Both circuits should have the same gate parameters
    assert len(qc1.data) == len(qc2.data)
    for inst1, inst2 in zip(qc1.data, qc2.data):
        assert inst1.operation.name == inst2.operation.name
        assert np.allclose(inst1.operation.params, inst2.operation.params, atol=1e-10)


def test_spinor_to_circuit_complex_amplitude():
    """Complex spinor amplitudes should work."""
    from rqm_qiskit import spinor_to_circuit

    qc = spinor_to_circuit(0.5 + 0.5j, 0.5 - 0.5j)
    assert isinstance(qc, QuantumCircuit)


def test_spinor_to_circuit_invalid_zero():
    """Zero spinor should raise ValueError."""
    from rqm_qiskit import spinor_to_circuit

    with pytest.raises(ValueError):
        spinor_to_circuit(0.0 + 0j, 0.0 + 0j)


def test_spinor_to_circuit_target_qubit():
    """target parameter should control which qubit is targeted."""
    from rqm_qiskit import spinor_to_circuit

    qc = spinor_to_circuit(1.0 + 0j, 0.0 + 0j, target=2)
    assert qc.num_qubits == 3  # qubits 0, 1, 2


# ---------------------------------------------------------------------------
# rqm-core bridge: bloch tests
# ---------------------------------------------------------------------------


def test_bloch_to_circuit_north_pole():
    """θ=0, φ=0 should produce RY(0) RZ(0) gates."""
    from rqm_qiskit import bloch_to_circuit

    qc = bloch_to_circuit(0.0, 0.0)
    assert isinstance(qc, QuantumCircuit)
    assert len(qc.data) == 2  # RY and RZ


def test_bloch_to_circuit_south_pole():
    """θ=π should produce a Bloch-south circuit."""
    from rqm_qiskit import bloch_to_circuit

    qc = bloch_to_circuit(math.pi, 0.0)
    assert isinstance(qc, QuantumCircuit)
    # RY(π) should prepare |1⟩
    ry_instr = qc.data[0]
    assert ry_instr.operation.name == "ry"
    assert math.isclose(ry_instr.operation.params[0], math.pi, abs_tol=1e-10)


def test_bloch_to_circuit_equator_x():
    """θ=π/2, φ=0 should produce the equatorial (|+⟩) state."""
    from rqm_qiskit import bloch_to_circuit

    qc = bloch_to_circuit(math.pi / 2, 0.0)
    ry_instr = qc.data[0]
    assert math.isclose(ry_instr.operation.params[0], math.pi / 2, abs_tol=1e-10)


def test_bloch_to_circuit_equator_y():
    """θ=π/2, φ=π/2 should produce a circuit with non-zero RZ."""
    from rqm_qiskit import bloch_to_circuit

    qc = bloch_to_circuit(math.pi / 2, math.pi / 2)
    rz_instr = qc.data[1]
    assert math.isclose(rz_instr.operation.params[0], math.pi / 2, abs_tol=1e-10)


def test_bloch_to_circuit_target_qubit():
    """target parameter should control which qubit is targeted."""
    from rqm_qiskit import bloch_to_circuit

    qc = bloch_to_circuit(0.0, 0.0, target=1)
    assert qc.num_qubits == 2


# ---------------------------------------------------------------------------
# Quaternion bridge (not implemented)
# ---------------------------------------------------------------------------


def test_quaternion_to_circuit_raises():
    """quaternion_to_circuit must raise NotImplementedError."""
    from rqm_qiskit.bridges import quaternion_to_circuit

    with pytest.raises(NotImplementedError):
        quaternion_to_circuit()


# ---------------------------------------------------------------------------
# QiskitTranslator tests
# ---------------------------------------------------------------------------


def test_translator_accepts_compiler_circuit():
    """QiskitTranslator must accept an rqm_compiler.Circuit."""
    from rqm_compiler import Circuit
    from rqm_qiskit import QiskitTranslator

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    qc = QiskitTranslator().compile_to_circuit(c)
    assert isinstance(qc, QuantumCircuit)
    assert qc.num_qubits == 1


def test_translator_accepts_compiled_circuit():
    """QiskitTranslator must accept an rqm_compiler.CompiledCircuit."""
    from rqm_compiler import Circuit, compile_circuit
    from rqm_qiskit import QiskitTranslator

    c = Circuit(1)
    c.ry(0, math.pi / 2)
    compiled = compile_circuit(c)
    qc = QiskitTranslator().compile_to_circuit(compiled)
    assert isinstance(qc, QuantumCircuit)


def test_translator_accepts_qiskit_circuit():
    """QiskitTranslator must pass through a QuantumCircuit unchanged."""
    from rqm_qiskit import QiskitTranslator

    qc_in = QuantumCircuit(1)
    qc_in.h(0)
    qc_out = QiskitTranslator().compile_to_circuit(qc_in)
    assert qc_out is qc_in


def test_translator_accepts_rqmgate_sequence():
    """QiskitTranslator must accept a list of RQMGate objects (named gate mode)."""
    from rqm_qiskit import QiskitTranslator, RQMGate

    gates = [RQMGate("H", target=0), RQMGate("X", target=0)]
    qc = QiskitTranslator().compile_to_circuit(gates)
    assert isinstance(qc, QuantumCircuit)


def test_translator_rejects_unsupported_type():
    """QiskitTranslator must raise TypeError for unsupported program types."""
    from rqm_qiskit import QiskitTranslator

    with pytest.raises(TypeError):
        QiskitTranslator().compile_to_circuit(42)


def test_compile_to_qiskit_circuit_function():
    """compile_to_qiskit_circuit convenience function must work."""
    from rqm_compiler import Circuit
    from rqm_qiskit import compile_to_qiskit_circuit

    c = Circuit(1)
    c.h(0)
    qc = compile_to_qiskit_circuit(c)
    assert isinstance(qc, QuantumCircuit)


def test_translator_multi_qubit():
    """Translator must handle 2-qubit circuits."""
    from rqm_compiler import Circuit
    from rqm_qiskit import QiskitTranslator

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0)
    c.measure(1)
    qc = QiskitTranslator().compile_to_circuit(c)
    assert qc.num_qubits == 2
    assert qc.num_clbits >= 2


# ---------------------------------------------------------------------------
# All gate mappings via translator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("gate_name", ["I", "X", "Y", "Z", "H", "S", "T"])
def test_translator_single_qubit_named_gates(gate_name):
    """Translator must handle all single-qubit named gates."""
    from rqm_qiskit import RQMGate, QiskitTranslator

    gates = [RQMGate(gate_name, target=0)]
    qc = QiskitTranslator().compile_to_circuit(gates)
    assert isinstance(qc, QuantumCircuit)


@pytest.mark.parametrize("gate_name,control,target", [
    ("CX", 0, 1), ("CY", 0, 1), ("CZ", 0, 1),
    ("CNOT", 0, 1), ("SWAP", 0, 1),
])
def test_translator_two_qubit_named_gates(gate_name, control, target):
    """Translator must handle all 2-qubit named gates."""
    from rqm_qiskit import RQMGate, QiskitTranslator

    gates = [RQMGate(gate_name, control=control, target=target)]
    qc = QiskitTranslator().compile_to_circuit(gates)
    assert isinstance(qc, QuantumCircuit)
    assert qc.num_qubits >= 2


# ---------------------------------------------------------------------------
# QiskitBackend tests
# ---------------------------------------------------------------------------


def test_backend_compile_to_circuit():
    """QiskitBackend.compile_to_circuit must return a QuantumCircuit."""
    from rqm_compiler import Circuit
    from rqm_qiskit import QiskitBackend

    c = Circuit(1)
    c.h(0)
    backend = QiskitBackend()
    qc = backend.compile_to_circuit(c)
    assert isinstance(qc, QuantumCircuit)


def test_backend_run_local_returns_result():
    """QiskitBackend.run_local must return a QiskitResult."""
    from rqm_compiler import Circuit
    from rqm_qiskit import QiskitBackend, QiskitResult

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    backend = QiskitBackend()
    result = backend.run_local(c, shots=100)
    assert isinstance(result, QiskitResult)


def test_backend_run_local_has_counts():
    """QiskitBackend.run_local result must have counts."""
    from rqm_compiler import Circuit
    from rqm_qiskit import QiskitBackend

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    result = QiskitBackend().run_local(c, shots=200)
    assert len(result.counts) > 0
    assert result.shots == 200


def test_backend_repr():
    from rqm_qiskit import QiskitBackend
    assert repr(QiskitBackend()) == "QiskitBackend()"


# ---------------------------------------------------------------------------
# Critical identity test (Bell state)
# ---------------------------------------------------------------------------


def test_compile_run_identity():
    """Compiler-first pipeline: compile + run must produce a Bell state."""
    from rqm_qiskit import RQMGate, QiskitBackend

    program = [
        RQMGate("H", target=0),
        RQMGate("CNOT", control=0, target=1),
    ]
    backend = QiskitBackend()
    result = backend.run_local(program, shots=200)
    assert "00" in result.counts
    assert "11" in result.counts


def test_compile_run_identity_via_compiler():
    """Compiler-first pipeline using rqm_compiler.Circuit directly."""
    from rqm_compiler import Circuit
    from rqm_qiskit import QiskitBackend

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0)
    c.measure(1)
    backend = QiskitBackend()
    result = backend.run_local(c, shots=200)
    assert "00" in result.counts
    assert "11" in result.counts


# ---------------------------------------------------------------------------
# QiskitResult tests
# ---------------------------------------------------------------------------


def test_qiskit_result_counts():
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"00": 512, "11": 512})
    assert result.counts == {"00": 512, "11": 512}


def test_qiskit_result_shots():
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"00": 512, "11": 512})
    assert result.shots == 1024


def test_qiskit_result_probabilities():
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"00": 600, "11": 400})
    assert abs(result.probabilities["00"] - 0.6) < 1e-10
    assert abs(result.probabilities["11"] - 0.4) < 1e-10


def test_qiskit_result_most_likely():
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"00": 600, "11": 400})
    assert result.most_likely_bitstring() == "00"


def test_qiskit_result_empty_raises():
    from rqm_qiskit import QiskitResult

    with pytest.raises(ValueError):
        QiskitResult({})


def test_qiskit_result_repr():
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"00": 512, "11": 512})
    r = repr(result)
    assert "QiskitResult" in r
    assert "1024" in r


# ---------------------------------------------------------------------------
# run_local / run_backend convenience functions
# ---------------------------------------------------------------------------


def test_run_local_with_compiler_circuit():
    """run_local should work with a rqm_compiler.Circuit."""
    from rqm_compiler import Circuit
    from rqm_qiskit import run_local

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    counts = run_local(c, shots=100)
    assert isinstance(counts, dict)
    assert len(counts) > 0


def test_run_local_with_qiskit_circuit():
    """run_local should work with a QuantumCircuit."""
    from rqm_qiskit import run_local

    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    counts = run_local(qc, shots=100)
    assert isinstance(counts, dict)


def test_run_local_with_gate_list():
    """run_local should work with a list of RQMGate objects."""
    from rqm_qiskit import run_local, RQMGate

    gates = [RQMGate("H", target=0)]
    counts = run_local(gates, shots=100)
    assert isinstance(counts, dict)


def test_run_backend_string_raises():
    """run_backend with a string backend must raise NotImplementedError."""
    from rqm_qiskit import run_backend, RQMGate

    gates = [RQMGate("H", target=0)]
    with pytest.raises(NotImplementedError):
        run_backend(gates, "ibm_nairobi", shots=100)
