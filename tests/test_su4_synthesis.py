from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import qiskit
from qiskit.circuit import Measure, Parameter
from qiskit.circuit.library import CZGate, RXGate, RZGate, RZZGate, SXGate, XGate
from qiskit.quantum_info import Operator
from qiskit.transpiler import InstructionProperties, Target
from rqm_compiler import Circuit
from rqm_entanglement import (
    QuaternionCartanBlock,
    cartan_core_from_weyl,
    phase_aligned_operator_error,
)

from rqm_qiskit import direct_rq_circuit, synthesize_su4_block, to_qiskit_circuit


def _target(*, fractional: bool) -> Target:
    target = Target(num_qubits=2, dt=2.22e-10)
    theta = Parameter("theta")
    one = {
        (0,): InstructionProperties(duration=3.5e-8, error=2.5e-4),
        (1,): InstructionProperties(duration=3.5e-8, error=2.5e-4),
    }
    virtual = {
        (0,): InstructionProperties(duration=0.0, error=0.0),
        (1,): InstructionProperties(duration=0.0, error=0.0),
    }
    two = {
        (0, 1): InstructionProperties(duration=2.7e-7, error=7.5e-3),
        (1, 0): InstructionProperties(duration=2.7e-7, error=7.5e-3),
    }
    target.add_instruction(RZGate(theta), virtual)
    target.add_instruction(SXGate(), one)
    target.add_instruction(XGate(), one)
    if fractional:
        target.add_instruction(RXGate(theta), one)
    target.add_instruction(CZGate(), two)
    if fractional:
        target.add_instruction(RZZGate(theta), two)
    target.add_instruction(
        Measure(),
        {
            (0,): InstructionProperties(duration=7e-7, error=1.5e-2),
            (1,): InstructionProperties(duration=7e-7, error=1.5e-2),
        },
    )
    return target


def _generic_block() -> QuaternionCartanBlock:
    return QuaternionCartanBlock.from_unitary(cartan_core_from_weyl(0.61, 0.27, -0.13))


def _assert_semantic(block: QuaternionCartanBlock, circuit) -> float:
    error, _ = phase_aligned_operator_error(block.to_unitary(), Operator(circuit).data)
    assert error <= 1e-10
    return error


def test_qiskit_25_compatibility_range_is_active() -> None:
    assert qiskit.__version__ == "2.5.1"
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    assert '"qiskit>=2.5.1,<2.6"' in pyproject


def test_standard_pair_rotation_translation() -> None:
    circuit = Circuit(2).rxx(0, 1, 0.2).ryy(0, 1, -0.3).rzz(0, 1, 0.4)
    translated = to_qiskit_circuit(circuit)
    assert [item.operation.name for item in translated.data] == ["rxx", "ryy", "rzz"]


def test_best_native_generates_all_candidate_families_and_allows_rq_to_lose() -> None:
    block = _generic_block()
    selected, report = synthesize_su4_block(
        block,
        include_report=True,
    )
    assert set(report["candidates"]) == {"Q3", "QF", "QC", "QX", "RQ"}
    assert report["selected_path"] != "RQ"
    assert report["candidates"]["RQ"]["valid"] is True
    _assert_semantic(block, selected)


def test_selection_record_matches_frozen_local_metric_hierarchy() -> None:
    _, report = synthesize_su4_block(_generic_block(), include_report=True)
    assert report["selection_hierarchy"] == [
        "semantic_validity",
        "two_qubit_count",
        "scheduled_duration",
        "total_native_gates",
        "two_qubit_depth",
        "full_depth",
        "compilation_latency",
        "qpy_size",
    ]


def test_ordinary_target_fails_fractional_candidates_closed() -> None:
    _, report = synthesize_su4_block(
        _generic_block(), target=_target(fractional=False), include_report=True
    )
    assert report["candidates"]["QF"]["valid"] is False
    assert report["candidates"]["QC"]["valid"] is False
    assert report["candidates"][report["selected_path"]]["valid"] is True


def test_rq_path_uses_positive_supported_rzz_and_no_generic_unitary() -> None:
    block = _generic_block()
    pre_native = direct_rq_circuit(block)
    angles = [
        float(item.operation.params[0])
        for item in pre_native.data
        if item.operation.name == "rzz"
    ]
    assert angles
    assert all(0.0 < angle <= math.pi / 2.0 + 1e-12 for angle in angles)
    assert pre_native.count_ops().get("unitary", 0) == 0
    _assert_semantic(block, pre_native)


@pytest.mark.parametrize("strategy", ["Q3", "QF", "QC", "QX", "RQ"])
def test_each_supported_fractional_target_candidate_is_semantic_and_native(strategy: str) -> None:
    block = _generic_block()
    circuit, report = synthesize_su4_block(
        block,
        target=_target(fractional=True),
        strategy=strategy,
        include_report=True,
    )
    record = report["candidates"][strategy]
    assert record["valid"] is True
    assert record["generic_unitary_count"] == 0
    _assert_semantic(block, circuit)


def test_compiler_su4q_round_trip_to_qiskit_operator_and_report() -> None:
    block = _generic_block()
    compiler_circuit = Circuit(2).su4q(0, 1, block)
    translated, synthesis_reports = to_qiskit_circuit(
        compiler_circuit,
        include_synthesis_report=True,
    )
    assert len(synthesis_reports) == 1
    assert synthesis_reports[0]["selected_path"] in {"Q3", "QF", "QC", "QX", "RQ"}
    assert translated.metadata["rqm_su4_synthesis"] == synthesis_reports
    _assert_semantic(block, translated)


def test_explicit_invalid_strategy_fails_closed() -> None:
    with pytest.raises(ValueError, match="QF"):
        synthesize_su4_block(
            _generic_block(),
            target=_target(fractional=False),
            strategy="QF",
        )


def test_deterministic_landmarks_have_valid_selected_candidates() -> None:
    workloads = [
        cartan_core_from_weyl(0.0, 0.0, 0.0),
        cartan_core_from_weyl(math.pi / 4, 0.0, 0.0),
        cartan_core_from_weyl(math.pi / 4, math.pi / 4, 0.0),
        cartan_core_from_weyl(math.pi / 8, math.pi / 8, math.pi / 8),
    ]
    maximum_error = 0.0
    for unitary in workloads:
        block = QuaternionCartanBlock.from_unitary(unitary)
        selected, report = synthesize_su4_block(block, include_report=True)
        maximum_error = max(maximum_error, _assert_semantic(block, selected))
        assert report["candidates"][report["selected_path"]]["valid"] is True
    assert maximum_error <= 1e-10


def test_report_is_json_compatible() -> None:
    import json

    _, report = synthesize_su4_block(_generic_block(), include_report=True)
    serialized = json.dumps(report, sort_keys=True)
    assert "selected_path" in serialized
    assert np.isfinite(report["candidates"][report["selected_path"]]["qpy_bytes"])
