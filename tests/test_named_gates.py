"""
Tests for named gate quaternions and gate recognition.

Validates that rqm-qiskit properly re-exports the gate factories and
match_gate function from rqm_core.gates, and that the conventions are
correct:

- gate_h, gate_s, gate_t return canonical (w ≥ 0) unit quaternions
- gate_rx, gate_ry, gate_rz return unit quaternions for parametric rotations
- match_gate identifies named gates and returns None for unknown quaternions
- gate matching checks both q and -q (same SU(2) element)
- named gate SU(2) matrices match the Qiskit gate matrices up to global phase
"""

import math
import pytest
import numpy as np

from rqm_qiskit import (
    Quaternion,
    gate_h,
    gate_s,
    gate_t,
    gate_rx,
    gate_ry,
    gate_rz,
    match_gate,
)


# ---------------------------------------------------------------------------
# Imports: verify rqm-qiskit re-exports from rqm_core.gates
# ---------------------------------------------------------------------------


def test_gate_h_importable_from_rqm_qiskit():
    """gate_h must be importable from the rqm_qiskit top-level namespace."""
    from rqm_qiskit import gate_h as g
    assert callable(g)


def test_match_gate_importable_from_rqm_qiskit():
    """match_gate must be importable from the rqm_qiskit top-level namespace."""
    from rqm_qiskit import match_gate as mg
    assert callable(mg)


def test_named_gates_imported_from_rqm_core():
    """gate_h, gate_s, gate_t, match_gate must come from rqm_core.gates."""
    import rqm_qiskit.gates as gates_module
    from rqm_core.gates import gate_h as core_gate_h
    from rqm_core.gates import match_gate as core_match_gate

    # The imported symbols in rqm_qiskit.gates should be the same objects
    # as in rqm_core.gates.
    assert gates_module.gate_h is core_gate_h
    assert gates_module.match_gate is core_match_gate


# ---------------------------------------------------------------------------
# gate_h: Hadamard gate quaternion
# ---------------------------------------------------------------------------


def test_gate_h_is_unit_quaternion():
    from rqm_core.quaternion import Quaternion as CoreQ
    q = gate_h()
    assert isinstance(q, CoreQ)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_gate_h_canonical_form():
    """gate_h must return the canonical representative (w ≥ 0)."""
    q = gate_h()
    assert q.w >= 0.0


def test_gate_h_su2_matrix_is_unitary():
    U = gate_h().to_su2_matrix()
    assert np.allclose(U.conj().T @ U, np.eye(2), atol=1e-12)


def test_gate_h_acts_as_hadamard_on_bloch():
    """H maps |0⟩ (north pole) to |+⟩ (equator at x=1)."""
    q = gate_h()
    bloch_zero = (0.0, 0.0, 1.0)
    rotated = q.rotate_vector(bloch_zero)
    # |+⟩ = (1, 0, 0) on the Bloch sphere
    assert math.isclose(abs(rotated[0]), 1.0, abs_tol=1e-10)
    assert math.isclose(rotated[1], 0.0, abs_tol=1e-10)
    assert math.isclose(rotated[2], 0.0, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# gate_s: S (phase) gate quaternion
# ---------------------------------------------------------------------------


def test_gate_s_is_unit_quaternion():
    from rqm_core.quaternion import Quaternion as CoreQ
    q = gate_s()
    assert isinstance(q, CoreQ)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_gate_s_canonical_form():
    assert gate_s().w >= 0.0


def test_gate_s_is_rz_half_pi():
    """S gate = R_z(π/2), so it must equal gate_rz(π/2)."""
    q_s = gate_s()
    q_rz = gate_rz(math.pi / 2)
    assert np.allclose(q_s.to_su2_matrix(), q_rz.to_su2_matrix(), atol=1e-12)


# ---------------------------------------------------------------------------
# gate_t: T gate quaternion
# ---------------------------------------------------------------------------


def test_gate_t_is_unit_quaternion():
    from rqm_core.quaternion import Quaternion as CoreQ
    q = gate_t()
    assert isinstance(q, CoreQ)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_gate_t_canonical_form():
    assert gate_t().w >= 0.0


def test_gate_t_is_rz_quarter_pi():
    """T gate = R_z(π/4), so it must equal gate_rz(π/4)."""
    q_t = gate_t()
    q_rz = gate_rz(math.pi / 4)
    assert np.allclose(q_t.to_su2_matrix(), q_rz.to_su2_matrix(), atol=1e-12)


# ---------------------------------------------------------------------------
# gate_rx, gate_ry, gate_rz: parametric rotation quaternions
# ---------------------------------------------------------------------------


def test_gate_rx_is_unit_quaternion():
    from rqm_core.quaternion import Quaternion as CoreQ
    q = gate_rx(1.0)
    assert isinstance(q, CoreQ)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_gate_ry_is_unit_quaternion():
    from rqm_core.quaternion import Quaternion as CoreQ
    q = gate_ry(1.0)
    assert isinstance(q, CoreQ)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_gate_rz_is_unit_quaternion():
    from rqm_core.quaternion import Quaternion as CoreQ
    q = gate_rz(1.0)
    assert isinstance(q, CoreQ)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_gate_rx_matches_quaternion_from_axis_angle():
    """gate_rx(θ) must match Quaternion.from_axis_angle('x', θ)."""
    angle = 1.23
    assert np.allclose(
        gate_rx(angle).to_su2_matrix(),
        Quaternion.from_axis_angle("x", angle).to_su2_matrix(),
        atol=1e-12,
    )


def test_gate_ry_zero_is_identity():
    U = gate_ry(0.0).to_su2_matrix()
    assert np.allclose(U, np.eye(2), atol=1e-12)


def test_gate_rz_pi_over_2_matches_gate_s():
    """gate_rz(π/2) must produce the same SU(2) matrix as gate_s."""
    assert np.allclose(
        gate_rz(math.pi / 2).to_su2_matrix(),
        gate_s().to_su2_matrix(),
        atol=1e-12,
    )


# ---------------------------------------------------------------------------
# match_gate: gate identification
# ---------------------------------------------------------------------------


def test_match_gate_identifies_h():
    assert match_gate(gate_h()) == "h"


def test_match_gate_identifies_s():
    assert match_gate(gate_s()) == "s"


def test_match_gate_identifies_t():
    assert match_gate(gate_t()) == "t"


def test_match_gate_identifies_negative_h():
    """match_gate must also recognize -q as the same gate (double-cover)."""
    q = gate_h()
    neg_q = Quaternion(-q.w, -q.x, -q.y, -q.z)
    assert match_gate(neg_q) == "h"


def test_match_gate_returns_none_for_unknown():
    """A generic rotation quaternion should not match any named gate."""
    q = Quaternion.from_axis_angle("x", 1.234)
    assert match_gate(q) is None


def test_match_gate_returns_none_for_identity():
    """Identity quaternion is not a named gate in the library."""
    assert match_gate(Quaternion.identity()) is None


# ---------------------------------------------------------------------------
# Integration: named gate quaternions vs RQMGate
# ---------------------------------------------------------------------------


def test_named_gate_rx_matches_rqm_gate_rx():
    """gate_rx(θ).to_su2_matrix() must match RQMGate.rx(θ).to_matrix()."""
    from rqm_qiskit import RQMGate

    for angle in [0.5, 1.0, math.pi / 2, math.pi]:
        assert np.allclose(
            gate_rx(angle).to_su2_matrix(),
            RQMGate.rx(angle).to_matrix(),
            atol=1e-12,
        ), f"Mismatch at angle={angle}"


def test_named_gate_ry_matches_rqm_gate_ry():
    """gate_ry(θ).to_su2_matrix() must match RQMGate.ry(θ).to_matrix()."""
    from rqm_qiskit import RQMGate

    for angle in [0.5, 1.0, math.pi / 2]:
        assert np.allclose(
            gate_ry(angle).to_su2_matrix(),
            RQMGate.ry(angle).to_matrix(),
            atol=1e-12,
        )


def test_named_gate_rz_matches_rqm_gate_rz():
    """gate_rz(θ).to_su2_matrix() must match RQMGate.rz(θ).to_matrix()."""
    from rqm_qiskit import RQMGate

    for angle in [0.5, 1.0, math.pi / 2]:
        assert np.allclose(
            gate_rz(angle).to_su2_matrix(),
            RQMGate.rz(angle).to_matrix(),
            atol=1e-12,
        )
