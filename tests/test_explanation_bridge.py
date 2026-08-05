from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qasm3
from qiskit.circuit import Parameter
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Operator, Statevector

from rqm_qiskit import (
    RQMExplanation,
    RQMExplanationSection,
    analyze_qiskit_circuit,
    analyze_qiskit_state,
)
from rqm_qiskit.cli import main as cli_main


def _matrix(payload: list[list[dict[str, float]]]) -> np.ndarray:
    return np.asarray(
        [[complex(value["real"], value["imag"]) for value in row] for row in payload],
        dtype=np.complex128,
    )


def _bell() -> QuantumCircuit:
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    return circuit


def _product() -> QuantumCircuit:
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.x(1)
    return circuit


def test_public_explanation_types_are_populated_and_json_safe() -> None:
    circuit = QuantumCircuit(1)
    circuit.ry(math.pi / 2, 0)

    report = analyze_qiskit_circuit(circuit)

    assert isinstance(report.explanation, RQMExplanation)
    assert all(
        isinstance(section, RQMExplanationSection) and section.evidence_paths
        for section in report.explanation.sections
    )
    assert {section.key for section in report.explanation.sections} >= {
        "quaternion",
        "rotation",
        "bloch",
        "phase",
        "measurement",
        "limitations",
    }
    json.dumps(report.to_dict(), allow_nan=False)


def test_one_qubit_operator_factorization_reconstructs_qiskit_exactly() -> None:
    circuit = QuantumCircuit(1, global_phase=0.37)
    circuit.rz(0.41, 0)
    circuit.ry(-0.72, 0)
    circuit.rx(1.13, 0)

    report = analyze_qiskit_circuit(circuit)
    local = report.local_geometry[0]
    phase = local["operator_global_phase"]["radians"]
    reconstructed = np.exp(1j * phase) * _matrix(local["su2_matrix"])

    assert report.status == "complete"
    assert np.allclose(reconstructed, Operator(circuit).data, atol=1e-9, rtol=1e-9)
    assert local["angle_pi_multiple"]
    assert local["angle_degrees"] == pytest.approx(math.degrees(local["angle"]))


def test_numeric_public_unitary_is_explained_without_becoming_optimizable() -> None:
    matrix = np.exp(0.23j) * np.asarray(
        [[math.cos(0.2), -math.sin(0.2)], [math.sin(0.2), math.cos(0.2)]],
        dtype=np.complex128,
    )
    circuit = QuantumCircuit(1)
    circuit.append(UnitaryGate(matrix), [0])

    explanation_only = analyze_qiskit_circuit(circuit)
    optimization_requested = analyze_qiskit_circuit(circuit, optimize=True)

    assert explanation_only.status == "complete"
    assert explanation_only.assurance is None
    assert optimization_requested.status == "partial"
    assert optimization_requested.assurance["assurance_status"] == "FALLBACK_ORIGINAL"
    assert optimization_requested.assurance["optimization_applied"] is False
    assert circuit.data[0].operation.name == "unitary"


def test_detail_levels_keep_matrices_and_fingerprints_technical() -> None:
    circuit = QuantumCircuit(1)
    circuit.h(0)
    report = analyze_qiskit_circuit(circuit)

    summary = report.to_text("summary")
    standard = report.to_text("standard")
    technical = report.to_text("technical")

    assert "Canonical fingerprint:" not in summary
    assert "Canonical fingerprint:" not in standard
    assert "SU(2) matrix:" not in standard
    assert "Canonical fingerprint:" in technical
    assert "SU(2) matrix:" in technical
    assert len(summary) < len(standard) < len(technical)
    with pytest.raises(ValueError, match="detail"):
        report.to_text("verbose")  # type: ignore[arg-type]


def test_phase_explanation_distinguishes_physical_invariance_and_control() -> None:
    circuit = QuantumCircuit(1, global_phase=math.pi / 7)
    circuit.x(0)
    text = analyze_qiskit_circuit(circuit).to_text()

    assert "U = e^(iφ)R(q)" in text
    assert "q and −q produce the same Bloch geometry" in text
    assert "coherently controlled" in text


def test_sign_negated_state_keeps_geometry_and_probability_invariants() -> None:
    positive = analyze_qiskit_state([1 / math.sqrt(3), math.sqrt(2 / 3) * 1j])
    negative = analyze_qiskit_state([-1 / math.sqrt(3), -math.sqrt(2 / 3) * 1j])

    assert positive.measurement_predictions == negative.measurement_predictions
    assert positive.local_geometry[0]["bloch"] == pytest.approx(
        negative.local_geometry[0]["bloch"]
    )
    assert (
        positive.local_geometry[0]["physical_state_fingerprint"]
        == (negative.local_geometry[0]["physical_state_fingerprint"])
    )


@pytest.mark.parametrize(
    ("circuit", "expected_class", "entanglement_phrase"),
    [
        (_bell(), "cnot_cz_class", "output state is entangled"),
        (_product(), "local_identity", "output state is a product state"),
    ],
)
def test_two_qubit_explanation_covers_weyl_and_entanglement(
    circuit: QuantumCircuit,
    expected_class: str,
    entanglement_phrase: str,
) -> None:
    report = analyze_qiskit_circuit(circuit)
    payload = report.nonlocal_geometry[0]
    text = report.to_text()

    assert report.status == "complete"
    assert payload["su4"]["verified"] is True
    assert payload["local_equivalence"]["class_label"] == expected_class
    assert "Weyl coordinates" in text
    assert "perfect entangler" in text
    assert entanglement_phrase in text
    assert "Concurrence:" in text
    assert "Entropy:" in text


def test_reversed_terminal_measurement_mapping_is_explained_exactly() -> None:
    qreg = QuantumRegister(2, "science")
    creg = ClassicalRegister(2, "readout")
    circuit = QuantumCircuit(qreg, creg)
    circuit.h(qreg[0])
    circuit.cx(qreg[0], qreg[1])
    circuit.measure(qreg[0], creg[1])
    circuit.measure(qreg[1], creg[0])
    before = circuit.copy()

    report = analyze_qiskit_circuit(circuit)

    assert circuit == before
    assert report.circuit_summary["terminal_measurements"] == [
        {"qubit": 0, "clbit": 1},
        {"qubit": 1, "clbit": 0},
    ]
    assert '"clbit": 1' in report.to_text()


def _boundary_circuits() -> list[QuantumCircuit]:
    theta = Parameter("theta")
    symbolic = QuantumCircuit(1)
    symbolic.rx(theta, 0)

    reset = QuantumCircuit(1)
    reset.reset(0)

    initialize = QuantumCircuit(1)
    initialize.initialize([1, 0], 0)

    mid_measurement = QuantumCircuit(1, 1)
    mid_measurement.h(0)
    mid_measurement.measure(0, 0)
    mid_measurement.x(0)

    control_flow = QuantumCircuit(1, 1)
    with control_flow.if_test((control_flow.clbits[0], True)):
        control_flow.x(0)

    return [symbolic, reset, initialize, mid_measurement, control_flow]


@pytest.mark.parametrize("circuit", _boundary_circuits())
def test_boundary_constructs_receive_useful_partial_explanations(
    circuit: QuantumCircuit,
) -> None:
    report = analyze_qiskit_circuit(circuit)
    text = report.to_text()

    assert report.status == "partial"
    assert "circuit_geometry" in report.not_computed
    assert report.measurement_predictions is None
    assert "Probabilities were not computed" in text
    assert "not_computed" in text


def test_larger_circuit_remains_structural_and_partial() -> None:
    circuit = QuantumCircuit(4)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.ry(0.3, 2)
    circuit.cz(2, 3)

    report = analyze_qiskit_circuit(circuit)

    assert report.status == "partial"
    assert "global_unitary" in report.not_computed
    assert report.nonlocal_geometry[0]["assurance_scope"] == (
        "independently_verified_regions"
    )


def test_text_and_json_are_deterministic_across_five_runs() -> None:
    circuit = QuantumCircuit(1, global_phase=0.19)
    circuit.rz(0.31, 0)
    circuit.ry(-0.47, 0)
    circuit.rz(0.83, 0)

    texts = []
    payloads = []
    for _ in range(5):
        report = analyze_qiskit_circuit(circuit)
        texts.append(report.to_text("technical"))
        payloads.append(json.dumps(report.to_dict(), sort_keys=True, allow_nan=False))

    assert len(set(texts)) == 1
    assert len(set(payloads)) == 1


def test_cli_explain_writes_markdown_and_optional_json(tmp_path) -> None:
    circuit = QuantumCircuit(1)
    circuit.ry(math.pi / 2, 0)
    source = tmp_path / "input.qasm"
    source.write_text(qasm3.dumps(circuit), encoding="utf-8")
    output = tmp_path / "EXPLANATION.md"
    report = tmp_path / "REPORT.json"

    exit_code = cli_main(
        [
            "explain",
            str(source),
            "--detail",
            "standard",
            "--output",
            str(output),
            "--report",
            str(report),
        ]
    )

    assert exit_code == 0
    assert "# Quaternionic explanation" in output.read_text(encoding="utf-8")
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "complete"


def test_cli_explain_uses_stdout_and_partial_exit_code(tmp_path, capsys) -> None:
    circuit = QuantumCircuit(1)
    circuit.reset(0)
    source = tmp_path / "partial.qasm"
    source.write_text(qasm3.dumps(circuit), encoding="utf-8")

    assert cli_main(["explain", str(source), "--detail", "summary"]) == 2
    output = capsys.readouterr().out
    assert "structural" in output or "not computed" in output


def test_representative_summary_texts_match_golden_hashes() -> None:
    phase = QuantumCircuit(1, global_phase=math.pi / 7)
    phase.x(0)
    partial = QuantumCircuit(1)
    partial.reset(0)
    cases = {
        "one_qubit": analyze_qiskit_circuit(QuantumCircuit(1)),
        "phase_sensitive": analyze_qiskit_circuit(phase),
        "bell": analyze_qiskit_circuit(_bell()),
        "product": analyze_qiskit_circuit(_product()),
        "partial": analyze_qiskit_circuit(partial),
        "unsupported": analyze_qiskit_state(Statevector.from_label("000")),
    }
    expected = {
        "one_qubit": "f5e39d5e064252fc63f04ad92bf46776bdb4551faaada94cb3817b8c2c5abade",
        "phase_sensitive": "7f6178f7c9da63d0aaab8a0e712874c32fc423fde40fe8d3c45ea354deda5497",
        "bell": "710e8d0e6b836056fadf2a0432975e44e7c1d9825675c8163628b80d0e52499b",
        "product": "373387fda6e946770065138dc00e4d84177023e2779a254667f5fda542070dc7",
        "partial": "7865486e40785965bfdc6558a33932139ad55edd6ebe2644d09b6433145b83a4",
        "unsupported": "0a37f336699d272754e8a06604442d09cff3c85bc1a37663e4cf2ba6ae849f59",
    }

    actual = {
        name: hashlib.sha256(report.to_text("summary").encode("utf-8")).hexdigest()
        for name, report in cases.items()
    }
    assert actual == expected
