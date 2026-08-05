#!/usr/bin/env python3
"""Cross-platform API and CLI qualification for the installed 0.4 wheel."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import Callable

import rqm_qiskit
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qasm3
from rqm_qiskit import (
    analyze_qiskit_circuit,
    assure_openqasm3,
    export_openqasm3,
    import_openqasm3,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _measurement_mapping(circuit: QuantumCircuit) -> list[dict[str, int]]:
    return analyze_qiskit_circuit(circuit).circuit_summary["terminal_measurements"]


def _close_sequence(actual: list[float], expected: list[float]) -> bool:
    return len(actual) == len(expected) and all(
        math.isclose(found, wanted, rel_tol=0.0, abs_tol=1e-12)
        for found, wanted in zip(actual, expected)
    )


def main() -> int:
    workspace = Path(os.environ["RQM_WORKSPACE"]).resolve()
    wheelhouse = Path(os.environ["RQM_WHEELHOUSE"]).resolve()
    result_path = Path(os.environ["RQM_RESULT_PATH"]).resolve()
    module_path = Path(rqm_qiskit.__file__).resolve()
    if module_path.is_relative_to(workspace):
        raise RuntimeError(f"rqm_qiskit resolved inside the checkout: {module_path}")

    checks: list[str] = []

    def check(name: str, assertion: Callable[[], bool]) -> None:
        if not assertion():
            raise AssertionError(name)
        checks.append(name)

    expected_versions = {
        "rqm-core": "0.2.2",
        "rqm-compiler": "0.3.0",
        "rqm-qiskit": "0.4.0",
        "rqm-entanglement": "0.2.1",
        "qiskit": "2.5.1",
        "qiskit-qasm3-import": "0.6.0",
    }
    versions = {project: version(project) for project in expected_versions}
    check("exact_dependency_versions", lambda: versions == expected_versions)
    check("installed_module_outside_checkout", lambda: not module_path.is_relative_to(workspace))

    one_qubit = QuantumCircuit(1)
    one_qubit.ry(math.pi / 2, 0)
    one_before = copy.deepcopy(one_qubit)
    one_report = analyze_qiskit_circuit(one_qubit)
    local = one_report.local_geometry[0]
    check("one_qubit_input_unchanged", lambda: one_qubit == one_before)
    check("one_qubit_complete", lambda: one_report.status == "complete")
    check("quaternion_present", lambda: len(local["canonical_quaternion"]) == 4)
    check("rotation_present", lambda: local["angle_pi_multiple"] == "π/2")
    check(
        "bloch_present",
        lambda: _close_sequence(
            local["final_state"]["bloch"], [1.0, 0.0, 0.0]
        ),
    )
    check(
        "one_qubit_probabilities",
        lambda: set(one_report.measurement_predictions["probabilities"]) == {"0", "1"},
    )

    qreg = QuantumRegister(2, "science")
    creg = ClassicalRegister(2, "readout")
    bell = QuantumCircuit(qreg, creg)
    bell.h(qreg[0])
    bell.cx(qreg[0], qreg[1])
    bell.measure(qreg[0], creg[1])
    bell.measure(qreg[1], creg[0])
    bell_before = copy.deepcopy(bell)
    bell_report = analyze_qiskit_circuit(bell)
    nonlocal_geometry = bell_report.nonlocal_geometry[0]
    expected_mapping = [{"qubit": 0, "clbit": 1}, {"qubit": 1, "clbit": 0}]
    check("two_qubit_input_unchanged", lambda: bell == bell_before)
    check("two_qubit_complete", lambda: bell_report.status == "complete")
    check("su4_present", lambda: bool(nonlocal_geometry["su4"]))
    check("weyl_present", lambda: len(nonlocal_geometry["weyl_coordinates"]) == 3)
    check(
        "entanglement_present",
        lambda: any(
            item["metric_name"] == "Concurrence"
            and math.isclose(
                item["metric_value"], 1.0, rel_tol=0.0, abs_tol=1e-12
            )
            for item in nonlocal_geometry["entanglement"]["entangled_pairs"]
        ),
    )
    check(
        "terminal_measurement_mapping",
        lambda: bell_report.circuit_summary["terminal_measurements"] == expected_mapping,
    )

    unitary = QuantumCircuit(2)
    unitary.h(0)
    unitary.cx(0, 1)
    source = qasm3.dumps(unitary) + "\n// UTF-8 marker: π\n"
    imported = import_openqasm3(source)
    check("openqasm_import", lambda: imported.report.status == "SUPPORTED")
    exported = export_openqasm3(imported.circuit)
    check("openqasm_export", lambda: exported.status == "EXPORTED")
    reparsed = import_openqasm3(exported.source or "")
    check("openqasm_reparse", lambda: reparsed.report.status == "SUPPORTED")

    measured_source = qasm3.dumps(bell) + "\n// UTF-8 marker: π\n"
    assured = assure_openqasm3(measured_source)
    check("openqasm_assurance", lambda: assured.assurance_status == "VERIFIED")
    returned = qasm3.loads(assured.returned_source)
    check("openqasm_registers", lambda: [reg.name for reg in returned.qregs] == ["science"] and [reg.name for reg in returned.cregs] == ["readout"])
    check("openqasm_measurements", lambda: _measurement_mapping(returned) == expected_mapping)

    executable_name = "rqm-qiskit.exe" if os.name == "nt" else "rqm-qiskit"
    executable = shutil.which("rqm-qiskit")
    check("console_entry_point", lambda: executable is not None)
    check(
        "windows_executable_entry_point",
        lambda: os.name != "nt" or Path(executable or "").name.lower() == executable_name,
    )

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    with tempfile.TemporaryDirectory(prefix="rqm-wheel-") as temp:
        unicode_dir = Path(temp) / "path with spaces – π"
        unicode_dir.mkdir()
        input_path = unicode_dir / "Bell input π.qasm"
        explanation_path = unicode_dir / "Explanation π.md"
        report_path = unicode_dir / "Report π.json"
        assured_path = unicode_dir / "Assured output π.qasm"
        assurance_report_path = unicode_dir / "Assurance report π.json"
        input_path.write_text(measured_source, encoding="utf-8")

        explain = subprocess.run(
            [
                executable or "rqm-qiskit",
                "explain",
                str(input_path),
                "--detail",
                "standard",
                "--output",
                str(explanation_path),
                "--report",
                str(report_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        check("cli_explain_exit", lambda: explain.returncode == 0)
        explanation = explanation_path.read_text(encoding="utf-8")
        report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        check(
            "cli_utf8_markdown",
            lambda: "⟩" in explanation and "Weyl" in explanation,
        )
        check("cli_json_report", lambda: report_payload["status"] == "complete")

        stdout_explain = subprocess.run(
            [executable or "rqm-qiskit", "explain", str(input_path), "--detail", "standard"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        check("cli_stdout_exit", lambda: stdout_explain.returncode == 0)
        check(
            "cli_utf8_stdout",
            lambda: stdout_explain.stdout.startswith("# Quaternionic explanation")
            and "Weyl" in stdout_explain.stdout,
        )

        assure = subprocess.run(
            [
                executable or "rqm-qiskit",
                "assure",
                str(input_path),
                "--output",
                str(assured_path),
                "--report",
                str(assurance_report_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        check("cli_assure_exit", lambda: assure.returncode == 0)
        assured_circuit = qasm3.loads(assured_path.read_text(encoding="utf-8"))
        assurance_payload = json.loads(
            assurance_report_path.read_text(encoding="utf-8")
        )
        check(
            "cli_assure_report",
            lambda: assurance_payload["assurance_status"] == "VERIFIED",
        )
        check("cli_qasm_mapping", lambda: _measurement_mapping(assured_circuit) == expected_mapping)

    wheel_manifest = json.loads(
        (wheelhouse / "candidate-wheelhouse.json").read_text(encoding="utf-8")
    )
    wheel_hashes = {
        path.name: _sha256(path) for path in sorted(wheelhouse.glob("*.whl"))
    }
    manifest_hashes = {
        item["filename"]: item["sha256"] for item in wheel_manifest["wheels"]
    }
    check("wheel_checksums", lambda: wheel_hashes == manifest_hashes)

    result = {
        "schema_version": "1",
        "status": "pass",
        "candidate_commit": os.environ["RQM_CANDIDATE_COMMIT"],
        "runner": {
            "label": os.environ["RQM_RUNNER_LABEL"],
            "os": platform.system(),
            "architecture": platform.machine(),
            "python_requested": os.environ["RQM_REQUESTED_PYTHON"],
            "python": platform.python_version(),
        },
        "installed": {
            "module_path": str(module_path),
            "entry_point": executable,
            "versions": versions,
        },
        "wheel_hashes": wheel_hashes,
        "checks": checks,
    }
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
