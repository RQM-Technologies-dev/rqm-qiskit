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


# ---------------------------------------------------------------------------
# from_axis_angle_vec (inherited from rqm-core)
# ---------------------------------------------------------------------------


def test_from_axis_angle_vec_x_axis():
    """from_axis_angle_vec([1,0,0], θ) must equal from_axis_angle('x', θ)."""
    angle = 1.2
    q_vec = Quaternion.from_axis_angle_vec([1.0, 0.0, 0.0], angle)
    q_label = Quaternion.from_axis_angle("x", angle)
    assert math.isclose(q_vec.w, q_label.w, abs_tol=1e-12)
    assert math.isclose(q_vec.x, q_label.x, abs_tol=1e-12)
    assert math.isclose(q_vec.y, q_label.y, abs_tol=1e-12)
    assert math.isclose(q_vec.z, q_label.z, abs_tol=1e-12)


def test_from_axis_angle_vec_arbitrary_axis():
    """from_axis_angle_vec with a non-cardinal axis should return a unit quaternion."""
    q = Quaternion.from_axis_angle_vec([1.0, 1.0, 1.0], math.pi / 3)
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_from_axis_angle_vec_unnormalized_axis():
    """Axis vector is normalized internally; scaling must not change the quaternion."""
    q1 = Quaternion.from_axis_angle_vec([2.0, 0.0, 0.0], 1.0)
    q2 = Quaternion.from_axis_angle_vec([1.0, 0.0, 0.0], 1.0)
    assert q1 == q2


def test_from_axis_angle_vec_zero_axis_raises():
    with pytest.raises(ValueError):
        Quaternion.from_axis_angle_vec([0.0, 0.0, 0.0], 1.0)


def test_from_axis_angle_vec_zero_angle_is_identity():
    q = Quaternion.from_axis_angle_vec([1.0, 1.0, 0.0], 0.0)
    assert math.isclose(q.w, 1.0, abs_tol=1e-10)
    assert math.isclose(q.x, 0.0, abs_tol=1e-10)
    assert math.isclose(q.y, 0.0, abs_tol=1e-10)
    assert math.isclose(q.z, 0.0, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# to_axis_angle (inherited from rqm-core)
# ---------------------------------------------------------------------------


def test_to_axis_angle_x_rotation():
    """R_x(π/2) → axis=(1,0,0), angle=π/2."""
    q = Quaternion.from_axis_angle("x", math.pi / 2)
    axis, angle = q.to_axis_angle()
    assert math.isclose(axis[0], 1.0, abs_tol=1e-10)
    assert math.isclose(axis[1], 0.0, abs_tol=1e-10)
    assert math.isclose(axis[2], 0.0, abs_tol=1e-10)
    assert math.isclose(angle, math.pi / 2, abs_tol=1e-10)


def test_to_axis_angle_z_rotation():
    """R_z(π/4) → axis=(0,0,1), angle=π/4."""
    q = Quaternion.from_axis_angle("z", math.pi / 4)
    axis, angle = q.to_axis_angle()
    assert math.isclose(axis[2], 1.0, abs_tol=1e-10)
    assert math.isclose(angle, math.pi / 4, abs_tol=1e-10)


def test_to_axis_angle_arbitrary_axis_round_trip():
    """from_axis_angle_vec → to_axis_angle should recover the original angle."""
    original_angle = 1.1
    q = Quaternion.from_axis_angle_vec([1.0, 1.0, 0.0], original_angle)
    _, recovered_angle = q.to_axis_angle()
    assert math.isclose(recovered_angle, original_angle, abs_tol=1e-10)


def test_to_axis_angle_identity_returns_zero_angle():
    """Identity quaternion → angle ≈ 0, axis is arbitrary."""
    _, angle = Quaternion.identity().to_axis_angle()
    assert math.isclose(angle, 0.0, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# canonicalize (inherited from rqm-core)
# ---------------------------------------------------------------------------


def test_canonicalize_positive_w_unchanged():
    """Quaternion with w > 0 should be unchanged by canonicalize."""
    q = Quaternion.from_axis_angle("y", 0.5)
    assert q.w > 0
    qc = q.canonicalize()
    assert math.isclose(qc.w, q.w, abs_tol=1e-12)


def test_canonicalize_negative_w_flipped():
    """Quaternion with w < 0 should have all components negated."""
    q = Quaternion(-0.8, 0.1, 0.2, 0.3).normalize()
    assert q.w < 0
    qc = q.canonicalize()
    assert qc.w >= 0.0


def test_canonicalize_is_unit():
    """Canonical representative must also be a unit quaternion."""
    q = Quaternion(-1.0, 0.0, 0.0, 0.0)
    assert math.isclose(q.canonicalize().norm(), 1.0, abs_tol=1e-10)


def test_canonicalize_same_su2_matrix():
    """Both q and -q represent the same SU(2) double-cover of the same SO(3) rotation.

    In SU(2), q and -q are distinct elements whose matrices differ by a global sign.
    However, they represent the same physical rotation (same Bloch-sphere action).
    The canonical form (w ≥ 0) picks one representative consistently.
    """
    q = Quaternion(0.5, 0.5, 0.5, 0.5)
    neg_q = Quaternion(-0.5, -0.5, -0.5, -0.5)
    # SU(2) matrices differ by a global sign (global phase of -1)
    assert np.allclose(q.to_su2_matrix(), -neg_q.to_su2_matrix(), atol=1e-12), (
        "q and -q must have SU(2) matrices that are negatives of each other"
    )
    # Canonical form picks the representative with w >= 0
    assert q.canonicalize().w >= 0.0
    assert neg_q.canonicalize().w >= 0.0
    # Both canonical forms must be the same quaternion
    assert q.canonicalize() == neg_q.canonicalize()


# ---------------------------------------------------------------------------
# rotate_vector (inherited from rqm-core)
# ---------------------------------------------------------------------------


def test_rotate_vector_identity_is_noop():
    """Identity quaternion should leave any vector unchanged."""
    v = (1.0, 2.0, 3.0)
    result = Quaternion.identity().rotate_vector(v)
    assert math.isclose(result[0], 1.0, abs_tol=1e-12)
    assert math.isclose(result[1], 2.0, abs_tol=1e-12)
    assert math.isclose(result[2], 3.0, abs_tol=1e-12)


def test_rotate_vector_rx_pi_z_to_neg_z():
    """R_x(π) should map (0, 0, 1) to (0, 0, -1) (Bloch north→south)."""
    q = Quaternion.from_axis_angle("x", math.pi)
    result = q.rotate_vector([0.0, 0.0, 1.0])
    assert math.isclose(result[0], 0.0, abs_tol=1e-10)
    assert math.isclose(result[1], 0.0, abs_tol=1e-10)
    assert math.isclose(result[2], -1.0, abs_tol=1e-10)


def test_rotate_vector_preserves_length():
    """Rotation must not change the length of the vector."""
    q = Quaternion.from_axis_angle_vec([1.0, 1.0, 1.0], 1.23)
    v = [1.0, 2.0, 3.0]
    original_len = math.sqrt(sum(x * x for x in v))
    result = q.rotate_vector(v)
    rotated_len = math.sqrt(sum(x * x for x in result))
    assert math.isclose(original_len, rotated_len, abs_tol=1e-10)


def test_rotate_vector_ry_pi_z_to_neg_z():
    """R_y(π) should map (0, 0, 1) to (0, 0, -1)."""
    q = Quaternion.from_axis_angle("y", math.pi)
    result = q.rotate_vector([0.0, 0.0, 1.0])
    assert math.isclose(result[2], -1.0, abs_tol=1e-10)


def test_rotate_vector_matches_rotation_matrix():
    """rotate_vector should match the 3×3 SO(3) rotation matrix."""
    q = Quaternion.from_axis_angle("z", math.pi / 3)
    v = np.array([1.0, 0.0, 0.0])
    R = q.to_rotation_matrix()
    expected = tuple(float(x) for x in R @ v)
    result = q.rotate_vector(v)
    for r, e in zip(result, expected):
        assert math.isclose(r, e, abs_tol=1e-12)
