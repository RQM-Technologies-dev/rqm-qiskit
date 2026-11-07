"""Offline paired replay of the untouched SIM-030 synthesis corpus.

Run with the frozen SIM-030 dependencies (including Qiskit 2.5.1), a baseline
``synthesis.py`` from 54ef52d or 5d67721, and this checkout on PYTHONPATH.
Nothing is written to the original study or to a provider.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
from pathlib import Path
import sys

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import CXGate, RZZGate
from qiskit.quantum_info import Operator
from qiskit.synthesis import TwoQubitBasisDecomposer, TwoQubitControlledUDecomposer
from rqm_entanglement import decompose_su4_verified
from rqm_qiskit import synthesis as candidate


BASELINE_SHA256 = "ea75f62dd854ee83f0bed920fd9a1aa34ae85cd3a25ffba6e313d3ab6212839e"
INPUT_SHA256 = {
    "frozen/synthesis_cases.json": "e098ae3081e9892d63a8659149b743e5acfb460873f89ad67d7bcc6b5cd1870d",
    "common.py": "cc81e55e9f8acbb93ead0f1b98f6a421ea4a429de841a4364a1356642fa43efc",
    "synthesis_benchmark.py": "69a15bca2ee7a60c265f1cfd633700855f1be46f81a7c2780ebdc9d690e65fb4",
}
STRATEGIES = ("Q3", "QF", "QC", "QX", "RQ", "best_native")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sim030-root", type=Path, required=True)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite an existing result")
    if importlib.metadata.version("qiskit") != "2.5.1":
        raise ValueError("this replay is frozen to Qiskit 2.5.1")
    if sha256(args.baseline_source) != BASELINE_SHA256:
        raise ValueError("baseline synthesis source differs from the frozen source")
    for relative, expected in INPUT_SHA256.items():
        if sha256(args.sim030_root / relative) != expected:
            raise ValueError(f"frozen SIM-030 input changed: {relative}")
    spec = importlib.util.spec_from_file_location("dispatch_baseline", args.baseline_source)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    sys.path.insert(0, str(args.sim030_root.resolve()))
    from common import count_depth, digest, measure, operator_error, source_circuit
    from synthesis_benchmark import make_target

    cases = json.loads((args.sim030_root / "frozen/synthesis_cases.json").read_text())
    result = {
        "study": "selected-synthesis-dispatch-v0.1",
        "purpose": "paired dispatch regression; not a new synthesis algorithm or Qiskit parity claim",
        "baseline_source_sha256": BASELINE_SHA256,
        "candidate_source_sha256": sha256(Path(candidate.__file__)),
        "script_sha256": sha256(Path(__file__)),
        "frozen_input_sha256": INPUT_SHA256,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "versions": {name: importlib.metadata.version(name) for name in (
                "numpy", "scipy", "qiskit", "rqm-core", "rqm-entanglement", "rqm-compiler",
            )},
        },
        "timing": {
            "warmups": 1, "repeats": 7,
            "order": "rotate deterministic method order each repetition",
            "scope": "raw descriptors, input conversion, decomposition, synthesis, full-operator and target checks",
            "timeout_seconds": 15,
        },
        "rows": [],
    }
    for case in cases:
        for basis in ("cx", "rzz"):
            target = make_target(basis)
            samples = {}

            def evaluate(name, module=None, strategy=None):
                source = source_circuit(case["operations"], 2)
                matrix = np.asarray(Operator(source).data)
                selected = None
                evaluated_paths = None
                if module is not None:
                    block = decompose_su4_verified(matrix, tolerance=1e-10).block
                    output, report = module.synthesize_su4_block(
                        block, target=target, strategy=strategy, include_report=True,
                    )
                    selected = report["selected_path"]
                    evaluated_paths = list(report["candidates"])
                elif name == "qiskit_dedicated":
                    if basis == "rzz":
                        intermediate = TwoQubitControlledUDecomposer(RZZGate)(matrix)
                    else:
                        intermediate = TwoQubitBasisDecomposer(
                            CXGate(), basis_fidelity=1.0, euler_basis="ZSX",
                        )(matrix, approximate=False)
                    output = transpile(intermediate, target=target, optimization_level=3,
                                       approximation_degree=1.0, seed_transpiler=730301)
                elif name == "qiskit_unitary":
                    intermediate = QuantumCircuit(2)
                    intermediate.unitary(matrix, [0, 1])
                    output = transpile(intermediate, target=target, optimization_level=3,
                                       approximation_degree=1.0, seed_transpiler=730301)
                elif name == "qiskit_source":
                    output = transpile(source, target=target, optimization_level=3,
                                       approximation_degree=1.0, seed_transpiler=730301)
                else:
                    raise ValueError(name)
                error = operator_error(matrix, np.asarray(Operator(output).data))
                if not np.isfinite(error) or error > 1e-10:
                    raise ValueError(f"full operator mismatch {error}")
                for item in output.data:
                    wires = tuple(output.find_bit(q).index for q in item.qubits)
                    if not target.instruction_supported(item.operation.name, wires):
                        raise ValueError(f"target violation: {item.operation.name}")
                metrics = {
                    **count_depth(output), "operator_error": error,
                    "target_compatible": True, "selected_path": selected,
                    "evaluated_paths": evaluated_paths,
                    "operation_counts": dict(output.count_ops()),
                    "instruction_digest": digest([
                        [item.operation.name,
                         [output.find_bit(q).index for q in item.qubits],
                         [float(p) for p in item.operation.params]]
                        for item in output.data
                    ]),
                    "correct": True,
                }
                samples.setdefault(name, []).append(metrics)
                return metrics

            methods = {}
            for strategy in STRATEGIES:
                for label, module in (("baseline", baseline), ("candidate", candidate)):
                    name = f"{label}_{strategy}"
                    methods[name] = lambda n=name, m=module, s=strategy: evaluate(n, m, s)
            for name in ("qiskit_dedicated", "qiskit_unitary", "qiskit_source"):
                methods[name] = lambda n=name: evaluate(n)
            timings, outputs = measure(methods, repeats=7, warmups=1)
            for name, metrics in outputs.items():
                timings[name].update(metrics)
                timings[name]["all_output_checks"] = samples[name]
            result["rows"].append({
                "case_id": case["window_id"], "family": case["family"],
                "heldout": case.get("heldout", False), "basis": basis,
                "source_digest": digest(case), "methods": timings,
            })
            print(f"completed {len(result['rows'])}/52: {case['window_id']} {basis}", flush=True)
    # Check every paired result, including unsupported strategy/target combinations.
    for row in result["rows"]:
        for strategy in STRATEGIES:
            before = row["methods"][f"baseline_{strategy}"]
            after = row["methods"][f"candidate_{strategy}"]
            if before["status"] != after["status"]:
                raise AssertionError(f"availability changed: {row['case_id']} {strategy}")
            if before["status"] == "ok" and strategy != "best_native":
                before_digests = {v["instruction_digest"] for v in before["all_output_checks"]}
                after_digests = {v["instruction_digest"] for v in after["all_output_checks"]}
                if before_digests != after_digests:
                    raise AssertionError(f"explicit output changed: {row['case_id']} {strategy}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
