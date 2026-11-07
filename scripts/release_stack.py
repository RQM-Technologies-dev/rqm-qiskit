"""Separate the next bridge candidate from the frozen published 0.4.1 stack.

The candidate requires the exact-phase releases. The public qualification job
continues to describe the already-published wheel until a new release exists.
"""

from pathlib import Path
import tomllib


_ROOT = Path(__file__).resolve().parents[1]
_BRIDGE_VERSION = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

CANDIDATE_VERSIONS = {
    "rqm-core": "0.3.1",
    "rqm-compiler": "0.3.8",
    "rqm-qiskit": _BRIDGE_VERSION,
    "rqm-entanglement": "0.2.3",
    "qiskit-qasm3-import": "0.6.0",
}

PUBLISHED_0_4_1_VERSIONS = {
    "rqm-core": "0.2.2",
    "rqm-compiler": "0.3.7",
    "rqm-qiskit": "0.4.1",
    "rqm-entanglement": "0.2.2",
    "qiskit-qasm3-import": "0.6.0",
}


def versions_for(distribution_source: str) -> dict[str, str]:
    if distribution_source == "candidate":
        return dict(CANDIDATE_VERSIONS)
    if distribution_source == "pypi":
        return dict(PUBLISHED_0_4_1_VERSIONS)
    raise ValueError(f"unsupported distribution source: {distribution_source}")
