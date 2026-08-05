#!/usr/bin/env python3
"""Run the frozen EXP-014 RQM-Qiskit circuit-lens experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import qiskit
from qiskit import QuantumCircuit, qasm3, transpile
from qiskit.quantum_info import Operator, Statevector
from rqm_core import (
    measurement_probabilities,
    spinor_to_quaternion,
    state_to_bloch,
    su2_to_quaternion,
)
from rqm_entanglement import decompose_su4_verified, nonlocal_fingerprint
from rqm_qiskit import assure_qiskit_circuit


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "PREREGISTRATION.json"
CORPUS_PATH = ROOT / "corpus_manifest.json"
RAW_PATH = ROOT / "raw_results.json"
SEED = 20260805
ROUND_DIGITS = 11


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(payload: Any) -> str:
    return _sha256_bytes(_canonical_json(payload).encode("utf-8"))


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _bootstrap_median_interval(
    values: list[float],
    *,
    seed: int,
    resamples: int,
    confidence_level: float,
) -> list[float]:
    rng = random.Random(seed)
    medians = []
    for _ in range(resamples):
        sample = [values[rng.randrange(len(values))] for _ in values]
        medians.append(float(statistics.median(sample)))
    tail = (1.0 - confidence_level) / 2.0
    return [_percentile(medians, tail), _percentile(medians, 1.0 - tail)]


def _phase_aligned_error(left: np.ndarray, right: np.ndarray) -> float:
    overlap = np.vdot(left.reshape(-1), right.reshape(-1))
    if abs(overlap) > 1e-15:
        right = right * np.exp(-1j * np.angle(overlap))
    return float(np.max(np.abs(left - right)))


def _canonical_quaternion_payload(unitary: np.ndarray) -> dict[str, Any]:
    determinant = np.linalg.det(unitary)
    if abs(determinant) < 1e-15:
        raise ValueError("Single-qubit unitary has a singular determinant.")
    su2 = unitary / np.sqrt(determinant)
    quaternion = su2_to_quaternion(su2).canonicalize()
    components = []
    for value in (quaternion.w, quaternion.x, quaternion.y, quaternion.z):
        normalized = 0.0 if abs(float(value)) < 5e-12 else round(float(value), ROUND_DIGITS)
        components.append(normalized)
    return {
        "convention": "rqm-core-su2-quaternion-sign-canonical-v1",
        "round_digits": ROUND_DIGITS,
        "components": components,
        "fingerprint": _digest(components),
    }


def _qiskit_serialized_fingerprint(circuit: QuantumCircuit, policy: dict[str, Any]) -> str:
    compiled = transpile(
        circuit,
        basis_gates=policy["basis_gates"],
        optimization_level=policy["qiskit_optimization_level"],
        seed_transpiler=policy["qiskit_transpiler_seed"],
    )
    return _sha256_bytes(qasm3.dumps(compiled).encode("utf-8"))


def _native_metrics(circuit: QuantumCircuit, policy: dict[str, Any]) -> dict[str, int]:
    compiled = transpile(
        circuit,
        basis_gates=policy["basis_gates"],
        optimization_level=policy["qiskit_optimization_level"],
        seed_transpiler=policy["qiskit_transpiler_seed"],
    )
    counts = compiled.count_ops()
    return {
        "one_qubit_cost": int(sum(int(counts.get(name, 0)) for name in ("rz", "sx", "x"))),
        "two_qubit_cost": int(counts.get("cx", 0)),
        "depth": int(compiled.depth()),
    }


def _build_variant(record: dict[str, Any], variant: str) -> QuantumCircuit:
    a, b, c = (float(value) for value in record["angles"])
    circuit = QuantumCircuit(1, name=f"{record['id']}-{variant}")
    if variant == "direct":
        circuit.rz(a, 0)
        circuit.ry(b, 0)
        circuit.rz(c, 0)
    elif variant == "split":
        circuit.rz(a / 2.0, 0)
        circuit.rz(a / 2.0, 0)
        circuit.ry(b / 2.0, 0)
        circuit.ry(b / 2.0, 0)
        circuit.rz(c / 2.0, 0)
        circuit.rz(c / 2.0, 0)
    elif variant == "identity_inserted":
        circuit.rz(a, 0)
        circuit.rx(0.0, 0)
        circuit.ry(b, 0)
        circuit.rz(c, 0)
    elif variant == "phase_equivalent":
        circuit.rz(a + 2.0 * math.pi, 0)
        circuit.ry(b, 0)
        circuit.rz(c, 0)
    elif variant == "inequivalent_control":
        circuit.rz(a, 0)
        circuit.ry(b, 0)
        circuit.rz(c + float(record["control_offset"]), 0)
    else:
        raise ValueError(f"Unknown variant {variant!r}")
    return circuit


def _generate_corpus(policy: dict[str, Any]) -> dict[str, Any]:
    rng = random.Random(int(policy["seed"]))
    partitions: dict[str, list[dict[str, Any]]] = {}
    for partition, count_key in (
        ("discovery", "discovery_families"),
        ("holdout", "holdout_families"),
    ):
        records = []
        for index in range(int(policy["partitions"][count_key])):
            angles = [rng.uniform(-math.pi, math.pi) for _ in range(3)]
            records.append(
                {
                    "id": f"{partition}-{index:03d}",
                    "angles": angles,
                    "control_offset": 0.125 + 0.001 * (index % 11),
                }
            )
        partitions[partition] = records
    body = {
        "schema_version": "1.0",
        "experiment_id": "EXP-014",
        "seed": int(policy["seed"]),
        "generator": "zyz-equivalent-families-v1",
        "variants": ["direct", "split", "identity_inserted", "phase_equivalent"],
        "partitions": partitions,
    }
    body["corpus_digest"] = _digest(body)
    return body


def _run_family(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    variant_names = ["direct", "split", "identity_inserted", "phase_equivalent"]
    source_reference = Operator(_build_variant(record, "direct")).data
    rqm_fingerprints: list[str] = []
    qiskit_fingerprints: list[str] = []
    errors: list[float] = []
    statuses: list[str] = []
    direct_latencies_ns: list[int] = []
    qiskit_latencies_ns: list[int] = []
    native_deltas: list[int] = []
    native_improvements: list[float] = []

    for variant_name in variant_names:
        circuit = _build_variant(record, variant_name)
        started = time.perf_counter_ns()
        assured = assure_qiskit_circuit(circuit)
        direct_latencies_ns.append(time.perf_counter_ns() - started)
        statuses.append(str(assured.assurance_status))
        assured_unitary = Operator(assured.returned_circuit).data
        errors.append(_phase_aligned_error(source_reference, assured_unitary))
        rqm_fingerprints.append(_canonical_quaternion_payload(assured_unitary)["fingerprint"])

        started = time.perf_counter_ns()
        qiskit_fingerprints.append(_qiskit_serialized_fingerprint(circuit, policy))
        qiskit_latencies_ns.append(time.perf_counter_ns() - started)

        source_native = _native_metrics(circuit, policy)
        rqm_native = _native_metrics(assured.returned_circuit, policy)
        native_deltas.append(source_native["one_qubit_cost"] - rqm_native["one_qubit_cost"])
        native_improvements.append(
            (source_native["one_qubit_cost"] - rqm_native["one_qubit_cost"])
            / source_native["one_qubit_cost"]
        )

    control = _build_variant(record, "inequivalent_control")
    control_result = assure_qiskit_circuit(control)
    control_fingerprint = _canonical_quaternion_payload(
        Operator(control_result.returned_circuit).data
    )["fingerprint"]

    return {
        "id": record["id"],
        "rqm_converged": len(set(rqm_fingerprints)) == 1,
        "qiskit_serialization_converged": len(set(qiskit_fingerprints)) == 1,
        "control_collision": control_fingerprint == rqm_fingerprints[0],
        "statuses": statuses,
        "max_phase_aligned_error": max(errors),
        "native_one_qubit_cost_deltas": native_deltas,
        "native_one_qubit_cost_improvements": native_improvements,
        "rqm_direct_latencies_ns": direct_latencies_ns,
        "qiskit_transpile_latencies_ns": qiskit_latencies_ns,
    }


def _summarize_partition(
    records: list[dict[str, Any]],
    policy: dict[str, Any],
    *,
    bootstrap_seed: int,
) -> dict[str, Any]:
    rows = [_run_family(record, policy) for record in records]
    rqm_convergence = statistics.fmean(float(row["rqm_converged"]) for row in rows)
    qiskit_convergence = statistics.fmean(
        float(row["qiskit_serialization_converged"]) for row in rows
    )
    rqm_latencies = [value for row in rows for value in row["rqm_direct_latencies_ns"]]
    qiskit_latencies = [
        value for row in rows for value in row["qiskit_transpile_latencies_ns"]
    ]
    native_deltas = [value for row in rows for value in row["native_one_qubit_cost_deltas"]]
    native_improvements = [
        value
        for row in rows
        for value in row["native_one_qubit_cost_improvements"]
    ]
    return {
        "family_count": len(rows),
        "rqm_convergence": rqm_convergence,
        "qiskit_serialization_convergence": qiskit_convergence,
        "convergence_advantage_percentage_points": rqm_convergence - qiskit_convergence,
        "control_collisions": sum(int(row["control_collision"]) for row in rows),
        "non_verified_variants": sum(
            sum(int(status != "VERIFIED") for status in row["statuses"]) for row in rows
        ),
        "max_phase_aligned_error": max(float(row["max_phase_aligned_error"]) for row in rows),
        "median_native_one_qubit_cost_delta": statistics.median(native_deltas),
        "median_native_one_qubit_cost_improvement": statistics.median(
            native_improvements
        ),
        "native_one_qubit_cost_improvement_bootstrap_interval": (
            _bootstrap_median_interval(
                native_improvements,
                seed=bootstrap_seed,
                resamples=int(policy["statistics"]["paired_bootstrap_resamples"]),
                confidence_level=float(policy["statistics"]["confidence_level"]),
            )
        ),
        "rqm_direct_latency_ns": {
            "median": statistics.median(rqm_latencies),
            "p95": _percentile(rqm_latencies, 0.95),
        },
        "qiskit_transpile_latency_ns": {
            "median": statistics.median(qiskit_latencies),
            "p95": _percentile(qiskit_latencies, 0.95),
        },
        "rows": rows,
    }


def _wavefunction_track(records: list[dict[str, Any]]) -> dict[str, Any]:
    probability_errors = []
    sign_errors = []
    for record in records:
        state = Statevector.from_instruction(_build_variant(record, "direct"))
        alpha, beta = complex(state.data[0]), complex(state.data[1])
        quaternion = spinor_to_quaternion(alpha, beta)
        negative = spinor_to_quaternion(-alpha, -beta)
        bloch = state_to_bloch(alpha, beta)
        predicted = measurement_probabilities(*bloch)
        actual = state.probabilities()
        probability_errors.append(max(abs(predicted[i] - float(actual[i])) for i in range(2)))
        sign_errors.append(
            max(
                abs(a + b)
                for a, b in zip(
                    (quaternion.w, quaternion.x, quaternion.y, quaternion.z),
                    (negative.w, negative.x, negative.y, negative.z),
                    strict=True,
                )
            )
        )
    return {
        "records": len(records),
        "max_probability_error": max(probability_errors),
        "max_q_negation_error": max(sign_errors),
        "interpretation": "standard-compatible spinor regrouping and ideal Z-basis prediction",
    }


def _two_qubit_circuits() -> list[tuple[str, QuantumCircuit]]:
    circuits: list[tuple[str, QuantumCircuit]] = []
    cx = QuantumCircuit(2, name="cx")
    cx.cx(0, 1)
    circuits.append(("cx", cx))
    cartan = QuantumCircuit(2, name="cartan_axes")
    cartan.rxx(0.37, 0, 1)
    cartan.ryy(-0.29, 0, 1)
    cartan.rzz(0.61, 0, 1)
    circuits.append(("cartan_axes", cartan))
    bell = QuantumCircuit(2, name="bell_like")
    bell.h(0)
    bell.cx(0, 1)
    circuits.append(("bell_like", bell))
    fixed = QuantumCircuit(2, name="fixed_pair_window")
    for angle in (0.17, -0.31, 0.43):
        fixed.rxx(angle, 0, 1)
        fixed.ryy(-angle / 2.0, 0, 1)
        fixed.rzz(angle / 3.0, 0, 1)
    circuits.append(("fixed_pair_window", fixed))
    return circuits


def _su4_track(policy: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for name, circuit in _two_qubit_circuits():
        unitary = np.asarray(Operator(circuit).data, dtype=np.complex128)
        decomposition = decompose_su4_verified(unitary)
        fingerprint = nonlocal_fingerprint(unitary)
        assured = assure_qiskit_circuit(circuit)
        source_metrics = _native_metrics(circuit, policy)
        result_metrics = _native_metrics(assured.returned_circuit, policy)
        rows.append(
            {
                "name": name,
                "verified_decomposition": bool(decomposition.verified),
                "reconstruction_error": float(decomposition.reconstruction_error),
                "fingerprint": fingerprint,
                "assurance_status": str(assured.assurance_status),
                "source_two_qubit_cost": source_metrics["two_qubit_cost"],
                "rqm_two_qubit_cost": result_metrics["two_qubit_cost"],
            }
        )
    eligible = [row for row in rows if row["source_two_qubit_cost"] > 0]
    improvements = [
        (row["source_two_qubit_cost"] - row["rqm_two_qubit_cost"])
        / row["source_two_qubit_cost"]
        for row in eligible
    ]
    return {
        "rows": rows,
        "max_reconstruction_error": max(row["reconstruction_error"] for row in rows),
        "median_two_qubit_cost_improvement": statistics.median(improvements),
    }


def _decision(
    holdout: dict[str, Any],
    su4: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    correctness = policy["correctness"]
    advantage = policy["advantage"]
    canonical_pass = (
        holdout["rqm_convergence"] == advantage["canonical_rqm_convergence"]
        and holdout["control_collisions"] <= correctness["max_fingerprint_collisions"]
        and holdout["non_verified_variants"] == 0
        and holdout["max_phase_aligned_error"]
        <= correctness["max_phase_aligned_operator_error"]
        and holdout["convergence_advantage_percentage_points"]
        >= advantage["canonical_minimum_percentage_point_advantage"]
    )
    native_interval = holdout[
        "native_one_qubit_cost_improvement_bootstrap_interval"
    ]
    circuit_efficiency_pass = (
        holdout["median_native_one_qubit_cost_improvement"]
        >= advantage["circuit_efficiency_minimum_median_improvement"]
        and native_interval[0] > 0.0
    )
    su4_pass = (
        su4["median_two_qubit_cost_improvement"]
        >= advantage["su4_minimum_two_qubit_improvement"]
        and all(
            row["verified_decomposition"]
            and row["assurance_status"] == "VERIFIED"
            for row in su4["rows"]
        )
    )
    return {
        "canonical_fingerprint_gate": canonical_pass,
        "target_native_cost_gate": circuit_efficiency_pass,
        "target_native_cost_interval": native_interval,
        "latency_advantage_gate": None,
        "latency_advantage_note": "Not promoted because RQM direct assurance and Qiskit level-3 transpilation end at different output stages.",
        "su4_cost_gate": su4_pass,
        "winning_candidate": "phase_aware_su2_canonical_fingerprint" if canonical_pass else None,
        "verdict": (
            "canonical_assurance_workflow_advantage_supported"
            if canonical_pass
            else "no_preregistered_advantage_supported"
        ),
        "candidate_productization_authorized": bool(canonical_pass),
        "package_release_authorized": False,
        "claim_boundary": (
            "Deterministic canonical SU(2) fingerprint convergence for the frozen equivalent-family workflow only; no general Qiskit, circuit-quality, latency, hardware, or physics advantage."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-corpus", action="store_true")
    args = parser.parse_args()

    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if args.freeze_corpus:
        if CORPUS_PATH.exists():
            raise SystemExit("corpus_manifest.json already exists; refusing to overwrite frozen corpus")
        corpus = _generate_corpus(policy)
        CORPUS_PATH.write_text(json.dumps(corpus, indent=2) + "\n", encoding="utf-8")
        print(f"frozen {CORPUS_PATH} digest={corpus['corpus_digest']}")
        return 0

    if not CORPUS_PATH.exists():
        raise SystemExit("corpus_manifest.json is missing; run --freeze-corpus before measurement")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    expected_digest = corpus["corpus_digest"]
    digest_body = dict(corpus)
    del digest_body["corpus_digest"]
    if _digest(digest_body) != expected_digest:
        raise SystemExit("corpus manifest digest mismatch")
    if qiskit.__version__ != policy["qiskit_version"]:
        raise SystemExit(
            f"Qiskit version mismatch: expected {policy['qiskit_version']}, got {qiskit.__version__}"
        )

    bootstrap_seed = int(policy["statistics"]["paired_bootstrap_seed"])
    discovery = _summarize_partition(
        corpus["partitions"]["discovery"],
        policy,
        bootstrap_seed=bootstrap_seed,
    )
    holdout = _summarize_partition(
        corpus["partitions"]["holdout"],
        policy,
        bootstrap_seed=bootstrap_seed + 1,
    )
    wavefunction = _wavefunction_track(corpus["partitions"]["holdout"])
    su4 = _su4_track(policy)
    decision = _decision(holdout, su4, policy)
    result = {
        "schema_version": "1.0",
        "experiment_id": "EXP-014",
        "policy_digest": _digest(policy),
        "corpus_digest": expected_digest,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "qiskit": qiskit.__version__,
            "numpy": np.__version__,
        },
        "discovery": discovery,
        "holdout": holdout,
        "quaternionic_wavefunction": wavefunction,
        "su4": su4,
        "decision": decision,
    }
    semantic_summary = {
        "corpus_digest": expected_digest,
        "discovery": {
            key: value
            for key, value in discovery.items()
            if key
            not in {
                "rows",
                "rqm_direct_latency_ns",
                "qiskit_transpile_latency_ns",
            }
        },
        "holdout": {
            key: value
            for key, value in holdout.items()
            if key
            not in {
                "rows",
                "rqm_direct_latency_ns",
                "qiskit_transpile_latency_ns",
            }
        },
        "quaternionic_wavefunction": wavefunction,
        "su4": su4,
        "decision": decision,
    }
    result["semantic_digest"] = _digest(semantic_summary)
    result["result_digest"] = _digest(result)
    RAW_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "result_digest": result["result_digest"]}, indent=2))
    return 0 if decision["candidate_productization_authorized"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
