"""
Tests for translation correctness, u1q gate support, optimize toggle,
execution, and roundtrip consistency.

These tests cover the augmented API introduced for rqm-API readiness:
- to_backend_circuit (primary translation API with optimize support)
- u1q gate: quaternion → Qiskit UnitaryGate
- QiskitResult.to_dict() standardized API format
- QiskitBackend.compile() / QiskitBackend.run()
"""

import math
import pytest
import numpy as np
from qiskit import QuantumCircuit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bell_circuit():
    """Return a 2-qubit Bell circuit as an rqm_compiler.Circuit."""
    from rqm_compiler import Circuit

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0)
    c.measure(1)
    return c


# ---------------------------------------------------------------------------
# to_backend_circuit – translation correctness
# ---------------------------------------------------------------------------


def test_to_backend_circuit_returns_quantum_circuit():
    """to_backend_circuit must return a QuantumCircuit."""
    from rqm_qiskit import to_backend_circuit

    qc = to_backend_circuit(_bell_circuit())
    assert isinstance(qc, QuantumCircuit)


def test_to_backend_circuit_correct_num_qubits():
    """to_backend_circuit must produce a circuit with the right qubit count."""
    from rqm_qiskit import to_backend_circuit
    from rqm_compiler import Circuit

    c = Circuit(3)
    c.h(0)
    c.h(1)
    c.h(2)
    qc = to_backend_circuit(c)
    assert qc.num_qubits == 3


def test_to_backend_circuit_optimize_false_runs():
    """to_backend_circuit(optimize=False) must succeed and return a QuantumCircuit."""
    from rqm_qiskit import to_backend_circuit

    qc = to_backend_circuit(_bell_circuit(), optimize=False)
    assert isinstance(qc, QuantumCircuit)


def test_to_backend_circuit_optimize_true_raises_when_unavailable():
    """to_backend_circuit(optimize=True) must raise ImportError if no optimizer installed."""
    from rqm_qiskit import to_backend_circuit

    # rqm-optimize is not installed in the test environment
    try:
        import rqm_optimize  # noqa: F401
        # If it IS installed, just check we get a QuantumCircuit
        qc = to_backend_circuit(_bell_circuit(), optimize=True)
        assert isinstance(qc, QuantumCircuit)
    except (ImportError, ModuleNotFoundError):
        with pytest.raises(ImportError, match="optimize"):
            to_backend_circuit(_bell_circuit(), optimize=True)


# ---------------------------------------------------------------------------
# u1q gate support
# ---------------------------------------------------------------------------


def test_u1q_identity_quaternion_produces_identity_unitary():
    """u1q with identity quaternion (w=1,x=y=z=0) must produce a near-identity unitary."""
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit.quantum_info import Operator

    c = Circuit(1)
    c.u1q(0, w=1.0, x=0.0, y=0.0, z=0.0)
    qc = compiled_circuit_to_qiskit(c)
    op = Operator(qc).data
    assert np.allclose(op, np.eye(2), atol=1e-6), (
        f"u1q identity should produce identity matrix, got:\n{op}"
    )


def test_u1q_rx_pi_over_2_matches_rx_gate():
    """u1q with Rx(π/2) quaternion must match Qiskit's RX(π/2) gate."""
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit.quantum_info import Operator

    # Rx(π/2) quaternion: w=cos(π/4), x=sin(π/4), y=0, z=0
    angle = math.pi / 2
    w = math.cos(angle / 2)
    x = math.sin(angle / 2)

    c_u1q = Circuit(1)
    c_u1q.u1q(0, w=w, x=x, y=0.0, z=0.0)
    qc_u1q = compiled_circuit_to_qiskit(c_u1q)

    c_rx = Circuit(1)
    c_rx.rx(0, angle)
    qc_rx = compiled_circuit_to_qiskit(c_rx)

    u1q_mat = Operator(qc_u1q).data
    rx_mat = Operator(qc_rx).data

    # Allow global phase difference
    assert np.allclose(u1q_mat, rx_mat, atol=1e-6) or np.allclose(
        u1q_mat, -rx_mat, atol=1e-6
    ), f"u1q Rx(π/2) mismatch.\nu1q={u1q_mat}\nrx={rx_mat}"


def test_u1q_h_gate_matches_h():
    """u1q with Hadamard quaternion must match Qiskit's H gate up to global phase."""
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit.quantum_info import Operator

    # H = (X + Z) / sqrt(2); quaternion form: w=0, x=1/sqrt(2), y=0, z=1/sqrt(2) normalized
    s2 = 1.0 / math.sqrt(2)
    c_u1q = Circuit(1)
    c_u1q.u1q(0, w=0.0, x=s2, y=0.0, z=s2)
    qc_u1q = compiled_circuit_to_qiskit(c_u1q)

    c_h = Circuit(1)
    c_h.h(0)
    qc_h = compiled_circuit_to_qiskit(c_h)

    u1q_mat = Operator(qc_u1q).data
    h_mat = Operator(qc_h).data

    # Allow global phase
    ratio = u1q_mat / h_mat
    assert np.allclose(ratio, ratio[0, 0] * np.ones((2, 2)), atol=1e-6), (
        f"u1q H-quaternion mismatch.\nu1q={u1q_mat}\nh={h_mat}"
    )


def test_u1q_circuit_executes():
    """u1q gate in a circuit must execute successfully on the local simulator."""
    from rqm_compiler import Circuit
    from rqm_qiskit.backend import QiskitBackend

    # X gate via quaternion: w=0, x=1, y=0, z=0
    c = Circuit(1)
    c.u1q(0, w=0.0, x=1.0, y=0.0, z=0.0)
    c.measure(0)

    backend = QiskitBackend()
    result = backend.run_local(c, shots=128)
    assert result.counts


# ---------------------------------------------------------------------------
# QiskitResult.to_dict – standardized API format
# ---------------------------------------------------------------------------


def test_qiskit_result_to_dict_has_required_keys():
    """QiskitResult.to_dict() must return all required API keys."""
    from rqm_qiskit.result import QiskitResult

    result = QiskitResult({"00": 512, "11": 512}, shots=1024)
    d = result.to_dict()

    assert "counts" in d
    assert "shots" in d
    assert "backend" in d
    assert "metadata" in d
    assert "most_likely" in d["metadata"]


def test_qiskit_result_to_dict_values():
    """QiskitResult.to_dict() must return correct values."""
    from rqm_qiskit.result import QiskitResult

    counts = {"00": 512, "11": 512}
    result = QiskitResult(counts, shots=1024)
    d = result.to_dict(backend="qiskit")

    assert d["counts"] == counts
    assert d["shots"] == 1024
    assert d["backend"] == "qiskit"
    assert isinstance(d["metadata"], dict)


def test_qiskit_result_to_dict_is_json_serializable():
    """QiskitResult.to_dict() output must be JSON-serializable."""
    import json
    from rqm_qiskit.result import QiskitResult

    result = QiskitResult({"0": 60, "1": 40}, shots=100)
    d = result.to_dict()
    # This must not raise
    serialized = json.dumps(d)
    assert isinstance(serialized, str)


def test_qiskit_result_to_dict_custom_backend_name():
    """QiskitResult.to_dict(backend=...) must use the provided backend name."""
    from rqm_qiskit.result import QiskitResult

    result = QiskitResult({"0": 100}, shots=100)
    d = result.to_dict(backend="aer_simulator")
    assert d["backend"] == "aer_simulator"


# ---------------------------------------------------------------------------
# QiskitBackend.compile() and QiskitBackend.run()
# ---------------------------------------------------------------------------


def test_backend_compile_returns_quantum_circuit():
    """QiskitBackend.compile() must return a QuantumCircuit."""
    from rqm_qiskit.backend import QiskitBackend

    backend = QiskitBackend()
    qc = backend.compile(_bell_circuit())
    assert isinstance(qc, QuantumCircuit)


def test_backend_compile_with_optimize_false():
    """QiskitBackend.compile(optimize=False) must succeed."""
    from rqm_qiskit.backend import QiskitBackend

    backend = QiskitBackend()
    qc = backend.compile(_bell_circuit(), optimize=False)
    assert isinstance(qc, QuantumCircuit)


def test_backend_run_returns_qiskit_result():
    """QiskitBackend.run() must return a QiskitResult."""
    from rqm_qiskit.backend import QiskitBackend
    from rqm_qiskit.result import QiskitResult

    backend = QiskitBackend()
    result = backend.run(_bell_circuit(), shots=64)
    assert isinstance(result, QiskitResult)
    assert result.shots == 64


def test_backend_run_shots_default():
    """QiskitBackend.run() default shots must be 1024."""
    from rqm_qiskit.backend import QiskitBackend
    from rqm_compiler import Circuit

    c = Circuit(1)
    c.measure(0)
    backend = QiskitBackend()
    result = backend.run(c)
    assert result.shots == 1024


def test_backend_run_result_has_counts():
    """QiskitBackend.run() result must have non-empty counts."""
    from rqm_qiskit.backend import QiskitBackend

    backend = QiskitBackend()
    result = backend.run(_bell_circuit(), shots=256)
    assert result.counts
    # Bell state should produce only "00" and "11"
    for key in result.counts:
        assert key in ("00", "11")


# ---------------------------------------------------------------------------
# Roundtrip consistency
# ---------------------------------------------------------------------------


def test_roundtrip_descriptor_to_execution():
    """Descriptors → Qiskit circuit → execution must be stable."""
    from rqm_compiler import Circuit, compile_circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from rqm_qiskit.ibm import run_on_aer_sampler

    c = Circuit(1)
    c.h(0)
    c.measure(0)

    compiled = compile_circuit(c)
    qc = compiled_circuit_to_qiskit(compiled)

    from rqm_qiskit.execution import _ensure_measurements
    qc = _ensure_measurements(qc)
    counts = run_on_aer_sampler(qc, shots=200)

    assert isinstance(counts, dict)
    assert sum(counts.values()) == 200


def test_roundtrip_all_single_qubit_gates():
    """All supported single-qubit gates must lower to a runnable circuit."""
    from rqm_compiler import Circuit
    from rqm_qiskit.backend import QiskitBackend

    c = Circuit(1)
    c.i(0)
    c.x(0)
    c.y(0)
    c.z(0)
    c.h(0)
    c.s(0)
    c.t(0)
    c.rx(0, math.pi / 4)
    c.ry(0, math.pi / 4)
    c.rz(0, math.pi / 4)
    c.phaseshift(0, math.pi / 4)
    c.u1q(0, w=1.0, x=0.0, y=0.0, z=0.0)
    c.measure(0)

    backend = QiskitBackend()
    result = backend.run_local(c, shots=64)
    assert result.counts
