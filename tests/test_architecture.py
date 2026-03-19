"""
Architecture tests: confirm that rqm-qiskit delegates math to rqm-core.

These tests validate the structural requirement that rqm-qiskit is a pure
Qiskit bridge layer with no duplicated quaternion, spinor, or Bloch math.

Single-lowering-path invariant
------------------------------
The tests in the "Single lowering path" section below use
``unittest.mock.patch`` to intercept calls to ``compiled_circuit_to_qiskit``
and assert that every public gate/circuit lowering helper actually invokes it.
This is an introspection-level guard: even if a future refactor changes the
implementation it will trip these tests before the regression ships.
"""

import math
import tomllib
from pathlib import Path
from unittest.mock import patch, MagicMock

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


# ---------------------------------------------------------------------------
# Single lowering path: introspection-based invariant tests
#
# These tests use unittest.mock.patch to intercept calls to
# compiled_circuit_to_qiskit and verify that the public gate/circuit
# lowering helpers actually call it.  They are deliberately introspective
# rather than output-based so that a future refactor that breaks the routing
# will be caught before it ships, even if the outputs happen to be identical.
# ---------------------------------------------------------------------------


def test_gate_to_quantum_circuit_calls_compiled_circuit_to_qiskit():
    """gate_to_quantum_circuit MUST call compiled_circuit_to_qiskit internally.

    Patches the function inside the convert module and asserts it is invoked
    exactly once per call to gate_to_quantum_circuit.
    """
    from rqm_qiskit import RQMGate
    import rqm_qiskit.convert as convert_module

    for axis, angle in [("x", 1.2), ("y", 0.8), ("z", 2.1)]:
        gate = RQMGate(axis, angle)
        with patch.object(
            convert_module,
            "compiled_circuit_to_qiskit",
            wraps=convert_module.compiled_circuit_to_qiskit,
        ) as mock_fn:
            convert_module.gate_to_quantum_circuit(gate)
            assert mock_fn.call_count == 1, (
                f"gate_to_quantum_circuit (axis={axis}) must call "
                f"compiled_circuit_to_qiskit exactly once; "
                f"got {mock_fn.call_count} call(s).  "
                "This test guards the single-lowering-path invariant."
            )


def test_rqmcircuit_to_qiskit_calls_compiled_circuit_to_qiskit():
    """RQMCircuit.to_qiskit() MUST call compiled_circuit_to_qiskit internally.

    Patches the function inside the convert module and asserts it is invoked
    when to_qiskit() is called on an RQMCircuit that has gate operations.
    """
    from rqm_qiskit import RQMCircuit, RQMGate
    import rqm_qiskit.convert as convert_module

    circ = RQMCircuit(1)
    circ.apply_gate(RQMGate.ry(0.5))

    with patch.object(
        convert_module,
        "compiled_circuit_to_qiskit",
        wraps=convert_module.compiled_circuit_to_qiskit,
    ) as mock_fn:
        circ.to_qiskit()
        assert mock_fn.call_count >= 1, (
            "RQMCircuit.to_qiskit() must call compiled_circuit_to_qiskit; "
            f"got {mock_fn.call_count} call(s).  "
            "This test guards the single-lowering-path invariant."
        )


def test_state_to_quantum_circuit_does_not_call_compiled_circuit_to_qiskit():
    """state_to_quantum_circuit must NOT call compiled_circuit_to_qiskit.

    State preparation uses Qiskit's initialize instruction, which has no
    rqm-compiler IR equivalent.  It is the only documented exception to the
    single-lowering-path rule and must stay outside that path.
    """
    from rqm_qiskit import RQMState
    import rqm_qiskit.convert as convert_module

    with patch.object(
        convert_module,
        "compiled_circuit_to_qiskit",
        wraps=convert_module.compiled_circuit_to_qiskit,
    ) as mock_fn:
        convert_module.state_to_quantum_circuit(RQMState.plus())
        assert mock_fn.call_count == 0, (
            "state_to_quantum_circuit is the only documented exception to the "
            "single-lowering-path rule.  It must NOT call "
            f"compiled_circuit_to_qiskit; got {mock_fn.call_count} call(s)."
        )


# ---------------------------------------------------------------------------
# Meta-test: all public lowering entrypoints route through compiled_circuit_to_qiskit
#
# This test auto-discovers every public function in rqm_qiskit.convert and
# asserts that each one either:
#   (a) calls compiled_circuit_to_qiskit(), OR
#   (b) is explicitly listed in LOWERING_EXCEPTIONS.
#
# The value over the individual per-function tests above is automation:
# if a contributor adds a new public lowering helper without routing it
# through compiled_circuit_to_qiskit(), this test will fail immediately,
# even before any output-based test would notice.
# ---------------------------------------------------------------------------


def test_all_lowering_entrypoints_route_through_compiled():
    """Every public helper in rqm_qiskit.convert must call compiled_circuit_to_qiskit
    OR be explicitly listed in LOWERING_EXCEPTIONS.

    The test auto-discovers public functions at import time so it catches
    newly added helpers automatically.  To add a new helper:

    * If it routes through compiled_circuit_to_qiskit: add it to FIXTURES.
    * If it is a documented exception: add it to LOWERING_EXCEPTIONS with a
      comment explaining why.
    """
    import inspect
    import rqm_qiskit.convert as convert_module
    from rqm_qiskit import RQMGate, RQMState

    # The primary lowering function is the path itself — skip it.
    PRIMARY = "compiled_circuit_to_qiskit"

    # Documented exceptions: public helpers that intentionally do NOT call
    # compiled_circuit_to_qiskit, with the reason recorded here.
    #
    # state_to_quantum_circuit: uses Qiskit's `initialize` instruction, which
    #   has no rqm-compiler IR equivalent.  State preparation is inherently
    #   Qiskit-specific and cannot be expressed as an rqm_compiler.Operation.

    LOWERING_EXCEPTIONS: frozenset[str] = frozenset({"state_to_quantum_circuit"})

    # Minimal valid argument fixtures so we can actually call each helper.
    # Add an entry here whenever a new public lowering helper is introduced.
    FIXTURES: dict[str, tuple] = {
        "gate_to_quantum_circuit": (RQMGate.rx(1.0),),
        "state_to_quantum_circuit": (RQMState.plus(),),
    }

    # --- Discover all public helpers (excluding PRIMARY itself) ---
    public_helpers = [
        name
        for name, obj in inspect.getmembers(convert_module, inspect.isfunction)
        if not name.startswith("_") and name != PRIMARY
    ]

    # --- Guard: any new helper must be registered in FIXTURES or EXCEPTIONS ---
    missing = [
        name
        for name in public_helpers
        if name not in FIXTURES and name not in LOWERING_EXCEPTIONS
    ]
    assert not missing, (
        "New public function(s) detected in rqm_qiskit.convert that are not yet "
        "covered by test_all_lowering_entrypoints_route_through_compiled: "
        f"{missing}. "
        "Add each to FIXTURES (if it must route through compiled_circuit_to_qiskit) "
        "or to LOWERING_EXCEPTIONS (if it is a documented exception to the rule)."
    )

    # --- Assert each non-exception helper calls the primary lowering path ---
    for name in public_helpers:
        if name in LOWERING_EXCEPTIONS:
            continue
        fn = getattr(convert_module, name)
        args = FIXTURES[name]
        with patch.object(
            convert_module,
            PRIMARY,
            wraps=getattr(convert_module, PRIMARY),
        ) as mock_fn:
            fn(*args)
            assert mock_fn.call_count >= 1, (
                f"rqm_qiskit.convert.{name}() must call {PRIMARY}() "
                f"(got {mock_fn.call_count} call(s)). "
                f"Either fix the routing or add '{name}' to LOWERING_EXCEPTIONS "
                "with a documented reason."
            )


# ---------------------------------------------------------------------------
# New rqm-core capabilities: named gate quaternions (rqm_core.gates)
# ---------------------------------------------------------------------------


def test_gate_factories_come_from_rqm_core():
    """Named gate factories must be imported from rqm_core.gates, not defined locally."""
    import rqm_qiskit.gates as gates_module
    from rqm_core.gates import gate_h as core_gate_h

    # The gate_h in rqm_qiskit.gates must be the same object as in rqm_core.gates
    assert gates_module.gate_h is core_gate_h, (
        "rqm_qiskit.gates.gate_h must re-export rqm_core.gates.gate_h, "
        "not define its own copy.  Named gate math belongs in rqm-core."
    )


def test_match_gate_comes_from_rqm_core():
    """match_gate must be imported from rqm_core.gates, not defined locally."""
    import rqm_qiskit.gates as gates_module
    from rqm_core.gates import match_gate as core_match_gate

    assert gates_module.match_gate is core_match_gate, (
        "rqm_qiskit.gates.match_gate must re-export rqm_core.gates.match_gate."
    )


def test_gate_rx_factory_produces_correct_su2():
    """gate_rx from rqm-core must match RQMGate.rx matrix (architecture consistency)."""
    from rqm_qiskit import RQMGate, gate_rx
    import numpy as np

    for angle in [0.0, 0.5, math.pi / 2, math.pi]:
        assert np.allclose(
            gate_rx(angle).to_su2_matrix(),
            RQMGate.rx(angle).to_matrix(),
            atol=1e-12,
        ), f"gate_rx({angle}) mismatches RQMGate.rx({angle}).to_matrix()"


# ---------------------------------------------------------------------------
# New rqm-core capabilities: spinor_embed
# ---------------------------------------------------------------------------


def test_spinor_embed_comes_from_rqm_core():
    """spinor_embed must be the same function as rqm_core.spinor.spinor_embed."""
    from rqm_qiskit.state import spinor_embed as bridge_embed
    from rqm_core.spinor import spinor_embed as core_embed

    assert bridge_embed is core_embed, (
        "rqm_qiskit.state.spinor_embed must re-export rqm_core.spinor.spinor_embed, "
        "not define its own copy.  Spinor embedding belongs in rqm-core."
    )


# ---------------------------------------------------------------------------
# New rqm-core capabilities: Quaternion extended methods
# ---------------------------------------------------------------------------


def test_quaternion_from_axis_angle_vec_inherited_from_rqm_core():
    """Quaternion.from_axis_angle_vec must be inherited from rqm-core, not defined in bridge."""
    from rqm_qiskit import Quaternion
    from rqm_core.quaternion import Quaternion as CoreQ

    # from_axis_angle_vec must exist and must not be overridden in the bridge class
    assert "from_axis_angle_vec" not in Quaternion.__dict__, (
        "from_axis_angle_vec must NOT be defined in rqm_qiskit.Quaternion directly. "
        "It belongs in rqm_core.Quaternion and should be inherited."
    )
    assert hasattr(Quaternion, "from_axis_angle_vec"), (
        "Quaternion.from_axis_angle_vec must be accessible (inherited from rqm-core)."
    )
    assert hasattr(CoreQ, "from_axis_angle_vec"), (
        "rqm_core.Quaternion must define from_axis_angle_vec."
    )


def test_quaternion_to_axis_angle_inherited_from_rqm_core():
    """Quaternion.to_axis_angle must be inherited from rqm-core."""
    from rqm_qiskit import Quaternion

    assert "to_axis_angle" not in Quaternion.__dict__, (
        "to_axis_angle must NOT be defined in rqm_qiskit.Quaternion directly."
    )
    assert hasattr(Quaternion, "to_axis_angle")


def test_quaternion_canonicalize_inherited_from_rqm_core():
    """Quaternion.canonicalize must be inherited from rqm-core."""
    from rqm_qiskit import Quaternion

    assert "canonicalize" not in Quaternion.__dict__, (
        "canonicalize must NOT be defined in rqm_qiskit.Quaternion directly."
    )
    assert hasattr(Quaternion, "canonicalize")


def test_quaternion_rotate_vector_inherited_from_rqm_core():
    """Quaternion.rotate_vector must be inherited from rqm-core."""
    from rqm_qiskit import Quaternion

    assert "rotate_vector" not in Quaternion.__dict__, (
        "rotate_vector must NOT be defined in rqm_qiskit.Quaternion directly."
    )
    assert hasattr(Quaternion, "rotate_vector")


def test_quaternion_ecosystem_convention_w_nonneg():
    """The w ≥ 0 canonical convention must be enforced by rqm-core's canonicalize."""
    from rqm_qiskit import Quaternion

    q = Quaternion(-0.5, -0.5, -0.5, -0.5).normalize()
    assert q.w < 0.0
    q_canon = q.canonicalize()
    assert q_canon.w >= 0.0, "canonicalize() must produce w ≥ 0 representative"
