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
    "rqm-compiler": "0.3.0",
    "rqm-qiskit": "0.4.0",
    "rqm-entanglement": "0.2.1",
    "qiskit": "2.5.1",
    "qiskit-qasm3-import": "0.6.0",
}
actual = {project: version(project) for project in expected}
if actual != expected:
    raise RuntimeError(f"installed versions differ: expected {expected}, found {actual}")
print(f"installed candidate import: {module_path}")
