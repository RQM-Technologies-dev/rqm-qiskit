#!/usr/bin/env python3
"""Bounded 0.3.7B IBM real-QPU canary.

This script is intentionally opt-in. It never submits without an IBM token,
a named backend, and an authorization marker supplied by the operator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

from rqm_qiskit import async_execute_rqm_program


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--shots", type=int, default=100)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--output", default="artifacts/0.3.7b-ibm-canary.json")
    args = parser.parse_args()

    if not 1 <= args.shots <= 1024:
        raise SystemExit("--shots must be between 1 and 1024 for the bounded canary")
    if not os.environ.get("QISKIT_IBM_TOKEN"):
        raise SystemExit("QISKIT_IBM_TOKEN is required; no submission was made")

    descriptor = {
        "num_qubits": 2,
        "operations": [
            {"gate": "h", "targets": [0], "controls": [], "params": {}},
            {"gate": "cx", "targets": [1], "controls": [0], "params": {}},
            {"gate": "measure", "targets": [0], "controls": [], "params": {"key": "m0"}},
            {"gate": "measure", "targets": [1], "controls": [], "params": {"key": "m1"}},
        ],
    }
    workload_bytes = json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode()
    workload_sha256 = hashlib.sha256(workload_bytes).hexdigest()

    job = async_execute_rqm_program(
        descriptor,
        backend=args.backend,
        shots=args.shots,
        optimize=True,
        include_report=True,
    )
    result = job.result(timeout=1800)
    payload = {
        "schema_version": "rqm.compiler.0.3.7b.ibm-canary.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "authorization_id": args.authorization_id,
        "backend": args.backend,
        "shots": args.shots,
        "workload_sha256": workload_sha256,
        "provider_job_id": job.job_id(),
        "provider_status": job.status(),
        "result": result.to_dict(backend=args.backend, job_id=job.job_id()),
        "claim_boundary": [
            "Evidence applies only to this bounded workload and named backend.",
            "A successful run establishes integration/execution, not universal compiler or hardware advantage.",
        ],
    }

    output = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
