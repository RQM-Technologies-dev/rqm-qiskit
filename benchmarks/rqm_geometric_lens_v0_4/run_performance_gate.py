#!/usr/bin/env python3
"""Measure the frozen rqm-qiskit 0.4 adapter and OpenQASM gates."""

from __future__ import annotations

import json
import math
import os
import platform
import statistics
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit, qasm3
from rqm_compiler import optimize_circuit
from rqm_qiskit import assure_openqasm3, assure_qiskit_circuit, import_qiskit_circuit
from rqm_qiskit.assurance import QiskitAssuranceResult
from rqm_qiskit._accelerator import native_build_info
from rqm_qiskit.convert import compiled_circuit_to_qiskit


ROOT = Path(__file__).resolve().parent
CORPUS = json.loads((ROOT / "corpus_manifest.json").read_text(encoding="utf-8"))
OUTPUT = Path(
    os.environ.get("RQM_PERFORMANCE_OUTPUT", ROOT / "PERFORMANCE_RESULTS.json")
)
EXPECTED_CORPUS_DIGEST = (
    "d244cfaa87ca2775c79845ae546e57e0931d5828aaee0d9b079bd12b51c16459"
)
BASELINE_ABSOLUTE_ADAPTER_MEDIAN_US = 274.994


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _circuit(record: dict[str, Any], variant: str) -> QuantumCircuit:
    a, b, c = (float(value) for value in record["angles"])
    output = QuantumCircuit(1)
    if variant == "direct":
        output.rz(a, 0)
        output.ry(b, 0)
        output.rz(c, 0)
    elif variant == "split":
        output.rz(a / 2, 0)
        output.rz(a / 2, 0)
        output.ry(b / 2, 0)
        output.ry(b / 2, 0)
        output.rz(c / 2, 0)
        output.rz(c / 2, 0)
    elif variant == "identity_inserted":
        output.rz(a, 0)
        output.rx(0.0, 0)
        output.ry(b, 0)
        output.rz(c, 0)
    elif variant == "phase_equivalent":
        output.rz(a + 2 * math.pi, 0)
        output.ry(b, 0)
        output.rz(c, 0)
    else:
        raise ValueError(variant)
    return output


def main() -> int:
    if CORPUS.get("corpus_digest") != EXPECTED_CORPUS_DIGEST:
        raise RuntimeError("Frozen EXP-014 corpus digest changed; refusing measurement")
    native_info = native_build_info()
    if not native_info.get("available"):
        raise RuntimeError("EXP-015 decision run requires the guarded native adapter")
    os.environ["RQM_QISKIT_REQUIRE_NATIVE"] = "1"

    ratios: list[float] = []
    direct_ns: list[float] = []
    qasm_ns: list[float] = []
    stage_ns = {name: [] for name in ("import", "compiler", "lowering", "report")}
    qasm_stage_ns = {name: [] for name in ("import", "assurance", "export")}
    raw_samples: list[dict[str, Any]] = []
    records = CORPUS["partitions"]["holdout"]

    warmup = _circuit(records[0], "direct")
    for _ in range(10):
        assure_qiskit_circuit(warmup)
        assure_openqasm3(qasm3.dumps(warmup))

    for record in records:
        for variant in CORPUS["variants"]:
            circuit = _circuit(record, variant)
            started = time.perf_counter_ns()
            imported = import_qiskit_circuit(circuit)
            after_import = time.perf_counter_ns()
            optimized, compiler_report = optimize_circuit(imported.circuit)
            after_compiler = time.perf_counter_ns()
            lowered = compiled_circuit_to_qiskit(optimized)
            after_lowering = time.perf_counter_ns()
            result = QiskitAssuranceResult(
                returned_circuit=lowered,
                assurance_status="VERIFIED",
                optimization_applied=compiler_report.optimization_applied,
                fallback_reason=None,
                import_report=imported.report,
                compiler_report=compiler_report,
                normalized_input=imported.circuit,
            )
            result.to_dict()
            after_report = time.perf_counter_ns()
            samples = {
                "import": after_import - started,
                "compiler": after_compiler - after_import,
                "lowering": after_lowering - after_compiler,
                "report": after_report - after_lowering,
            }
            for name, value in samples.items():
                stage_ns[name].append(float(value))
            ratios.append(
                (samples["import"] + samples["lowering"] + samples["report"])
                / samples["compiler"]
            )

            started = time.perf_counter_ns()
            assure_qiskit_circuit(circuit)
            direct_sample = float(time.perf_counter_ns() - started)
            direct_ns.append(direct_sample)
            source = qasm3.dumps(circuit)

            started = time.perf_counter_ns()
            parsed = qasm3.loads(source)
            after_qasm_import = time.perf_counter_ns()
            qasm_assurance = assure_qiskit_circuit(parsed)
            after_qasm_assurance = time.perf_counter_ns()
            qasm3.dumps(qasm_assurance.returned_circuit)
            after_qasm_export = time.perf_counter_ns()
            qasm_stage_sample = {
                "import": float(after_qasm_import - started),
                "assurance": float(after_qasm_assurance - after_qasm_import),
                "export": float(after_qasm_export - after_qasm_assurance),
            }
            for name, value in qasm_stage_sample.items():
                qasm_stage_ns[name].append(value)

            started = time.perf_counter_ns()
            assure_openqasm3(source)
            qasm_sample = float(time.perf_counter_ns() - started)
            qasm_ns.append(qasm_sample)
            raw_samples.append(
                {
                    "record_id": record["id"],
                    "variant": variant,
                    "adapter_stage_ns": samples,
                    "adapter_overhead_ratio": ratios[-1],
                    "direct_assurance_ns": direct_sample,
                    "openqasm_stage_ns": qasm_stage_sample,
                    "openqasm_complete_ns": qasm_sample,
                }
            )

    metrics = {
        "adapter_overhead_ratio_median": statistics.median(ratios),
        "absolute_adapter_time_median_us": statistics.median(
            [
                sample["adapter_stage_ns"]["import"]
                + sample["adapter_stage_ns"]["lowering"]
                + sample["adapter_stage_ns"]["report"]
                for sample in raw_samples
            ]
        )
        / 1e3,
        "direct_assurance_p95_ms": _percentile(direct_ns, 0.95) / 1e6,
        "openqasm_assurance_p95_ms": _percentile(qasm_ns, 0.95) / 1e6,
        "openqasm_stage_p95_ms": {
            name: _percentile(values, 0.95) / 1e6
            for name, values in qasm_stage_ns.items()
        },
        "stage_medians_us": {
            name: statistics.median(values) / 1e3 for name, values in stage_ns.items()
        },
        "sample_count": len(ratios),
    }
    gates = {
        "adapter_overhead_ratio": metrics["adapter_overhead_ratio_median"] <= 0.25,
        "absolute_adapter_time_improved": metrics[
            "absolute_adapter_time_median_us"
        ]
        < BASELINE_ABSOLUTE_ADAPTER_MEDIAN_US,
        "direct_assurance_p95": metrics["direct_assurance_p95_ms"] <= 5.0,
        "openqasm_assurance_p95": metrics["openqasm_assurance_p95_ms"] <= 25.0,
        "openqasm_import_p95": metrics["openqasm_stage_p95_ms"]["import"] <= 25.0,
        "openqasm_processing_p95": metrics["openqasm_stage_p95_ms"]["assurance"]
        <= 25.0,
        "openqasm_export_p95": metrics["openqasm_stage_p95_ms"]["export"] <= 25.0,
    }
    payload = {
        "schema_version": "1.0",
        "corpus_digest": CORPUS["corpus_digest"],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "qiskit": version("qiskit"),
            "rqm_qiskit": version("rqm-qiskit"),
            "rqm_compiler": version("rqm-compiler"),
            "native_adapter": native_info,
        },
        "thresholds": {
            "adapter_overhead_ratio_max": 0.25,
            "baseline_absolute_adapter_median_us": BASELINE_ABSOLUTE_ADAPTER_MEDIAN_US,
            "direct_assurance_p95_ms_max": 5.0,
            "openqasm_assurance_p95_ms_max": 25.0,
            "openqasm_each_stage_p95_ms_max": 25.0,
        },
        "metrics": metrics,
        "raw_samples": raw_samples,
        "gates": gates,
        "release_gate_passed": all(gates.values()),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "raw_samples"}, indent=2))
    return 0 if payload["release_gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
