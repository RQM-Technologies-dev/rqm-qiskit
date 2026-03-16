"""
Architecture tests: confirm that rqm-qiskit delegates math to rqm-core.

These tests validate the structural requirement that rqm-qiskit is a pure
Qiskit bridge layer with no duplicated quaternion, spinor, or Bloch math.
"""

import math
import tomllib
from pathlib import Path

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
# Dependency-boundary guard: pyproject.toml must declare rqm-core and rqm-compiler
# ---------------------------------------------------------------------------


def test_pyproject_depends_on_rqm_core():
    """rqm-qiskit must declare rqm-core as a dependency in pyproject.toml."""
    data = tomllib.loads(
        (Path(__file__).parent.parent / "pyproject.toml").read_text()
    )
    deps = data["project"]["dependencies"]
    assert any("rqm-core" in d for d in deps), (
        "pyproject.toml must list rqm-core as a dependency. "
        "rqm-qiskit is a bridge layer and must not re-implement core math."
    )


def test_pyproject_depends_on_rqm_compiler():
    """rqm-qiskit must declare rqm-compiler as a dependency in pyproject.toml."""
    data = tomllib.loads(
        (Path(__file__).parent.parent / "pyproject.toml").read_text()
    )
    deps = data["project"]["dependencies"]
    assert any("rqm-compiler" in d for d in deps), (
        "pyproject.toml must list rqm-compiler as a dependency. "
        "rqm-qiskit delegates canonical circuit/gate ownership to rqm-compiler."
    )


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


# ---------------------------------------------------------------------------
# rqm-compiler delegation: RQMGate → rqm_compiler.Operation
# ---------------------------------------------------------------------------


def test_rqmgate_to_operation_returns_compiler_operation():
    """RQMGate.to_operation() must return an rqm_compiler.Operation."""
    from rqm_qiskit import RQMGate
    from rqm_compiler import Operation

    for axis, angle in [("x", 1.2), ("y", 0.8), ("z", 2.1)]:
        gate = RQMGate(axis, angle)
        op = gate.to_operation(qubit=0)
        assert isinstance(op, Operation), (
            "RQMGate.to_operation() must return an rqm_compiler.Operation — "
            "gate ownership belongs to rqm-compiler."
        )


def test_rqmgate_to_operation_gate_name():
    """RQMGate.to_operation() gate name must follow the rqm-compiler canonical form."""
    from rqm_qiskit import RQMGate

    assert RQMGate.rx(1.0).to_operation().gate == "rx"
    assert RQMGate.ry(1.0).to_operation().gate == "ry"
    assert RQMGate.rz(1.0).to_operation().gate == "rz"


def test_rqmgate_to_operation_angle_param():
    """RQMGate.to_operation() must carry the rotation angle in params['angle']."""
    from rqm_qiskit import RQMGate

    angle = 1.23456
    op = RQMGate.ry(angle).to_operation(qubit=2)
    assert math.isclose(op.params["angle"], angle, abs_tol=1e-14)
    assert op.targets == [2]


# ---------------------------------------------------------------------------
# rqm-compiler delegation: RQMCircuit uses CompilerCircuit internally
# ---------------------------------------------------------------------------


def test_rqmcircuit_exposes_compiler_circuit():
    """RQMCircuit.compiler_circuit must return an rqm_compiler.Circuit."""
    from rqm_qiskit import RQMCircuit
    from rqm_compiler import Circuit

    circ = RQMCircuit(1)
    assert isinstance(circ.compiler_circuit, Circuit), (
        "RQMCircuit.compiler_circuit must be an rqm_compiler.Circuit — "
        "canonical circuit ownership belongs to rqm-compiler."
    )


def test_rqmcircuit_apply_gate_adds_to_compiler_circuit():
    """RQMCircuit.apply_gate() must delegate to rqm-compiler Circuit."""
    from rqm_qiskit import RQMCircuit, RQMGate

    circ = RQMCircuit(1)
    assert len(circ.compiler_circuit) == 0

    circ.apply_gate(RQMGate.ry(0.5))
    assert len(circ.compiler_circuit) == 1

    op = circ.compiler_circuit.operations[0]
    assert op.gate == "ry"
    assert math.isclose(op.params["angle"], 0.5, abs_tol=1e-14)


def test_rqmcircuit_measure_all_adds_to_compiler_circuit():
    """RQMCircuit.measure_all() must add measure operations to the compiler circuit."""
    from rqm_qiskit import RQMCircuit

    circ = RQMCircuit(2)
    circ.measure_all()
    gates = [op.gate for op in circ.compiler_circuit.operations]
    assert gates.count("measure") == 2, (
        "measure_all() on a 2-qubit circuit must add 2 measure operations "
        "to the underlying rqm-compiler Circuit."
    )


# ---------------------------------------------------------------------------
# compiled_circuit_to_qiskit: the bridge translation function
# ---------------------------------------------------------------------------


def test_compiled_circuit_to_qiskit_accepts_circuit():
    """compiled_circuit_to_qiskit must accept an rqm_compiler.Circuit."""
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit import QuantumCircuit

    c = Circuit(1)
    c.ry(0, math.pi / 2)
    qc = compiled_circuit_to_qiskit(c)
    assert isinstance(qc, QuantumCircuit)
    assert qc.num_qubits == 1
    assert len(qc.data) > 0


def test_compiled_circuit_to_qiskit_accepts_compiled_circuit():
    """compiled_circuit_to_qiskit must accept an rqm_compiler.CompiledCircuit."""
    from rqm_compiler import Circuit, compile_circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit
    from qiskit import QuantumCircuit

    c = Circuit(1)
    c.rz(0, 1.0)
    compiled = compile_circuit(c)
    qc = compiled_circuit_to_qiskit(compiled)
    assert isinstance(qc, QuantumCircuit)
    assert len(qc.data) > 0


def test_compiled_circuit_to_qiskit_measure_adds_clbits():
    """compiled_circuit_to_qiskit must add classical bits for measure operations."""
    from rqm_compiler import Circuit
    from rqm_qiskit.convert import compiled_circuit_to_qiskit

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    qc = compiled_circuit_to_qiskit(c)
    assert qc.num_clbits >= 1
