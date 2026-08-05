from __future__ import annotations

import math

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator
from rqm_compiler import Circuit
from rqm_compiler.ops import Operation

import rqm_qiskit.assurance as assurance_module
from rqm_qiskit import (
    assure_qiskit_circuit,
    compiled_circuit_to_qiskit,
    export_openqasm3,
    import_openqasm3,
    import_qiskit_circuit,
)
from rqm_qiskit.assurance import (
    export_openqasm3_isolated,
    import_openqasm3_isolated,
)
from rqm_qiskit.errors import TranslationError


def _equivalent_up_to_phase(left: QuantumCircuit, right: QuantumCircuit) -> bool:
    lhs = Operator(left).data
    rhs = Operator(right).data
    overlap = np.vdot(rhs.reshape(-1), lhs.reshape(-1))
    if abs(overlap) == 0.0:
        return False
    phase = overlap / abs(overlap)
    return bool(np.allclose(lhs, phase * rhs, atol=1e-10, rtol=1e-10))


def test_import_supported_qiskit_gate_subset() -> None:
    circuit = QuantumCircuit(3)
    circuit.id(0)
    circuit.x(0)
    circuit.y(1)
    circuit.z(2)
    circuit.h(0)
    circuit.s(1)
    circuit.t(2)
    circuit.rx(0.1, 0)
    circuit.ry(-0.2, 1)
    circuit.rz(math.pi, 2)
    circuit.p(0.3, 0)
    circuit.cx(0, 1)
    circuit.cy(1, 2)
    circuit.cz(2, 0)
    circuit.swap(0, 1)
    circuit.iswap(1, 2)
    circuit.rxx(0.2, 0, 1)
    circuit.ryy(0.3, 1, 2)
    circuit.rzz(0.4, 2, 0)

    result = import_qiskit_circuit(circuit)

    assert result.report.status == "SUPPORTED"
    assert result.circuit is not None
    assert [op.gate for op in result.circuit.operations] == [
        "i",
        "x",
        "y",
        "z",
        "h",
        "s",
        "t",
        "rx",
        "ry",
        "rz",
        "phaseshift",
        "cx",
        "cy",
        "cz",
        "swap",
        "iswap",
        "rxx",
        "ryy",
        "rzz",
    ]


@pytest.mark.parametrize(
    ("builder", "reason"),
    [
        (
            lambda: QuantumCircuit(4),
            "qubit_count_out_of_range",
        ),
        (
            lambda: QuantumCircuit(1, 1),
            "classical_data_unsupported",
        ),
    ],
)
def test_import_rejects_boundary_violations(builder, reason: str) -> None:
    result = import_qiskit_circuit(builder())

    assert result.report.status == "UNSUPPORTED"
    assert result.circuit is None
    assert reason in {item.code for item in result.report.unsupported_reasons}


def test_import_rejects_symbolic_parameter() -> None:
    theta = Parameter("theta")
    circuit = QuantumCircuit(1)
    circuit.rx(theta, 0)

    result = import_qiskit_circuit(circuit)

    assert result.report.status == "UNSUPPORTED"
    assert "symbolic_parameters_unsupported" in {
        item.code for item in result.report.unsupported_reasons
    }


def test_import_rejects_nonzero_global_phase() -> None:
    circuit = QuantumCircuit(1, global_phase=0.25)
    circuit.x(0)

    result = import_qiskit_circuit(circuit)

    assert result.report.status == "UNSUPPORTED"
    assert "nonzero_global_phase_unsupported" in {
        item.code for item in result.report.unsupported_reasons
    }


def test_import_rejects_measurement_without_partial_translation() -> None:
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)

    result = import_qiskit_circuit(circuit)

    assert result.report.status == "UNSUPPORTED"
    assert result.circuit is None
    assert "classical_operation_unsupported" in {
        item.code for item in result.report.unsupported_reasons
    }


def test_assurance_returns_verified_compiler_result() -> None:
    circuit = QuantumCircuit(1, name="merge")
    circuit.rx(0.2, 0)
    circuit.ry(0.3, 0)

    result = assure_qiskit_circuit(circuit)

    assert result.assurance_status == "VERIFIED"
    assert result.optimization_applied is True
    assert result.fallback_reason is None
    assert result.compiler_report.equivalence_status == "VERIFIED"
    assert _equivalent_up_to_phase(circuit, result.returned_circuit)


def test_assurance_verifies_rewrites_around_iswap() -> None:
    circuit = QuantumCircuit(2, name="iswap-regression")
    circuit.h(0)
    circuit.iswap(0, 1)
    circuit.h(0)

    result = assure_qiskit_circuit(circuit)

    assert result.assurance_status == "VERIFIED"
    assert result.optimization_applied is True
    assert result.fallback_reason is None
    assert result.compiler_report.equivalence_status == "VERIFIED"
    assert _equivalent_up_to_phase(circuit, result.returned_circuit)


def test_assurance_supports_terminal_measurement_suffix() -> None:
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)

    result = assure_qiskit_circuit(circuit)

    assert result.assurance_status == "VERIFIED"
    assert result.fallback_reason is None
    assert result.returned_circuit.num_clbits == 1
    assert result.returned_circuit is not circuit
    assert result.normalized_input is not None


def test_openqasm_roundtrip_remains_in_supported_subset() -> None:
    circuit = QuantumCircuit(2)
    circuit.rx(0.2, 0)
    circuit.ry(0.3, 0)
    circuit.cx(0, 1)
    circuit.rzz(0.4, 0, 1)
    imported = import_qiskit_circuit(circuit)
    assert imported.circuit is not None

    exported = export_openqasm3(imported.circuit)
    reparsed = import_openqasm3(exported.source or "")

    assert exported.status == "EXPORTED"
    assert reparsed.report.status == "SUPPORTED"
    assert reparsed.circuit is not None
    returned = compiled_circuit_to_qiskit(reparsed.circuit)
    assert _equivalent_up_to_phase(circuit, returned)


def test_export_uses_canonical_lowering_without_retranspilation(monkeypatch) -> None:
    circuit = Circuit(1)
    circuit.add(Operation(gate="rx", targets=[0], params={"angle": 0.25}))
    real_dumps = assurance_module.qasm3.dumps
    calls = 0

    def counted_dumps(value):
        nonlocal calls
        calls += 1
        return real_dumps(value)

    monkeypatch.setattr(assurance_module.qasm3, "dumps", counted_dumps)

    result = export_openqasm3(circuit)

    assert result.status == "EXPORTED"
    assert calls == 1
    assert result.source is not None
    assert import_openqasm3(result.source).report.status == "SUPPORTED"


def test_toolchain_versions_are_cached_across_hot_path_requests(monkeypatch) -> None:
    calls: list[str] = []

    def counted_version(name: str) -> str:
        calls.append(name)
        return f"{name}-test"

    assurance_module._package_version.cache_clear()
    monkeypatch.setattr(assurance_module, "version", counted_version)
    circuit = QuantumCircuit(1)
    circuit.x(0)

    first = import_qiskit_circuit(circuit)
    second = import_qiskit_circuit(circuit)

    assert first.report.adapter_version == "rqm-qiskit-test"
    assert second.report.qiskit_version == "qiskit-test"
    assert calls == ["rqm-qiskit", "qiskit"]
    assurance_module._package_version.cache_clear()


def test_import_report_to_dict_preserves_dataclass_shape() -> None:
    from dataclasses import asdict

    circuit = QuantumCircuit(1)
    circuit.rx(0.25, 0)
    report = import_qiskit_circuit(circuit).report

    assert report.to_dict() == asdict(report)


def test_assurance_report_to_dict_does_not_alias_evidence() -> None:
    circuit = QuantumCircuit(1)
    circuit.rx(0.25, 0)
    circuit.ry(-0.5, 0)
    result = assure_qiskit_circuit(circuit)
    payload = result.to_dict()

    payload["compiler_report"]["passes_applied"].append("external_mutation")
    payload["compiler_report"]["equivalence_report"]["notes"].append(
        "external_mutation"
    )
    payload["normalized_input"]["descriptors"][0]["params"][
        "external_mutation"
    ] = True

    assert "external_mutation" not in result.compiler_report.passes_applied
    assert (
        "external_mutation"
        not in result.compiler_report.equivalence_report["notes"]
    )
    assert (
        "external_mutation"
        not in result.normalized_input.to_descriptors()[0]["params"]
    )


def test_malformed_openqasm_returns_structured_error() -> None:
    result = import_openqasm3("OPENQASM 3.0;\nqubit[1] q;\nrx( q[0];")

    assert result.circuit is None
    assert result.report.status == "ERROR"
    assert result.report.error
    assert result.report.source_sha256


def test_isolated_openqasm_bridge_roundtrips_for_server_use() -> None:
    source = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\nh q[0];\n'

    imported = import_openqasm3_isolated(source)
    assert imported.report.status == "SUPPORTED"
    assert imported.circuit is not None

    exported = export_openqasm3_isolated(imported.circuit)
    assert exported.status == "EXPORTED"
    assert exported.source is not None
    assert import_openqasm3(exported.source).report.status == "SUPPORTED"


def test_isolated_worker_preserves_runtime_injected_import_paths(monkeypatch) -> None:
    monkeypatch.setattr(
        assurance_module.sys,
        "path",
        ["/var/task", "/var/task/_vendor", ""],
    )
    monkeypatch.setenv("PYTHONPATH", "/configured")

    environment = assurance_module._isolated_worker_environment()

    assert environment["PYTHONPATH"].split(assurance_module.os.pathsep) == [
        "/var/task",
        "/var/task/_vendor",
        "/configured",
    ]


def test_unknown_compiler_gate_is_never_silently_ignored() -> None:
    circuit = Circuit(1)
    circuit.add(Operation(gate="unknown", targets=[0]))

    with pytest.raises(TranslationError, match="refusing to omit"):
        compiled_circuit_to_qiskit(circuit)
