"""
Tests for the Quaternion class (src/rqm_qiskit/quaternion.py).
"""

import math
import pytest
import numpy as np

from rqm_qiskit import Quaternion


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_quaternion_stores_components():
    q = Quaternion(1.0, 2.0, 3.0, 4.0)
    assert q.w == 1.0
    assert q.x == 2.0
    assert q.y == 3.0
    assert q.z == 4.0


# ---------------------------------------------------------------------------
# identity()
# ---------------------------------------------------------------------------


def test_identity_components():
    q = Quaternion.identity()
    assert q.w == 1.0
    assert q.x == 0.0
    assert q.y == 0.0
    assert q.z == 0.0


def test_identity_is_unit():
    assert math.isclose(Quaternion.identity().norm(), 1.0, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# norm()
# ---------------------------------------------------------------------------


def test_norm_identity():
    assert math.isclose(Quaternion.identity().norm(), 1.0, abs_tol=1e-10)


def test_norm_general():
    q = Quaternion(1.0, 1.0, 1.0, 1.0)
    assert math.isclose(q.norm(), 2.0, abs_tol=1e-10)


def test_norm_zero():
    q = Quaternion(0.0, 0.0, 0.0, 0.0)
    assert math.isclose(q.norm(), 0.0, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------


def test_normalize_returns_unit():
    q = Quaternion(2.0, 0.0, 0.0, 0.0)
    qn = q.normalize()
    assert math.isclose(qn.norm(), 1.0, abs_tol=1e-10)
    assert math.isclose(qn.w, 1.0, abs_tol=1e-10)


def test_normalize_general_vector():
    q = Quaternion(1.0, 1.0, 1.0, 1.0)
    qn = q.normalize()
    assert math.isclose(qn.norm(), 1.0, abs_tol=1e-10)


def test_normalize_zero_raises():
    with pytest.raises(ValueError, match="zero quaternion"):
        Quaternion(0.0, 0.0, 0.0, 0.0).normalize()


def test_is_unit_true():
    assert Quaternion.identity().is_unit()


def test_is_unit_false():
    assert not Quaternion(2.0, 0.0, 0.0, 0.0).is_unit()


# ---------------------------------------------------------------------------
# conjugate()
# ---------------------------------------------------------------------------


def test_conjugate_w_unchanged():
    q = Quaternion(1.0, 2.0, 3.0, 4.0)
    qc = q.conjugate()
    assert math.isclose(qc.w, 1.0)


def test_conjugate_xyz_negated():
    q = Quaternion(1.0, 2.0, 3.0, 4.0)
    qc = q.conjugate()
    assert math.isclose(qc.x, -2.0)
    assert math.isclose(qc.y, -3.0)
    assert math.isclose(qc.z, -4.0)


def test_unit_quaternion_conjugate_is_inverse():
    """For a unit quaternion q, q * q* should equal identity."""
    q = Quaternion.from_axis_angle("y", 1.23)
    product = q * q.conjugate()
    assert math.isclose(product.w, 1.0, abs_tol=1e-10)
    assert math.isclose(product.x, 0.0, abs_tol=1e-10)
    assert math.isclose(product.y, 0.0, abs_tol=1e-10)
    assert math.isclose(product.z, 0.0, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# Multiplication
# ---------------------------------------------------------------------------


def test_multiply_with_identity():
    q = Quaternion.from_axis_angle("x", 0.7)
    result = q * Quaternion.identity()
    assert q == result


def test_multiply_identity_left():
    q = Quaternion.from_axis_angle("z", 1.5)
    result = Quaternion.identity() * q
    assert result == q


def test_multiply_two_rotations():
    """R_x(π) * R_x(π) should give R_x(2π) ≈ -identity."""
    qx_pi = Quaternion.from_axis_angle("x", math.pi)
    product = qx_pi * qx_pi
    # R_x(2π) = -I: quaternion should be (-1, 0, 0, 0) or (1,0,0,0) within ±sign
    assert math.isclose(abs(product.w), 1.0, abs_tol=1e-10)
    assert math.isclose(product.x, 0.0, abs_tol=1e-10)
    assert math.isclose(product.y, 0.0, abs_tol=1e-10)
    assert math.isclose(product.z, 0.0, abs_tol=1e-10)


def test_multiply_non_commutative():
    """Quaternion multiplication is generally non-commutative."""
    qi = Quaternion(0.0, 1.0, 0.0, 0.0)  # pure i
    qj = Quaternion(0.0, 0.0, 1.0, 0.0)  # pure j
    ij = qi * qj  # should give k
    ji = qj * qi  # should give -k
    assert not (ij == ji)


# ---------------------------------------------------------------------------
# from_axis_angle
# ---------------------------------------------------------------------------


def test_from_axis_angle_returns_unit_x():
    q = Quaternion.from_axis_angle("x", 1.0)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_from_axis_angle_returns_unit_y():
    q = Quaternion.from_axis_angle("y", 0.5)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_from_axis_angle_returns_unit_z():
    q = Quaternion.from_axis_angle("z", 2.0)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_from_axis_angle_zero_is_identity():
    for axis in ("x", "y", "z"):
        q = Quaternion.from_axis_angle(axis, 0.0)
        assert math.isclose(q.w, 1.0, abs_tol=1e-10)
        assert math.isclose(q.x, 0.0, abs_tol=1e-10)
        assert math.isclose(q.y, 0.0, abs_tol=1e-10)
        assert math.isclose(q.z, 0.0, abs_tol=1e-10)


def test_from_axis_angle_x_pi_half():
    """R_x(π/2): q = (cos(π/4), sin(π/4), 0, 0)."""
    q = Quaternion.from_axis_angle("x", math.pi / 2)
    expected_w = math.cos(math.pi / 4)
    expected_x = math.sin(math.pi / 4)
    assert math.isclose(q.w, expected_w, abs_tol=1e-10)
    assert math.isclose(q.x, expected_x, abs_tol=1e-10)
    assert math.isclose(q.y, 0.0, abs_tol=1e-10)
    assert math.isclose(q.z, 0.0, abs_tol=1e-10)


def test_from_axis_angle_invalid_axis():
    with pytest.raises(ValueError, match="axis must be one of"):
        Quaternion.from_axis_angle("w", 1.0)


def test_from_axis_angle_case_insensitive():
    q = Quaternion.from_axis_angle("X", 1.0)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# to_su2_matrix
# ---------------------------------------------------------------------------


def test_to_su2_matrix_shape():
    mat = Quaternion.identity().to_su2_matrix()
    assert mat.shape == (2, 2)


def test_to_su2_matrix_dtype_complex():
    mat = Quaternion.identity().to_su2_matrix()
    assert np.issubdtype(mat.dtype, np.complexfloating)


def test_to_su2_matrix_identity_is_eye():
    mat = Quaternion.identity().to_su2_matrix()
    assert np.allclose(mat, np.eye(2), atol=1e-12)


def test_to_su2_matrix_is_unitary():
    """SU(2) matrices should be unitary: U†U = I."""
    for axis in ("x", "y", "z"):
        q = Quaternion.from_axis_angle(axis, 1.23)
        U = q.to_su2_matrix()
        assert np.allclose(U.conj().T @ U, np.eye(2), atol=1e-12)


def test_to_su2_matrix_rx_matches_gate():
    """Quaternion SU(2) matrix should match RQMGate.to_matrix() for R_x."""
    from rqm_qiskit import RQMGate

    gate = RQMGate.rx(1.5)
    gate_mat = gate.to_matrix()
    quat_mat = gate.quaternion.to_su2_matrix()
    assert np.allclose(gate_mat, quat_mat, atol=1e-12)


def test_to_su2_matrix_ry_matches_gate():
    """Quaternion SU(2) matrix should match RQMGate.to_matrix() for R_y."""
    from rqm_qiskit import RQMGate

    gate = RQMGate.ry(0.8)
    gate_mat = gate.to_matrix()
    quat_mat = gate.quaternion.to_su2_matrix()
    assert np.allclose(gate_mat, quat_mat, atol=1e-12)


def test_to_su2_matrix_rz_matches_gate():
    """Quaternion SU(2) matrix should match RQMGate.to_matrix() for R_z."""
    from rqm_qiskit import RQMGate

    gate = RQMGate.rz(0.3)
    gate_mat = gate.to_matrix()
    quat_mat = gate.quaternion.to_su2_matrix()
    assert np.allclose(gate_mat, quat_mat, atol=1e-12)


# ---------------------------------------------------------------------------
# pretty() and __repr__
# ---------------------------------------------------------------------------


def test_pretty_returns_string():
    assert isinstance(Quaternion.identity().pretty(), str)


def test_repr_contains_components():
    r = repr(Quaternion(1.0, 2.0, 3.0, 4.0))
    assert "w=" in r
    assert "x=" in r
    assert "y=" in r
    assert "z=" in r
