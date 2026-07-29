"""Fail-closed Qiskit and OpenQASM 3 assurance bridges.

This module owns format adaptation only.  Circuit optimization and semantic
verification remain delegated to :mod:`rqm_compiler`, while lowering back to
Qiskit always routes through :func:`compiled_circuit_to_qiskit`.

The v0.1 boundary intentionally accepts only bound, standalone unitary
circuits on one to three qubits.  Equivalence is established up to global
phase; callers must not treat a returned circuit as safe to promote directly
to a coherently controlled subcircuit.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal

from qiskit import QuantumCircuit, qasm3, transpile

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
)
MAX_ASSURANCE_QUBITS = 3

_NO_PARAM_GATES = frozenset({"id", "x", "y", "z", "h", "s", "t"})
_ANGLE_GATES = frozenset({"rx", "ry", "rz", "p", "rxx", "ryy", "rzz"})
_CONTROLLED_GATES = frozenset({"cx", "cy", "cz"})
_TWO_TARGET_GATES = frozenset({"swap", "iswap", "rxx", "ryy", "rzz"})
_PARSE_LOCATION_PATTERNS = (
    re.compile(r"(?:line\s+)?(?P<line>\d+)\s*[,;:]\s*(?:column\s+)?(?P<column>\d+)", re.IGNORECASE),
    re.compile(r"line\s+(?P<line>\d+).*column\s+(?P<column>\d+)", re.IGNORECASE),
)


def _package_version(name: str, fallback: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return fallback


def _adapter_version() -> str:
    return _package_version("rqm-qiskit", "0.3.0+local")


@dataclass(frozen=True)
class QiskitUnsupportedReason:
    """One stable, actionable reason why a circuit is outside the v0.1 boundary."""

    code: str
    message: str
    operation_index: int | None = None
    operation_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        return asdict(self)


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
        return asdict(self)


def _limitations() -> tuple[str, ...]:
    return (
        "Supports only bound standalone unitary circuits on one to three qubits.",
        "Semantic equivalence is bounded numerical or canonical verification up to global phase.",
        "The result is not formal verification and contains no simulator, emulator, or QPU evidence.",
        "Do not promote the returned circuit directly to a coherently controlled subcircuit.",
    )


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


def import_qiskit_circuit(circuit: QuantumCircuit) -> QiskitImportResult:
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
    if circuit.num_qubits < 1 or circuit.num_qubits > MAX_ASSURANCE_QUBITS:
        reasons.append(
            _reason(
                "qubit_count_out_of_range",
                f"Expected 1-{MAX_ASSURANCE_QUBITS} qubits; received {circuit.num_qubits}.",
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
                "OpenQASM assurance v0.1 accepts only circuits with zero declared global phase.",
            )
        )

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
                    f"Operation {gate!r} is not supported by the v0.1 assurance bridge.",
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
            descriptors.append(Operation(gate=canonical_gate, targets=qubits, params=params))
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


def assure_qiskit_circuit(circuit: QuantumCircuit) -> QiskitAssuranceResult:
    """Optimize a Qiskit circuit through the compiler's fail-closed workflow."""

    original = circuit.copy()
    imported = import_qiskit_circuit(circuit)
    if imported.circuit is None:
        fallback = (
            "unsupported_input"
            if imported.report.status == "UNSUPPORTED"
            else "import_error"
        )
        return QiskitAssuranceResult(
            returned_circuit=original,
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason=fallback,
            import_report=imported.report,
            compiler_report=None,
            normalized_input=None,
        )

    try:
        from rqm_compiler import optimize_circuit

        returned, report = optimize_circuit(imported.circuit)
        proof_verified = (
            getattr(report, "equivalence_status", None) == "VERIFIED"
            and getattr(report, "equivalence_guaranteed", False) is True
            and getattr(report, "fallback_reason", None) is None
        )
        if not proof_verified:
            return QiskitAssuranceResult(
                returned_circuit=original,
                assurance_status="FALLBACK_ORIGINAL",
                optimization_applied=False,
                fallback_reason=getattr(report, "fallback_reason", None)
                or "verification_not_established",
                import_report=imported.report,
                compiler_report=report,
                normalized_input=imported.circuit,
            )
        lowered = compiled_circuit_to_qiskit(returned)
        lowered.name = circuit.name
        lowered.metadata = dict(circuit.metadata or {})
        return QiskitAssuranceResult(
            returned_circuit=lowered,
            assurance_status="VERIFIED",
            optimization_applied=bool(getattr(report, "optimization_applied", False)),
            fallback_reason=None,
            import_report=imported.report,
            compiler_report=report,
            normalized_input=imported.circuit,
        )
    except Exception:  # noqa: BLE001 - public assurance must fail closed
        return QiskitAssuranceResult(
            returned_circuit=original,
            assurance_status="FALLBACK_ORIGINAL",
            optimization_applied=False,
            fallback_reason="internal_assurance_error",
            import_report=imported.report,
            compiler_report=None,
            normalized_input=imported.circuit,
        )


def export_openqasm3(source: Any) -> QiskitExportResult:
    """Lower compiler IR through the canonical bridge and emit OpenQASM 3."""

    try:
        circuit = compiled_circuit_to_qiskit(source)
        portable = transpile(
            circuit,
            basis_gates=list(SUPPORTED_QISKIT_GATES),
            optimization_level=0,
        )
        exported = qasm3.dumps(portable)
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
