"""Qiskit-compatible quaternionic explanations built from public interfaces."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from fractions import Fraction
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal, Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterExpression
from qiskit.quantum_info import Operator, Statevector
from rqm_core import (
    Quaternion,
    factor_u2_global_phase,
    measurement_probabilities,
    spinor_to_quaternion,
    state_to_bloch,
    su2_to_quaternion,
)
from rqm_entanglement import analyze_entanglement, decompose_su4_verified

from rqm_qiskit.assurance import _terminal_measurement_split, assure_qiskit_circuit


GeometryStatus = Literal["complete", "partial", "unsupported", "error"]
ExplanationDetail = Literal["summary", "standard", "technical"]
ExplanationSectionStatus = Literal["available", "not_computed"]
GEOMETRY_SCHEMA_VERSION = "0.4.0"
_FINGERPRINT_CONVENTION = "rqm-core-su2-quaternion-sign-canonical-v1"
_ROUND_DIGITS = 11
_NONUNITARY_NAMES = frozenset({"reset", "initialize"})


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _json_ready(value.to_dict())
    if hasattr(value, "value"):
        return _json_ready(value.value)
    return repr(value)


def _sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _zero_small(value: float, *, atol: float = 5e-12) -> float:
    return 0.0 if abs(float(value)) < atol else float(value)


def _rounded_components(quaternion: Quaternion) -> list[float]:
    return [
        _zero_small(round(float(value), _ROUND_DIGITS))
        for value in (quaternion.w, quaternion.x, quaternion.y, quaternion.z)
    ]


def _rounded_vector(values: Sequence[float]) -> list[float]:
    return [_zero_small(float(value)) for value in values]


def _complex_matrix(matrix: np.ndarray) -> list[list[dict[str, float]]]:
    return [
        [
            {"real": _zero_small(value.real), "imag": _zero_small(value.imag)}
            for value in row
        ]
        for row in np.asarray(matrix, dtype=np.complex128)
    ]


def _format_number(value: float) -> str:
    normalized = _zero_small(float(value), atol=5e-10)
    return f"{normalized:.6g}"


def _pi_multiple(value: float) -> str:
    if abs(value) < 5e-10:
        return "0"
    ratio = value / math.pi
    fraction = Fraction(ratio).limit_denominator(16)
    if abs(float(fraction) - ratio) > 1e-8:
        return f"{ratio:.6g}π"
    numerator, denominator = fraction.numerator, fraction.denominator
    sign = "-" if numerator < 0 else ""
    magnitude = abs(numerator)
    coefficient = "" if magnitude == 1 else str(magnitude)
    if denominator == 1:
        return f"{sign}{coefficient}π"
    return f"{sign}{coefficient}π/{denominator}"


def _quaternion_text(components: Sequence[float]) -> str:
    labels = ("", "i", "j", "k")
    pieces: list[str] = []
    for index, (value, label) in enumerate(zip(components, labels, strict=True)):
        magnitude = _format_number(abs(float(value)))
        term = f"{magnitude}{label}"
        if index == 0:
            pieces.append(f"-{term}" if value < 0 else term)
        else:
            pieces.append((" - " if value < 0 else " + ") + term)
    return "".join(pieces)


def _without_barriers(circuit: QuantumCircuit) -> QuantumCircuit:
    output = QuantumCircuit(
        circuit.num_qubits,
        name=circuit.name,
        global_phase=circuit.global_phase,
    )
    for instruction in circuit.data:
        if instruction.operation.name.lower() == "barrier":
            continue
        qubits = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        output.append(
            instruction.operation, [output.qubits[index] for index in qubits], []
        )
    return output


def _has_unbound_parameters(circuit: QuantumCircuit) -> bool:
    if circuit.parameters:
        return True
    return isinstance(circuit.global_phase, ParameterExpression) and bool(
        circuit.global_phase.parameters
    )


def _structural_boundary_reason(circuit: QuantumCircuit) -> str | None:
    if _has_unbound_parameters(circuit):
        return "Bind every symbolic parameter before requesting geometric analysis."
    for instruction in circuit.data:
        name = instruction.operation.name.lower()
        if name in _NONUNITARY_NAMES:
            return (
                f"Operation {name!r} is state preparation or nonunitary, so operator "
                "geometry is not computed."
            )
        if getattr(instruction.operation, "blocks", ()):
            return "Control-flow circuits receive a structural explanation only."
    return None


def _canonical_quaternion(
    circuit: QuantumCircuit,
) -> tuple[float, Quaternion, np.ndarray]:
    if circuit.num_qubits != 1:
        raise ValueError("Canonical SU(2) fingerprints require exactly one qubit.")
    operator = np.asarray(Operator(circuit).data, dtype=np.complex128)
    phase, special_unitary = factor_u2_global_phase(operator)
    raw_quaternion = su2_to_quaternion(special_unitary)
    quaternion = raw_quaternion.canonicalize()
    raw_components = np.asarray(_rounded_components(raw_quaternion))
    canonical_components = np.asarray(_rounded_components(quaternion))
    if float(np.dot(raw_components, canonical_components)) < 0.0:
        special_unitary = -special_unitary
        phase += math.pi
        if phase > math.pi:
            phase -= 2.0 * math.pi
    return phase, quaternion, special_unitary


def canonical_su2_fingerprint(circuit: QuantumCircuit) -> str:
    """Return the EXP-014 phase-aware canonical fingerprint for a 1Q circuit."""

    prefix, _, split_report = _terminal_measurement_split(circuit)
    if prefix is None:
        reason = (
            split_report.unsupported_reasons[0].message
            if split_report
            else "unsupported input"
        )
        raise ValueError(reason)
    boundary_reason = _structural_boundary_reason(prefix)
    if boundary_reason is not None:
        raise ValueError(boundary_reason)
    _, quaternion, _ = _canonical_quaternion(_without_barriers(prefix))
    return _sha256(_rounded_components(quaternion))


@dataclass(frozen=True)
class RQMExplanationSection:
    """One deterministic explanation section linked to report evidence."""

    key: str
    title: str
    status: ExplanationSectionStatus
    summary: str
    facts: tuple[str, ...]
    technical_facts: tuple[str, ...]
    evidence_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "facts": list(self.facts),
            "technical_facts": list(self.technical_facts),
            "evidence_paths": list(self.evidence_paths),
        }


@dataclass(frozen=True)
class RQMExplanation:
    """Deterministic, evidence-linked prose derived only from report fields."""

    headline: str
    overview: str
    sections: tuple[RQMExplanationSection, ...]
    closing_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "overview": self.overview,
            "sections": [section.to_dict() for section in self.sections],
            "closing_notes": list(self.closing_notes),
        }

    def to_text(self, detail: ExplanationDetail = "standard") -> str:
        if detail not in {"summary", "standard", "technical"}:
            raise ValueError("detail must be 'summary', 'standard', or 'technical'")
        lines = [f"# {self.headline}", "", self.overview]
        for section in self.sections:
            lines.extend(("", f"## {section.title}", "", section.summary))
            if detail != "summary":
                lines.extend(f"- {fact}" for fact in section.facts)
            if detail == "technical":
                lines.extend(f"- {fact}" for fact in section.technical_facts)
            evidence = ", ".join(f"`{path}`" for path in section.evidence_paths)
            lines.extend(("", f"Evidence: {evidence}."))
        if self.closing_notes:
            lines.extend(("", "## Reading notes", ""))
            lines.extend(f"- {note}" for note in self.closing_notes)
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class RQMGeometricReport:
    """Versioned, JSON-safe geometric analysis and explanation report."""

    schema_version: str
    status: GeometryStatus
    circuit_summary: dict[str, Any]
    local_geometry: tuple[dict[str, Any], ...]
    nonlocal_geometry: tuple[dict[str, Any], ...]
    measurement_predictions: dict[str, Any] | None
    optimization: dict[str, Any] | None
    assurance: dict[str, Any] | None
    not_computed: tuple[str, ...]
    limitations: tuple[str, ...]
    provenance: dict[str, Any]
    explanation: RQMExplanation | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_ready(
            {
                "schema_version": self.schema_version,
                "status": self.status,
                "circuit_summary": dict(self.circuit_summary),
                "local_geometry": list(self.local_geometry),
                "nonlocal_geometry": list(self.nonlocal_geometry),
                "measurement_predictions": self.measurement_predictions,
                "optimization": self.optimization,
                "assurance": self.assurance,
                "not_computed": list(self.not_computed),
                "limitations": list(self.limitations),
                "provenance": dict(self.provenance),
                "explanation": self.explanation.to_dict() if self.explanation else None,
            }
        )

    def to_text(self, detail: ExplanationDetail = "standard") -> str:
        explanation = self.explanation or _build_explanation(self)
        return explanation.to_text(detail)


def _provenance() -> dict[str, str]:
    return {
        "rqm_qiskit": _package_version("rqm-qiskit"),
        "rqm_core": _package_version("rqm-core"),
        "rqm_entanglement": _package_version("rqm-entanglement"),
        "rqm_compiler": _package_version("rqm-compiler"),
        "qiskit": _package_version("qiskit"),
        "qiskit_interface": "public Operator and Statevector APIs",
        "fingerprint_convention": _FINGERPRINT_CONVENTION,
    }


def _section(
    key: str,
    title: str,
    summary: str,
    evidence_paths: Sequence[str],
    *,
    facts: Sequence[str] = (),
    technical_facts: Sequence[str] = (),
    status: ExplanationSectionStatus = "available",
) -> RQMExplanationSection:
    return RQMExplanationSection(
        key=key,
        title=title,
        status=status,
        summary=summary,
        facts=tuple(facts),
        technical_facts=tuple(technical_facts),
        evidence_paths=tuple(evidence_paths),
    )


def _probability_facts(predictions: dict[str, Any]) -> tuple[str, ...]:
    probabilities = predictions.get("probabilities", {})
    return tuple(
        f"P(|{basis}⟩) = {_format_number(float(probability))}."
        for basis, probability in sorted(probabilities.items())
    )


def _metric_facts(entanglement: dict[str, Any]) -> tuple[str, ...]:
    facts: list[str] = []
    for item in entanglement.get("entangled_pairs", []):
        name = item.get("metric_name", "metric")
        value = _format_number(float(item.get("metric_value", 0.0)))
        facts.append(
            f"{name}: {value} ({item.get('interpretation', 'reported value')})."
        )
    return tuple(facts)


def _build_explanation(report: RQMGeometricReport) -> RQMExplanation:
    summary = report.circuit_summary
    source_type = summary.get("source_type", "input")
    source_label = "quantum state" if source_type == "statevector" else "Qiskit circuit"
    headline = "Quaternionic explanation of the quantum computation"
    overview = (
        f"This {report.status} report explains the {source_label} using ordinary quantum "
        "mechanics expressed through quaternion, rotation, Bloch, and—where available—"
        "two-qubit Cartan geometry. Analysis does not mutate the input."
    )
    sections: list[RQMExplanationSection] = [
        _section(
            "scope",
            "What was analyzed",
            (
                f"The input contains {summary.get('num_qubits', 'an unknown number of')} "
                f"qubit(s); geometric status is {report.status}."
            ),
            ("circuit_summary", "status", "not_computed"),
            facts=(
                f"Source type: {source_type}.",
                f"Unavailable sections: {', '.join(report.not_computed) or 'none'}.",
            ),
        )
    ]

    if report.local_geometry:
        local = report.local_geometry[0]
        components = local.get("canonical_quaternion") or local.get(
            "quaternionic_wavefunction"
        )
        if components is not None:
            kind = (
                "SU(2) operator"
                if "canonical_quaternion" in local
                else "state representative"
            )
            sections.append(
                _section(
                    "quaternion",
                    "Quaternion",
                    f"The {kind} is q = {_quaternion_text(components)}.",
                    ("local_geometry[0].canonical_quaternion",)
                    if "canonical_quaternion" in local
                    else ("local_geometry[0].quaternionic_wavefunction",),
                    facts=(
                        "The four real coefficients are w, x, y, and z in q = w + xi + yj + zk.",
                        "This is a re-expression of the same complex quantum object, not extra quantum information.",
                    ),
                    technical_facts=(
                        f"Quaternion components: {json.dumps(components)}.",
                        f"Canonical fingerprint: {local.get('canonical_su2_fingerprint') or local.get('physical_state_fingerprint')}.",
                        f"SU(2) matrix: {json.dumps(local.get('su2_matrix'), sort_keys=True)}.",
                    ),
                )
            )

        axis = local.get("axis")
        angle = local.get("angle")
        if axis is not None and angle is not None:
            degrees = local.get("angle_degrees", math.degrees(float(angle)))
            pi_value = local.get("angle_pi_multiple", _pi_multiple(float(angle)))
            axis_text = ", ".join(_format_number(float(value)) for value in axis)
            sections.append(
                _section(
                    "rotation",
                    "Rotation axis and angle",
                    f"The geometric axis is ({axis_text}) and the angle is {_format_number(float(angle))} radians.",
                    ("local_geometry[0].axis", "local_geometry[0].angle"),
                    facts=(
                        f"Angle in degrees: {_format_number(float(degrees))}°.",
                        f"Recognizable multiple of π: {pi_value}.",
                    ),
                )
            )

        state_geometry = local.get("final_state", local)
        bloch = state_geometry.get("bloch")
        if bloch is not None:
            bloch_text = ", ".join(_format_number(float(value)) for value in bloch)
            sections.append(
                _section(
                    "bloch",
                    "Bloch-sphere geometry",
                    f"Starting from ordinary |0⟩, the final Bloch vector is ({bloch_text})."
                    if "final_state" in local
                    else f"The state's Bloch vector is ({bloch_text}).",
                    ("local_geometry[0].final_state.bloch",)
                    if "final_state" in local
                    else ("local_geometry[0].bloch",),
                    facts=(
                        "The x and y coordinates describe equatorial coherence; z gives the computational-basis bias.",
                    ),
                )
            )

        phase = local.get("operator_global_phase")
        phase_summary = (
            f"The operator factors as U = e^(iφ)R(q), with φ = {_format_number(float(phase['radians']))} radians ({phase['pi_multiple']})."
            if phase is not None
            else "Changing q to −q changes the representative's global sign but not the isolated physical state."
        )
        phase_evidence = (
            (
                "local_geometry[0].operator_global_phase",
                "local_geometry[0].canonical_quaternion",
            )
            if phase is not None
            else (
                "local_geometry[0].quaternionic_wavefunction",
                "local_geometry[0].physical_state_fingerprint",
            )
        )
        sections.append(
            _section(
                "phase",
                "Phase behavior",
                phase_summary,
                phase_evidence,
                facts=(
                    "q and −q produce the same Bloch geometry and isolated measurement probabilities.",
                    "A phase that is global for an isolated operation can become observable when that operation is coherently controlled, so controlled context must preserve the original U(2) phase.",
                ),
            )
        )

    if report.nonlocal_geometry:
        nonlocal_item = report.nonlocal_geometry[0]
        su4 = nonlocal_item.get("su4")
        if su4 is not None:
            classification = su4["classification"]
            coordinates = nonlocal_item["weyl_coordinates"]
            coordinate_text = ", ".join(
                _format_number(float(value)) for value in coordinates
            )
            perfect = "is" if classification["perfect_entangler"] else "is not"
            sections.append(
                _section(
                    "su4_weyl",
                    "SU(4) and Weyl geometry",
                    f"The nonlocal Weyl coordinates are ({coordinate_text}), placing the operator in the {classification['class_label']} class.",
                    (
                        "nonlocal_geometry[0].su4",
                        "nonlocal_geometry[0].weyl_coordinates",
                        "nonlocal_geometry[0].local_equivalence",
                    ),
                    facts=(
                        f"The decomposition {perfect} a perfect entangler.",
                        f"Verified reconstruction error: {_format_number(float(su4['reconstruction_error']))}.",
                    ),
                    technical_facts=(
                        f"Nonlocal fingerprint: {classification['nonlocal_fingerprint']}.",
                        f"SU(4) decomposition: {json.dumps(su4, sort_keys=True)}.",
                    ),
                )
            )
        entanglement = nonlocal_item.get("entanglement")
        if entanglement is not None:
            has_entanglement = any(
                float(item.get("metric_value", 0.0)) > 1e-10
                for item in entanglement.get("entangled_pairs", [])
                if item.get("metric_name") in {"Concurrence", "Entropy"}
            )
            sections.append(
                _section(
                    "entanglement",
                    "Entanglement of the final state",
                    "The |0…0⟩ output state is entangled."
                    if has_entanglement
                    else "The |0…0⟩ output state is a product state within the reported tolerance.",
                    ("nonlocal_geometry[0].entanglement",),
                    facts=_metric_facts(entanglement),
                )
            )

    if report.measurement_predictions is not None:
        mapping = summary.get("terminal_measurements", [])
        mapping_note = (
            f"Terminal measurement mapping is preserved as {json.dumps(mapping, sort_keys=True)}."
            if mapping
            else "No terminal measurement mapping was present."
        )
        sections.append(
            _section(
                "measurement",
                "Ideal measurement predictions",
                "These are ideal computational-basis probabilities, not sampled hardware results.",
                ("measurement_predictions", "circuit_summary.terminal_measurements"),
                facts=(
                    *_probability_facts(report.measurement_predictions),
                    mapping_note,
                ),
            )
        )
    else:
        sections.append(
            _section(
                "measurement",
                "Ideal measurement predictions",
                "Probabilities were not computed because the input lies outside the bounded unitary analysis path.",
                ("measurement_predictions", "not_computed", "limitations"),
                status="not_computed",
            )
        )

    if report.assurance is not None:
        sections.append(
            _section(
                "optimization",
                "Optional optimization assurance",
                f"The optional assurance result is {report.assurance.get('assurance_status', 'unknown')}.",
                ("assurance", "optimization"),
                facts=(
                    "Explanation and optimization are independent: geometry can be complete even when optimization safely returns the exact original circuit.",
                ),
            )
        )

    limitation_summary = (
        "The report explicitly records every unavailable quantity and analysis boundary."
        if report.not_computed
        else "No requested bounded geometry section is unavailable."
    )
    sections.append(
        _section(
            "limitations",
            "Limitations",
            limitation_summary,
            ("not_computed", "limitations"),
            facts=report.limitations or ("No additional limitations were recorded.",),
            status="not_computed" if report.not_computed else "available",
        )
    )
    return RQMExplanation(
        headline=headline,
        overview=overview,
        sections=tuple(sections),
        closing_notes=(
            "Quaternionic geometry here is a standard re-expression of complex quantum mechanics.",
            "Optimization is optional and never changes a circuit without independent verification.",
        ),
    )


def _finish(report: RQMGeometricReport) -> RQMGeometricReport:
    return replace(report, explanation=_build_explanation(report))


def _state_probabilities(state: Statevector) -> dict[str, float]:
    qubits = int(round(math.log2(len(state.data))))
    return {
        format(index, f"0{qubits}b"): _zero_small(float(probability))
        for index, probability in enumerate(state.probabilities())
    }


def analyze_qiskit_state(state: Statevector | Sequence[complex]) -> RQMGeometricReport:
    """Analyze a normalized one- or two-qubit state through existing RQM math."""

    try:
        statevector = state if isinstance(state, Statevector) else Statevector(state)
    except Exception as exc:  # noqa: BLE001 - public report normalizes invalid inputs
        return _finish(
            RQMGeometricReport(
                schema_version=GEOMETRY_SCHEMA_VERSION,
                status="error",
                circuit_summary={"source_type": "statevector", "error": str(exc)},
                local_geometry=(),
                nonlocal_geometry=(),
                measurement_predictions=None,
                optimization=None,
                assurance=None,
                not_computed=("state_geometry",),
                limitations=(
                    "Input must be a valid normalized one- or two-qubit state.",
                ),
                provenance=_provenance(),
            )
        )

    if not statevector.is_valid():
        return _finish(
            RQMGeometricReport(
                schema_version=GEOMETRY_SCHEMA_VERSION,
                status="error",
                circuit_summary={
                    "source_type": "statevector",
                    "dimension": len(statevector.data),
                },
                local_geometry=(),
                nonlocal_geometry=(),
                measurement_predictions=None,
                optimization=None,
                assurance=None,
                not_computed=("state_geometry", "measurement_predictions"),
                limitations=("State amplitudes must have unit norm.",),
                provenance=_provenance(),
            )
        )

    size = len(statevector.data)
    if size not in (2, 4):
        return _finish(
            RQMGeometricReport(
                schema_version=GEOMETRY_SCHEMA_VERSION,
                status="unsupported",
                circuit_summary={"source_type": "statevector", "dimension": size},
                local_geometry=(),
                nonlocal_geometry=(),
                measurement_predictions=None,
                optimization=None,
                assurance=None,
                not_computed=("state_geometry", "measurement_predictions"),
                limitations=(
                    "State analysis is bounded to one or two qubits in version 0.4.",
                ),
                provenance=_provenance(),
            )
        )

    probabilities = _state_probabilities(statevector)
    if size == 2:
        alpha, beta = (complex(value) for value in statevector.data)
        quaternion = spinor_to_quaternion(alpha, beta).normalize()
        components = _rounded_components(quaternion)
        axis, angle = quaternion.to_axis_angle()
        bloch = state_to_bloch(alpha, beta)
        predicted = measurement_probabilities(*bloch)
        local = {
            "qubit": 0,
            "quaternionic_wavefunction": components,
            "quaternionic_wavefunction_fingerprint": _sha256(components),
            "physical_state_fingerprint": _sha256(
                _rounded_components(quaternion.canonicalize())
            ),
            "axis": _rounded_vector(axis),
            "angle": _zero_small(angle),
            "angle_degrees": _zero_small(math.degrees(angle)),
            "angle_pi_multiple": _pi_multiple(angle),
            "su2_matrix": _complex_matrix(np.asarray(quaternion.to_su2_matrix())),
            "bloch": _rounded_vector(bloch),
            "ideal_z_probabilities": {
                "0": _zero_small(predicted[0]),
                "1": _zero_small(predicted[1]),
            },
        }
        return _finish(
            RQMGeometricReport(
                schema_version=GEOMETRY_SCHEMA_VERSION,
                status="complete",
                circuit_summary={"source_type": "statevector", "num_qubits": 1},
                local_geometry=(local,),
                nonlocal_geometry=(),
                measurement_predictions={
                    "basis": "computational",
                    "probabilities": probabilities,
                },
                optimization=None,
                assurance=None,
                not_computed=(),
                limitations=(
                    "The quaternionic wavefunction is a standard-compatible regrouping of a C2 spinor.",
                    "Predictions are ideal probabilities, not hardware measurements.",
                ),
                provenance=_provenance(),
            )
        )

    entanglement = analyze_entanglement(
        np.asarray(statevector.data, dtype=np.complex128)
    )
    return _finish(
        RQMGeometricReport(
            schema_version=GEOMETRY_SCHEMA_VERSION,
            status="complete",
            circuit_summary={"source_type": "statevector", "num_qubits": 2},
            local_geometry=(),
            nonlocal_geometry=({"entanglement": _json_ready(entanglement)},),
            measurement_predictions={
                "basis": "computational",
                "probabilities": probabilities,
            },
            optimization=None,
            assurance=None,
            not_computed=("single_qubit_pure_state_geometry",),
            limitations=(
                "Entanglement metrics use ordinary complex tensor products.",
                "Predictions are ideal probabilities, not hardware measurements.",
            ),
            provenance=_provenance(),
        )
    )


def _measurement_mapping(circuit: QuantumCircuit) -> list[dict[str, int]]:
    mapping = []
    for instruction in circuit.data:
        if instruction.operation.name.lower() != "measure":
            continue
        mapping.append(
            {
                "qubit": circuit.find_bit(instruction.qubits[0]).index,
                "clbit": circuit.find_bit(instruction.clbits[0]).index,
            }
        )
    return mapping


def _summary(circuit: QuantumCircuit) -> dict[str, Any]:
    return {
        "source_type": "qiskit_circuit",
        "name": circuit.name,
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "operation_count": len(circuit.data),
        "depth": circuit.depth(),
        "gate_counts": {
            str(key): int(value) for key, value in circuit.count_ops().items()
        },
        "declared_global_phase": _json_ready(circuit.global_phase),
        "terminal_measurements": _measurement_mapping(circuit),
    }


def _stable_verification_payload(value: Any) -> Any:
    """Project compiler evidence without run-to-run timing observations."""

    if isinstance(value, dict):
        return {
            str(key): _stable_verification_payload(item)
            for key, item in value.items()
            if key not in {"elapsed_ns", "stage_timings_ns"}
        }
    if isinstance(value, (list, tuple)):
        return [_stable_verification_payload(item) for item in value]
    return value


def _partial_report(
    summary: dict[str, Any],
    limitations: Sequence[str],
    *,
    optimize: bool,
) -> RQMGeometricReport:
    unavailable = ["circuit_geometry", "measurement_predictions"]
    if optimize:
        unavailable.append("optimization")
    return _finish(
        RQMGeometricReport(
            schema_version=GEOMETRY_SCHEMA_VERSION,
            status="partial",
            circuit_summary=summary,
            local_geometry=(),
            nonlocal_geometry=(),
            measurement_predictions=None,
            optimization=None,
            assurance=None,
            not_computed=tuple(unavailable),
            limitations=tuple(dict.fromkeys(limitations)),
            provenance=_provenance(),
        )
    )


def analyze_qiskit_circuit(
    circuit: QuantumCircuit,
    *,
    optimize: bool = False,
    target: Any | None = None,
) -> RQMGeometricReport:
    """Explain a Qiskit circuit without broadening the optimization boundary."""

    if not isinstance(circuit, QuantumCircuit):
        return _finish(
            RQMGeometricReport(
                schema_version=GEOMETRY_SCHEMA_VERSION,
                status="error",
                circuit_summary={"source_type": type(circuit).__name__},
                local_geometry=(),
                nonlocal_geometry=(),
                measurement_predictions=None,
                optimization=None,
                assurance=None,
                not_computed=("circuit_geometry",),
                limitations=("Expected a qiskit.QuantumCircuit.",),
                provenance=_provenance(),
            )
        )

    summary = _summary(circuit)
    prefix, _, split_report = _terminal_measurement_split(circuit)
    if prefix is None:
        reasons = [
            reason.message
            for reason in (split_report.unsupported_reasons if split_report else ())
        ]
        return _partial_report(
            summary,
            reasons or ("The circuit is outside the unitary analysis boundary.",),
            optimize=optimize,
        )

    boundary_reason = _structural_boundary_reason(prefix)
    if boundary_reason is not None:
        return _partial_report(summary, (boundary_reason,), optimize=optimize)

    assurance_result = (
        assure_qiskit_circuit(circuit, target=target) if optimize else None
    )
    assurance_payload = (
        assurance_result.to_dict() if assurance_result is not None else None
    )
    optimization_payload = (
        assurance_payload.get("compiler_report") if assurance_payload else None
    )
    local_geometry: list[dict[str, Any]] = []
    nonlocal_geometry: list[dict[str, Any]] = []
    not_computed: list[str] = []
    limitations = [
        "All geometry is standard-compatible and adds no quantum information.",
        "Ideal probabilities are not simulator, emulator, or QPU evidence.",
    ]

    try:
        semantic = _without_barriers(prefix)
        if circuit.num_qubits == 1:
            phase, quaternion, special_unitary = _canonical_quaternion(semantic)
            components = _rounded_components(quaternion)
            axis, angle = quaternion.to_axis_angle()
            state_report = analyze_qiskit_state(Statevector.from_instruction(semantic))
            state_local = state_report.local_geometry[0]
            local_geometry.append(
                {
                    "qubit": 0,
                    "canonical_quaternion": components,
                    "canonical_su2_fingerprint": _sha256(components),
                    "operator_global_phase": {
                        "radians": _zero_small(phase),
                        "degrees": _zero_small(math.degrees(phase)),
                        "pi_multiple": _pi_multiple(phase),
                        "factorization": "U = exp(i * phase) * SU(2)",
                        "phase_is_unique_modulo": "pi",
                    },
                    "axis": _rounded_vector(axis),
                    "angle": _zero_small(angle),
                    "angle_degrees": _zero_small(math.degrees(angle)),
                    "angle_pi_multiple": _pi_multiple(angle),
                    "su2_matrix": _complex_matrix(special_unitary),
                    "final_state": state_local,
                }
            )
            measurement_predictions = state_report.measurement_predictions
            status: GeometryStatus = "complete"
        elif circuit.num_qubits == 2:
            unitary = np.asarray(Operator(semantic).data, dtype=np.complex128)
            decomposition = decompose_su4_verified(unitary)
            decomposition_payload = decomposition.to_dict()
            classification = decomposition_payload["classification"]
            state_report = analyze_qiskit_state(Statevector.from_instruction(semantic))
            nonlocal_geometry.append(
                {
                    "su4": decomposition_payload,
                    "weyl_coordinates": classification["cartan"],
                    "local_equivalence": {
                        "nonlocal_fingerprint": classification["nonlocal_fingerprint"],
                        "class_label": classification["class_label"],
                        "convention_version": classification["convention_version"],
                    },
                    "entanglement": state_report.nonlocal_geometry[0]["entanglement"],
                }
            )
            measurement_predictions = state_report.measurement_predictions
            not_computed.append("per_qubit_pure_state_geometry")
            status = "complete"
        else:
            measurement_predictions = None
            not_computed.extend(
                ("global_state", "global_unitary", "measurement_predictions")
            )
            analysis_assurance = assurance_result or assure_qiskit_circuit(
                circuit, target=target
            )
            analysis_payload = analysis_assurance.to_dict()
            regional_payload = _stable_verification_payload(
                analysis_payload.get("compiler_report")
            )
            if circuit.num_qubits == 3 and regional_payload is not None:
                nonlocal_geometry.append(
                    {
                        "assurance_scope": "whole_circuit_up_to_three_qubits",
                        "verification": regional_payload,
                    }
                )
            elif regional_payload is not None:
                nonlocal_geometry.append(
                    {
                        "assurance_scope": "independently_verified_regions",
                        "verified_regions": regional_payload.get("regions", []),
                    }
                )
            if analysis_assurance.assurance_status != "VERIFIED":
                limitations.append(
                    "Regional assurance fell back to the original circuit: "
                    f"{analysis_assurance.fallback_reason}."
                )
            limitations.append(
                "Three-qubit circuits receive bounded whole-circuit verification; larger circuits receive independently verified regional summaries. No dense global geometry is computed."
            )
            status = "partial"
    except Exception as exc:  # noqa: BLE001 - convert unavailable math to a partial report
        measurement_predictions = None
        not_computed.extend(("circuit_geometry", "measurement_predictions"))
        limitations.append(str(exc))
        status = "partial"

    if assurance_result is not None and assurance_result.assurance_status != "VERIFIED":
        status = "partial" if status == "complete" else status
        limitations.append(
            f"Optimization fell back to the original circuit: {assurance_result.fallback_reason}."
        )

    return _finish(
        RQMGeometricReport(
            schema_version=GEOMETRY_SCHEMA_VERSION,
            status=status,
            circuit_summary=summary,
            local_geometry=tuple(local_geometry),
            nonlocal_geometry=tuple(nonlocal_geometry),
            measurement_predictions=measurement_predictions,
            optimization=optimization_payload,
            assurance=assurance_payload,
            not_computed=tuple(dict.fromkeys(not_computed)),
            limitations=tuple(dict.fromkeys(limitations)),
            provenance=_provenance(),
        )
    )
