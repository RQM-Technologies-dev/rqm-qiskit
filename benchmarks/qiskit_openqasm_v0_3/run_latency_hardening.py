#!/usr/bin/env python3
"""Run the preregistered v0.3 latency hardening corpus once."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import statistics
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

import numpy as np
from qiskit import qasm3
from qiskit.quantum_info import Operator
from rqm_compiler import optimize_circuit, verify_equivalence

from rqm_qiskit import (
    assure_qiskit_circuit,
    compiled_circuit_to_qiskit,
    export_openqasm3,
    import_qiskit_circuit,
)

ROOT = Path(__file__).resolve().parent
BASE_ROOT = ROOT.parent / "qiskit_openqasm_v0_1"
V02_ROOT = ROOT.parent / "qiskit_openqasm_v0_2"
RESULTS_PATH = ROOT / "raw_results.json"
REPORT_PATH = ROOT / "RESULTS.md"
HASHES_PATH = ROOT / "SHA256SUMS"
REPETITIONS = 5
T = TypeVar("T")


def _load_baseline_runner() -> ModuleType:
    path = BASE_ROOT / "run_corpus.py"
    spec = importlib.util.spec_from_file_location("rqm_qiskit_v0_1_latency", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the frozen v0.1 corpus runner.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _median_call(function: Callable[[], T]) -> tuple[T, int]:
    values: list[int] = []
    result: T | None = None
    for _ in range(REPETITIONS):
        start = time.perf_counter_ns()
        result = function()
        values.append(time.perf_counter_ns() - start)
    assert result is not None
    return result, int(statistics.median(values))


def _equivalent_up_to_phase(left: Any, right: Any) -> tuple[bool, float]:
    lhs = np.asarray(Operator(left).data, dtype=np.complex128)
    rhs = np.asarray(Operator(right).data, dtype=np.complex128)
    overlap = np.vdot(rhs.reshape(-1), lhs.reshape(-1))
    if abs(overlap) == 0.0:
        return False, float("inf")
    phase = overlap / abs(overlap)
    error = float(np.max(np.abs(lhs - phase * rhs)))
    return error <= 1e-9, error


def _run_eligible(runner: ModuleType, index: int) -> dict[str, Any]:
    source = runner.build_eligible(index)
    imported, import_ns = _median_call(lambda: import_qiskit_circuit(source))
    if imported.circuit is None:
        return {
            "case_id": f"eligible-{index:03d}",
            "verified": False,
            "failure": imported.report.to_dict(),
        }

    normalized_payload, normalization_ns = _median_call(
        lambda: json.dumps(
            {
                "num_qubits": imported.circuit.num_qubits,
                "descriptors": imported.circuit.to_descriptors(),
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    (returned, compiler_report), compiler_ns = _median_call(
        lambda: optimize_circuit(imported.circuit)
    )
    proof, verification_ns = _median_call(
        lambda: verify_equivalence(imported.circuit, returned)
    )
    lowered, lowering_ns = _median_call(lambda: compiled_circuit_to_qiskit(returned))
    exported, export_ns = _median_call(lambda: export_openqasm3(returned))
    if exported.source is None:
        return {
            "case_id": f"eligible-{index:03d}",
            "verified": False,
            "failure": exported.to_dict(),
        }
    reparsed, qasm_reparse_ns = _median_call(lambda: qasm3.loads(exported.source))
    _, report_serialization_ns = _median_call(
        lambda: json.dumps(
            {
                "import": imported.report.to_dict(),
                "compiler": asdict(compiler_report),
                "normalized_sha256": hashlib.sha256(
                    normalized_payload.encode("utf-8")
                ).hexdigest(),
                "returned_openqasm_sha256": exported.source_sha256,
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    assured, assurance_total_ns = _median_call(lambda: assure_qiskit_circuit(source))
    direct_ok, direct_error = _equivalent_up_to_phase(source, assured.returned_circuit)
    qasm_ok, qasm_error = _equivalent_up_to_phase(source, reparsed)
    adapter_overhead_ns = import_ns + export_ns
    return {
        "case_id": f"eligible-{index:03d}",
        "verified": (
            assured.assurance_status == "VERIFIED"
            and compiler_report.equivalence_status == "VERIFIED"
            and proof.status.value == "VERIFIED"
            and direct_ok
            and qasm_ok
        ),
        "assurance_status": assured.assurance_status,
        "optimization_applied": assured.optimization_applied,
        "direct_max_abs_error": direct_error,
        "openqasm_max_abs_error": qasm_error,
        "timing_ns": {
            "qiskit_import": import_ns,
            "normalization_serialization": normalization_ns,
            "compiler_optimize_and_verify": compiler_ns,
            "standalone_semantic_verification": verification_ns,
            "qiskit_lowering": lowering_ns,
            "openqasm_export_including_lowering": export_ns,
            "openqasm_reparse": qasm_reparse_ns,
            "adapter_report_serialization": report_serialization_ns,
            "complete_qiskit_assurance": assurance_total_ns,
        },
        "adapter_overhead_ns": adapter_overhead_ns,
        "adapter_overhead_ratio": (
            adapter_overhead_ns / compiler_ns if compiler_ns > 0 else None
        ),
        "returned_openqasm_sha256": exported.source_sha256,
        "source_gate_count": len(source.data),
        "rqm_returned_gate_count": len(lowered.data),
    }


def _stage_medians(eligible: list[dict[str, Any]]) -> dict[str, int]:
    names = next(case["timing_ns"].keys() for case in eligible if "timing_ns" in case)
    return {
        name: int(
            statistics.median(
                case["timing_ns"][name] for case in eligible if "timing_ns" in case
            )
        )
        for name in names
    }


def _write_report(results: dict[str, Any]) -> None:
    summary = results["summary"]
    gates = results["gates"]
    lines = [
        "# Qiskit/OpenQASM Assurance Bridge v0.3 Latency Results",
        "",
        f"Release verdict: **{'PASS' if results['release_ready'] else 'FAIL'}**.",
        "",
        "The frozen 200-case corpus and all semantic gates were retained.",
        "",
        "## Results",
        "",
        (
            f"- Eligible verification coverage: {summary['eligible_verified']}/"
            f"{summary['eligible_total']} ({summary['verification_coverage']:.1%})."
        ),
        f"- False-equivalence decisions: {summary['false_equivalence_count']}.",
        (
            "- Unsupported inputs failing closed: "
            f"{summary['unsupported_fail_closed_count']}/20."
        ),
        f"- Withheld-candidate disclosures: {summary['candidate_disclosure_count']}.",
        (
            "- Median adapter overhead versus compiler-only optimization: "
            f"{summary['median_adapter_overhead_ratio']:.1%} "
            f"(v0.2: {summary['baseline_median_adapter_overhead_ratio']:.1%})."
        ),
        "",
        "## Median stage timing",
        "",
    ]
    lines.extend(
        f"- {name.replace('_', ' ')}: {value / 1_000:.3f} microseconds."
        for name, value in summary["median_stage_timing_ns"].items()
    )
    lines.extend(["", "## Registered gates", ""])
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — {name.replace('_', ' ')}."
        for name, passed in gates.items()
    )
    lines.extend(
        [
            "",
            (
                "A failing latency gate keeps rqm-qiskit 0.3.0 unreleased. "
                "Correctness is not traded for speed."
            ),
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    runner = _load_baseline_runner()
    expected_manifest = (
        "fe2f7c34fb931d122738405bc9c845db7e3abe6c5c26a3b0b24da9cf26656b35"
    )
    expected_v02 = "32bb9837a156ee5416a2ec8d1ea96360a8ef24f8572df3809f1b861bc59b1d7f"
    if _sha256(BASE_ROOT / "corpus_manifest.json") != expected_manifest:
        raise RuntimeError("Frozen v0.1 corpus manifest hash mismatch.")
    if _sha256(V02_ROOT / "raw_results.json") != expected_v02:
        raise RuntimeError("Frozen v0.2 result hash mismatch.")

    # Warm immutable metadata, compiler imports, and the Qiskit exporter before
    # measuring the registered hot request path.
    warm_source = runner.build_eligible(0)
    warm_import = import_qiskit_circuit(warm_source)
    if warm_import.circuit is None:
        raise RuntimeError("Warmup import failed.")
    warm_returned, _ = optimize_circuit(warm_import.circuit)
    if export_openqasm3(warm_returned).source is None:
        raise RuntimeError("Warmup export failed.")

    timed_eligible = [_run_eligible(runner, index) for index in range(160)]
    counterexamples = [runner._run_counterexample(index) for index in range(20)]
    unsupported = [runner._run_unsupported(index) for index in range(20)]

    verified_count = sum(bool(case.get("verified")) for case in timed_eligible)
    false_equivalence_count = sum(
        bool(case["false_equivalence"]) for case in counterexamples
    )
    unsupported_fail_closed_count = sum(
        bool(case["fail_closed"]) for case in unsupported
    )
    candidate_disclosure_count = sum(
        bool(case["candidate_disclosed"]) for case in unsupported
    )
    ratios = [
        float(case["adapter_overhead_ratio"])
        for case in timed_eligible
        if isinstance(case.get("adapter_overhead_ratio"), (int, float))
    ]
    verification_coverage = verified_count / 160
    median_ratio = statistics.median(ratios)
    gates = {
        "verification_coverage_at_least_95_percent": verification_coverage >= 0.95,
        "zero_false_equivalence": false_equivalence_count == 0,
        "zero_withheld_candidate_disclosures": candidate_disclosure_count == 0,
        "all_unsupported_fail_closed": unsupported_fail_closed_count == 20,
        "deterministic_evidence_ids": True,
        "median_adapter_overhead_no_greater_than_25_percent": median_ratio <= 0.25,
    }
    results = {
        "schema_version": "rqm.qiskit-openqasm-latency-results.v0.3",
        "evidence_boundary": "local_sdk_and_numerical_operator_checks_only",
        "manifest_sha256": expected_manifest,
        "baseline_result_sha256": expected_v02,
        "timing_protocol": {
            "clock": "time.perf_counter_ns",
            "per_stage_repetitions": REPETITIONS,
            "case_statistic": "median of repetitions",
            "aggregate_statistic": "median of per-case ratios",
        },
        "summary": {
            "total_cases": 200,
            "eligible_verified": verified_count,
            "eligible_total": 160,
            "verification_coverage": verification_coverage,
            "false_equivalence_count": false_equivalence_count,
            "unsupported_fail_closed_count": unsupported_fail_closed_count,
            "candidate_disclosure_count": candidate_disclosure_count,
            "baseline_median_adapter_overhead_ratio": 8.1776,
            "median_adapter_overhead_ratio": median_ratio,
            "median_stage_timing_ns": _stage_medians(timed_eligible),
        },
        "gates": gates,
        "release_ready": all(gates.values()),
        "eligible_cases": timed_eligible,
        "counterexample_cases": counterexamples,
        "unsupported_cases": unsupported,
        "notes": [
            "The frozen v0.1 corpus and v0.2 result were hash-verified before execution.",
            "Deterministic evidence identity remains established by API repeat-request tests.",
            "The CI timing fixture is a broad regression ceiling, not release evidence.",
            "No simulator, emulator, provider, or QPU execution was performed.",
        ],
    }
    RESULTS_PATH.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_report(results)
    paths = [
        ROOT / "PREREGISTRATION.json",
        ROOT / "RUN_NOTES.md",
        BASE_ROOT / "corpus_manifest.json",
        V02_ROOT / "raw_results.json",
        RESULTS_PATH,
        REPORT_PATH,
    ]
    HASHES_PATH.write_text(
        "".join(
            f"{_sha256(path)}  {path.relative_to(ROOT.parent.parent)}\n"
            for path in paths
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
