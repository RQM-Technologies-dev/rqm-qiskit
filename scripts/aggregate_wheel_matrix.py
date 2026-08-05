#!/usr/bin/env python3
"""Require all nine hosted wheel-smoke records and aggregate their evidence."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


EXPECTED = {
    (runner, python)
    for runner in ("ubuntu-latest", "macos-latest", "windows-latest")
    for python in ("3.11", "3.12", "3.13")
}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: aggregate_wheel_matrix.py RESULTS_DIR OUTPUT.json")
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    paths = sorted(source.rglob("wheel-smoke-result.json"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    combinations = [
        (record["runner"]["label"], record["runner"]["python_requested"])
        for record in records
    ]
    if len(records) != 9 or len(set(combinations)) != 9 or set(combinations) != EXPECTED:
        raise RuntimeError(
            f"expected the complete nine-job matrix; found {sorted(combinations)}"
        )
    if any(record.get("status") != "pass" for record in records):
        raise RuntimeError("at least one wheel-smoke result did not pass")
    expected_commit = os.environ["RQM_CANDIDATE_COMMIT"]
    if {record["candidate_commit"] for record in records} != {expected_commit}:
        raise RuntimeError("matrix records do not share the dispatched candidate commit")
    wheel_hash_sets = {
        json.dumps(record["wheel_hashes"], sort_keys=True) for record in records
    }
    if len(wheel_hash_sets) != 1:
        raise RuntimeError("matrix jobs did not install the identical wheel bundle")
    payload = {
        "schema_version": "1",
        "status": "pass",
        "candidate_commit": expected_commit,
        "github": {
            "run_id": os.environ["RQM_RUN_ID"],
            "run_attempt": os.environ["RQM_RUN_ATTEMPT"],
            "run_url": os.environ["RQM_RUN_URL"],
        },
        "wheelhouse_artifact_digest": os.environ[
            "RQM_WHEELHOUSE_ARTIFACT_DIGEST"
        ],
        "wheel_hashes": records[0]["wheel_hashes"],
        "matrix": records,
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
