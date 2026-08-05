#!/usr/bin/env python3
"""Repeat the unchanged EXP-015 gate in isolated Python processes."""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_performance_gate.py"
OUTPUT = ROOT / "PERFORMANCE_REPRODUCTION_RESULTS.json"
RUN_COUNT = 3


def main() -> int:
    runs: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="rqm-exp015-") as temporary:
        temporary_root = Path(temporary)
        for index in range(RUN_COUNT):
            run_output = temporary_root / f"run-{index + 1}.json"
            environment = dict(os.environ)
            environment["RQM_PERFORMANCE_OUTPUT"] = str(run_output)
            completed = subprocess.run(
                [sys.executable, str(RUNNER)],
                cwd=ROOT,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode not in (0, 2) or not run_output.exists():
                raise RuntimeError(
                    f"Reproduction run {index + 1} failed before producing evidence: "
                    f"{completed.stderr.strip() or completed.stdout.strip()}"
                )
            payload = json.loads(run_output.read_text(encoding="utf-8"))
            payload["process_index"] = index + 1
            payload["process_returncode"] = completed.returncode
            runs.append(payload)

    ratios = [
        float(run["metrics"]["adapter_overhead_ratio_median"]) for run in runs
    ]
    absolute_times = [
        float(run["metrics"]["absolute_adapter_time_median_us"]) for run in runs
    ]
    payload = {
        "schema_version": "1.0",
        "experiment_id": "EXP-015",
        "run_count": RUN_COUNT,
        "corpus_digest": runs[0]["corpus_digest"],
        "summary": {
            "adapter_overhead_ratio_process_median": statistics.median(ratios),
            "adapter_overhead_ratio_process_min": min(ratios),
            "adapter_overhead_ratio_process_max": max(ratios),
            "absolute_adapter_time_process_median_us": statistics.median(
                absolute_times
            ),
            "ratio_gate_passed_in_all_processes": all(
                run["gates"]["adapter_overhead_ratio"] for run in runs
            ),
            "all_release_gates_passed_in_all_processes": all(
                run["release_gate_passed"] for run in runs
            ),
        },
        "runs": runs,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "runs"}, indent=2))
    return 0 if payload["summary"]["all_release_gates_passed_in_all_processes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
