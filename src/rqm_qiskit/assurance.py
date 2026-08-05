"""Fail-closed Qiskit and OpenQASM 3 assurance bridges.

This module owns format adaptation only.  Circuit optimization and semantic
verification remain delegated to :mod:`rqm_compiler`, while lowering back to
Qiskit always routes through :func:`compiled_circuit_to_qiskit`.

The v0.4 boundary accepts bound unitary regions of at most three qubits and an
optional terminal-measurement suffix. Larger circuits are partitioned at
measurement and barrier boundaries and are changed only when every affected
region is independently verified. Equivalence is established up to global
phase; callers must not treat a returned circuit as safe to promote directly
to a coherently controlled subcircuit.
"""

from __future__ import annotations

import asyncio
import copy
import contextlib
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal

from qiskit import QuantumCircuit, qasm3

from rqm_qiskit._accelerator import extract_1q_operations
from rqm_qiskit.convert import compiled_circuit_to_qiskit

ImportStatus = Literal["SUPPORTED", "UNSUPPORTED", "ERROR"]
AssuranceStatus = Literal["VERIFIED", "FALLBACK_ORIGINAL"]
ExportStatus = Literal["EXPORTED", "ERROR"]

SUPPORTED_QISKIT_GATES: tuple[str, ...] = (
    "id",
    "x",
    "y",
    "z",
    "h",
    "s",
    "t",
    "rx",
    "ry",
    "rz",
    "p",
    "cx",
    "cy",
    "cz",
    "swap",
    "iswap",
    "rxx",
    "ryy",
    "rzz",
    "barrier",
)
MAX_ASSURANCE_QUBITS = 3

_NO_PARAM_GATES = frozenset({"id", "x", "y", "z", "h", "s", "t", "barrier"})
_ANGLE_GATES = frozenset({"rx", "ry", "rz", "p", "rxx", "ryy", "rzz"})
_CONTROLLED_GATES = frozenset({"cx", "cy", "cz"})
_TWO_TARGET_GATES = frozenset({"swap", "iswap", "rxx", "ryy", "rzz"})
_PARSE_LOCATION_PATTERNS = (
    re.compile(
        r"(?:line\s+)?(?P<line>\d+)\s*[,;:]\s*(?:column\s+)?(?P<column>\d+)",
        re.IGNORECASE,
    ),
    re.compile(r"line\s+(?P<line>\d+).*column\s+(?P<column>\d+)", re.IGNORECASE),
)
_LIMITATIONS = (
    "Dense whole-circuit assurance is limited to one to three qubits; larger circuits use verified regions of at most three qubits.",
    "Only terminal measurement suffixes are preserved; mid-circuit measurement and control flow fail closed.",
    "Semantic equivalence is bounded numerical or canonical verification up to global phase.",
    "The result is not formal verification and contains no simulator, emulator, or QPU evidence.",
    "Do not promote the returned circuit directly to a coherently controlled subcircuit.",
)


def _copy_report_value(value: Any) -> Any:
    """Copy report-shaped data without recursive dataclass reflection."""

    value_type = type(value)
    if value is None or value_type in (str, int, float, bool):
        return value
    if value_type is dict:
        return {
            _copy_report_value(key): _copy_report_value(item)
            for key, item in value.items()
        }
    if value_type is list:
        return [_copy_report_value(item) for item in value]
    if value_type is tuple:
        return tuple(_copy_report_value(item) for item in value)
    return copy.deepcopy(value)


@cache
def _package_version(name: str, fallback: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return fallback


def _adapter_version() -> str:
    return _package_version("rqm-qiskit", "0.0.0+unknown")


@dataclass(frozen=True)
class QiskitUnsupportedReason:
    """One stable, actionable reason why a circuit is outside the v0.4 boundary."""

    code: str
    message: str
    operation_index: int | None = None
    operation_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "operation_index": self.operation_index,
            "operation_name": self.operation_name,
        }


@dataclass(frozen=True)
class QiskitImportReport:
    """Structured report for a Qiskit or OpenQASM 3 import attempt."""

    status: ImportStatus
    source_format: Literal["qiskit", "openqasm3"]
    supported: bool
    num_qubits: int | None
    operation_count: int | None
    source_sha256: str | None
    unsupported_reasons: tuple[QiskitUnsupportedReason, ...] = ()
    error: str | None = None
    error_line: int | None = None
    error_column: int | None = None
    adapter_version: str = ""
    qiskit_version: str = ""
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_format": self.source_format,
            "supported": self.supported,
            "num_qubits": self.num_qubits,
            "operation_count": self.operation_count,
            "source_sha256": self.source_sha256,
            "unsupported_reasons": tuple(
                reason.to_dict() for reason in self.unsupported_reasons
            ),
            "error": self.error,
            "error_line": self.error_line,
            "error_column": self.error_column,
            "adapter_version": self.adapter_version,
            "qiskit_version": self.qiskit_version,
            "limitations": tuple(self.limitations),
        }


@dataclass(frozen=True)
class QiskitImportResult:
    """Imported compiler circuit plus its format-adaptation report."""

    circuit: Any | None
    report: QiskitImportReport


@dataclass(frozen=True)
class QiskitAssuranceResult:
    """Fail-closed result for a direct :class:`~qiskit.QuantumCircuit`."""

    returned_circuit: QuantumCircuit
    assurance_status: AssuranceStatus
    optimization_applied: bool
    fallback_reason: str | None
    import_report: QiskitImportReport
    compiler_report: Any | None
    normalized_input: Any | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe report without embedding live Qiskit objects."""

        normalized = (
            {
                "num_qubits": int(self.normalized_input.num_qubits),
                "descriptors": self.normalized_input.to_descriptors(),
            }
            if self.normalized_input is not None
            else None
        )
        compiler_report = None
        if self.compiler_report is not None:
            to_dict = getattr(self.compiler_report, "to_dict", None)
            compiler_report = (
                to_dict()
                if callable(to_dict)
                else _json_safe(dict(vars(self.compiler_report)))
            )
        return {
            "returned_circuit": {
                "name": self.returned_circuit.name,
                "num_qubits": self.returned_circuit.num_qubits,
                "num_clbits": self.returned_circuit.num_clbits,
                "operation_count": len(self.returned_circuit.data),
            },
            "assurance_status": self.assurance_status,
            "optimization_applied": self.optimization_applied,
            "fallback_reason": self.fallback_reason,
            "import_report": self.import_report.to_dict(),
            "compiler_report": compiler_report,
            "normalized_input": normalized,
        }


@dataclass(frozen=True)
class OpenQASMAssuranceResult:
    """Fail-closed assurance result for an OpenQASM 3 source string."""

    returned_source: str
    assurance_status: AssuranceStatus
    optimization_applied: bool
    fallback_reason: str | None
    source_sha256: str
    returned_source_sha256: str
    assurance_report: dict[str, Any] | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "returned_source": self.returned_source,
            "assurance_status": self.assurance_status,
            "optimization_applied": self.optimization_applied,
            "fallback_reason": self.fallback_reason,
            "source_sha256": self.source_sha256,
            "returned_source_sha256": self.returned_source_sha256,
            "assurance_report": _copy_report_value(self.assurance_report),
            "error": self.error,
        }


@dataclass(frozen=True)
class QiskitExportResult:
    """OpenQASM 3 export result for a compiler circuit."""

    status: ExportStatus
    source: str | None
    source_sha256: str | None
    error: str | None
    adapter_version: str
    qiskit_version: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "error": self.error,
            "adapter_version": self.adapter_version,
            "qiskit_version": self.qiskit_version,
            "limitations": tuple(self.limitations),
        }


def _limitations() -> tuple[str, ...]:
    return _LIMITATIONS


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return _json_safe(value.value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _json_safe(value.to_dict())
    return repr(value)


def _base_report(
    *,
    status: ImportStatus,
    source_format: Literal["qiskit", "openqasm3"],
    supported: bool,
    num_qubits: int | None,
    operation_count: int | None,
    source_sha256: str | None = None,
    reasons: tuple[QiskitUnsupportedReason, ...] = (),
    error: str | None = None,
    error_line: int | None = None,
    error_column: int | None = None,
) -> QiskitImportReport:
    return QiskitImportReport(
        status=status,
        source_format=source_format,
        supported=supported,
        num_qubits=num_qubits,
        operation_count=operation_count,
        source_sha256=source_sha256,
        unsupported_reasons=reasons,
        error=error,
        error_line=error_line,
        error_column=error_column,
        adapter_version=_adapter_version(),
        qiskit_version=_package_version("qiskit", "unknown"),
        limitations=_limitations(),
    )


def _reason(
    code: str,
    message: str,
    *,
    operation_index: int | None = None,
    operation_name: str | None = None,
) -> QiskitUnsupportedReason:
    return QiskitUnsupportedReason(
        code=code,
        message=message,
        operation_index=operation_index,
        operation_name=operation_name,
    )


def _finite_float(value: Any) -> float | None:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    return resolved if math.isfinite(resolved) else None


def _parse_error_location(message: str) -> tuple[int | None, int | None]:
    for pattern in _PARSE_LOCATION_PATTERNS:
        match = pattern.search(message)
        if match is not None:
            return int(match.group("line")), int(match.group("column"))
    return None, None


def import_qiskit_circuit(
    circuit: QuantumCircuit,
    *,
    max_qubits: int | None = MAX_ASSURANCE_QUBITS,
) -> QiskitImportResult:
    """Adapt a supported Qiskit circuit into the canonical compiler IR.

    Unsupported inputs return a structured result instead of a partial circuit.
    No instruction is ever skipped.
    """

    from rqm_compiler import Circuit
    from rqm_compiler.ops import Operation

    if not isinstance(circuit, QuantumCircuit):
        report = _base_report(
            status="ERROR",
            source_format="qiskit",
            supported=False,
            num_qubits=None,
            operation_count=None,
            error=f"Expected QuantumCircuit, received {type(circuit).__name__}.",
        )
        return QiskitImportResult(circuit=None, report=report)

    reasons: list[QiskitUnsupportedReason] = []
    if circuit.num_qubits < 1 or (
        max_qubits is not None and circuit.num_qubits > max_qubits
    ):
        expected = f"1-{max_qubits}" if max_qubits is not None else "at least 1"
        reasons.append(
            _reason(
                "qubit_count_out_of_range",
                f"Expected {expected} qubits; received {circuit.num_qubits}.",
            )
        )
    if circuit.num_clbits:
        reasons.append(
            _reason(
                "classical_data_unsupported",
                "Classical bits and registers are outside the v0.1 unitary boundary.",
            )
        )
    if circuit.parameters:
        reasons.append(
            _reason(
                "symbolic_parameters_unsupported",
                "Bind every Qiskit parameter before requesting assurance.",
            )
        )

    global_phase = _finite_float(circuit.global_phase)
    if global_phase is None:
        reasons.append(
            _reason(
                "symbolic_global_phase_unsupported",
                "The circuit global phase must be a finite numeric zero.",
            )
        )
    elif global_phase != 0.0:
        reasons.append(
            _reason(
                "nonzero_global_phase_unsupported",
                "OpenQASM assurance v0.4 accepts only circuits with zero declared global phase.",
            )
        )

    if not reasons and circuit.num_qubits == 1:
        native_records = extract_1q_operations(circuit)
        if native_records is not None:
            normalized = Circuit(1)
            add_operation = normalized.add
            for gate, angle in native_records:
                if angle is None:
                    add_operation(Operation(gate, [0]))
                else:
                    add_operation(Operation(gate, [0], [], {"angle": angle}))
            report = _base_report(
                status="SUPPORTED",
                source_format="qiskit",
                supported=True,
                num_qubits=1,
                operation_count=len(native_records),
            )
            return QiskitImportResult(circuit=normalized, report=report)

    descriptors: list[Operation] = []
    for index, instruction in enumerate(circuit.data):
        operation = instruction.operation
        gate = operation.name.lower()
        if instruction.clbits or getattr(operation, "num_clbits", 0):
            reasons.append(
                _reason(
                    "classical_operation_unsupported",
                    f"Operation {gate!r} reads or writes classical data.",
                    operation_index=index,
                    operation_name=gate,
                )
            )
            continue
        if getattr(operation, "condition", None) is not None:
            reasons.append(
                _reason(
                    "conditional_operation_unsupported",
                    f"Conditional operation {gate!r} is outside the v0.1 unitary boundary.",
                    operation_index=index,
                    operation_name=gate,
                )
            )
            continue
        if gate not in SUPPORTED_QISKIT_GATES:
            reasons.append(
                _reason(
                    "unsupported_operation",
                    f"Operation {gate!r} is not supported by the v0.4 assurance bridge.",
                    operation_index=index,
                    operation_name=gate,
                )
            )
            continue

        params: dict[str, Any] = {}
        if gate in _NO_PARAM_GATES:
            if operation.params:
                reasons.append(
                    _reason(
                        "unexpected_gate_parameters",
                        f"Operation {gate!r} must not contain parameters.",
                        operation_index=index,
                        operation_name=gate,
                    )
                )
                continue
        elif gate in _ANGLE_GATES:
            if len(operation.params) != 1:
                reasons.append(
                    _reason(
                        "invalid_gate_parameters",
                        f"Operation {gate!r} requires exactly one finite angle.",
                        operation_index=index,
                        operation_name=gate,
                    )
                )
                continue
            angle = _finite_float(operation.params[0])
            if angle is None:
                reasons.append(
                    _reason(
                        "unbound_or_nonfinite_parameter",
                        f"Operation {gate!r} has an unbound or non-finite angle.",
                        operation_index=index,
                        operation_name=gate,
                    )
                )
                continue
            params["angle"] = angle

        qubits = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        canonical_gate = "i" if gate == "id" else "phaseshift" if gate == "p" else gate
        if gate in _CONTROLLED_GATES:
            if len(qubits) != 2:
                reasons.append(
                    _reason(
                        "invalid_gate_arity",
                        f"Operation {gate!r} requires two qubits.",
                        operation_index=index,
                        operation_name=gate,
                    )
                )
                continue
            descriptors.append(
                Operation(
                    gate=canonical_gate,
                    controls=[qubits[0]],
                    targets=[qubits[1]],
                    params=params,
                )
            )
        elif gate in _TWO_TARGET_GATES:
            if len(qubits) != 2:
                reasons.append(
                    _reason(
                        "invalid_gate_arity",
                        f"Operation {gate!r} requires two qubits.",
                        operation_index=index,
                        operation_name=gate,
                    )
                )
                continue
            descriptors.append(
                Operation(gate=canonical_gate, targets=qubits, params=params)
            )
        elif gate == "barrier":
            descriptors.append(Operation(gate="barrier", targets=qubits))
        else:
            if len(qubits) != 1:
                reasons.append(
                    _reason(
                        "invalid_gate_arity",
                        f"Operation {gate!r} requires one qubit.",
                        operation_index=index,
                        operation_name=gate,
                    )
                )
                continue
            descriptors.append(
                Operation(gate=canonical_gate, targets=[qubits[0]], params=params)
            )

    if reasons:
        report = _base_report(
            status="UNSUPPORTED",
            source_format="qiskit",
            supported=False,
            num_qubits=circuit.num_qubits,
            operation_count=len(circuit.data),
            reasons=tuple(reasons),
        )
        return QiskitImportResult(circuit=None, report=report)

    # Qiskit assigns process-local names such as ``circuit-17`` by default.
    # Names are presentation metadata, not unitary semantics, so excluding them
    # keeps normalized public artifacts and evidence identities deterministic.
    normalized = Circuit(circuit.num_qubits)
    for descriptor in descriptors:
        normalized.add(descriptor)
    report = _base_report(
        status="SUPPORTED",
        source_format="qiskit",
        supported=True,
        num_qubits=circuit.num_qubits,
        operation_count=len(circuit.data),
    )
    return QiskitImportResult(circuit=normalized, report=report)


def _terminal_measurement_split(
    circuit: QuantumCircuit,
) -> tuple[QuantumCircuit | None, list[tuple[Any, list[int], list[int]]], QiskitImportReport | None]:
    """Return a unitary/barrier prefix and an exact terminal measurement suffix."""

    prefix = QuantumCircuit(circuit.num_qubits, name=circuit.name, global_phase=circuit.global_phase)
    prefix.metadata = dict(circuit.metadata or {})
    suffix: list[tuple[Any, list[int], list[int]]] = []
    measurement_started = False
    reasons: list[QiskitUnsupportedReason] = []

    for index, instruction in enumerate(circuit.data):
        operation = instruction.operation
        name = operation.name.lower()
        qubits = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        clbits = [circuit.find_bit(clbit).index for clbit in instruction.clbits]
        if name == "measure":
            measurement_started = True
            if len(qubits) != 1 or len(clbits) != 1:
                reasons.append(
                    _reason(
                        "invalid_measurement_arity",
                        "Terminal measurements require exactly one qubit and one classical bit.",
                        operation_index=index,
                        operation_name=name,
                    )
                )
            suffix.append((operation, qubits, clbits))
            continue
        if measurement_started:
            reasons.append(
                _reason(
                    "mid_circuit_measurement_unsupported",
                    f"Operation {name!r} appears after measurement; only a terminal measurement suffix is supported.",
                    operation_index=index,
                    operation_name=name,
                )
            )
            continue
        if instruction.clbits or getattr(operation, "num_clbits", 0):
            reasons.append(
                _reason(
                    "classical_operation_unsupported",
                    f"Operation {name!r} reads or writes classical data.",
                    operation_index=index,
                    operation_name=name,
                )
            )
            continue
        prefix.append(operation, [prefix.qubits[q] for q in qubits], [])

    if circuit.num_clbits and not suffix:
        reasons.append(
            _reason(
                "unused_classical_data_unsupported",
                "Classical registers are supported only when used by terminal measurements.",
            )
        )
    if reasons:
        report = _base_report(
            status="UNSUPPORTED",
            source_format="qiskit",
            supported=False,
            num_qubits=circuit.num_qubits,
            operation_count=len(circuit.data),
            reasons=tuple(reasons),
        )
        return None, suffix, report
    return prefix, suffix, None


def _rebuild_with_terminal_measurements(
    original: QuantumCircuit,
    lowered_prefix: QuantumCircuit,
    suffix: list[tuple[Any, list[int], list[int]]],
) -> QuantumCircuit:
    output = original.copy_empty_like()
    output.name = original.name
    output.metadata = dict(original.metadata or {})
    for instruction in lowered_prefix.data:
        qubits = [lowered_prefix.find_bit(qubit).index for qubit in instruction.qubits]
        output.append(instruction.operation, [output.qubits[index] for index in qubits], [])
    for operation, qubits, clbits in suffix:
        output.append(
            operation,
            [output.qubits[index] for index in qubits],
            [output.clbits[index] for index in clbits],
        )
    return output


def import_openqasm3(source: str) -> QiskitImportResult:
    """Parse OpenQASM 3 through Qiskit and adapt it to compiler IR."""

    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    parser_stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(parser_stderr):
            circuit = qasm3.loads(source)
    except Exception as exc:  # noqa: BLE001 - parser failures are normalized for callers
        diagnostic = parser_stderr.getvalue().strip()
        message = (
            str(exc).strip()
            or diagnostic
            or f"{type(exc).__name__}: OpenQASM 3 parsing failed."
        )
        line, column = _parse_error_location(message)
        report = _base_report(
            status="ERROR",
            source_format="openqasm3",
            supported=False,
            num_qubits=None,
            operation_count=None,
            source_sha256=source_sha256,
            error=message,
            error_line=line,
            error_column=column,
        )
        return QiskitImportResult(circuit=None, report=report)

    imported = import_qiskit_circuit(circuit)
    return QiskitImportResult(
        circuit=imported.circuit,
        report=replace(
            imported.report,
            source_format="openqasm3",
            source_sha256=source_sha256,
        ),
    )


def _report_from_dict(payload: dict[str, Any]) -> QiskitImportReport:
    return QiskitImportReport(
        status=payload["status"],
        source_format=payload["source_format"],
        supported=bool(payload["supported"]),
        num_qubits=payload.get("num_qubits"),
        operation_count=payload.get("operation_count"),
        source_sha256=payload.get("source_sha256"),
        unsupported_reasons=tuple(
            QiskitUnsupportedReason(**reason)
            for reason in payload.get("unsupported_reasons", [])
        ),
        error=payload.get("error"),
        error_line=payload.get("error_line"),
        error_column=payload.get("error_column"),
        adapter_version=str(payload.get("adapter_version", "")),
        qiskit_version=str(payload.get("qiskit_version", "")),
        limitations=tuple(str(item) for item in payload.get("limitations", [])),
    )


def _isolated_worker_environment() -> dict[str, str]:
    """Preserve runtime-injected package paths for the child interpreter."""

    environment = os.environ.copy()
    import_paths = [entry for entry in sys.path if entry]
    configured_paths = [
        entry
        for entry in environment.get("PYTHONPATH", "").split(os.pathsep)
        if entry
    ]
    environment["PYTHONPATH"] = os.pathsep.join(
        dict.fromkeys([*import_paths, *configured_paths])
    )
    return environment


def import_openqasm3_isolated(source: str) -> QiskitImportResult:
    """Run native Qiskit parsing in an isolated process for server safety."""

    request = json.dumps(
        {"action": "import", "source": source},
        allow_nan=False,
        ensure_ascii=False,
    )
    completed = subprocess.run(
        [sys.executable, "-m", "rqm_qiskit._qasm_worker"],
        input=request,
        capture_output=True,
        check=False,
        env=_isolated_worker_environment(),
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        report = _base_report(
            status="ERROR",
            source_format="openqasm3",
            supported=False,
            num_qubits=None,
            operation_count=None,
            source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            error=(
                "Isolated OpenQASM parser failed closed "
                f"(exit status {completed.returncode})."
            ),
        )
        return QiskitImportResult(circuit=None, report=report)
    try:
        payload = json.loads(completed.stdout)
        report = _report_from_dict(payload["report"])
        circuit_payload = payload.get("circuit")
        if circuit_payload is None:
            return QiskitImportResult(circuit=None, report=report)
        from rqm_compiler import Circuit

        circuit = Circuit.from_descriptors(
            circuit_payload["descriptors"],
            num_qubits=int(circuit_payload["num_qubits"]),
        )
        return QiskitImportResult(circuit=circuit, report=report)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        report = _base_report(
            status="ERROR",
            source_format="openqasm3",
            supported=False,
            num_qubits=None,
            operation_count=None,
            source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            error="Isolated OpenQASM parser returned an invalid response.",
        )
        return QiskitImportResult(circuit=None, report=report)


def assure_qiskit_circuit(
    circuit: QuantumCircuit,
    *,
    target: Any | None = None,
) -> QiskitAssuranceResult:
    """Optimize a Qiskit circuit through the compiler's fail-closed workflow."""

    if not isinstance(circuit, QuantumCircuit):
        imported = import_qiskit_circuit(circuit)
        return QiskitAssuranceResult(
            returned_circuit=QuantumCircuit(1),
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="import_error",
            import_report=imported.report,
            compiler_report=None,
            normalized_input=None,
        )

    prefix, measurement_suffix, split_report = _terminal_measurement_split(circuit)
    if prefix is None:
        assert split_report is not None
        return QiskitAssuranceResult(
            returned_circuit=circuit.copy(),
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="unsupported_input",
            import_report=split_report,
            compiler_report=None,
            normalized_input=None,
        )

    imported = import_qiskit_circuit(prefix, max_qubits=None)
    imported = QiskitImportResult(
        circuit=imported.circuit,
        report=replace(
            imported.report,
            num_qubits=circuit.num_qubits,
            operation_count=len(circuit.data),
        ),
    )
    if imported.circuit is None:
        fallback = (
            "unsupported_input"
            if imported.report.status == "UNSUPPORTED"
            else "import_error"
        )
        return QiskitAssuranceResult(
            returned_circuit=circuit.copy(),
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason=fallback,
            import_report=imported.report,
            compiler_report=None,
            normalized_input=None,
        )

    try:
        from rqm_compiler import optimize_circuit, optimize_circuit_regions

        use_regions = circuit.num_qubits > MAX_ASSURANCE_QUBITS or any(
            operation.gate == "barrier" for operation in imported.circuit.operations
        )
        if use_regions:
            returned, report = optimize_circuit_regions(imported.circuit)
            proof_verified = (
                getattr(report, "equivalence_status", None) == "VERIFIED"
                and getattr(report, "fallback_reason", None) is None
            )
            optimization_applied = bool(getattr(report, "committed", False))
        else:
            returned, report = optimize_circuit(imported.circuit)
            proof_verified = (
                getattr(report, "equivalence_status", None) == "VERIFIED"
                and getattr(report, "equivalence_guaranteed", False) is True
                and getattr(report, "fallback_reason", None) is None
            )
            optimization_applied = bool(getattr(report, "optimization_applied", False))
        if not proof_verified:
            return QiskitAssuranceResult(
                returned_circuit=circuit.copy(),
                assurance_status="FALLBACK_ORIGINAL",
                optimization_applied=False,
                fallback_reason=getattr(report, "fallback_reason", None)
                or "verification_not_established",
                import_report=imported.report,
                compiler_report=report,
                normalized_input=imported.circuit,
            )
        lowered = compiled_circuit_to_qiskit(returned, target=target)
        lowered = _rebuild_with_terminal_measurements(circuit, lowered, measurement_suffix)
        return QiskitAssuranceResult(
            returned_circuit=lowered,
            assurance_status="VERIFIED",
            optimization_applied=optimization_applied,
            fallback_reason=None,
            import_report=imported.report,
            compiler_report=report,
            normalized_input=imported.circuit,
        )
    except Exception:  # noqa: BLE001 - public assurance must fail closed
        return QiskitAssuranceResult(
            returned_circuit=circuit.copy(),
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="internal_assurance_error",
            import_report=imported.report,
            compiler_report=None,
            normalized_input=imported.circuit,
        )


def assure_openqasm3(source: str) -> OpenQASMAssuranceResult:
    """Assure an OpenQASM 3 document and return the exact source on fallback."""

    if not isinstance(source, str):
        source = str(source)
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    parser_stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(parser_stderr):
            circuit = qasm3.loads(source)
    except Exception as exc:  # noqa: BLE001 - normalized at the public boundary
        diagnostic = parser_stderr.getvalue().strip()
        message = str(exc).strip() or diagnostic or "OpenQASM 3 parsing failed."
        return OpenQASMAssuranceResult(
            returned_source=source,
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="import_error",
            source_sha256=source_sha256,
            returned_source_sha256=source_sha256,
            assurance_report=None,
            error=message,
        )

    assurance = assure_qiskit_circuit(circuit)
    if assurance.assurance_status != "VERIFIED":
        return OpenQASMAssuranceResult(
            returned_source=source,
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason=assurance.fallback_reason,
            source_sha256=source_sha256,
            returned_source_sha256=source_sha256,
            assurance_report=assurance.to_dict(),
        )
    try:
        returned_source = qasm3.dumps(assurance.returned_circuit)
    except Exception as exc:  # noqa: BLE001 - export failure must preserve source
        return OpenQASMAssuranceResult(
            returned_source=source,
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="export_error",
            source_sha256=source_sha256,
            returned_source_sha256=source_sha256,
            assurance_report=assurance.to_dict(),
            error=str(exc),
        )
    return OpenQASMAssuranceResult(
        returned_source=returned_source,
        assurance_status="VERIFIED",
        optimization_applied=assurance.optimization_applied,
        fallback_reason=None,
        source_sha256=source_sha256,
        returned_source_sha256=hashlib.sha256(returned_source.encode("utf-8")).hexdigest(),
        assurance_report=assurance.to_dict(),
    )


def _openqasm_assurance_from_dict(payload: dict[str, Any]) -> OpenQASMAssuranceResult:
    return OpenQASMAssuranceResult(
        returned_source=str(payload["returned_source"]),
        assurance_status=payload["assurance_status"],
        optimization_applied=bool(payload["optimization_applied"]),
        fallback_reason=payload.get("fallback_reason"),
        source_sha256=str(payload["source_sha256"]),
        returned_source_sha256=str(payload["returned_source_sha256"]),
        assurance_report=payload.get("assurance_report"),
        error=payload.get("error"),
    )


def assure_openqasm3_isolated(source: str) -> OpenQASMAssuranceResult:
    """Run complete OpenQASM assurance in an isolated child interpreter."""

    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    completed = subprocess.run(
        [sys.executable, "-m", "rqm_qiskit._qasm_worker"],
        input=json.dumps({"action": "assure", "source": source}, ensure_ascii=False),
        capture_output=True,
        check=False,
        env=_isolated_worker_environment(),
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        return OpenQASMAssuranceResult(
            returned_source=source,
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="isolated_worker_error",
            source_sha256=source_sha256,
            returned_source_sha256=source_sha256,
            assurance_report=None,
            error=f"Isolated OpenQASM assurance failed closed (exit status {completed.returncode}).",
        )
    try:
        return _openqasm_assurance_from_dict(json.loads(completed.stdout))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return OpenQASMAssuranceResult(
            returned_source=source,
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="isolated_worker_error",
            source_sha256=source_sha256,
            returned_source_sha256=source_sha256,
            assurance_report=None,
            error="Isolated OpenQASM assurance returned an invalid response.",
        )


async def async_assure_openqasm3(source: str) -> OpenQASMAssuranceResult:
    """Await process-isolated OpenQASM assurance without blocking the event loop."""

    return await asyncio.to_thread(assure_openqasm3_isolated, source)


def export_openqasm3(source: Any) -> QiskitExportResult:
    """Lower compiler IR through the canonical bridge and emit OpenQASM 3."""

    try:
        circuit = compiled_circuit_to_qiskit(source)
        # Canonical lowering has already resolved every compiler operation to
        # a Qiskit instruction or failed closed. Re-transpiling here repeats
        # instruction analysis without adding a semantic or portability gate.
        exported = qasm3.dumps(circuit)
    except Exception as exc:  # noqa: BLE001 - public export must return structured failure
        return QiskitExportResult(
            status="ERROR",
            source=None,
            source_sha256=None,
            error=str(exc),
            adapter_version=_adapter_version(),
            qiskit_version=_package_version("qiskit", "unknown"),
            limitations=_limitations(),
        )
    return QiskitExportResult(
        status="EXPORTED",
        source=exported,
        source_sha256=hashlib.sha256(exported.encode("utf-8")).hexdigest(),
        error=None,
        adapter_version=_adapter_version(),
        qiskit_version=_package_version("qiskit", "unknown"),
        limitations=_limitations(),
    )


def export_openqasm3_isolated(source: Any) -> QiskitExportResult:
    """Run native Qiskit export in an isolated process for server safety."""

    descriptors = (
        list(source.descriptors)
        if hasattr(source, "descriptors")
        else source.to_descriptors()
    )
    request = json.dumps(
        {
            "action": "export",
            "circuit": {
                "num_qubits": int(source.num_qubits),
                "descriptors": descriptors,
            },
        },
        allow_nan=False,
        ensure_ascii=False,
    )
    completed = subprocess.run(
        [sys.executable, "-m", "rqm_qiskit._qasm_worker"],
        input=request,
        capture_output=True,
        check=False,
        env=_isolated_worker_environment(),
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        return QiskitExportResult(
            status="ERROR",
            source=None,
            source_sha256=None,
            error=(
                "Isolated OpenQASM exporter failed closed "
                f"(exit status {completed.returncode})."
            ),
            adapter_version=_adapter_version(),
            qiskit_version=_package_version("qiskit", "unknown"),
            limitations=_limitations(),
        )
    try:
        payload = json.loads(completed.stdout)
        return QiskitExportResult(
            status=payload["status"],
            source=payload.get("source"),
            source_sha256=payload.get("source_sha256"),
            error=payload.get("error"),
            adapter_version=payload["adapter_version"],
            qiskit_version=payload["qiskit_version"],
            limitations=tuple(payload.get("limitations", [])),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return QiskitExportResult(
            status="ERROR",
            source=None,
            source_sha256=None,
            error="Isolated OpenQASM exporter returned an invalid response.",
            adapter_version=_adapter_version(),
            qiskit_version=_package_version("qiskit", "unknown"),
            limitations=_limitations(),
        )
