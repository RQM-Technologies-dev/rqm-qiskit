"""Bounded, artifact-bound OpenQASM handoff; compiler owns equivalence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from inspect import signature
from typing import Any

from qiskit import qasm3

from rqm_qiskit.assurance import (
    _isolated_worker_environment,
    _rebuild_with_terminal_measurements,
    _terminal_measurement_split,
    export_openqasm3,
    import_qiskit_circuit,
)

MAX_QUBITS = 4
MAX_OPERATIONS = 512
MAX_SOURCE_BYTES = 65_536
PHASE_SEMANTICS = ("exact", "phase_invariant")


def _digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _prefix(circuit):
    if not 1 <= circuit.num_qubits <= MAX_QUBITS:
        raise ValueError("Handoff supports one to four qubits.")
    if circuit.num_clbits > 64 or len(circuit.data) > MAX_OPERATIONS:
        raise ValueError(
            "Handoff supports at most 64 classical bits and 512 operations."
        )
    prefix, suffix, error = _terminal_measurement_split(circuit)
    if error is not None:
        raise ValueError(str(error.to_dict()))
    # QASM may redefine a familiar name (for example `gate h { U(...) }`).
    # The compiler importer consumes names, so establish that each actual
    # SDK operation has the named gate's semantics before handing it off.
    # Qiskit's QASM exporter also emits legitimate custom rzz definitions;
    # class/name checks alone cannot distinguish those from altered gates.
    import numpy as np
    from qiskit.circuit import Barrier
    from qiskit.circuit.library import get_standard_gate_name_mapping
    from qiskit.quantum_info import Operator

    standard = get_standard_gate_name_mapping()
    for item in prefix.data:
        operation = item.operation
        if isinstance(operation, Barrier):
            continue
        if operation.name not in standard or operation.num_qubits > 2:
            raise ValueError("Unsupported gate definition.")
        expected = standard[operation.name].to_mutable()
        expected.params = list(operation.params)
        if expected.num_qubits != operation.num_qubits or not np.allclose(
            Operator(operation).data, Operator(expected).data, atol=1e-12, rtol=0.0
        ):
            raise ValueError(
                f"Gate definition differs from standard {operation.name} semantics."
            )
    imported = import_qiskit_circuit(prefix, max_qubits=MAX_QUBITS)
    if imported.circuit is None:
        raise ValueError(str(imported.report.to_dict()))
    # Names and register ordering define how the customer interprets readout.
    readout = {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "quantum_registers": [(r.name, len(r)) for r in circuit.qregs],
        "classical_registers": [(r.name, len(r)) for r in circuit.cregs],
        "measurements": [(q, c) for _, q, c in suffix],
    }
    return imported.circuit, suffix, readout


def verify_openqasm3_artifact(
    source: str, artifact: str, *, phase_semantics: str = "exact"
) -> dict[str, Any]:
    """Verify the actual serialized artifact, including terminal readout wiring.

    Exact means phase-preserving bounded numerical evidence, not symbolic proof.
    Declared nonzero global phase and nonstandard gates remain unsupported.
    """
    result: dict[str, Any] = {
        "status": "UNSUPPORTED",
        "equivalent": None,
        "phase_invariant": phase_semantics == "phase_invariant",
        "source_sha256": _digest(source),
        "artifact_sha256": _digest(artifact),
        "phase_semantics": phase_semantics,
    }
    try:
        if phase_semantics not in PHASE_SEMANTICS:
            raise ValueError("phase_semantics must be exact or phase_invariant.")
        if max(len(source.encode()), len(artifact.encode())) > MAX_SOURCE_BYTES:
            raise ValueError("OpenQASM source exceeds 65536 bytes.")
        from rqm_compiler import verify_equivalence

        if "phase_invariant" not in signature(verify_equivalence).parameters:
            raise ValueError("Compiler runtime lacks explicit phase semantics.")
        original_sdk, returned_sdk = qasm3.loads(source), qasm3.loads(artifact)
        left, _, before = _prefix(original_sdk)
        right, _, after = _prefix(returned_sdk)
        result["readout"] = after
        result["measurement_map_preserved"] = before == after
        if before != after:
            result.update(
                status="COUNTEREXAMPLE",
                equivalent=False,
                reason="Register or measurement mapping changed.",
            )
            return result
        proof = verify_equivalence(
            left,
            right,
            max_dense_qubits=MAX_QUBITS,
            phase_invariant=phase_semantics == "phase_invariant",
            atol=1e-10,
            rtol=0.0,
        )
        result.update(asdict(proof))
        result["status"] = proof.status.value
        result["equivalent"] = proof.verified
        # Independently close the adapter boundary on the complete SDK objects.
        # This checks actual QASM definitions, rather than accumulating a
        # tolerance across individually named operations. Never promote a
        # nonverified compiler verdict based on this additional check.
        if proof.status.value == "VERIFIED" and proof.verified is True:
            import numpy as np
            from qiskit.quantum_info import Operator

            actual_before = Operator(
                original_sdk.remove_final_measurements(inplace=False)
            )
            actual_after = Operator(
                returned_sdk.remove_final_measurements(inplace=False)
            )
            preserved = (
                actual_before.equiv(actual_after, atol=1e-10, rtol=0.0)
                if phase_semantics == "phase_invariant"
                else np.allclose(
                    actual_before.data, actual_after.data, atol=1e-10, rtol=0.0
                )
            )
            result["artifact_semantics_checked"] = True
            if not preserved:
                result.update(
                    status="COUNTEREXAMPLE",
                    equivalent=False,
                    reason="Actual serialized operators differ.",
                )
        result["controlled_reuse_eligible"] = (
            result["status"] == "VERIFIED"
            and result["equivalent"] is True
            and not proof.phase_invariant
            and not before["measurements"]
        )
    except Exception as exc:
        result.update(
            status="UNSUPPORTED",
            equivalent=None,
            controlled_reuse_eligible=False,
            reason=str(exc),
        )
    return result


def assure_openqasm3_handoff(
    source: str, *, phase_semantics: str = "exact"
) -> dict[str, Any]:
    """Compile, serialize, reload and verify; withhold any unverified candidate."""
    result: dict[str, Any] = {
        "returned_openqasm3": source,
        "source_sha256": _digest(source),
        "returned_source_sha256": _digest(source),
        "assurance_status": "FALLBACK_ORIGINAL",
        "optimization_applied": False,
        "phase_semantics": phase_semantics,
        "limitations": [
            "Bounded numerical evidence, not formal verification or hardware qualification.",
            "Assurance starts at supplied QASM bytes; phase lost before submission is not recoverable.",
            "Only bound standard gates, zero declared global phase and terminal measurements.",
            "Measured circuits and phase-invariant proofs do not justify controlled reuse.",
        ],
    }
    try:
        # Validate before compilation; also proves support for the phase contract.
        admission = verify_openqasm3_artifact(
            source, source, phase_semantics=phase_semantics
        )
        result["verification"] = admission
        if admission["status"] != "VERIFIED":
            result["fallback_reason"] = "unsupported_input_or_runtime"
            return result
        from rqm_compiler import optimize_circuit_regions

        original = qasm3.loads(source)
        imported, suffix, _ = _prefix(original)
        candidate, report = optimize_circuit_regions(imported)
        exported = export_openqasm3(candidate)
        if exported.status != "EXPORTED" or exported.source is None:
            raise ValueError(exported.error or "Compiler artifact cannot be exported.")
        lowered = qasm3.loads(exported.source)
        rebuilt = _rebuild_with_terminal_measurements(original, lowered, suffix)
        artifact = qasm3.dumps(rebuilt)
        proof = verify_openqasm3_artifact(
            source, artifact, phase_semantics=phase_semantics
        )
        result["verification"] = proof
        result["compiler_report"] = report.to_dict()
        if proof["status"] != "VERIFIED" or proof["equivalent"] is not True:
            result["fallback_reason"] = "emitted_artifact_not_verified"
            return result
        result.update(
            returned_openqasm3=artifact,
            returned_source_sha256=_digest(artifact),
            assurance_status="VERIFIED",
            fallback_reason=None,
            optimization_applied=candidate.to_descriptors()
            != imported.to_descriptors(),
        )
    except Exception as exc:
        result.update(fallback_reason="handoff_error", error=str(exc))
    return result


def assure_openqasm3_handoff_isolated(
    source: str, *, phase_semantics: str = "exact"
) -> dict[str, Any]:
    """Isolate native parsing; bound runtime and preserve the source on failure."""
    if (
        len(source.encode()) > MAX_SOURCE_BYTES
        or phase_semantics not in PHASE_SEMANTICS
    ):
        raise ValueError("Invalid handoff source size or phase semantics.")
    completed = subprocess.run(
        [sys.executable, "-m", "rqm_qiskit._qasm_worker"],
        input=json.dumps(
            {"action": "handoff", "source": source, "phase_semantics": phase_semantics}
        ),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
        env=_isolated_worker_environment(),
    )
    return json.loads(completed.stdout)
