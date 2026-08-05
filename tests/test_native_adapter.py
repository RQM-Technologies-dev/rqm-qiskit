from __future__ import annotations

import gc
import math
import sys

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Gate, Parameter
from qiskit.quantum_info import Operator
from rqm_compiler import Circuit

import rqm_qiskit._accelerator as accelerator
from rqm_qiskit import compiled_circuit_to_qiskit, import_qiskit_circuit


requires_native = pytest.mark.skipif(
    not accelerator.native_build_info()["available"],
    reason="optional native adapter was not built",
)


def _reference_import(circuit: QuantumCircuit, monkeypatch):
    monkeypatch.setattr(accelerator, "_NATIVE_AVAILABLE", False)
    return import_qiskit_circuit(circuit)


def _native_import(circuit: QuantumCircuit, monkeypatch):
    monkeypatch.setattr(accelerator, "_NATIVE_AVAILABLE", True)
    return import_qiskit_circuit(circuit)


@pytest.mark.parametrize(
    "angles",
    [
        (0.0, 0.0, 0.0),
        (math.pi, -math.pi / 2, 2 * math.pi),
        (-0.0, 1e-12, -1e-12),
        (0.31, -0.47, 1.19),
    ],
)
@requires_native
def test_native_import_matches_reference_for_noncommuting_chains(
    angles: tuple[float, float, float], monkeypatch
) -> None:
    circuit = QuantumCircuit(1)
    circuit.rz(angles[0], 0)
    circuit.ry(angles[1], 0)
    circuit.rx(angles[2], 0)
    circuit.p(-angles[0], 0)

    reference = _reference_import(circuit, monkeypatch)
    native = _native_import(circuit, monkeypatch)

    assert native.circuit.to_descriptors() == reference.circuit.to_descriptors()
    assert native.report.to_dict() == reference.report.to_dict()


@pytest.mark.parametrize(
    "builder",
    [
        lambda: QuantumCircuit(2),
        lambda: QuantumCircuit(1, 1),
        lambda: QuantumCircuit(1, global_phase=0.25),
    ],
)
@requires_native
def test_ineligible_circuits_keep_reference_report(builder, monkeypatch) -> None:
    circuit = builder()
    reference = _reference_import(circuit, monkeypatch)
    native_enabled = _native_import(circuit, monkeypatch)

    if reference.circuit is None:
        assert native_enabled.circuit is None
    else:
        assert native_enabled.circuit is not None
        assert (
            native_enabled.circuit.to_descriptors()
            == reference.circuit.to_descriptors()
        )
    assert native_enabled.report.to_dict() == reference.report.to_dict()


@requires_native
def test_symbolic_and_nonfinite_parameters_keep_reference_report(monkeypatch) -> None:
    symbolic = QuantumCircuit(1)
    symbolic.rx(Parameter("theta"), 0)
    nonfinite = QuantumCircuit(1)
    nonfinite.rx(float("nan"), 0)

    for circuit in (symbolic, nonfinite):
        reference = _reference_import(circuit, monkeypatch)
        native_enabled = _native_import(circuit, monkeypatch)
        assert native_enabled.circuit == reference.circuit
        assert native_enabled.report.to_dict() == reference.report.to_dict()


@requires_native
def test_custom_instruction_keeps_reference_report(monkeypatch) -> None:
    circuit = QuantumCircuit(1)
    circuit.append(Gate("custom_probe", 1, []), [0])

    reference = _reference_import(circuit, monkeypatch)
    native_enabled = _native_import(circuit, monkeypatch)

    assert native_enabled.circuit is None
    assert native_enabled.report.to_dict() == reference.report.to_dict()


@pytest.mark.parametrize(
    "quaternion",
    [
        (1.0, 0.0, 0.0, 0.0),
        (0.5, 0.5, 0.5, 0.5),
        (-0.5, -0.5, -0.5, -0.5),
    ],
)
@requires_native
def test_native_lowering_matches_reference_and_registers(
    quaternion: tuple[float, float, float, float], monkeypatch
) -> None:
    circuit = Circuit(1)
    circuit.u1q(0, *quaternion)

    monkeypatch.setattr(accelerator, "_NATIVE_AVAILABLE", False)
    reference = compiled_circuit_to_qiskit(circuit)
    monkeypatch.setattr(accelerator, "_NATIVE_AVAILABLE", True)
    native = compiled_circuit_to_qiskit(circuit)

    assert Operator(native).equiv(Operator(reference))
    assert [register.name for register in native.qregs] == ["q"]
    assert [register.size for register in native.qregs] == [1]
    assert native.num_clbits == reference.num_clbits == 0


@requires_native
def test_native_lowering_returns_fresh_mutation_isolated_circuits() -> None:
    circuit = Circuit(1)
    circuit.u1q(0, 0.5, 0.5, 0.5, 0.5)

    first = compiled_circuit_to_qiskit(circuit)
    second = compiled_circuit_to_qiskit(circuit)
    first.x(0)

    assert first is not second
    assert first.qubits[0] is not second.qubits[0]
    assert len(first.data) == len(second.data) + 1


@requires_native
def test_normal_mode_falls_back_after_native_fault(monkeypatch) -> None:
    circuit = QuantumCircuit(1)
    circuit.rx(0.25, 0)

    def fail(_value):
        raise RuntimeError("injected native fault")

    monkeypatch.setattr(accelerator._native, "extract_1q_operations", fail)
    result = import_qiskit_circuit(circuit)

    assert result.report.status == "SUPPORTED"
    assert result.circuit is not None


@requires_native
def test_evidence_mode_fails_loudly_after_native_fault(monkeypatch) -> None:
    circuit = QuantumCircuit(1)
    circuit.rx(0.25, 0)

    def fail(_value):
        raise RuntimeError("injected native fault")

    monkeypatch.setenv("RQM_QISKIT_REQUIRE_NATIVE", "1")
    monkeypatch.setattr(accelerator._native, "extract_1q_operations", fail)

    with pytest.raises(RuntimeError, match="Native one-qubit import failed"):
        import_qiskit_circuit(circuit)


def test_evidence_mode_rejects_missing_native_capability(monkeypatch) -> None:
    circuit = QuantumCircuit(1)
    circuit.x(0)
    monkeypatch.setenv("RQM_QISKIT_REQUIRE_NATIVE", "1")
    monkeypatch.setattr(accelerator, "_NATIVE_AVAILABLE", False)

    with pytest.raises(RuntimeError, match="capability is unavailable"):
        import_qiskit_circuit(circuit)


@requires_native
def test_native_calls_do_not_retain_input_objects() -> None:
    circuit = QuantumCircuit(1)
    circuit.rz(0.2, 0)
    circuit.ry(-0.4, 0)
    before = sys.getrefcount(circuit)

    for _ in range(2_000):
        result = accelerator.extract_1q_operations(circuit)
        assert result is not None
    del result
    gc.collect()

    assert sys.getrefcount(circuit) == before


@requires_native
def test_native_q_and_minus_q_remain_global_phase_equivalent() -> None:
    positive = Circuit(1)
    negative = Circuit(1)
    positive.u1q(0, 0.5, 0.5, 0.5, 0.5)
    negative.u1q(0, -0.5, -0.5, -0.5, -0.5)

    left = Operator(compiled_circuit_to_qiskit(positive)).data
    right = Operator(compiled_circuit_to_qiskit(negative)).data
    overlap = np.vdot(right.reshape(-1), left.reshape(-1))
    phase = overlap / abs(overlap)

    assert np.allclose(left, phase * right, atol=1e-12, rtol=1e-12)
