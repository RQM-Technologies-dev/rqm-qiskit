"""
Tests for RQMGate (src/rqm_qiskit/gates.py).
"""

import math
import pytest
import numpy as np

from rqm_qiskit import RQMGate


# ---------------------------------------------------------------------------
# Construction and axis validation
# ---------------------------------------------------------------------------


def test_valid_axes():
    for axis in ("x", "y", "z"):
        gate = RQMGate(axis, 1.0)
        assert gate.axis == axis


def test_invalid_axis_raises():
    with pytest.raises(ValueError, match="Invalid axis"):
        RQMGate("w", 1.0)


def test_invalid_axis_raises_empty_string():
    with pytest.raises(ValueError):
        RQMGate("", 1.0)


def test_axis_case_insensitive():
    gate = RQMGate("X", math.pi)
    assert gate.axis == "x"


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def test_rx_constructor():
    gate = RQMGate.rx(1.0)
    assert gate.axis == "x"
    assert math.isclose(gate.angle, 1.0)


def test_ry_constructor():
    gate = RQMGate.ry(2.0)
    assert gate.axis == "y"
    assert math.isclose(gate.angle, 2.0)


def test_rz_constructor():
    gate = RQMGate.rz(0.5)
    assert gate.axis == "z"
    assert math.isclose(gate.angle, 0.5)


# ---------------------------------------------------------------------------
# Matrix shape and properties
# ---------------------------------------------------------------------------


def test_matrix_shape_x():
    mat = RQMGate.rx(1.0).to_matrix()
    assert mat.shape == (2, 2)


def test_matrix_shape_y():
    mat = RQMGate.ry(1.0).to_matrix()
    assert mat.shape == (2, 2)


def test_matrix_shape_z():
    mat = RQMGate.rz(1.0).to_matrix()
    assert mat.shape == (2, 2)


def test_matrix_dtype_is_complex():
    for axis in ("x", "y", "z"):
        mat = RQMGate(axis, 1.0).to_matrix()
        assert np.issubdtype(mat.dtype, np.complexfloating)


def test_matrix_is_unitary():
    """R_n(θ) should be unitary: U† U = I."""
    for axis in ("x", "y", "z"):
        mat = RQMGate(axis, 1.23).to_matrix()
        product = mat.conj().T @ mat
        assert np.allclose(product, np.eye(2), atol=1e-12), (
            f"Gate R{axis}(1.23) is not unitary"
        )


def test_rx_zero_angle_is_identity():
    mat = RQMGate.rx(0.0).to_matrix()
    assert np.allclose(mat, np.eye(2), atol=1e-12)


def test_ry_zero_angle_is_identity():
    mat = RQMGate.ry(0.0).to_matrix()
    assert np.allclose(mat, np.eye(2), atol=1e-12)


def test_rz_zero_angle_is_identity():
    mat = RQMGate.rz(0.0).to_matrix()
    assert np.allclose(mat, np.eye(2), atol=1e-12)


def test_rx_pi_flips_state():
    """R_x(π)|0> should give -i|1> (up to global phase)."""
    mat = RQMGate.rx(math.pi).to_matrix()
    state_0 = np.array([1.0, 0.0])
    result = mat @ state_0
    # Up to global phase, result ≈ |1>
    assert np.isclose(abs(result[1]), 1.0, atol=1e-10)


def test_ry_half_pi():
    """R_y(π/2)|0> should give (|0> + |1>) / sqrt(2), i.e. |+>."""
    mat = RQMGate.ry(math.pi / 2).to_matrix()
    state_0 = np.array([1.0, 0.0])
    result = mat @ state_0
    expected = np.array([1.0 / math.sqrt(2), 1.0 / math.sqrt(2)])
    assert np.allclose(result, expected, atol=1e-10)


# ---------------------------------------------------------------------------
# Qiskit gate conversion
# ---------------------------------------------------------------------------


def test_to_qiskit_gate_x():
    from qiskit.circuit.library import RXGate

    g = RQMGate.rx(1.0).to_qiskit_gate()
    assert isinstance(g, RXGate)


def test_to_qiskit_gate_y():
    from qiskit.circuit.library import RYGate

    g = RQMGate.ry(1.0).to_qiskit_gate()
    assert isinstance(g, RYGate)


def test_to_qiskit_gate_z():
    from qiskit.circuit.library import RZGate

    g = RQMGate.rz(1.0).to_qiskit_gate()
    assert isinstance(g, RZGate)


# ---------------------------------------------------------------------------
# pretty() and __repr__
# ---------------------------------------------------------------------------


def test_pretty_returns_string():
    assert isinstance(RQMGate.rx(1.0).pretty(), str)


def test_repr_contains_axis_and_angle():
    r = repr(RQMGate("y", 2.5))
    assert "axis" in r
    assert "angle" in r


# ---------------------------------------------------------------------------
# quaternion property
# ---------------------------------------------------------------------------


def test_quaternion_property_returns_quaternion():
    from rqm_qiskit import Quaternion

    q = RQMGate.rx(1.0).quaternion
    assert isinstance(q, Quaternion)


def test_quaternion_property_is_unit():
    """Gate quaternions should all be unit quaternions."""
    for axis in ("x", "y", "z"):
        q = RQMGate(axis, 1.23).quaternion
        assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_quaternion_su2_matches_gate_matrix():
    """quaternion.to_su2_matrix() must equal gate.to_matrix() for all axes."""
    import numpy as np

    for axis in ("x", "y", "z"):
        gate = RQMGate(axis, 0.9)
        assert np.allclose(gate.quaternion.to_su2_matrix(), gate.to_matrix(), atol=1e-12)


def test_quaternion_zero_angle_is_identity():
    """A zero-angle gate should give the identity quaternion."""
    for axis in ("x", "y", "z"):
        q = RQMGate(axis, 0.0).quaternion
        assert math.isclose(q.w, 1.0, abs_tol=1e-10)
        assert math.isclose(q.x, 0.0, abs_tol=1e-10)
        assert math.isclose(q.y, 0.0, abs_tol=1e-10)
        assert math.isclose(q.z, 0.0, abs_tol=1e-10)
