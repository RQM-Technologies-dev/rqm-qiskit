"""The released science stack must preserve composable operators at the bridge."""

import json
import math

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
from rqm_compiler import Circuit, compile_circuit

from rqm_qiskit import compiled_circuit_to_qiskit, to_qiskit_circuit


@pytest.mark.parametrize("axis", ["rx", "ry", "rz"])
@pytest.mark.parametrize("angles", [(2 * math.pi,), (-2 * math.pi,), (math.pi, math.pi), (0.23, -0.11)])
@pytest.mark.parametrize("optimize", [False, True])
def test_rotation_json_lowering_preserves_exact_operator(axis, angles, optimize):
    source, expected = Circuit(1), QuantumCircuit(1)
    for angle in angles:
        getattr(source, axis)(0, angle)
        getattr(expected, axis)(angle, 0)
    restored = Circuit.from_descriptors(
        json.loads(json.dumps(source.to_descriptors())), num_qubits=1
    )
    actual = to_qiskit_circuit(restored, optimize=optimize)
    np.testing.assert_allclose(Operator(actual).data, Operator(expected).data, atol=1e-10, rtol=0)
    np.testing.assert_allclose(
        Operator(actual.to_gate().control()).data,
        Operator(expected.to_gate().control()).data,
        atol=1e-10, rtol=0,
    )


@pytest.mark.parametrize("gate", ["x", "y", "z", "h", "s", "t", "phaseshift"])
def test_named_u2_gates_retain_scalar_phase_after_optimization(gate):
    source, expected = Circuit(1), QuantumCircuit(1)
    if gate == "phaseshift":
        source.phaseshift(0, 0.27)
        expected.p(0.27, 0)
    else:
        getattr(source, gate)(0)
        getattr(expected, gate)(0)
    source.rx(0, 0.21)
    expected.rx(0.21, 0)
    actual = to_qiskit_circuit(source, optimize=True)
    np.testing.assert_allclose(Operator(actual).data, Operator(expected).data, atol=1e-10, rtol=0)


@pytest.mark.parametrize("compiled", [False, True])
def test_signed_quaternion_survives_controlled_reuse(compiled):
    source = Circuit(1).u1q(0, w=-1.0, x=0.0, y=0.0, z=0.0)
    source = compile_circuit(source) if compiled else source
    lowered = compiled_circuit_to_qiskit(source)
    np.testing.assert_allclose(Operator(lowered).data, -np.eye(2), atol=1e-12, rtol=0)
    interferometer = QuantumCircuit(2)
    interferometer.h(0)
    interferometer.append(lowered.to_gate().control(), [0, 1])
    interferometer.h(0)
    probabilities = Statevector.from_instruction(interferometer).probabilities([0])
    np.testing.assert_allclose(probabilities, [0.0, 1.0], atol=1e-10, rtol=0)
