#!/usr/bin/env python3
"""Require all nine hosted wheel-smoke records and aggregate their evidence."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
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
    expected_source = os.environ.get("RQM_DISTRIBUTION_SOURCE", "candidate")
    if {record["distribution_source"] for record in records} != {expected_source}:
        raise RuntimeError("matrix records do not share the expected distribution source")
    expected_ref = os.environ["RQM_QUALIFICATION_REF"]
    if {record["qualification_ref"] for record in records} != {expected_ref}:
        raise RuntimeError("matrix records do not share the dispatched qualification ref")
    wheel_hash_sets = {
        json.dumps(record["wheel_hashes"], sort_keys=True) for record in records
    }
    if len(wheel_hash_sets) != 1:
        raise RuntimeError("matrix jobs did not install the identical wheel bundle")
    pypi_digests: dict[str, str] | None = None
    if expected_source == "pypi":
        pypi_digests = {}
        versions = records[0]["installed"]["versions"]
        for project in ("rqm-core", "rqm-compiler", "rqm-qiskit"):
            url = f"https://pypi.org/pypi/{project}/{versions[project]}/json"
            with urllib.request.urlopen(url, timeout=30) as response:
                metadata = json.load(response)
            for artifact in metadata["urls"]:
                if artifact["filename"].endswith(".whl"):
                    pypi_digests[artifact["filename"]] = artifact["digests"]["sha256"]
        installed_hashes = records[0]["wheel_hashes"]
        if installed_hashes != {
            filename: pypi_digests[filename] for filename in installed_hashes
        }:
            raise RuntimeError("downloaded wheel hashes do not match PyPI metadata")

    payload = {
        "schema_version": "2",
        "status": "pass",
        "distribution_source": expected_source,
        "qualification_ref": expected_ref,
        "github": {
            "run_id": os.environ["RQM_RUN_ID"],
            "run_attempt": os.environ["RQM_RUN_ATTEMPT"],
            "run_url": os.environ["RQM_RUN_URL"],
        },
        "wheel_bundle_artifact_digest": os.environ.get(
            "RQM_WHEEL_BUNDLE_ARTIFACT_DIGEST"
        ),
        "wheel_hashes": records[0]["wheel_hashes"],
        "pypi_sha256_digests": pypi_digests,
        "matrix": records,
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
