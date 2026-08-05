#!/usr/bin/env python3
"""Run the frozen EXP-014-A01 representative and boundary coverage extension."""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator

from rqm_qiskit import (
    analyze_qiskit_circuit,
    assure_qiskit_circuit,
    canonical_su2_fingerprint,
)


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "coverage_manifest.json"
RESULT_PATH = ROOT / "coverage_results.json"


def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _phase_aligned_error(left: np.ndarray, right: np.ndarray) -> float:
    overlap = np.vdot(left.reshape(-1), right.reshape(-1))
    if abs(overlap) > 1e-15:
        right = right * np.exp(-1j * np.angle(overlap))
    return float(np.max(np.abs(left - right)))


def _generated_chain(seed: int, length: int) -> tuple[QuantumCircuit, QuantumCircuit, QuantumCircuit]:
    rng = random.Random(seed)
    operations = [(rng.choice(("rx", "ry", "rz")), rng.uniform(-2.4, 2.4)) for _ in range(length)]
    direct = QuantumCircuit(1)
    split = QuantumCircuit(1)
    reversed_order = QuantumCircuit(1)
    for gate, angle in operations:
        getattr(direct, gate)(angle, 0)
        getattr(split, gate)(angle / 2.0, 0)
        getattr(split, gate)(angle / 2.0, 0)
    for gate, angle in reversed(operations):
        getattr(reversed_order, gate)(angle, 0)
    return direct, split, reversed_order


def _generated_track(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    offset = 0
    for partition in ("discovery", "holdout"):
        for index in range(int(manifest["generated_chains"][partition])):
            direct, split, reversed_order = _generated_chain(
                int(manifest["seed"]) + offset,
                int(manifest["generated_chains"]["length"]),
            )
            offset += 1
            direct_fp = canonical_su2_fingerprint(direct)
            split_fp = canonical_su2_fingerprint(split)
            reversed_fp = canonical_su2_fingerprint(reversed_order)
            rows.append(
                {
                    "partition": partition,
                    "index": index,
                    "equivalent_fingerprints_match": direct_fp == split_fp,
                    "reversed_counterexample_distinct": reversed_fp != direct_fp,
                    "equivalent_operator_error": _phase_aligned_error(
                        np.asarray(Operator(direct).data),
                        np.asarray(Operator(split).data),
                    ),
                }
            )
    return {"rows": rows}


def _representatives() -> list[tuple[str, QuantumCircuit]]:
    bell = QuantumCircuit(2, name="bell")
    bell.h(0)
    bell.cx(0, 1)

    ghz = QuantumCircuit(3, name="ghz")
    ghz.h(0)
    ghz.cx(0, 1)
    ghz.cx(1, 2)

    qft_style = QuantumCircuit(3, name="qft_style")
    for qubit in range(3):
        qft_style.h(qubit)
        qft_style.rz(math.pi / (2 ** (qubit + 1)), qubit)
    qft_style.cx(0, 1)
    qft_style.rz(math.pi / 4, 1)
    qft_style.cx(1, 2)
    qft_style.swap(0, 2)

    vqe_style = QuantumCircuit(4, name="vqe_style")
    for qubit, angle in enumerate((0.17, -0.31, 0.43, -0.59)):
        vqe_style.ry(angle, qubit)
        vqe_style.rz(angle / 2.0, qubit)
    for control, target in ((0, 1), (1, 2), (2, 3)):
        vqe_style.cx(control, target)

    qaoa_style = QuantumCircuit(5, name="qaoa_style")
    for qubit in range(5):
        qaoa_style.h(qubit)
    for left, right in ((0, 1), (1, 2), (2, 3), (3, 4)):
        qaoa_style.rzz(0.37, left, right)
    for qubit in range(5):
        qaoa_style.rx(-0.41, qubit)
    return [
        ("bell", bell),
        ("ghz", ghz),
        ("qft_style", qft_style),
        ("vqe_style", vqe_style),
        ("qaoa_style", qaoa_style),
    ]


def _representative_track() -> dict[str, Any]:
    rows = []
    for name, circuit in _representatives():
        assurance = assure_qiskit_circuit(circuit)
        report = analyze_qiskit_circuit(circuit)
        rows.append(
            {
                "name": name,
                "num_qubits": circuit.num_qubits,
                "assurance_status": assurance.assurance_status,
                "optimization_applied": assurance.optimization_applied,
                "report_status": report.status,
                "report_has_bounded_geometry": bool(
                    report.local_geometry or report.nonlocal_geometry
                ),
            }
        )
    return {"rows": rows}


def _unsupported_boundaries() -> list[tuple[str, QuantumCircuit]]:
    mid_measure = QuantumCircuit(1, 1)
    mid_measure.h(0)
    mid_measure.measure(0, 0)
    mid_measure.x(0)

    reset = QuantumCircuit(1)
    reset.reset(0)

    theta = Parameter("theta")
    symbolic = QuantumCircuit(1)
    symbolic.rx(theta, 0)

    custom_body = QuantumCircuit(1, name="custom_body")
    custom_body.h(0)
    custom = QuantumCircuit(1)
    custom.append(custom_body.to_gate(), [0])

    controlled_phase = QuantumCircuit(2)
    controlled_phase.cp(0.37, 0, 1)
    return [
        ("mid_circuit_measurement", mid_measure),
        ("reset", reset),
        ("symbolic_parameter", symbolic),
        ("custom_instruction", custom),
        ("controlled_phase", controlled_phase),
    ]


def _boundary_track() -> dict[str, Any]:
    unsupported = []
    for name, circuit in _unsupported_boundaries():
        result = assure_qiskit_circuit(circuit)
        unsupported.append(
            {
                "name": name,
                "status": result.assurance_status,
                "fallback_reason": result.fallback_reason,
                "exact_original_returned": result.returned_circuit == circuit,
            }
        )

    qreg = QuantumRegister(2, "science")
    creg = ClassicalRegister(2, "readout")
    measured = QuantumCircuit(qreg, creg)
    measured.h(qreg[0])
    measured.cx(qreg[0], qreg[1])
    measured.measure(qreg[0], creg[1])
    measured.measure(qreg[1], creg[0])
    result = assure_qiskit_circuit(measured)
    returned = result.returned_circuit
    mapping = [
        [returned.find_bit(item.qubits[0]).index, returned.find_bit(item.clbits[0]).index]
        for item in returned.data
        if item.operation.name == "measure"
    ]
    terminal = {
        "status": result.assurance_status,
        "quantum_registers": [register.name for register in returned.qregs],
        "classical_registers": [register.name for register in returned.cregs],
        "mapping": mapping,
    }
    return {"unsupported": unsupported, "terminal_measurement": terminal}


def _q_neg_q_track() -> dict[str, float]:
    circuit = QuantumCircuit(1)
    circuit.rz(0.37, 0)
    circuit.ry(-0.81, 0)
    unitary = np.asarray(Operator(circuit).data, dtype=np.complex128)
    negative = -unitary
    initial = np.asarray([1.0, 0.0], dtype=np.complex128)
    probability_error = float(
        np.max(np.abs(np.abs(unitary @ initial) ** 2 - np.abs(negative @ initial) ** 2))
    )
    identity = np.eye(2, dtype=np.complex128)
    zero = np.zeros((2, 2), dtype=np.complex128)
    controlled_q = np.block([[identity, zero], [zero, unitary]])
    controlled_negative_q = np.block([[identity, zero], [zero, negative]])
    return {
        "standalone_probability_error": probability_error,
        "controlled_operator_phase_aligned_separation": _phase_aligned_error(
            controlled_q,
            controlled_negative_q,
        ),
    }


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    generated = _generated_track(manifest)
    representatives = _representative_track()
    boundaries = _boundary_track()
    q_neg_q = _q_neg_q_track()
    thresholds = manifest["thresholds"]
    checks = {
        "generated_equivalence": all(
            row["equivalent_fingerprints_match"]
            and row["equivalent_operator_error"]
            <= thresholds["max_phase_aligned_operator_error"]
            for row in generated["rows"]
        ),
        "noncommuting_counterexamples": all(
            row["reversed_counterexample_distinct"] for row in generated["rows"]
        ),
        "representatives_verified": all(
            row["assurance_status"] == "VERIFIED"
            and row["report_has_bounded_geometry"]
            for row in representatives["rows"]
        ),
        "unsupported_fail_closed": all(
            row["status"] == "FALLBACK_ORIGINAL"
            and row["exact_original_returned"]
            for row in boundaries["unsupported"]
        ),
        "terminal_measurement_exact": boundaries["terminal_measurement"]
        == {
            "status": "VERIFIED",
            "quantum_registers": ["science"],
            "classical_registers": ["readout"],
            "mapping": [[0, 1], [1, 0]],
        },
        "q_neg_q_control": q_neg_q["standalone_probability_error"]
        <= thresholds["max_standalone_q_neg_q_probability_error"]
        and q_neg_q["controlled_operator_phase_aligned_separation"]
        >= thresholds["minimum_controlled_q_neg_q_operator_separation"],
    }
    result = {
        "schema_version": "1.0",
        "extension_id": manifest["extension_id"],
        "manifest_digest": _digest(manifest),
        "primary_cohort_immutable": True,
        "generated": generated,
        "representatives": representatives,
        "boundaries": boundaries,
        "q_neg_q": q_neg_q,
        "checks": checks,
        "passed": all(checks.values()),
        "claim_boundary": "Correctness and coverage validation only; the primary EXP-014 advantage cohort and claim are unchanged.",
    }
    result["result_digest"] = _digest(result)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "checks": checks}, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
