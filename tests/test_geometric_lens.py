from __future__ import annotations

import asyncio
import json
import math

import numpy as np
import pytest
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qasm3
from qiskit.quantum_info import Operator, Statevector

from rqm_qiskit import (
    analyze_qiskit_circuit,
    analyze_qiskit_state,
    assure_openqasm3,
    assure_qiskit_circuit,
    async_assure_openqasm3,
    canonical_su2_fingerprint,
)
from rqm_qiskit.cli import main as cli_main


def _equivalent_up_to_phase(left: QuantumCircuit, right: QuantumCircuit) -> bool:
    lhs = Operator(left.remove_final_measurements(inplace=False)).data
    rhs = Operator(right.remove_final_measurements(inplace=False)).data
    overlap = np.vdot(rhs.reshape(-1), lhs.reshape(-1))
    if abs(overlap) == 0:
        return False
    return bool(np.allclose(lhs, overlap / abs(overlap) * rhs, atol=1e-9, rtol=1e-9))


def _equivalent_family() -> tuple[list[QuantumCircuit], QuantumCircuit]:
    a, b, c = (0.37, -0.81, 1.13)
    direct = QuantumCircuit(1)
    direct.rz(a, 0)
    direct.ry(b, 0)
    direct.rz(c, 0)
    split = QuantumCircuit(1)
    split.rz(a / 2, 0)
    split.rz(a / 2, 0)
    split.ry(b / 2, 0)
    split.ry(b / 2, 0)
    split.rz(c / 2, 0)
    split.rz(c / 2, 0)
    identity = QuantumCircuit(1)
    identity.rz(a, 0)
    identity.rx(0, 0)
    identity.ry(b, 0)
    identity.rz(c, 0)
    phase = QuantumCircuit(1)
    phase.rz(a + 2 * math.pi, 0)
    phase.ry(b, 0)
    phase.rz(c, 0)
    control = QuantumCircuit(1)
    control.rz(a, 0)
    control.ry(b, 0)
    control.rz(c + 0.125, 0)
    return [direct, split, identity, phase], control


def test_canonical_su2_fingerprint_converges_without_control_collision() -> None:
    family, control = _equivalent_family()
    fingerprints = {canonical_su2_fingerprint(circuit) for circuit in family}

    assert len(fingerprints) == 1
    assert canonical_su2_fingerprint(control) not in fingerprints


def test_canonical_fingerprint_preserves_noncommutative_order() -> None:
    left = QuantumCircuit(1)
    left.rx(0.37, 0)
    left.ry(-0.81, 0)
    right = QuantumCircuit(1)
    right.ry(-0.81, 0)
    right.rx(0.37, 0)

    assert canonical_su2_fingerprint(left) != canonical_su2_fingerprint(right)


@pytest.mark.parametrize("seed", range(12))
def test_fingerprint_property_split_rotations_converge(seed: int) -> None:
    rng = np.random.default_rng(seed)
    direct = QuantumCircuit(1)
    split = QuantumCircuit(1)
    for gate, angle in zip(
        ("rx", "ry", "rz", "rx", "rz"),
        rng.uniform(-2, 2, size=5),
        strict=True,
    ):
        getattr(direct, gate)(float(angle), 0)
        getattr(split, gate)(float(angle) / 2, 0)
        getattr(split, gate)(float(angle) / 2, 0)

    assert canonical_su2_fingerprint(direct) == canonical_su2_fingerprint(split)


def test_fingerprint_metamorphic_identity_and_global_sign_are_invariant() -> None:
    source = QuantumCircuit(1)
    source.rz(0.37, 0)
    source.ry(-0.81, 0)
    transformed = QuantumCircuit(1)
    transformed.rz(0.37 + 2 * math.pi, 0)
    transformed.rx(0.0, 0)
    transformed.ry(-0.81, 0)

    assert canonical_su2_fingerprint(source) == canonical_su2_fingerprint(
        transformed
    )


@pytest.mark.parametrize("seed", range(8))
def test_generated_assurance_differentially_matches_qiskit(seed: int) -> None:
    rng = np.random.default_rng(100 + seed)
    circuit = QuantumCircuit(1)
    for gate, angle in zip(
        ("rx", "ry", "rz", "ry", "rx", "rz", "rx"),
        rng.uniform(-math.pi, math.pi, size=7),
        strict=True,
    ):
        getattr(circuit, gate)(float(angle), 0)

    result = assure_qiskit_circuit(circuit)

    assert result.assurance_status == "VERIFIED"
    assert _equivalent_up_to_phase(circuit, result.returned_circuit)


def test_one_qubit_circuit_report_is_complete_and_json_safe() -> None:
    circuit = QuantumCircuit(1)
    circuit.ry(math.pi / 2, 0)

    report = analyze_qiskit_circuit(circuit, optimize=True)
    payload = report.to_dict()

    assert report.status == "complete"
    assert report.local_geometry[0]["canonical_su2_fingerprint"]
    probabilities = report.measurement_predictions["probabilities"]
    assert probabilities["0"] == pytest.approx(0.5)
    assert probabilities["1"] == pytest.approx(0.5)
    assert report.assurance["assurance_status"] == "VERIFIED"
    json.dumps(payload, allow_nan=False)


def test_quaternionic_state_report_preserves_ideal_measurement_probabilities() -> None:
    state = Statevector([math.sqrt(0.25), math.sqrt(0.75)])

    report = analyze_qiskit_state(state)

    assert report.status == "complete"
    assert report.local_geometry[0]["ideal_z_probabilities"] == pytest.approx(
        {"0": 0.25, "1": 0.75}
    )
    assert report.local_geometry[0]["su2_matrix"]


def test_state_analysis_rejects_non_normalized_amplitudes() -> None:
    report = analyze_qiskit_state([1.0, 1.0])

    assert report.status == "error"
    assert report.measurement_predictions is None
    assert "unit norm" in report.limitations[0]


def test_q_and_negative_q_keep_phase_sensitive_and_physical_fingerprints() -> None:
    positive = analyze_qiskit_state([math.sqrt(0.25), math.sqrt(0.75)])
    negative = analyze_qiskit_state([-math.sqrt(0.25), -math.sqrt(0.75)])
    positive_local = positive.local_geometry[0]
    negative_local = negative.local_geometry[0]

    assert positive_local["quaternionic_wavefunction_fingerprint"] != negative_local[
        "quaternionic_wavefunction_fingerprint"
    ]
    assert positive_local["physical_state_fingerprint"] == negative_local[
        "physical_state_fingerprint"
    ]
    assert positive.measurement_predictions == negative.measurement_predictions


def test_two_qubit_report_contains_verified_su4_and_entanglement() -> None:
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)

    report = analyze_qiskit_circuit(bell)
    payload = report.to_dict()

    assert report.status == "complete"
    assert payload["nonlocal_geometry"][0]["su4"]["verified"] is True
    assert payload["nonlocal_geometry"][0]["weyl_coordinates"]
    assert payload["nonlocal_geometry"][0]["local_equivalence"][
        "nonlocal_fingerprint"
    ]
    metrics = payload["nonlocal_geometry"][0]["entanglement"]["entangled_pairs"]
    assert any(item["metric_value"] == pytest.approx(1.0) for item in metrics)


def test_terminal_measurements_are_preserved_with_original_register_mapping() -> None:
    qreg = QuantumRegister(2, "science")
    creg = ClassicalRegister(2, "readout")
    circuit = QuantumCircuit(qreg, creg, name="mapped")
    circuit.rx(0.2, qreg[0])
    circuit.ry(0.3, qreg[0])
    circuit.cx(qreg[0], qreg[1])
    circuit.measure(qreg[0], creg[1])
    circuit.measure(qreg[1], creg[0])

    result = assure_qiskit_circuit(circuit)
    returned = result.returned_circuit
    measurements = [item for item in returned.data if item.operation.name == "measure"]

    assert result.assurance_status == "VERIFIED"
    assert [register.name for register in returned.qregs] == ["science"]
    assert [register.name for register in returned.cregs] == ["readout"]
    assert [returned.find_bit(item.clbits[0]).index for item in measurements] == [1, 0]
    assert _equivalent_up_to_phase(circuit, returned)


def test_larger_circuit_uses_verified_regions_and_returns_partial_geometry() -> None:
    circuit = QuantumCircuit(6, 6)
    for qubit in range(6):
        circuit.rx(0.1 + qubit * 0.01, qubit)
        circuit.ry(-0.2, qubit)
    for qubit in range(6):
        circuit.measure(qubit, qubit)

    assurance = assure_qiskit_circuit(circuit)
    report = analyze_qiskit_circuit(circuit, optimize=True)

    assert assurance.assurance_status == "VERIFIED"
    assert assurance.compiler_report.committed is True
    assert all(len(region.qubits) <= 3 for region in assurance.compiler_report.regions)
    assert report.status == "partial"
    assert "global_state" in report.not_computed
    assert report.nonlocal_geometry[0]["verified_regions"]


def test_larger_circuit_reports_regions_without_optimization_request() -> None:
    circuit = QuantumCircuit(5)
    for qubit in range(5):
        circuit.rx(0.1, qubit)
        circuit.ry(0.2, qubit)

    report = analyze_qiskit_circuit(circuit)

    assert report.status == "partial"
    assert report.optimization is None
    assert report.assurance is None
    assert report.nonlocal_geometry[0]["assurance_scope"] == (
        "independently_verified_regions"
    )
    assert report.nonlocal_geometry[0]["verified_regions"]


def test_mid_circuit_measurement_fails_closed_to_exact_original() -> None:
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)
    circuit.x(0)

    result = assure_qiskit_circuit(circuit)

    assert result.assurance_status == "FALLBACK_ORIGINAL"
    assert result.returned_circuit == circuit
    assert result.fallback_reason == "unsupported_input"
    assert any(
        reason.code == "mid_circuit_measurement_unsupported"
        for reason in result.import_report.unsupported_reasons
    )


def test_openqasm_sync_and_async_assurance_preserve_terminal_measurement() -> None:
    circuit = QuantumCircuit(1, 1)
    circuit.rx(0.2, 0)
    circuit.ry(0.3, 0)
    circuit.measure(0, 0)
    source = qasm3.dumps(circuit)

    sync_result = assure_openqasm3(source)
    async_result = asyncio.run(async_assure_openqasm3(source))

    assert sync_result.assurance_status == "VERIFIED"
    assert async_result.assurance_status == "VERIFIED"
    assert qasm3.loads(sync_result.returned_source).num_clbits == 1
    json.dumps(sync_result.to_dict(), allow_nan=False)


def test_openqasm_parse_failure_returns_exact_source() -> None:
    source = "OPENQASM 3.0; qubit[1] q; rx( q[0];"

    result = assure_openqasm3(source)

    assert result.assurance_status == "FALLBACK_ORIGINAL"
    assert result.fallback_reason == "import_error"
    assert result.returned_source == source


def test_cli_analyze_and_assure(tmp_path) -> None:
    circuit = QuantumCircuit(1, 1)
    circuit.ry(math.pi / 2, 0)
    circuit.measure(0, 0)
    source = tmp_path / "input.qasm"
    source.write_text(qasm3.dumps(circuit), encoding="utf-8")
    analysis = tmp_path / "analysis.json"
    optimized = tmp_path / "optimized.qasm"
    assurance = tmp_path / "assurance.json"

    assert cli_main(["analyze", str(source), "--report", str(analysis)]) == 0
    assert cli_main(
        [
            "assure",
            str(source),
            "--report",
            str(assurance),
            "--output",
            str(optimized),
        ]
    ) == 0
    assert json.loads(analysis.read_text())["status"] == "complete"
    assert json.loads(assurance.read_text())["assurance_status"] == "VERIFIED"
    assert qasm3.loads(optimized.read_text()).num_clbits == 1


def test_cli_safe_fallback_and_invalid_input_exit_codes(tmp_path) -> None:
    unsupported = QuantumCircuit(1, 1)
    unsupported.h(0)
    unsupported.measure(0, 0)
    unsupported.x(0)
    source_text = qasm3.dumps(unsupported)
    source = tmp_path / "unsupported.qasm"
    source.write_text(source_text, encoding="utf-8")
    report = tmp_path / "fallback.json"
    output = tmp_path / "fallback.qasm"

    assert cli_main(
        [
            "assure",
            str(source),
            "--report",
            str(report),
            "--output",
            str(output),
        ]
    ) == 2
    assert output.read_text(encoding="utf-8") == source_text

    malformed = tmp_path / "malformed.qasm"
    malformed.write_text("OPENQASM 3.0; qubit[1] q; rx( q[0];", encoding="utf-8")
    assert cli_main(
        ["analyze", str(malformed), "--report", str(tmp_path / "error.json")]
    ) == 1


def test_state_analysis_rejects_larger_dense_state() -> None:
    report = analyze_qiskit_state(Statevector.from_label("000"))

    assert report.status == "unsupported"
    assert "state_geometry" in report.not_computed
