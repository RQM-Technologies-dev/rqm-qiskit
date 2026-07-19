"""Target-local candidate synthesis for internal quaternion-Cartan blocks."""

from __future__ import annotations

import io
import math
import time
from collections.abc import Callable
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from qiskit import QuantumCircuit, qpy, transpile
from qiskit.circuit.library import CXGate, RZZGate, UnitaryGate
from qiskit.quantum_info import Operator
from qiskit.synthesis import (
    OneQubitEulerDecomposer,
    TwoQubitBasisDecomposer,
    TwoQubitControlledUDecomposer,
)
from qiskit.transpiler import Target
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from rqm_entanglement import (
    QuaternionCartanBlock,
    classify_su4,
    phase_aligned_operator_error,
    quaternion_to_su2_matrix,
)

SynthesisStrategy = Literal["best_native", "Q3", "QF", "QC", "QX", "RQ"]
_PATHS = ("Q3", "QF", "QC", "QX", "RQ")
_SEMANTIC_TOLERANCE = 1e-10
_ANGLE_TOLERANCE = 1e-12
_TRANSPILER_SEED = 12012009


def _source_circuit(unitary: NDArray[np.complex128]) -> QuantumCircuit:
    circuit = QuantumCircuit(2)
    circuit.append(UnitaryGate(np.asarray(unitary, dtype=np.complex128)), [0, 1])
    return circuit


def _transpile_candidate(
    circuit: QuantumCircuit,
    target: Target | None,
    *,
    optimization_level: int,
) -> QuantumCircuit:
    if target is None:
        return transpile(
            circuit,
            basis_gates=["rz", "sx", "x", "cx"],
            optimization_level=optimization_level,
            seed_transpiler=_TRANSPILER_SEED,
        )
    if target.num_qubits != 2:
        raise ValueError("SU(4) local synthesis currently requires a two-qubit target")
    manager = generate_preset_pass_manager(
        target=target,
        optimization_level=optimization_level,
        seed_transpiler=_TRANSPILER_SEED,
        approximation_degree=1.0,
        initial_layout=[0, 1],
    )
    return manager.run(circuit)


def _synthesize_q3(
    unitary: NDArray[np.complex128], target: Target | None
) -> tuple[QuantumCircuit, float, dict[str, Any]]:
    start = time.perf_counter_ns()
    circuit = _transpile_candidate(_source_circuit(unitary), target, optimization_level=3)
    return circuit, (time.perf_counter_ns() - start) / 1e9, {"optimization_level": 3}


def _synthesize_qf(
    unitary: NDArray[np.complex128], target: Target | None
) -> tuple[QuantumCircuit, float, dict[str, Any]]:
    if target is None or not _target_has(target, "rzz") or not _target_has(target, "rx"):
        raise ValueError("fractional target requires parameterized RX and RZZ support")
    start = time.perf_counter_ns()
    circuit = _transpile_candidate(_source_circuit(unitary), target, optimization_level=3)
    return circuit, (time.perf_counter_ns() - start) / 1e9, {"fractional_target": True}


def _synthesize_qc(
    unitary: NDArray[np.complex128], target: Target | None
) -> tuple[QuantumCircuit, float, dict[str, Any]]:
    if target is not None and not _target_has(target, "rzz"):
        raise ValueError("controlled-U/RZZ synthesis requires target RZZ support")
    start = time.perf_counter_ns()
    pre_native = TwoQubitControlledUDecomposer(RZZGate)(unitary)
    circuit = _transpile_candidate(pre_native, target, optimization_level=3)
    return (
        circuit,
        (time.perf_counter_ns() - start) / 1e9,
        {"decomposer": "TwoQubitControlledUDecomposer(RZZGate)"},
    )


def _synthesize_qx(
    unitary: NDArray[np.complex128], target: Target | None
) -> tuple[QuantumCircuit, float, dict[str, Any]]:
    start = time.perf_counter_ns()
    pre_native = TwoQubitBasisDecomposer(CXGate(), basis_fidelity=1.0, euler_basis="ZSX")(
        unitary, approximate=False
    )
    circuit = _transpile_candidate(pre_native, target, optimization_level=3)
    return (
        circuit,
        (time.perf_counter_ns() - start) / 1e9,
        {"decomposer": "TwoQubitBasisDecomposer(CXGate)"},
    )


def _append_local(
    destination: QuantumCircuit,
    quaternion: tuple[float, float, float, float],
    qubit: int,
) -> None:
    local = OneQubitEulerDecomposer("ZSX")(quaternion_to_su2_matrix(quaternion))
    destination.compose(local, qubits=[qubit], inplace=True)


def _basis_before(circuit: QuantumCircuit, axis: str) -> None:
    if axis == "x":
        circuit.h(0)
        circuit.h(1)
    elif axis == "y":
        circuit.sdg(0)
        circuit.h(0)
        circuit.sdg(1)
        circuit.h(1)
    elif axis != "z":
        raise ValueError(f"unsupported Pauli axis: {axis}")


def _basis_after(circuit: QuantumCircuit, axis: str) -> None:
    if axis == "x":
        circuit.h(0)
        circuit.h(1)
    elif axis == "y":
        circuit.h(0)
        circuit.s(0)
        circuit.h(1)
        circuit.s(1)
    elif axis != "z":
        raise ValueError(f"unsupported Pauli axis: {axis}")


def _append_positive_rzz_interaction(
    circuit: QuantumCircuit, axis: str, coefficient: float
) -> None:
    if abs(coefficient) <= _ANGLE_TOLERANCE:
        return
    requested_angle = -2.0 * float(coefficient)
    positive_angle = abs(requested_angle)
    if not (_ANGLE_TOLERANCE < positive_angle <= math.pi / 2.0 + _ANGLE_TOLERANCE):
        raise ValueError(f"Cartan {axis} interaction requires unsupported RZZ angle")
    _basis_before(circuit, axis)
    if requested_angle < 0.0:
        circuit.x(0)
    circuit.rzz(positive_angle, 0, 1)
    if requested_angle < 0.0:
        circuit.x(0)
    _basis_after(circuit, axis)


def direct_rq_circuit(block: QuaternionCartanBlock) -> QuantumCircuit:
    """Build the exact direct RQ shell/core candidate without generic unitary gates."""
    circuit = QuantumCircuit(2, name="RQ-quaternion-Cartan")
    _append_local(circuit, block.right_q0, 0)
    _append_local(circuit, block.right_q1, 1)
    for axis, coefficient in zip(("x", "y", "z"), block.cartan, strict=True):
        _append_positive_rzz_interaction(circuit, axis, coefficient)
    _append_local(circuit, block.left_q0, 0)
    _append_local(circuit, block.left_q1, 1)
    circuit.global_phase += block.global_phase
    return circuit


def _synthesize_rq(
    block: QuaternionCartanBlock, target: Target | None
) -> tuple[QuantumCircuit, float, dict[str, Any]]:
    start = time.perf_counter_ns()
    pre_native = direct_rq_circuit(block)
    positive_angles = [
        float(item.operation.params[0])
        for item in pre_native.data
        if item.operation.name == "rzz"
    ]
    circuit = (
        _transpile_candidate(pre_native, target, optimization_level=1)
        if target is not None
        else pre_native
    )
    return (
        circuit,
        (time.perf_counter_ns() - start) / 1e9,
        {
            "positive_fractional_rzz_only": True,
            "pre_native_rzz_angles": positive_angles,
        },
    )


def _target_has(target: Target, name: str) -> bool:
    return name in target.operation_names


def _target_compatibility(circuit: QuantumCircuit, target: Target | None) -> dict[str, Any]:
    if target is None:
        return {"compatible": True, "unsupported": []}
    unsupported: list[dict[str, Any]] = []
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in {"barrier", "delay"}:
            continue
        qargs = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        try:
            supported = target.instruction_supported(name, qargs)
        except (KeyError, TypeError):
            supported = False
        if not supported:
            unsupported.append({"name": name, "qubits": list(qargs)})
    return {"compatible": not unsupported, "unsupported": unsupported}


def _scheduled_duration(circuit: QuantumCircuit, target: Target | None) -> float | None:
    if target is None:
        return None
    total = 0.0
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in {"barrier", "delay"}:
            continue
        qargs = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        try:
            properties = target[name][qargs]
        except (KeyError, TypeError):
            return None
        duration = getattr(properties, "duration", None)
        if duration is None:
            return None
        total += float(duration)
    return total


def _qpy_size(circuit: QuantumCircuit) -> int:
    buffer = io.BytesIO()
    qpy.dump(circuit, buffer)
    return len(buffer.getvalue())


def _semantic_error(
    source: NDArray[np.complex128], circuit: QuantumCircuit
) -> tuple[float, bool]:
    if circuit.num_qubits != 2:
        return math.inf, False
    candidate = np.asarray(Operator(circuit).data, dtype=np.complex128)
    error, _ = phase_aligned_operator_error(source, candidate)
    return error, error <= _SEMANTIC_TOLERANCE


def _candidate_metrics(
    path: str,
    source: NDArray[np.complex128],
    circuit: QuantumCircuit,
    target: Target | None,
    latency: float,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    compatibility = _target_compatibility(circuit, target)
    operator_error, semantic_valid = _semantic_error(source, circuit)
    two_qubit_count = sum(
        instruction.operation.num_qubits == 2 for instruction in circuit.data
    )
    two_qubit_depth = circuit.depth(
        filter_function=lambda instruction: instruction.operation.num_qubits == 2
    )
    generic_unitary_count = int(circuit.count_ops().get("unitary", 0))
    valid = bool(semantic_valid and compatibility["compatible"] and generic_unitary_count == 0)
    return {
        "path": path,
        "valid": valid,
        "semantic_valid": semantic_valid,
        "phase_aligned_operator_error": operator_error,
        "target_compatible": compatibility["compatible"],
        "unsupported_operations": compatibility["unsupported"],
        "generic_unitary_count": generic_unitary_count,
        "two_qubit_count": int(two_qubit_count),
        "duration_seconds": _scheduled_duration(circuit, target),
        "total_native_gates": len(circuit.data),
        "two_qubit_depth": int(two_qubit_depth or 0),
        "depth": int(circuit.depth() or 0),
        "compilation_latency_seconds": float(latency),
        "qpy_bytes": _qpy_size(circuit),
        "metadata": metadata,
    }


def _selection_key(record: dict[str, Any]) -> tuple[float, ...]:
    duration = record["duration_seconds"]
    return (
        0.0 if record["valid"] else 1.0,
        float(record.get("two_qubit_count", math.inf)),
        float(duration) if duration is not None else math.inf,
        float(record.get("total_native_gates", math.inf)),
        float(record.get("two_qubit_depth", math.inf)),
        float(record.get("depth", math.inf)),
        float(record.get("compilation_latency_seconds", math.inf)),
        float(record.get("qpy_bytes", math.inf)),
    )


def synthesize_su4_block(
    block: QuaternionCartanBlock,
    *,
    target: Target | None = None,
    strategy: SynthesisStrategy = "best_native",
    include_report: bool = False,
) -> QuantumCircuit | tuple[QuantumCircuit, dict[str, Any]]:
    """Generate, validate, and select local/native Qiskit synthesis candidates."""
    if not isinstance(block, QuaternionCartanBlock):
        raise TypeError("block must be a QuaternionCartanBlock")
    if strategy not in {"best_native", *_PATHS}:
        raise ValueError(f"unsupported synthesis strategy: {strategy}")
    source = block.to_unitary()
    factories: tuple[
        tuple[str, Callable[[], tuple[QuantumCircuit, float, dict[str, Any]]]], ...
    ] = (
        ("Q3", lambda: _synthesize_q3(source, target)),
        ("QF", lambda: _synthesize_qf(source, target)),
        ("QC", lambda: _synthesize_qc(source, target)),
        ("QX", lambda: _synthesize_qx(source, target)),
        ("RQ", lambda: _synthesize_rq(block, target)),
    )
    records: dict[str, dict[str, Any]] = {}
    circuits: dict[str, QuantumCircuit] = {}
    for path, factory in factories:
        try:
            circuit, latency, metadata = factory()
            circuits[path] = circuit
            records[path] = _candidate_metrics(
                path, source, circuit, target, latency, metadata
            )
        except Exception as exc:  # noqa: BLE001 - each candidate fails closed independently
            records[path] = {
                "path": path,
                "valid": False,
                "fallback_reason": str(exc),
                "error_type": type(exc).__name__,
            }

    if strategy == "best_native":
        valid_paths = [path for path in _PATHS if records[path].get("valid")]
        if not valid_paths:
            raise ValueError("no semantically valid target-compatible SU(4) synthesis candidate")
        selected_path = min(valid_paths, key=lambda path: _selection_key(records[path]))
        selection_reason = (
            "selected by semantic validity, two-qubit count, scheduled duration, total native "
            "gates, two-qubit depth, full depth, compilation latency, and QPY size"
        )
    else:
        selected_path = strategy
        if not records[selected_path].get("valid"):
            raise ValueError(
                f"requested synthesis strategy {selected_path} is invalid: "
                f"{records[selected_path].get('fallback_reason', 'semantic or target failure')}"
            )
        selection_reason = f"explicit strategy request: {selected_path}"

    classification = classify_su4(block)
    report = {
        "selected_path": selected_path,
        "weyl_class": classification.class_label,
        "nonlocal_fingerprint": block.nonlocal_fingerprint(),
        "candidates": records,
        "selection_reason": selection_reason,
        "selection_hierarchy": [
            "semantic_validity",
            "two_qubit_count",
            "scheduled_duration",
            "total_native_gates",
            "two_qubit_depth",
            "full_depth",
            "compilation_latency",
            "qpy_size",
        ],
    }
    selected = circuits[selected_path]
    return (selected, report) if include_report else selected
