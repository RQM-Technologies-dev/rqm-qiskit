"""
Tests for RQMState (src/rqm_qiskit/state.py).
"""

import math
import cmath
import pytest
import numpy as np

from rqm_qiskit import RQMState


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_normalization_from_unnormalized_input():
    """State should be auto-normalized even if raw input is not unit."""
    state = RQMState(2.0, 2.0)
    assert math.isclose(state.norm(), 1.0, abs_tol=1e-10)


def test_norm_is_one_for_all_constructors():
    for s in [RQMState.zero(), RQMState.one(), RQMState.plus(), RQMState.minus()]:
        assert math.isclose(s.norm(), 1.0, abs_tol=1e-10)


def test_zero_norm_raises():
    with pytest.raises(ValueError, match="zero norm"):
        RQMState(0.0, 0.0)


# ---------------------------------------------------------------------------
# Known states
# ---------------------------------------------------------------------------


def test_zero_state():
    s = RQMState.zero()
    assert np.isclose(s.alpha, 1.0)
    assert np.isclose(s.beta, 0.0)


def test_one_state():
    s = RQMState.one()
    assert np.isclose(s.alpha, 0.0)
    assert np.isclose(s.beta, 1.0)


def test_plus_state():
    s = RQMState.plus()
    expected = 1.0 / math.sqrt(2)
    assert np.isclose(s.alpha, expected)
    assert np.isclose(s.beta, expected)


def test_minus_state():
    s = RQMState.minus()
    expected = 1.0 / math.sqrt(2)
    assert np.isclose(s.alpha, expected)
    assert np.isclose(s.beta, -expected)


# ---------------------------------------------------------------------------
# vector() method
# ---------------------------------------------------------------------------


def test_vector_returns_tuple():
    s = RQMState.plus()
    v = s.vector()
    assert isinstance(v, tuple)
    assert len(v) == 2


# ---------------------------------------------------------------------------
# Bloch vectors for simple states
# ---------------------------------------------------------------------------


def test_bloch_vector_zero():
    """The |0> state should sit at the north pole: (0, 0, 1)."""
    bv = RQMState.zero().bloch_vector()
    assert np.allclose(bv, (0.0, 0.0, 1.0), atol=1e-10)


def test_bloch_vector_one():
    """The |1> state should sit at the south pole: (0, 0, -1)."""
    bv = RQMState.one().bloch_vector()
    assert np.allclose(bv, (0.0, 0.0, -1.0), atol=1e-10)


def test_bloch_vector_plus():
    """The |+> state should sit on the positive x-axis: (1, 0, 0)."""
    bv = RQMState.plus().bloch_vector()
    assert np.allclose(bv, (1.0, 0.0, 0.0), atol=1e-10)


def test_bloch_vector_minus():
    """The |-> state should sit on the negative x-axis: (-1, 0, 0)."""
    bv = RQMState.minus().bloch_vector()
    assert np.allclose(bv, (-1.0, 0.0, 0.0), atol=1e-10)


# ---------------------------------------------------------------------------
# from_bloch constructor
# ---------------------------------------------------------------------------


def test_from_bloch_north_pole():
    """theta=0 should give |0>."""
    s = RQMState.from_bloch(0.0, 0.0)
    assert np.isclose(s.alpha, 1.0, atol=1e-10)
    assert np.isclose(abs(s.beta), 0.0, atol=1e-10)


def test_from_bloch_south_pole():
    """theta=pi should give |1>."""
    s = RQMState.from_bloch(math.pi, 0.0)
    assert np.isclose(abs(s.alpha), 0.0, atol=1e-10)
    assert np.isclose(abs(s.beta), 1.0, atol=1e-10)


def test_from_bloch_equator_plus():
    """theta=pi/2, phi=0 should give |+>."""
    s = RQMState.from_bloch(math.pi / 2, 0.0)
    bv = s.bloch_vector()
    assert np.allclose(bv, (1.0, 0.0, 0.0), atol=1e-10)


# ---------------------------------------------------------------------------
# as_qiskit_statevector
# ---------------------------------------------------------------------------


def test_as_qiskit_statevector_type():
    from qiskit.quantum_info import Statevector

    sv = RQMState.plus().as_qiskit_statevector()
    assert isinstance(sv, Statevector)


def test_as_qiskit_statevector_values():
    from qiskit.quantum_info import Statevector

    s = RQMState.zero()
    sv = s.as_qiskit_statevector()
    expected = Statevector([1.0, 0.0])
    assert sv.equiv(expected)


# ---------------------------------------------------------------------------
# pretty() and __repr__
# ---------------------------------------------------------------------------


def test_pretty_returns_string():
    assert isinstance(RQMState.zero().pretty(), str)


def test_repr_contains_alpha_beta():
    r = repr(RQMState.zero())
    assert "alpha" in r
    assert "beta" in r


# ---------------------------------------------------------------------------
# Invalid inputs
# ---------------------------------------------------------------------------


def test_invalid_state_not_a_number():
    with pytest.raises((TypeError, ValueError)):
        RQMState("not", "numbers")  # type: ignore[arg-type]
