"""
Tests for spinor_embed – the spinor-to-quaternion embedding re-exported
from rqm_core.spinor via the rqm-qiskit bridge layer.

spinor_embed(α, β) maps a quantum state spinor to a unit quaternion,
cleanly separating the spinor embedding operation from state-preparation
rotation semantics.
"""

import math
import pytest
import numpy as np

from rqm_qiskit import spinor_embed, Quaternion, RQMState
from rqm_core.spinor import spinor_to_quaternion


# ---------------------------------------------------------------------------
# Import path validation
# ---------------------------------------------------------------------------


def test_spinor_embed_importable_from_rqm_qiskit():
    """spinor_embed must be importable from the rqm_qiskit top-level namespace."""
    from rqm_qiskit import spinor_embed as se
    assert callable(se)


def test_spinor_embed_importable_from_rqm_qiskit_state():
    """spinor_embed must also be importable from rqm_qiskit.state."""
    from rqm_qiskit.state import spinor_embed as se
    assert callable(se)


def test_spinor_embed_delegates_to_rqm_core():
    """spinor_embed must produce the same result as rqm_core.spinor.spinor_to_quaternion."""
    alpha, beta = 0.6 + 0j, 0.8 + 0j
    q_embed = spinor_embed(alpha, beta)
    q_core = spinor_to_quaternion(alpha, beta)
    assert math.isclose(q_embed.w, q_core.w, abs_tol=1e-12)
    assert math.isclose(q_embed.x, q_core.x, abs_tol=1e-12)
    assert math.isclose(q_embed.y, q_core.y, abs_tol=1e-12)
    assert math.isclose(q_embed.z, q_core.z, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# Basic properties
# ---------------------------------------------------------------------------


def test_spinor_embed_returns_quaternion():
    from rqm_core.quaternion import Quaternion as CoreQ
    q = spinor_embed(1.0 + 0j, 0.0 + 0j)
    assert isinstance(q, CoreQ)


def test_spinor_embed_returns_unit_quaternion():
    """The embedded quaternion must always be a unit quaternion."""
    for alpha, beta in [
        (1.0, 0.0),
        (0.0, 1.0),
        (1.0 / math.sqrt(2), 1.0 / math.sqrt(2)),
        (0.6, 0.8),
        (0.5 + 0.5j, 0.5 - 0.5j),
    ]:
        q = spinor_embed(complex(alpha), complex(beta))
        assert math.isclose(q.norm(), 1.0, abs_tol=1e-10), (
            f"spinor_embed({alpha}, {beta}) returned non-unit quaternion"
        )


def test_spinor_embed_normalizes_input():
    """spinor_embed should normalize the spinor before embedding."""
    # Unnormalized spinor (norm = 5)
    q_raw = spinor_embed(3.0 + 0j, 4.0 + 0j)
    # Normalized spinor (norm = 1)
    q_norm = spinor_embed(0.6 + 0j, 0.8 + 0j)
    assert math.isclose(q_raw.w, q_norm.w, abs_tol=1e-12)
    assert math.isclose(q_raw.x, q_norm.x, abs_tol=1e-12)
    assert math.isclose(q_raw.y, q_norm.y, abs_tol=1e-12)
    assert math.isclose(q_raw.z, q_norm.z, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# State-specific checks
# ---------------------------------------------------------------------------


def test_spinor_embed_zero_state_is_identity():
    """The |0⟩ spinor (1, 0) should embed to the identity quaternion."""
    q = spinor_embed(1.0 + 0j, 0.0 + 0j)
    assert math.isclose(q.w, 1.0, abs_tol=1e-10)
    assert math.isclose(q.x, 0.0, abs_tol=1e-10)
    assert math.isclose(q.y, 0.0, abs_tol=1e-10)
    assert math.isclose(q.z, 0.0, abs_tol=1e-10)


def test_spinor_embed_one_state():
    """The |1⟩ spinor (0, 1) should embed to (0, 0, 1, 0) quaternion."""
    q = spinor_embed(0.0 + 0j, 1.0 + 0j)
    assert math.isclose(q.w, 0.0, abs_tol=1e-10)
    assert math.isclose(q.y, 1.0, abs_tol=1e-10)


def test_spinor_embed_matches_rqmstate_to_quaternion():
    """spinor_embed(α, β) must match RQMState.to_quaternion() for all basis states."""
    for state in [RQMState.zero(), RQMState.one(), RQMState.plus(), RQMState.minus()]:
        alpha, beta = state.vector()
        q_embed = spinor_embed(alpha, beta)
        q_state = state.to_quaternion()
        assert math.isclose(q_embed.w, q_state.w, abs_tol=1e-12)
        assert math.isclose(q_embed.x, q_state.x, abs_tol=1e-12)
        assert math.isclose(q_embed.y, q_state.y, abs_tol=1e-12)
        assert math.isclose(q_embed.z, q_state.z, abs_tol=1e-12)


def test_spinor_embed_zero_spinor_raises():
    """spinor_embed with zero amplitude should raise ValueError."""
    with pytest.raises(ValueError):
        spinor_embed(0.0 + 0j, 0.0 + 0j)
