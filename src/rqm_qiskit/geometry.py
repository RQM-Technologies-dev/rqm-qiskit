"""Standard-compatible quaternion/SU(2)/SU(4) analysis for Qiskit objects."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal, Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
from rqm_core import Quaternion, measurement_probabilities, spinor_to_quaternion, state_to_bloch
from rqm_entanglement import analyze_entanglement, decompose_su4_verified

from rqm_qiskit.assurance import (
    _terminal_measurement_split,
    assure_qiskit_circuit,
    import_qiskit_circuit,
)


GeometryStatus = Literal["complete", "partial", "unsupported", "error"]
GEOMETRY_SCHEMA_VERSION = "0.4.0"
_FINGERPRINT_CONVENTION = "rqm-core-su2-quaternion-sign-canonical-v1"
_ROUND_DIGITS = 11


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


def _rounded_components(quaternion: Quaternion) -> list[float]:
    values = []
    for value in (quaternion.w, quaternion.x, quaternion.y, quaternion.z):
        normalized = 0.0 if abs(float(value)) < 5e-12 else round(float(value), _ROUND_DIGITS)
        values.append(normalized)
    return values


def _complex_matrix(matrix: np.ndarray) -> list[list[dict[str, float]]]:
    return [
        [
            {"real": float(value.real), "imag": float(value.imag)}
            for value in row
        ]
        for row in np.asarray(matrix, dtype=np.complex128)
    ]


def _without_barriers(circuit: QuantumCircuit) -> QuantumCircuit:
    output = QuantumCircuit(circuit.num_qubits, name=circuit.name, global_phase=circuit.global_phase)
    for instruction in circuit.data:
        if instruction.operation.name.lower() == "barrier":
            continue
        qubits = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        output.append(instruction.operation, [output.qubits[index] for index in qubits], [])
    return output


def _canonical_quaternion(circuit: QuantumCircuit) -> Quaternion:
    if circuit.num_qubits != 1:
        raise ValueError("Canonical SU(2) fingerprints require exactly one qubit.")
    prefix, _, split_report = _terminal_measurement_split(circuit)
    if prefix is None:
        reason = split_report.unsupported_reasons[0].message if split_report else "unsupported input"
        raise ValueError(reason)
    semantic = _without_barriers(prefix)
    imported = import_qiskit_circuit(semantic, max_qubits=1)
    if imported.circuit is None:
        if imported.report.unsupported_reasons:
            reason = imported.report.unsupported_reasons[0].message
        else:
            reason = imported.report.error or "Circuit is outside the supported SU(2) boundary."
        raise ValueError(reason)

    from rqm_compiler import optimize_circuit

    optimized, report = optimize_circuit(imported.circuit)
    if report.equivalence_status != "VERIFIED" or report.fallback_reason is not None:
        raise ValueError("Canonical SU(2) optimization was not verified.")
    operations = optimized.operations
    if not operations:
        return Quaternion.identity()
    if len(operations) != 1 or operations[0].gate != "u1q":
        raise ValueError("Compiler did not produce one canonical u1q representative.")
    params = operations[0].params
    return Quaternion(
        float(params["w"]),
        float(params["x"]),
        float(params["y"]),
        float(params["z"]),
    ).canonicalize()


def canonical_su2_fingerprint(circuit: QuantumCircuit) -> str:
    """Return the EXP-014 phase-aware canonical fingerprint for a 1Q circuit."""

    components = _rounded_components(_canonical_quaternion(circuit))
    return _sha256(components)


@dataclass(frozen=True)
class RQMGeometricReport:
    """Versioned, JSON-safe geometric analysis report."""

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

    def to_dict(self) -> dict[str, Any]:
        return _json_ready(asdict(self))


def _provenance() -> dict[str, str]:
    return {
        "rqm_qiskit": _package_version("rqm-qiskit"),
        "rqm_core": _package_version("rqm-core"),
        "rqm_entanglement": _package_version("rqm-entanglement"),
        "rqm_compiler": _package_version("rqm-compiler"),
        "qiskit": _package_version("qiskit"),
        "fingerprint_convention": _FINGERPRINT_CONVENTION,
    }


def _state_probabilities(state: Statevector) -> dict[str, float]:
    qubits = int(round(math.log2(len(state.data))))
    return {
        format(index, f"0{qubits}b"): float(probability)
        for index, probability in enumerate(state.probabilities())
    }


def analyze_qiskit_state(state: Statevector | Sequence[complex]) -> RQMGeometricReport:
    """Analyze a normalized one- or two-qubit state through existing RQM math."""

    try:
        statevector = state if isinstance(state, Statevector) else Statevector(state)
    except Exception as exc:  # noqa: BLE001 - public report normalizes invalid inputs
        return RQMGeometricReport(
            schema_version=GEOMETRY_SCHEMA_VERSION,
            status="error",
            circuit_summary={"source_type": "statevector", "error": str(exc)},
            local_geometry=(),
            nonlocal_geometry=(),
            measurement_predictions=None,
            optimization=None,
            assurance=None,
            not_computed=("state_geometry",),
            limitations=("Input must be a valid normalized one- or two-qubit state.",),
            provenance=_provenance(),
        )

    if not statevector.is_valid():
        return RQMGeometricReport(
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

    size = len(statevector.data)
    if size not in (2, 4):
        return RQMGeometricReport(
            schema_version=GEOMETRY_SCHEMA_VERSION,
            status="unsupported",
            circuit_summary={"source_type": "statevector", "dimension": size},
            local_geometry=(),
            nonlocal_geometry=(),
            measurement_predictions=None,
            optimization=None,
            assurance=None,
            not_computed=("state_geometry", "measurement_predictions"),
            limitations=("State analysis is bounded to one or two qubits in version 0.4.",),
            provenance=_provenance(),
        )

    probabilities = _state_probabilities(statevector)
    if size == 2:
        alpha, beta = (complex(value) for value in statevector.data)
        quaternion = spinor_to_quaternion(alpha, beta)
        components = _rounded_components(quaternion)
        axis, angle = quaternion.normalize().to_axis_angle()
        bloch = state_to_bloch(alpha, beta)
        predicted = measurement_probabilities(*bloch)
        local = {
            "qubit": 0,
            "quaternionic_wavefunction": components,
            "quaternionic_wavefunction_fingerprint": _sha256(components),
            "physical_state_fingerprint": _sha256(
                _rounded_components(quaternion.canonicalize())
            ),
            "axis": list(axis),
            "angle": float(angle),
            "su2_matrix": _complex_matrix(
                np.asarray(quaternion.normalize().to_su2_matrix())
            ),
            "bloch": list(bloch),
            "ideal_z_probabilities": {"0": predicted[0], "1": predicted[1]},
        }
        return RQMGeometricReport(
            schema_version=GEOMETRY_SCHEMA_VERSION,
            status="complete",
            circuit_summary={"source_type": "statevector", "num_qubits": 1},
            local_geometry=(local,),
            nonlocal_geometry=(),
            measurement_predictions={"basis": "computational", "probabilities": probabilities},
            optimization=None,
            assurance=None,
            not_computed=(),
            limitations=(
                "The quaternionic wavefunction is a standard-compatible regrouping of a C2 spinor.",
                "Predictions are ideal probabilities, not hardware measurements.",
            ),
            provenance=_provenance(),
        )

    entanglement = analyze_entanglement(np.asarray(statevector.data, dtype=np.complex128))
    return RQMGeometricReport(
        schema_version=GEOMETRY_SCHEMA_VERSION,
        status="complete",
        circuit_summary={"source_type": "statevector", "num_qubits": 2},
        local_geometry=(),
        nonlocal_geometry=({"entanglement": _json_ready(entanglement)},),
        measurement_predictions={"basis": "computational", "probabilities": probabilities},
        optimization=None,
        assurance=None,
        not_computed=("single_qubit_pure_state_geometry",),
        limitations=(
            "Entanglement metrics use ordinary complex tensor products.",
            "Predictions are ideal probabilities, not hardware measurements.",
        ),
        provenance=_provenance(),
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


def analyze_qiskit_circuit(
    circuit: QuantumCircuit,
    *,
    optimize: bool = False,
    target: Any | None = None,
) -> RQMGeometricReport:
    """Describe a Qiskit circuit through the bounded RQM geometric lens."""

    if not isinstance(circuit, QuantumCircuit):
        return RQMGeometricReport(
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

    prefix, _, split_report = _terminal_measurement_split(circuit)
    summary = {
        "source_type": "qiskit_circuit",
        "name": circuit.name,
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "operation_count": len(circuit.data),
        "depth": circuit.depth(),
        "gate_counts": {str(key): int(value) for key, value in circuit.count_ops().items()},
        "terminal_measurements": _measurement_mapping(circuit),
    }
    if prefix is None:
        return RQMGeometricReport(
            schema_version=GEOMETRY_SCHEMA_VERSION,
            status="unsupported",
            circuit_summary=summary,
            local_geometry=(),
            nonlocal_geometry=(),
            measurement_predictions=None,
            optimization=None,
            assurance=None,
            not_computed=("circuit_geometry", "optimization"),
            limitations=tuple(
                reason.message for reason in (split_report.unsupported_reasons if split_report else ())
            ),
            provenance=_provenance(),
        )

    assurance_result = assure_qiskit_circuit(circuit, target=target) if optimize else None
    assurance_payload = assurance_result.to_dict() if assurance_result is not None else None
    optimization_payload = (
        assurance_payload.get("compiler_report") if assurance_payload is not None else None
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
            quaternion = _canonical_quaternion(semantic)
            components = _rounded_components(quaternion)
            axis, angle = quaternion.to_axis_angle()
            state_report = analyze_qiskit_state(Statevector.from_instruction(semantic))
            state_local = state_report.local_geometry[0]
            local_geometry.append(
                {
                    "qubit": 0,
                    "canonical_quaternion": components,
                    "canonical_su2_fingerprint": _sha256(components),
                    "axis": list(axis),
                    "angle": float(angle),
                    "su2_matrix": _complex_matrix(np.asarray(quaternion.to_su2_matrix())),
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
                        "nonlocal_fingerprint": classification[
                            "nonlocal_fingerprint"
                        ],
                        "class_label": classification["class_label"],
                        "convention_version": classification[
                            "convention_version"
                        ],
                    },
                    "entanglement": state_report.nonlocal_geometry[0]["entanglement"],
                }
            )
            measurement_predictions = state_report.measurement_predictions
            not_computed.append("per_qubit_pure_state_geometry")
            status = "complete"
        else:
            measurement_predictions = None
            not_computed.extend(("global_state", "global_unitary", "measurement_predictions"))
            analysis_assurance = assurance_result or assure_qiskit_circuit(
                circuit,
                target=target,
            )
            analysis_payload = analysis_assurance.to_dict()
            regional_payload = analysis_payload.get("compiler_report")
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
    except Exception as exc:  # noqa: BLE001 - return a bounded unsupported report
        measurement_predictions = None
        not_computed.extend(("circuit_geometry", "measurement_predictions"))
        limitations.append(str(exc))
        status = "unsupported"

    if assurance_result is not None and assurance_result.assurance_status != "VERIFIED":
        status = "partial" if status == "complete" else status
        limitations.append(
            f"Optimization fell back to the original circuit: {assurance_result.fallback_reason}."
        )

    return RQMGeometricReport(
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
