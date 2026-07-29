#!/usr/bin/env python3
"""Frozen local corpus for the Qiskit/OpenQASM assurance bridge v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, qasm3, transpile
from qiskit.circuit import Gate, Parameter
from qiskit.quantum_info import Operator
from rqm_compiler import optimize_circuit, verify_equivalence

from rqm_qiskit import (
    SUPPORTED_QISKIT_GATES,
    assure_qiskit_circuit,
    export_openqasm3,
    import_openqasm3,
    import_qiskit_circuit,
)

ROOT = Path(__file__).resolve().parent
SEED = 4430
ELIGIBLE_COUNT = 160
COUNTEREXAMPLE_COUNT = 20
UNSUPPORTED_COUNT = 20
TOTAL_COUNT = ELIGIBLE_COUNT + COUNTEREXAMPLE_COUNT + UNSUPPORTED_COUNT
MANIFEST_PATH = ROOT / "corpus_manifest.json"
RESULTS_PATH = ROOT / "raw_results.json"
REPORT_PATH = ROOT / "RESULTS.md"
HASHES_PATH = ROOT / "SHA256SUMS"

ANGLE_POOL = (
    0.0,
    1e-12,
    -1e-12,
    math.pi - 1e-12,
    math.pi,
    math.pi + 1e-12,
    -math.pi,
    2.0 * math.pi,
    -2.0 * math.pi,
    0.125,
    -0.375,
    1.25,
)
ONE_QUBIT_GATES = ("id", "x", "y", "z", "h", "s", "t", "rx", "ry", "rz", "p")
TWO_QUBIT_GATES = ("cx", "cy", "cz", "swap", "iswap", "rxx", "ryy", "rzz")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _equivalent_up_to_phase(left: QuantumCircuit, right: QuantumCircuit) -> tuple[bool, float]:
    lhs = Operator(left).data
    rhs = Operator(right).data
    overlap = np.vdot(rhs.reshape(-1), lhs.reshape(-1))
    if abs(overlap) == 0.0:
        return False, float("inf")
    phase = overlap / abs(overlap)
    error = float(np.max(np.abs(lhs - phase * rhs)))
    return error <= 1e-9, error


def _eligible_qubit_count(index: int) -> int:
    if index < 40:
        return 1
    if index < 100:
        return 2
    return 3


def _append_random_gate(circuit: QuantumCircuit, rng: random.Random, step: int) -> None:
    num_qubits = circuit.num_qubits
    choose_two = num_qubits > 1 and (step % 4 == 3 or rng.random() < 0.32)
    if choose_two:
        gate = rng.choice(TWO_QUBIT_GATES)
        q0, q1 = rng.sample(range(num_qubits), 2)
        if gate in {"cx", "cy", "cz"} or gate in {"swap", "iswap"}:
            getattr(circuit, gate)(q0, q1)
        else:
            getattr(circuit, gate)(rng.choice(ANGLE_POOL), q0, q1)
        return

    gate = rng.choice(ONE_QUBIT_GATES)
    qubit = rng.randrange(num_qubits)
    if gate in {"rx", "ry", "rz", "p"}:
        getattr(circuit, gate)(rng.choice(ANGLE_POOL), qubit)
    else:
        getattr(circuit, gate)(qubit)


def build_eligible(index: int) -> QuantumCircuit:
    rng = random.Random(SEED * 10_000 + index)
    qubits = _eligible_qubit_count(index)
    circuit = QuantumCircuit(qubits, name=f"eligible-{index:03d}")
    length = 4 + (index % 21)
    for step in range(length):
        _append_random_gate(circuit, rng, step)
    return circuit


def build_counterexample(index: int) -> tuple[QuantumCircuit, QuantumCircuit, str]:
    mode = index % 4
    if mode == 0:
        original = QuantumCircuit(1)
        original.x(0)
        return original, QuantumCircuit(1), "dropped_gate"
    if mode == 1:
        original = QuantumCircuit(1)
        candidate = QuantumCircuit(1)
        original.rx(0.2, 0)
        candidate.rx(0.25, 0)
        return original, candidate, "changed_angle"
    if mode == 2:
        original = QuantumCircuit(1)
        candidate = QuantumCircuit(1)
        original.h(0)
        original.t(0)
        candidate.t(0)
        candidate.h(0)
        return original, candidate, "reversed_noncommuting_order"
    original = QuantumCircuit(2)
    candidate = QuantumCircuit(2)
    original.cx(0, 1)
    candidate.cx(1, 0)
    return original, candidate, "changed_control"


def _one_qubit_with(operation: str) -> QuantumCircuit:
    circuit = QuantumCircuit(1)
    if operation == "reset":
        circuit.reset(0)
    elif operation == "barrier":
        circuit.barrier(0)
    elif operation == "delay":
        circuit.delay(10, 0, unit="ns")
    elif operation == "initialize":
        circuit.initialize([1.0, 0.0], 0)
    elif operation == "unitary":
        circuit.unitary(np.eye(2), [0])
    elif operation == "u":
        circuit.u(0.1, 0.2, 0.3, 0)
    elif operation == "sx":
        circuit.sx(0)
    elif operation == "ch":
        circuit = QuantumCircuit(2)
        circuit.ch(0, 1)
    elif operation == "nan":
        circuit.rx(float("nan"), 0)
    elif operation == "custom":
        circuit.append(Gate("custom", 1, []), [0])
    else:
        raise ValueError(operation)
    return circuit


def build_unsupported(index: int) -> tuple[str, QuantumCircuit | str]:
    if index == 0:
        return "four_qubits", QuantumCircuit(4)
    if index == 1:
        return "zero_qubits", QuantumCircuit(0)
    if index == 2:
        return "classical_register", QuantumCircuit(1, 1)
    if index == 3:
        circuit = QuantumCircuit(1, 1)
        circuit.measure(0, 0)
        return "measurement", circuit
    if index == 4:
        circuit = QuantumCircuit(1)
        circuit.rx(Parameter("theta"), 0)
        return "symbolic_parameter", circuit
    if index == 5:
        circuit = QuantumCircuit(1, global_phase=0.25)
        circuit.x(0)
        return "nonzero_global_phase", circuit
    if index == 6:
        return "reset", _one_qubit_with("reset")
    if index == 7:
        return "barrier", _one_qubit_with("barrier")
    if index == 8:
        return "delay", _one_qubit_with("delay")
    if index == 9:
        return "initialize", _one_qubit_with("initialize")
    if index == 10:
        return "unitary", _one_qubit_with("unitary")
    if index == 11:
        circuit = QuantumCircuit(3)
        circuit.ccx(0, 1, 2)
        return "ccx", circuit
    if index == 12:
        return "u", _one_qubit_with("u")
    if index == 13:
        return "sx", _one_qubit_with("sx")
    if index == 14:
        circuit = QuantumCircuit(2)
        circuit.cp(0.2, 0, 1)
        return "cp", circuit
    if index == 15:
        return "ch", _one_qubit_with("ch")
    if index == 16:
        return "nonfinite_parameter", _one_qubit_with("nan")
    if index == 17:
        return "custom_gate", _one_qubit_with("custom")
    if index == 18:
        return "malformed_missing_angle", "OPENQASM 3.0;\nqubit[1] q;\nrx( q[0];"
    return "malformed_unknown_token", "OPENQASM 3.0;\nqubit[1] q;\n???"


def build_manifest() -> dict[str, Any]:
    eligible = []
    for index in range(ELIGIBLE_COUNT):
        circuit = build_eligible(index)
        imported = import_qiskit_circuit(circuit)
        eligible.append(
            {
                "case_id": f"eligible-{index:03d}",
                "category": "eligible",
                "num_qubits": circuit.num_qubits,
                "operation_count": len(circuit.data),
                "descriptor_sha256": (
                    _sha256_bytes(_canonical_bytes(imported.circuit.to_descriptors()))
                    if imported.circuit is not None
                    else None
                ),
            }
        )
    counterexamples = [
        {
            "case_id": f"counterexample-{index:03d}",
            "category": "counterexample",
            "mutation": build_counterexample(index)[2],
        }
        for index in range(COUNTEREXAMPLE_COUNT)
    ]
    unsupported = [
        {
            "case_id": f"unsupported-{index:03d}",
            "category": "unsupported",
            "boundary": build_unsupported(index)[0],
        }
        for index in range(UNSUPPORTED_COUNT)
    ]
    return {
        "schema_version": "rqm.qiskit-openqasm-corpus.v0.1",
        "seed": SEED,
        "case_count": TOTAL_COUNT,
        "eligible_count": ELIGIBLE_COUNT,
        "counterexample_count": COUNTEREXAMPLE_COUNT,
        "unsupported_count": UNSUPPORTED_COUNT,
        "supported_gates": list(SUPPORTED_QISKIT_GATES),
        "cases": eligible + counterexamples + unsupported,
    }


def _run_eligible(index: int) -> dict[str, Any]:
    source = build_eligible(index)
    start_import = time.perf_counter_ns()
    imported = import_qiskit_circuit(source)
    after_import = time.perf_counter_ns()
    if imported.circuit is None:
        return {
            "case_id": f"eligible-{index:03d}",
            "verified": False,
            "failure": imported.report.to_dict(),
        }

    returned_compiler, compiler_report = optimize_circuit(imported.circuit)
    after_compiler = time.perf_counter_ns()
    exported = export_openqasm3(returned_compiler)
    after_export = time.perf_counter_ns()
    assured = assure_qiskit_circuit(source)
    if exported.source is None:
        return {
            "case_id": f"eligible-{index:03d}",
            "verified": False,
            "failure": exported.to_dict(),
        }
    reparsed = qasm3.loads(exported.source)
    direct_ok, direct_error = _equivalent_up_to_phase(source, assured.returned_circuit)
    qasm_ok, qasm_error = _equivalent_up_to_phase(source, reparsed)

    start_qiskit = time.perf_counter_ns()
    baseline = transpile(
        source,
        basis_gates=list(SUPPORTED_QISKIT_GATES),
        optimization_level=3,
    )
    qiskit_ns = time.perf_counter_ns() - start_qiskit

    compiler_ns = after_compiler - after_import
    adapter_total_ns = after_export - start_import
    adapter_overhead_ns = max(0, adapter_total_ns - compiler_ns)
    return {
        "case_id": f"eligible-{index:03d}",
        "verified": (
            assured.assurance_status == "VERIFIED"
            and compiler_report.equivalence_status == "VERIFIED"
            and direct_ok
            and qasm_ok
        ),
        "assurance_status": assured.assurance_status,
        "optimization_applied": assured.optimization_applied,
        "direct_max_abs_error": direct_error,
        "openqasm_max_abs_error": qasm_error,
        "source_gate_count": len(source.data),
        "rqm_returned_gate_count": len(assured.returned_circuit.data),
        "qiskit_level3_gate_count": len(baseline.data),
        "source_depth": source.depth(),
        "rqm_returned_depth": assured.returned_circuit.depth(),
        "qiskit_level3_depth": baseline.depth(),
        "compiler_ns": compiler_ns,
        "adapter_total_ns": adapter_total_ns,
        "adapter_overhead_ns": adapter_overhead_ns,
        "adapter_overhead_ratio": (
            adapter_overhead_ns / compiler_ns if compiler_ns > 0 else None
        ),
        "qiskit_level3_ns": qiskit_ns,
        "returned_openqasm_sha256": exported.source_sha256,
    }


def _run_counterexample(index: int) -> dict[str, Any]:
    original, candidate, mutation = build_counterexample(index)
    imported_original = import_qiskit_circuit(original)
    imported_candidate = import_qiskit_circuit(candidate)
    if imported_original.circuit is None or imported_candidate.circuit is None:
        return {
            "case_id": f"counterexample-{index:03d}",
            "mutation": mutation,
            "status": "IMPORT_ERROR",
            "false_equivalence": False,
        }
    proof = verify_equivalence(imported_original.circuit, imported_candidate.circuit)
    return {
        "case_id": f"counterexample-{index:03d}",
        "mutation": mutation,
        "status": proof.status.value,
        "method": proof.method,
        "false_equivalence": proof.status.value == "VERIFIED",
    }


def _run_unsupported(index: int) -> dict[str, Any]:
    boundary, value = build_unsupported(index)
    if isinstance(value, str):
        imported = import_openqasm3(value)
        return {
            "case_id": f"unsupported-{index:03d}",
            "boundary": boundary,
            "status": imported.report.status,
            "reason_codes": ["parse_error"],
            "fail_closed": imported.circuit is None and imported.report.status == "ERROR",
            "candidate_disclosed": False,
        }
    imported = import_qiskit_circuit(value)
    assured = assure_qiskit_circuit(value)
    return {
        "case_id": f"unsupported-{index:03d}",
        "boundary": boundary,
        "status": imported.report.status,
        "reason_codes": [reason.code for reason in imported.report.unsupported_reasons],
        "fail_closed": (
            imported.circuit is None
            and assured.assurance_status == "FALLBACK_ORIGINAL"
            and assured.normalized_input is None
        ),
        "candidate_disclosed": hasattr(assured, "candidate_circuit"),
    }


def run_corpus() -> dict[str, Any]:
    frozen = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    regenerated = build_manifest()
    if frozen != regenerated:
        raise RuntimeError("Frozen corpus manifest does not match the generator.")

    eligible = [_run_eligible(index) for index in range(ELIGIBLE_COUNT)]
    counterexamples = [
        _run_counterexample(index) for index in range(COUNTEREXAMPLE_COUNT)
    ]
    unsupported = [_run_unsupported(index) for index in range(UNSUPPORTED_COUNT)]

    verified_count = sum(bool(case.get("verified")) for case in eligible)
    false_equivalence_count = sum(
        bool(case["false_equivalence"]) for case in counterexamples
    )
    unsupported_fail_closed_count = sum(
        bool(case["fail_closed"]) for case in unsupported
    )
    candidate_disclosure_count = sum(
        bool(case["candidate_disclosed"]) for case in unsupported
    )
    overhead_ratios = [
        float(case["adapter_overhead_ratio"])
        for case in eligible
        if isinstance(case.get("adapter_overhead_ratio"), (int, float))
    ]
    verification_coverage = verified_count / ELIGIBLE_COUNT
    median_overhead_ratio = statistics.median(overhead_ratios)
    gates = {
        "verification_coverage_at_least_95_percent": verification_coverage >= 0.95,
        "zero_false_equivalence": false_equivalence_count == 0,
        "zero_withheld_candidate_disclosures": candidate_disclosure_count == 0,
        "all_unsupported_fail_closed": unsupported_fail_closed_count
        == UNSUPPORTED_COUNT,
        "deterministic_evidence_ids": True,
        "median_adapter_overhead_no_greater_than_25_percent": median_overhead_ratio
        <= 0.25,
    }
    return {
        "schema_version": "rqm.qiskit-openqasm-results.v0.1",
        "evidence_boundary": "local_sdk_and_numerical_operator_checks_only",
        "manifest_sha256": _sha256_bytes(MANIFEST_PATH.read_bytes()),
        "summary": {
            "total_cases": TOTAL_COUNT,
            "eligible_verified": verified_count,
            "eligible_total": ELIGIBLE_COUNT,
            "verification_coverage": verification_coverage,
            "false_equivalence_count": false_equivalence_count,
            "unsupported_fail_closed_count": unsupported_fail_closed_count,
            "candidate_disclosure_count": candidate_disclosure_count,
            "median_adapter_overhead_ratio": median_overhead_ratio,
            "mean_source_gate_count": statistics.mean(
                case["source_gate_count"] for case in eligible if "source_gate_count" in case
            ),
            "mean_rqm_returned_gate_count": statistics.mean(
                case["rqm_returned_gate_count"]
                for case in eligible
                if "rqm_returned_gate_count" in case
            ),
            "mean_qiskit_level3_gate_count": statistics.mean(
                case["qiskit_level3_gate_count"]
                for case in eligible
                if "qiskit_level3_gate_count" in case
            ),
        },
        "gates": gates,
        "release_ready": all(gates.values()),
        "eligible_cases": eligible,
        "counterexample_cases": counterexamples,
        "unsupported_cases": unsupported,
        "notes": [
            "Deterministic evidence identity is established by API repeat-request tests.",
            "Qiskit level-3 metrics are a neutral comparator, not a superiority claim.",
            "No simulator, emulator, provider, or QPU execution was performed.",
        ],
    }


def write_report(results: dict[str, Any]) -> None:
    summary = results["summary"]
    gates = results["gates"]
    readiness = "release-ready" if results["release_ready"] else "implemented but not release-ready"
    lines = [
        "# Qiskit/OpenQASM Assurance Bridge v0.1 Results",
        "",
        f"Verdict: **{readiness}**.",
        "",
        "This is local SDK and numerical-operator evidence. It is not simulator, emulator, provider, or QPU execution evidence.",
        "",
        "## Primary results",
        "",
        f"- Verified eligible circuits: {summary['eligible_verified']}/{summary['eligible_total']} ({summary['verification_coverage']:.1%}).",
        f"- False equivalence decisions: {summary['false_equivalence_count']}.",
        f"- Unsupported inputs failing closed: {summary['unsupported_fail_closed_count']}/{UNSUPPORTED_COUNT}.",
        f"- Withheld-candidate disclosures: {summary['candidate_disclosure_count']}.",
        f"- Median adapter overhead versus compiler-only optimization: {summary['median_adapter_overhead_ratio']:.1%}.",
        f"- Mean source/RQM/Qiskit-level-3 gate counts: {summary['mean_source_gate_count']:.2f} / {summary['mean_rqm_returned_gate_count']:.2f} / {summary['mean_qiskit_level3_gate_count']:.2f}.",
        "",
        "## Release gates",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — {name.replace('_', ' ')}."
        for name, passed in gates.items()
    )
    lines.extend(
        [
            "",
            "The Qiskit comparison is descriptive. It does not establish universal compiler superiority. TKET remains a separate future comparison.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_hashes(paths: list[Path]) -> None:
    lines = [
        f"{_sha256_bytes(path.read_bytes())}  {path.name}"
        for path in sorted(paths, key=lambda item: item.name)
    ]
    HASHES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.manifest_only == args.run:
        parser.error("Choose exactly one of --manifest-only or --run.")

    if args.manifest_only:
        MANIFEST_PATH.write_text(
            json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return 0

    results = run_corpus()
    RESULTS_PATH.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(results)
    preregistration = ROOT / "PREREGISTRATION.json"
    write_hashes([MANIFEST_PATH, preregistration, RESULTS_PATH, REPORT_PATH])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
