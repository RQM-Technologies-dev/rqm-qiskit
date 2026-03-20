"""
Tests for u1q gate translation.

Covers:
- u1q with identity quaternion produces identity matrix
- u1q with Pauli-X quaternion (w=0, x=1) produces X gate matrix
- u1q with Ry(π/2) quaternion matches Ry(π/2) gate
- u1q with Hadamard quaternion matches H gate (up to global phase)
- u1q in a circuit executes successfully on local simulator
- u1q with general valid quaternion translates without error
"""

import math
import pytest
import numpy as np
from qiskit import QuantumCircuit


def _u1q_circuit(w, x, y, z):
    """Build a 1-qubit circuit with a u1q gate."""
    from rqm_compiler import Circuit

    c = Circuit(1)
    c.u1q(0, w=w, x=x, y=y, z=z)
    return c


def _to_matrix(circuit):
    """Compile a circuit and return the unitary matrix."""
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit.quantum_info import Operator

    qc = compiled_circuit_to_qiskit(circuit)
    return Operator(qc).data


def _matrices_equal_up_to_phase(a, b, atol=1e-6):
    """Return True if a and b are equal up to a global phase factor."""
    # Find a non-zero element in b to extract the phase
    for i in range(a.shape[0]):
        for j in range(a.shape[1]):
            if abs(b[i, j]) > atol:
                phase = a[i, j] / b[i, j]
                return np.allclose(a, phase * b, atol=atol)
    return False


# ---------------------------------------------------------------------------
# Identity quaternion
# ---------------------------------------------------------------------------


def test_u1q_identity_quaternion_produces_identity():
    """u1q with identity quaternion (w=1,x=0,y=0,z=0) must be the identity matrix."""
    mat = _to_matrix(_u1q_circuit(w=1.0, x=0.0, y=0.0, z=0.0))
    assert np.allclose(mat, np.eye(2), atol=1e-6), f"Expected identity, got:\n{mat}"


def test_u1q_identity_quaternion_num_qubits():
    """u1q circuit must produce a 1-qubit circuit."""
    from rqm_qiskit.convert import compiled_circuit_to_qiskit

    qc = compiled_circuit_to_qiskit(_u1q_circuit(w=1.0, x=0.0, y=0.0, z=0.0))
    assert qc.num_qubits == 1


# ---------------------------------------------------------------------------
# Pauli-X quaternion
# ---------------------------------------------------------------------------


def test_u1q_pauli_x_quaternion_matches_x_gate():
    """u1q with Pauli-X quaternion (w=0,x=1,y=0,z=0) must match X gate up to phase."""
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit.quantum_info import Operator

    # X gate SU(2) rep: w=0, x=1, y=0, z=0
    u1q_mat = _to_matrix(_u1q_circuit(w=0.0, x=1.0, y=0.0, z=0.0))

    cx = Circuit(1)
    cx.x(0)
    x_mat = _to_matrix(cx)

    assert _matrices_equal_up_to_phase(u1q_mat, x_mat), (
        f"u1q Pauli-X mismatch.\nu1q={u1q_mat}\nx={x_mat}"
    )


# ---------------------------------------------------------------------------
# Ry(π/2) quaternion
# ---------------------------------------------------------------------------


def test_u1q_ry_pi_over_2_matches_ry_gate():
    """u1q with Ry(π/2) quaternion must match Ry(π/2) gate up to phase."""
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit

    angle = math.pi / 2
    w = math.cos(angle / 2)
    y = math.sin(angle / 2)

    u1q_mat = _to_matrix(_u1q_circuit(w=w, x=0.0, y=y, z=0.0))

    c_ry = Circuit(1)
    c_ry.ry(0, angle)
    ry_mat = _to_matrix(c_ry)

    assert _matrices_equal_up_to_phase(u1q_mat, ry_mat) or np.allclose(
        u1q_mat, ry_mat, atol=1e-6
    ), f"u1q Ry(π/2) mismatch.\nu1q={u1q_mat}\nry={ry_mat}"


# ---------------------------------------------------------------------------
# Hadamard quaternion
# ---------------------------------------------------------------------------


def test_u1q_hadamard_quaternion_matches_h_gate():
    """u1q with Hadamard quaternion must match H gate up to global phase."""
    from rqm_compiler import Circuit

    # H = (X + Z) / sqrt(2); quaternion: w=0, x=1/sqrt(2), y=0, z=1/sqrt(2) normalized
    s = 1.0 / math.sqrt(2)
    u1q_mat = _to_matrix(_u1q_circuit(w=0.0, x=s, y=0.0, z=s))

    ch = Circuit(1)
    ch.h(0)
    h_mat = _to_matrix(ch)

    assert _matrices_equal_up_to_phase(u1q_mat, h_mat), (
        f"u1q Hadamard mismatch.\nu1q={u1q_mat}\nh={h_mat}"
    )


# ---------------------------------------------------------------------------
# Rx(π/2) quaternion
# ---------------------------------------------------------------------------


def test_u1q_rx_pi_over_2_matches_rx_gate():
    """u1q with Rx(π/2) quaternion must match Rx(π/2) gate up to phase."""
    from rqm_compiler import Circuit

    angle = math.pi / 2
    w = math.cos(angle / 2)
    x = math.sin(angle / 2)

    u1q_mat = _to_matrix(_u1q_circuit(w=w, x=x, y=0.0, z=0.0))

    c_rx = Circuit(1)
    c_rx.rx(0, angle)
    rx_mat = _to_matrix(c_rx)

    assert _matrices_equal_up_to_phase(u1q_mat, rx_mat) or np.allclose(
        u1q_mat, rx_mat, atol=1e-6
    ), f"u1q Rx(π/2) mismatch.\nu1q={u1q_mat}\nrx={rx_mat}"


# ---------------------------------------------------------------------------
# Rz(π/2) quaternion
# ---------------------------------------------------------------------------


def test_u1q_rz_pi_over_2_matches_rz_gate():
    """u1q with Rz(π/2) quaternion must match Rz(π/2) gate up to phase."""
    from rqm_compiler import Circuit

    angle = math.pi / 2
    w = math.cos(angle / 2)
    z = math.sin(angle / 2)

    u1q_mat = _to_matrix(_u1q_circuit(w=w, x=0.0, y=0.0, z=z))

    c_rz = Circuit(1)
    c_rz.rz(0, angle)
    rz_mat = _to_matrix(c_rz)

    assert _matrices_equal_up_to_phase(u1q_mat, rz_mat) or np.allclose(
        u1q_mat, rz_mat, atol=1e-6
    ), f"u1q Rz(π/2) mismatch.\nu1q={u1q_mat}\nrz={rz_mat}"


# ---------------------------------------------------------------------------
# General valid quaternion
# ---------------------------------------------------------------------------


def test_u1q_general_quaternion_translates_without_error():
    """u1q with a general unit quaternion must translate without error."""
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit.quantum_info import Operator

    # Arbitrary unit quaternion: normalize (1, 1, 1, 1) / 2
    w = x = y = z = 0.5  # norm = 1
    qc = compiled_circuit_to_qiskit(_u1q_circuit(w=w, x=x, y=y, z=z))
    op = Operator(qc).data
    assert op.shape == (2, 2)


def test_u1q_general_quaternion_produces_unitary():
    """u1q with a general unit quaternion must produce a unitary matrix."""
    from qiskit.quantum_info import Operator

    w = x = y = z = 0.5  # norm = 1
    qc_mat = _to_matrix(_u1q_circuit(w=w, x=x, y=y, z=z))
    # Verify U†U ≈ I
    assert np.allclose(qc_mat @ qc_mat.conj().T, np.eye(2), atol=1e-6)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def test_u1q_x_gate_quaternion_executes_and_flips_qubit():
    """u1q X-gate quaternion in a circuit must flip the qubit (measure → '1')."""
    from rqm_compiler import Circuit
    from rqm_qiskit.backend import QiskitBackend

    # X gate: w=0, x=1, y=0, z=0
    c = Circuit(1)
    c.u1q(0, w=0.0, x=1.0, y=0.0, z=0.0)
    c.measure(0)

    backend = QiskitBackend()
    result = backend.run_local(c, shots=128)
    assert result.counts
    # X gate on |0⟩ → |1⟩, so we should see only "1"
    assert "1" in result.counts
    assert result.counts.get("0", 0) == 0


def test_u1q_identity_executes_no_flip():
    """u1q identity quaternion in a circuit must not flip the qubit."""
    from rqm_compiler import Circuit
    from rqm_qiskit.backend import QiskitBackend

    c = Circuit(1)
    c.u1q(0, w=1.0, x=0.0, y=0.0, z=0.0)
    c.measure(0)

    backend = QiskitBackend()
    result = backend.run_local(c, shots=128)
    assert result.counts
    assert "0" in result.counts
    assert result.counts.get("1", 0) == 0


def test_u1q_in_circuit_with_multiple_gates():
    """u1q in a multi-gate circuit must execute successfully."""
    from rqm_compiler import Circuit
    from rqm_qiskit.backend import QiskitBackend

    c = Circuit(1)
    c.h(0)
    c.u1q(0, w=1.0, x=0.0, y=0.0, z=0.0)  # identity after H
    c.measure(0)

    backend = QiskitBackend()
    result = backend.run_local(c, shots=128)
    assert result.counts
    assert len(result.counts) > 0
