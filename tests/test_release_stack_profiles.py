"""Guard dependency resolution and keep historical qualification honest."""

import importlib.util
from pathlib import Path
import tomllib

import pytest
from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_stack", ROOT / "scripts/release_stack.py")
stack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stack)


def test_candidate_versions_satisfy_declared_requirements():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    requirements = {r.name: r for r in map(Requirement, project["dependencies"])}
    assert stack.CANDIDATE_VERSIONS["rqm-qiskit"] == project["version"]
    for package in ("rqm-core", "rqm-compiler", "rqm-entanglement"):
        assert stack.CANDIDATE_VERSIONS[package] in requirements[package].specifier
    for package, old in (("rqm-core", "0.2.3"), ("rqm-compiler", "0.3.7"), ("rqm-entanglement", "0.2.2")):
        assert old not in requirements[package].specifier


def test_candidate_and_public_profiles_do_not_relabel_history():
    assert stack.versions_for("candidate")["rqm-core"] == "0.3.1"
    assert stack.versions_for("candidate")["rqm-compiler"] == "0.3.8"
    assert stack.versions_for("pypi")["rqm-core"] == "0.2.2"
    assert stack.versions_for("pypi")["rqm-compiler"] == "0.3.7"
    assert stack.versions_for("pypi")["rqm-qiskit"] == "0.4.1"
    candidate = stack.versions_for("candidate")
    candidate["rqm-core"] = "invalid"
    assert stack.versions_for("candidate")["rqm-core"] == "0.3.1"
    with pytest.raises(ValueError):
        stack.versions_for("unknown")


def test_ci_uses_exact_released_source_commits():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "RQM_CORE_COMMIT: 8c3e62d5318eb869bd22afe11092faf3eb48147b" in workflow
    assert "RQM_COMPILER_COMMIT: 0feb4af3a9e6f6ff19f5e59b568ce923a7971644" in workflow
