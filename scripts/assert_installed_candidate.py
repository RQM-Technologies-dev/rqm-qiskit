#!/usr/bin/env python3
"""Fail when CI imports rqm-qiskit from its checkout instead of its wheel."""

from __future__ import annotations

import os
from importlib.metadata import version
from pathlib import Path

import rqm_qiskit


workspace = Path(os.environ["RQM_WORKSPACE"]).resolve()
module_path = Path(rqm_qiskit.__file__).resolve()
if module_path.is_relative_to(workspace):
    raise RuntimeError(f"rqm_qiskit resolved inside the checkout: {module_path}")

expected = {
    "rqm-core": "0.2.2",
    "rqm-compiler": "0.3.7",
    "rqm-qiskit": "0.4.1",
    "rqm-entanglement": "0.2.2",
    "qiskit-qasm3-import": "0.6.0",
}
actual = {project: version(project) for project in (*expected, "qiskit")}
for project, expected_version in expected.items():
    if actual[project] != expected_version:
        raise RuntimeError(
            f"installed {project} differs: expected {expected_version}, found {actual[project]}"
        )

qiskit_parts = actual["qiskit"].split(".")
if len(qiskit_parts) < 2 or qiskit_parts[0] != "2" or qiskit_parts[1] != "5":
    raise RuntimeError(
        "installed Qiskit is outside rqm-qiskit's declared >=2.5.1,<2.6 range: "
        f"found {actual['qiskit']}"
    )
patch = int(qiskit_parts[2].split("+")[0].split("-")[0]) if len(qiskit_parts) > 2 else 0
if patch < 1:
    raise RuntimeError(f"Qiskit {actual['qiskit']} is below the supported 2.5.1 minimum")

print(f"installed candidate import: {module_path}")
print(f"supported Qiskit: {actual['qiskit']}")
