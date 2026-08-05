#!/usr/bin/env python3
"""Run the frozen EXP-016 hybrid quaternionic explanation gate."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import qiskit
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qasm3
from qiskit.circuit import Parameter
from qiskit.circuit.library import QFTGate, UnitaryGate
from qiskit.quantum_info import Operator, Statevector
from rqm_qiskit import analyze_qiskit_circuit, analyze_qiskit_state


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "EXP-016_PREREGISTRATION.json"
CORPUS_PATH = ROOT / "EXP-016_CORPUS_MANIFEST.json"
RAW_PATH = ROOT / "EXP-016_RAW_RESULTS.json"
TOLERANCE = 1e-9


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * 0.95
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _git_head(path: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _rqm_qiskit_root() -> Path:
    import rqm_qiskit

    return Path(rqm_qiskit.__file__).resolve().parents[2]


def _one_qubit_circuits() -> dict[str, QuantumCircuit]:
    circuits: dict[str, QuantumCircuit] = {}
    circuits["1q_identity"] = QuantumCircuit(1)
    for identifier, name in (
        ("1q_x", "x"),
        ("1q_h", "h"),
        ("1q_s", "s"),
        ("1q_t", "t"),
    ):
        circuit = QuantumCircuit(1)
        getattr(circuit, name)(0)
        circuits[identifier] = circuit
    for identifier, name in (
        ("1q_rx_pi_2", "rx"),
        ("1q_ry_pi_2", "ry"),
        ("1q_rz_pi_2", "rz"),
    ):
        circuit = QuantumCircuit(1)
        getattr(circuit, name)(math.pi / 2, 0)
        circuits[identifier] = circuit
    noncommuting = QuantumCircuit(1)
    noncommuting.rx(0.37, 0)
    noncommuting.ry(-0.81, 0)
    circuits["1q_noncommuting_rx_ry"] = noncommuting
    zyz = QuantumCircuit(1)
    zyz.rz(0.37, 0)
    zyz.ry(-0.81, 0)
    zyz.rz(1.13, 0)
    circuits["1q_zyz_general"] = zyz
    global_phase = QuantumCircuit(1, global_phase=math.pi / 7)
    global_phase.x(0)
    circuits["1q_global_phase"] = global_phase
    terminal = QuantumCircuit(1, 1)
    terminal.ry(math.pi / 3, 0)
    terminal.measure(0, 0)
    circuits["1q_terminal_measurement"] = terminal
    matrix = np.exp(0.23j) * np.asarray(
        [[math.cos(0.2), -math.sin(0.2)], [math.sin(0.2), math.cos(0.2)]],
        dtype=np.complex128,
    )
    public_unitary = QuantumCircuit(1)
    public_unitary.append(UnitaryGate(matrix), [0])
    circuits["1q_public_unitary"] = public_unitary
    return circuits


def _two_qubit_circuits() -> dict[str, QuantumCircuit]:
    circuits: dict[str, QuantumCircuit] = {}
    product = QuantumCircuit(2)
    product.h(0)
    product.x(1)
    circuits["2q_product"] = product
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    circuits["2q_bell"] = bell
    cz = QuantumCircuit(2)
    cz.h(0)
    cz.h(1)
    cz.cz(0, 1)
    circuits["2q_cz"] = cz
    iswap = QuantumCircuit(2)
    iswap.x(0)
    iswap.iswap(0, 1)
    circuits["2q_iswap"] = iswap
    swap = QuantumCircuit(2)
    swap.x(0)
    swap.swap(0, 1)
    circuits["2q_swap"] = swap
    rxx = QuantumCircuit(2)
    rxx.rxx(math.pi / 4, 0, 1)
    circuits["2q_rxx_pi_4"] = rxx
    local_equivalent = QuantumCircuit(2)
    local_equivalent.h(1)
    local_equivalent.cx(0, 1)
    local_equivalent.h(1)
    circuits["2q_local_equivalent_cx"] = local_equivalent
    unitary_source = QuantumCircuit(2)
    unitary_source.ry(0.31, 0)
    unitary_source.rz(-0.42, 1)
    unitary_source.cx(0, 1)
    unitary_source.rx(0.19, 1)
    public_unitary = QuantumCircuit(2)
    public_unitary.append(UnitaryGate(Operator(unitary_source).data), [0, 1])
    circuits["2q_public_unitary"] = public_unitary
    qreg = QuantumRegister(2, "science")
    creg = ClassicalRegister(2, "readout")
    terminal = QuantumCircuit(qreg, creg)
    terminal.h(qreg[0])
    terminal.cx(qreg[0], qreg[1])
    terminal.measure(qreg[0], creg[1])
    terminal.measure(qreg[1], creg[0])
    circuits["2q_terminal_measurement_reversed"] = terminal
    return circuits


def _states() -> dict[str, Statevector]:
    general = Statevector([1 / math.sqrt(3), math.sqrt(2 / 3) * 1j])
    return {
        "state_zero": Statevector.from_label("0"),
        "state_one": Statevector.from_label("1"),
        "state_plus": Statevector([1 / math.sqrt(2), 1 / math.sqrt(2)]),
        "state_plus_i": Statevector([1 / math.sqrt(2), 1j / math.sqrt(2)]),
        "state_general": general,
        "state_general_negative": Statevector(-general.data),
    }


def _boundaries() -> dict[str, QuantumCircuit]:
    theta = Parameter("theta")
    symbolic = QuantumCircuit(1)
    symbolic.rx(theta, 0)
    reset = QuantumCircuit(1)
    reset.reset(0)
    initialize = QuantumCircuit(1)
    initialize.initialize([1, 0], 0)
    mid_measurement = QuantumCircuit(1, 1)
    mid_measurement.h(0)
    mid_measurement.measure(0, 0)
    mid_measurement.x(0)
    control_flow = QuantumCircuit(1, 1)
    with control_flow.if_test((control_flow.clbits[0], True)):
        control_flow.x(0)
    ghz = QuantumCircuit(3)
    ghz.h(0)
    ghz.cx(0, 1)
    ghz.cx(1, 2)
    qft = QuantumCircuit(3)
    qft.append(QFTGate(3), range(3))
    regional = QuantumCircuit(6)
    for qubit in range(6):
        regional.rx(0.1 + qubit * 0.01, qubit)
        regional.ry(-0.2, qubit)
    return {
        "boundary_symbolic": symbolic,
        "boundary_reset": reset,
        "boundary_initialize": initialize,
        "boundary_mid_circuit_measurement": mid_measurement,
        "boundary_control_flow": control_flow,
        "boundary_ghz_3q": ghz,
        "boundary_qft_3q": qft,
        "boundary_regional_6q": regional,
    }


def _corpus(policy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    objects: dict[str, Any] = {}
    categories = {
        "one_qubit_circuits": _one_qubit_circuits(),
        "two_qubit_circuits": _two_qubit_circuits(),
        "states": _states(),
        "partial_boundaries": _boundaries(),
    }
    manifest_records = []
    for category, identifiers in policy["records"].items():
        built = categories[category]
        if set(identifiers) != set(built):
            raise RuntimeError(
                f"Frozen {category} identifiers do not match the builder."
            )
        for identifier in identifiers:
            value = built[identifier]
            objects[identifier] = value
            if isinstance(value, QuantumCircuit):
                manifest_records.append(
                    {
                        "id": identifier,
                        "category": category,
                        "num_qubits": value.num_qubits,
                        "num_clbits": value.num_clbits,
                        "operations": [item.operation.name for item in value.data],
                    }
                )
            else:
                manifest_records.append(
                    {
                        "id": identifier,
                        "category": category,
                        "dimension": len(value.data),
                        "amplitudes": [
                            {"real": float(item.real), "imag": float(item.imag)}
                            for item in value.data
                        ],
                    }
                )
    manifest = {
        "schema_version": "1.0",
        "experiment_id": "EXP-016",
        "records": manifest_records,
    }
    manifest["corpus_digest"] = _digest(manifest_records)
    return objects, manifest


def _semantic_circuit(circuit: QuantumCircuit) -> QuantumCircuit:
    return circuit.remove_final_measurements(inplace=False)


def _matrix(payload: list[list[dict[str, float]]]) -> np.ndarray:
    return np.asarray(
        [[complex(value["real"], value["imag"]) for value in row] for row in payload],
        dtype=np.complex128,
    )


def _probability_error(report: Any, state: Statevector) -> float:
    predicted = report.measurement_predictions["probabilities"]
    qubits = int(round(math.log2(len(state.data))))
    expected = {
        format(index, f"0{qubits}b"): float(value)
        for index, value in enumerate(state.probabilities())
    }
    return max(abs(float(predicted[key]) - expected[key]) for key in expected)


def _analyze_record(
    identifier: str,
    category: str,
    value: Any,
    repetitions: int,
) -> dict[str, Any]:
    direct_ms: list[float] = []
    texts: list[str] = []
    payloads: list[str] = []
    input_unchanged = True
    numeric_error = 0.0
    explanation_keys: list[str] = []
    status = "error"
    terminal_mapping: Any = None

    original = value.copy() if isinstance(value, QuantumCircuit) else value.copy()
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        report = (
            analyze_qiskit_circuit(value)
            if isinstance(value, QuantumCircuit)
            else analyze_qiskit_state(value)
        )
        text = report.to_text("technical")
        direct_ms.append((time.perf_counter_ns() - start) / 1_000_000)
        texts.append(text)
        payloads.append(_canonical_json(report.to_dict()))
        status = report.status
        explanation_keys = [section.key for section in report.explanation.sections]
        terminal_mapping = report.circuit_summary.get("terminal_measurements")
        if isinstance(value, QuantumCircuit):
            input_unchanged = input_unchanged and value == original
        else:
            input_unchanged = input_unchanged and np.array_equal(
                value.data, original.data
            )

    deterministic = len(set(texts)) == 1 and len(set(payloads)) == 1
    report_payload = json.loads(payloads[0])
    complete_expected = category != "partial_boundaries"
    status_ok = (
        status == "complete"
        if complete_expected
        else status in {"partial", "unsupported"}
    )
    explanatory_ok = True
    if category == "one_qubit_circuits":
        explanatory_ok = {
            "quaternion",
            "rotation",
            "bloch",
            "phase",
            "measurement",
            "limitations",
        }.issubset(explanation_keys)
        local = report_payload["local_geometry"][0]
        reconstructed = np.exp(
            1j * local["operator_global_phase"]["radians"]
        ) * _matrix(local["su2_matrix"])
        operator = np.asarray(Operator(_semantic_circuit(value)).data)
        numeric_error = max(
            float(np.max(np.abs(reconstructed - operator))),
            _probability_error(
                report, Statevector.from_instruction(_semantic_circuit(value))
            ),
        )
    elif category == "two_qubit_circuits":
        explanatory_ok = {
            "su4_weyl",
            "entanglement",
            "measurement",
            "limitations",
        }.issubset(explanation_keys)
        numeric_error = max(
            float(
                report_payload["nonlocal_geometry"][0]["su4"]["reconstruction_error"]
            ),
            _probability_error(
                report, Statevector.from_instruction(_semantic_circuit(value))
            ),
        )
    elif category == "states":
        numeric_error = _probability_error(report, value)
    else:
        unavailable = set(report_payload["not_computed"])
        narrated = (
            "The geometric axis is" in texts[0]
            or "The nonlocal Weyl coordinates are" in texts[0]
        )
        explanatory_ok = bool(unavailable) and not narrated

    return {
        "id": identifier,
        "category": category,
        "status": status,
        "status_ok": status_ok,
        "deterministic_five_runs": deterministic,
        "input_unchanged": input_unchanged,
        "explanatory_coverage_ok": explanatory_ok,
        "numeric_max_error": numeric_error,
        "numeric_ok": numeric_error <= TOLERANCE,
        "terminal_measurement_mapping": terminal_mapping,
        "direct_explanation_ms": direct_ms,
        "text_sha256": hashlib.sha256(texts[0].encode("utf-8")).hexdigest(),
        "json_sha256": hashlib.sha256(payloads[0].encode("utf-8")).hexdigest(),
    }


def _openqasm_samples(
    objects: dict[str, Any], repetitions: int
) -> tuple[list[float], list[str]]:
    samples: list[float] = []
    included: list[str] = []
    for identifier, value in objects.items():
        if not isinstance(value, QuantumCircuit) or value.num_qubits > 2:
            continue
        try:
            source = qasm3.dumps(value)
            qasm3.loads(source)
        except Exception:  # public UnitariyGate may not round-trip through OpenQASM
            continue
        included.append(identifier)
        for _ in range(repetitions):
            start = time.perf_counter_ns()
            report = analyze_qiskit_circuit(qasm3.loads(source))
            report.to_text("standard")
            samples.append((time.perf_counter_ns() - start) / 1_000_000)
    return samples, included


def _private_api_violations(source_root: Path) -> list[str]:
    forbidden = re.compile(r"(?:from|import)\s+qiskit\._|\.\_data\b")
    violations = []
    for path in source_root.rglob("*"):
        if path.suffix not in {".py", ".c", ".h"}:
            continue
        if forbidden.search(path.read_text(encoding="utf-8")):
            violations.append(str(path.relative_to(source_root)))
    return sorted(violations)


def main() -> int:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    objects, manifest = _corpus(policy)
    categories = {
        identifier: category
        for category, identifiers in policy["records"].items()
        for identifier in identifiers
    }
    repetitions = int(policy["repetitions_per_record"])

    # Warm public Qiskit and RQM paths before prospective timing.
    analyze_qiskit_circuit(objects["1q_identity"]).to_text("standard")
    analyze_qiskit_circuit(objects["2q_product"]).to_text("standard")

    records = [
        _analyze_record(
            identifier, categories[identifier], objects[identifier], repetitions
        )
        for identifier in categories
    ]
    direct_samples = [
        sample
        for record in records
        if record["category"] in {"one_qubit_circuits", "two_qubit_circuits"}
        for sample in record["direct_explanation_ms"]
    ]
    qasm_samples, qasm_records = _openqasm_samples(objects, repetitions)
    qiskit_root = _rqm_qiskit_root()
    private_violations = _private_api_violations(qiskit_root / "src" / "rqm_qiskit")
    direct_p95 = _p95(direct_samples)
    qasm_p95 = _p95(qasm_samples)
    record_gate = all(
        record["status_ok"]
        and record["deterministic_five_runs"]
        and record["input_unchanged"]
        and record["explanatory_coverage_ok"]
        and record["numeric_ok"]
        for record in records
    )
    performance_gate = (
        direct_p95 <= policy["latency_thresholds_ms"]["direct_explanation_p95_max"]
        and qasm_p95 <= policy["latency_thresholds_ms"]["openqasm_explanation_p95_max"]
    )
    passed = record_gate and performance_gate and not private_violations
    raw = {
        "schema_version": "1.0",
        "experiment_id": "EXP-016",
        "decision": "pass" if passed else "fail",
        "corpus_digest": manifest["corpus_digest"],
        "record_count": len(records),
        "repetitions_per_record": repetitions,
        "records": records,
        "summary": {
            "complete_records": sum(
                record["status"] == "complete" for record in records
            ),
            "partial_or_unsupported_records": sum(
                record["status"] in {"partial", "unsupported"} for record in records
            ),
            "deterministic_records": sum(
                record["deterministic_five_runs"] for record in records
            ),
            "unchanged_inputs": sum(record["input_unchanged"] for record in records),
            "numeric_records_within_tolerance": sum(
                record["numeric_ok"] for record in records
            ),
            "explanatory_coverage_records": sum(
                record["explanatory_coverage_ok"] for record in records
            ),
            "direct_explanation_p95_ms": direct_p95,
            "direct_explanation_median_ms": statistics.median(direct_samples),
            "openqasm_explanation_p95_ms": qasm_p95,
            "openqasm_explanation_median_ms": statistics.median(qasm_samples),
            "openqasm_records": qasm_records,
            "private_qiskit_api_violations": private_violations,
            "record_gate_passed": record_gate,
            "absolute_latency_gate_passed": performance_gate,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "qiskit": qiskit.__version__,
            "rqm_qiskit_commit": _git_head(qiskit_root),
            "rqm_experiments_commit": "sanitized-public-mirror-c156e6e",
            "provider": "local-only",
            "network": False,
            "hardware": False,
        },
    }
    CORPUS_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    RAW_PATH.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(raw["summary"], indent=2))
    print(f"EXP-016 decision: {raw['decision']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
