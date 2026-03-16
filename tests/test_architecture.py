"""
Architecture tests: confirm that rqm-qiskit delegates math to rqm-core.

These tests validate the structural requirement that rqm-qiskit is a pure
Qiskit bridge layer with no duplicated quaternion, spinor, or Bloch math.
"""

import math
import numpy as np

from rqm_core.quaternion import Quaternion as CoreQuaternion


# ---------------------------------------------------------------------------
# Quaternion compatibility: rqm-qiskit shim wraps rqm-core
# ---------------------------------------------------------------------------


def test_quaternion_from_package_import():
    """from rqm_qiskit import Quaternion must work."""
    from rqm_qiskit import Quaternion

    q = Quaternion(1.0, 0.0, 0.0, 0.0)
    assert q.w == 1.0


def test_quaternion_from_module_import():
    """from rqm_qiskit.quaternion import Quaternion must work."""
    from rqm_qiskit.quaternion import Quaternion

    q = Quaternion.identity()
    assert math.isclose(q.norm(), 1.0, abs_tol=1e-10)


def test_quaternion_is_subclass_of_core():
    """rqm_qiskit.Quaternion must be a subclass of rqm_core.Quaternion."""
    from rqm_qiskit import Quaternion

    assert issubclass(Quaternion, CoreQuaternion)


def test_quaternion_instance_is_core_type():
    """An rqm_qiskit Quaternion instance is also an rqm_core Quaternion."""
    from rqm_qiskit import Quaternion

    q = Quaternion.from_axis_angle("y", 1.0)
    assert isinstance(q, CoreQuaternion)


def test_quaternion_core_methods_work():
    """Inherited core methods (from_axis_angle, to_su2_matrix, etc.) work."""
    from rqm_qiskit import Quaternion

    q = Quaternion.from_axis_angle("x", math.pi / 2)
    mat = q.to_su2_matrix()
    assert mat.shape == (2, 2)
    assert np.allclose(mat.conj().T @ mat, np.eye(2), atol=1e-12)


# ---------------------------------------------------------------------------
# Spinor logic comes from rqm-core
# ---------------------------------------------------------------------------


def test_rqmstate_uses_rqm_core_spinor_norm():
    """RQMState.norm() must delegate to rqm_core.spinor.spinor_norm."""
    from rqm_qiskit import RQMState
    from rqm_core.spinor import spinor_norm

    state = RQMState.plus()
    alpha, beta = state.vector()
    assert math.isclose(state.norm(), spinor_norm(alpha, beta), abs_tol=1e-12)


def test_rqmstate_normalization_matches_rqm_core():
    """RQMState normalization must produce the same result as rqm_core.spinor."""
    from rqm_qiskit import RQMState
    from rqm_core.spinor import normalize_spinor

    raw_alpha, raw_beta = 3.0 + 0j, 4.0 + 0j
    state = RQMState(raw_alpha, raw_beta)
    core_alpha, core_beta = normalize_spinor(raw_alpha, raw_beta)

    assert math.isclose(abs(state.alpha), abs(core_alpha), abs_tol=1e-12)
    assert math.isclose(abs(state.beta), abs(core_beta), abs_tol=1e-12)


def test_rqmstate_to_quaternion_matches_rqm_core():
    """RQMState.to_quaternion() result must match rqm_core.spinor.spinor_to_quaternion."""
    from rqm_qiskit import RQMState
    from rqm_core.spinor import spinor_to_quaternion

    for state in [RQMState.zero(), RQMState.one(), RQMState.plus(), RQMState.minus()]:
        q_bridge = state.to_quaternion()
        q_core = spinor_to_quaternion(state.alpha, state.beta)
        assert math.isclose(q_bridge.w, q_core.w, abs_tol=1e-12)
        assert math.isclose(q_bridge.x, q_core.x, abs_tol=1e-12)
        assert math.isclose(q_bridge.y, q_core.y, abs_tol=1e-12)
        assert math.isclose(q_bridge.z, q_core.z, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# Bloch logic comes from rqm-core
# ---------------------------------------------------------------------------


def test_rqmstate_bloch_vector_matches_rqm_core():
    """RQMState.bloch_vector() must match rqm_core.bloch.state_to_bloch."""
    from rqm_qiskit import RQMState
    from rqm_core.bloch import state_to_bloch

    for state in [RQMState.zero(), RQMState.one(), RQMState.plus(), RQMState.minus()]:
        bv_bridge = state.bloch_vector()
        bv_core = state_to_bloch(state.alpha, state.beta)
        assert np.allclose(bv_bridge, bv_core, atol=1e-12)


def test_rqmstate_from_bloch_matches_rqm_core():
    """RQMState.from_bloch() must produce a state consistent with rqm_core.bloch."""
    from rqm_qiskit import RQMState
    from rqm_core.bloch import bloch_to_state

    for theta, phi in [(0.0, 0.0), (math.pi, 0.0), (math.pi / 2, math.pi / 3)]:
        state = RQMState.from_bloch(theta, phi)
        core_alpha, core_beta = bloch_to_state(theta, phi)
        # Compare amplitudes up to global phase via absolute values
        assert math.isclose(abs(state.alpha), abs(core_alpha), abs_tol=1e-10)
        assert math.isclose(abs(state.beta), abs(core_beta), abs_tol=1e-10)


# ---------------------------------------------------------------------------
# SU(2) / gate matrix comes from rqm-core
# ---------------------------------------------------------------------------


def test_rqmgate_matrix_matches_rqm_core():
    """RQMGate.to_matrix() must match rqm_core.su2.axis_angle_to_su2."""
    from rqm_qiskit import RQMGate
    from rqm_core.su2 import axis_angle_to_su2

    for axis, angle in [("x", 1.2), ("y", 0.8), ("z", 2.1)]:
        gate = RQMGate(axis, angle)
        mat_bridge = gate.to_matrix()
        mat_core = axis_angle_to_su2(axis, angle)
        assert np.allclose(mat_bridge, mat_core, atol=1e-12)


# ---------------------------------------------------------------------------
# No local math duplication: utils.py must not contain spinor normalize
# ---------------------------------------------------------------------------


def test_utils_has_no_duplicate_normalize():
    """utils.py must not contain a local normalize function that duplicates rqm-core."""
    import rqm_qiskit.utils as utils_module

    assert not hasattr(utils_module, "normalize"), (
        "rqm_qiskit.utils should not define a local normalize() "
        "that duplicates rqm_core.spinor.normalize_spinor."
    )
