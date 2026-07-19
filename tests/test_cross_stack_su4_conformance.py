"""Editable-local conformance for the promoted quaternion-Cartan SU(4) stack."""

from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np
import pytest
from qiskit.quantum_info import Operator

from rqm_compiler import Circuit
from rqm_entanglement import (
    CNOT,
    ISWAP,
    SWAP,
    QuaternionCartanBlock,
    canonical_entangler,
    decompose_su4,
    phase_aligned_operator_error,
)
from rqm_qiskit import to_qiskit_circuit


def _unit_quaternion(values: tuple[float, float, float, float]) -> tuple[float, ...]:
    vector = np.asarray(values, dtype=np.float64)
    return tuple(vector / np.linalg.norm(vector))


def _generic_interior() -> np.ndarray:
    block = QuaternionCartanBlock.from_components(
        left_q0=_unit_quaternion((0.91, 0.11, -0.27, 0.29)),
        left_q1=_unit_quaternion((0.71, -0.41, 0.19, 0.53)),
        cartan_a=0.61,
        cartan_b=0.27,
        cartan_c=-0.13,
        right_q0=_unit_quaternion((0.66, 0.43, 0.37, -0.49)),
        right_q1=_unit_quaternion((0.84, -0.23, 0.44, 0.21)),
        global_phase=0.317,
    )
    return block.to_unitary()


def _sqrt_swap() -> np.ndarray:
    diagonal = (1.0 + 1.0j) / 2.0
    off_diagonal = (1.0 - 1.0j) / 2.0
    return np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, diagonal, off_diagonal, 0.0],
            [0.0, off_diagonal, diagonal, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.complex128,
    )


WORKLOADS: tuple[tuple[str, Callable[[], np.ndarray]], ...] = (
    ("identity", lambda: np.eye(4, dtype=np.complex128)),
    ("cnot_class", lambda: np.asarray(CNOT, dtype=np.complex128)),
    ("iswap_class", lambda: np.asarray(ISWAP, dtype=np.complex128)),
    ("sqrt_swap_class", _sqrt_swap),
    ("swap_class", lambda: np.asarray(SWAP, dtype=np.complex128)),
    ("generic_interior", _generic_interior),
    ("qaoa_rzz", lambda: canonical_entangler(0.0, 0.0, 0.73)),
    ("mixed_xx_yy_zz", lambda: canonical_entangler(0.37, -0.28, 0.19)),
)


def evaluate_cross_stack_workload(name: str, source: np.ndarray) -> dict[str, object]:
    """Run the required decomposition/IR/JSON/Qiskit/operator flow for one unitary."""
    block = decompose_su4(source)
    compiler_circuit = Circuit(2).su4q(0, 1, block)
    serialized = json.loads(json.dumps(compiler_circuit.to_descriptors(), sort_keys=True))
    restored = Circuit.from_descriptors(serialized, num_qubits=2)
    assert restored.to_descriptors() == compiler_circuit.to_descriptors()

    selected, reports = to_qiskit_circuit(
        restored,
        include_synthesis_report=True,
    )
    assert len(reports) == 1
    report = reports[0]
    selected_record = report["candidates"][report["selected_path"]]
    assert selected_record["valid"] is True
    assert selected_record["semantic_valid"] is True
    assert selected_record["target_compatible"] is True
    assert selected_record["generic_unitary_count"] == 0
    assert selected.count_ops().get("unitary", 0) == 0

    operator = np.asarray(Operator(selected).data, dtype=np.complex128)
    error, _ = phase_aligned_operator_error(source, operator)
    return {
        "workload": name,
        "operator_error": error,
        "selected_path": report["selected_path"],
        "weyl_class": report["weyl_class"],
        "nonlocal_fingerprint": report["nonlocal_fingerprint"],
        "serialization_round_trip": True,
        "selected_candidate_valid": True,
        "generic_unitary_count": 0,
    }


@pytest.mark.parametrize(("name", "factory"), WORKLOADS)
def test_required_cross_stack_workloads(
    name: str,
    factory: Callable[[], np.ndarray],
) -> None:
    result = evaluate_cross_stack_workload(name, factory())
    assert result["operator_error"] <= 1e-10


def test_local_equivalence_fingerprint_with_distinct_full_hashes() -> None:
    identity = (1.0, 0.0, 0.0, 0.0)
    base = QuaternionCartanBlock.from_components(
        left_q0=identity,
        left_q1=identity,
        cartan_a=0.51,
        cartan_b=0.24,
        cartan_c=-0.11,
        right_q0=identity,
        right_q1=identity,
    )
    orbit = QuaternionCartanBlock.from_components(
        left_q0=_unit_quaternion((0.73, -0.31, 0.21, 0.55)),
        left_q1=_unit_quaternion((0.61, 0.44, -0.33, 0.57)),
        cartan_a=0.51,
        cartan_b=0.24,
        cartan_c=-0.11,
        right_q0=identity,
        right_q1=identity,
    )
    recovered_base = decompose_su4(base.to_unitary())
    recovered_orbit = decompose_su4(orbit.to_unitary())
    assert recovered_base.nonlocal_fingerprint() == recovered_orbit.nonlocal_fingerprint()
    assert recovered_base.full_canonical_hash() != recovered_orbit.full_canonical_hash()


def test_conformance_workload_names_are_frozen() -> None:
    assert [name for name, _ in WORKLOADS] == [
        "identity",
        "cnot_class",
        "iswap_class",
        "sqrt_swap_class",
        "swap_class",
        "generic_interior",
        "qaoa_rzz",
        "mixed_xx_yy_zz",
    ]
    assert np.allclose(_sqrt_swap() @ _sqrt_swap(), SWAP, atol=1e-12, rtol=0.0)
