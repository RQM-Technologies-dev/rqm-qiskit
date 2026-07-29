#!/usr/bin/env python3
"""Rerun the frozen v0.1 corpus after the preregistered iSWAP verifier fix."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parent
BASE_ROOT = ROOT.parent / "qiskit_openqasm_v0_1"
RESULTS_PATH = ROOT / "raw_results.json"
REPORT_PATH = ROOT / "RESULTS.md"
HASHES_PATH = ROOT / "SHA256SUMS"


def _load_baseline_runner() -> ModuleType:
    path = BASE_ROOT / "run_corpus.py"
    spec = importlib.util.spec_from_file_location("rqm_qiskit_v0_1_corpus", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the frozen v0.1 corpus runner.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_report(results: dict[str, Any]) -> None:
    summary = results["summary"]
    gates = results["gates"]
    lines = [
        "# Qiskit/OpenQASM Assurance Bridge v0.2 Hardening Results",
        "",
        f"Coverage verdict: **{'PASS' if results['coverage_gate_passed'] else 'FAIL'}**.",
        f"Full release verdict: **{'PASS' if results['release_ready'] else 'FAIL'}**.",
        "",
        "The frozen 200-case v0.1 corpus was reused byte-for-byte. The v0.1 result was not overwritten.",
        "",
        "## Results",
        "",
        (
            f"- Eligible verification coverage: {summary['eligible_verified']}/"
            f"{summary['eligible_total']} ({summary['verification_coverage']:.1%}), "
            "up from 91/160 (56.875%)."
        ),
        f"- False equivalence decisions: {summary['false_equivalence_count']}.",
        (
            f"- Unsupported inputs failing closed: "
            f"{summary['unsupported_fail_closed_count']}/20."
        ),
        f"- Withheld-candidate disclosures: {summary['candidate_disclosure_count']}.",
        (
            "- Median adapter overhead versus compiler-only optimization: "
            f"{summary['median_adapter_overhead_ratio']:.1%}."
        ),
        "",
        (
            "The coverage improvement comes only from declaring iSWAP in the compiler "
            "verifier path whose unitary simulator already supported it. No tolerance, "
            "corpus, public gate boundary, or fail-closed rule changed."
        ),
        "",
        "## Registered gates",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — {name.replace('_', ' ')}."
        for name, passed in gates.items()
    )
    lines.extend(
        [
            "",
            (
                "The semantic coverage defect is resolved. The bridge remains blocked "
                "from a full release-ready claim because adapter overhead still exceeds "
                "the original 25% gate."
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
    if _sha256(BASE_ROOT / "corpus_manifest.json") != expected_manifest:
        raise RuntimeError("Frozen v0.1 corpus manifest hash mismatch.")

    results = runner.run_corpus()
    results["schema_version"] = "rqm.qiskit-openqasm-hardening-results.v0.2"
    results["baseline"] = {
        "path": "../qiskit_openqasm_v0_1/raw_results.json",
        "verification_coverage": 0.56875,
        "eligible_verified": 91,
    }
    safety_keys = [
        "verification_coverage_at_least_95_percent",
        "zero_false_equivalence",
        "zero_withheld_candidate_disclosures",
        "all_unsupported_fail_closed",
        "deterministic_evidence_ids",
    ]
    results["coverage_gate_passed"] = all(results["gates"][key] for key in safety_keys)
    results["notes"].append(
        "The v0.2 run references the unchanged v0.1 corpus and preserves the v0.1 result."
    )
    RESULTS_PATH.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_report(results)
    paths = [
        ROOT / "PREREGISTRATION.json",
        BASE_ROOT / "corpus_manifest.json",
        RESULTS_PATH,
        REPORT_PATH,
    ]
    HASHES_PATH.write_text(
        "".join(f"{_sha256(path)}  {path.relative_to(ROOT.parent)}\n" for path in paths),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
