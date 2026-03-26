"""
rqm_qiskit – IBM Quantum / Qiskit execution bridge for the RQM ecosystem.

Architecture
------------
rqm-core        (math foundation: Quaternion, SU(2), Bloch, spinor, named gates)
       ↓
rqm-circuits    (canonical external/public circuit IR — ecosystem wire format)
       ↓
rqm-compiler    (internal optimization / rewriting engine)
       ↓
rqm-qiskit      (Qiskit / IBM lowering and execution bridge)   ← this package
       ↓
 Qiskit QuantumCircuit / transpilation / execution

rqm-qiskit is downstream of both rqm-circuits and rqm-compiler.  It does not
implement canonical math, define the public circuit schema, or own compiler
logic.  All math is delegated to rqm-core; all compilation to rqm-compiler.

Typical flow: external callers (Studio, API) produce rqm-circuits payloads →
parsed/validated upstream → optimized by rqm-compiler → rqm-qiskit lowers to
Qiskit and executes.  Helper functions in this package accept compiler Circuit
objects directly for in-process / server-side usage.

Public API — three tiers
------------------------

Tier 1 — Execution  (start here)
  Functional (primary):
    run_qiskit(circuit, *, shots, backend, optimize, include_report)
        → dict  (JSON-compatible: counts, shots, backend, metadata)

    async_run_qiskit(circuit, *, shots, backend, optimize, include_report, ...)
        → QiskitJob  (handle with .job_id(), .status(), .result())

    execute_rqm_program(program_descriptor, *, backend, shots, optimize)
        → dict  (accepts canonical RQM descriptor dicts from rqm-api)

  OO (equivalent):
    QiskitBackend().run(circuit, *, shots, optimize, include_report)
        → QiskitResult

    QiskitBackend().async_run(circuit, *, shots, backend, optimize, ...)
        → QiskitJob

Tier 2 — Translation
  Functional:
    to_qiskit_circuit(circuit, *, optimize, include_report)
        → QuantumCircuit  (or (QuantumCircuit, report) when include_report=True)

  OO:
    QiskitTranslator().to_quantum_circuit(circuit, *, optimize, include_report)
        → QuantumCircuit  (or tuple)
    QiskitTranslator().apply_gate(qc, descriptor)
        → None  (mutates qc in-place)

Tier 3 — Advanced / internal
  QiskitBackend().compile(...)    : translate-only OO alias
  QiskitBackend().run_local(...)  : run on local Aer, returns QiskitResult
  compiled_circuit_to_qiskit(...) : core lowering path (all tiers route here)
  run_local(...)                  : raw Aer execution, returns dict[str, int]
  run_backend(...)                : raw real-backend execution
  spinor_to_circuit(...)          : spinor → QuantumCircuit (delegates to rqm-core)
  bloch_to_circuit(...)           : Bloch angles → QuantumCircuit
  QiskitResult                    : structured result wrapper
  QiskitJob                       : async job handle
  get_ibmq_provider(...)          : obtain authenticated IBM Quantum provider
  Quaternion                      : re-export from rqm-core

  Errors (subclass RuntimeError):
    RQMQiskitError, BackendNotFoundError, CredentialsError,
    JobFailedError, TranslationError

Legacy / transitional (may be removed in a future release):
  RQMState, RQMGate, RQMCircuit
  compiled_circuit_to_qiskit, state_to_quantum_circuit, gate_to_quantum_circuit
  summarize_counts, format_counts_summary
  spinor_embed, gate_h, gate_s, gate_t, gate_rx, gate_ry, gate_rz, match_gate

IBM Quantum credentials
-----------------------
Set the following environment variables to use IBM Quantum backends:

    QISKIT_IBM_TOKEN      IBM Quantum API token (required)
    QISKIT_IBM_INSTANCE   Service instance (optional)
    QISKIT_IBM_CHANNEL    Channel (optional, default "ibm_quantum")

See :func:`get_ibmq_provider` for details.
"""

from rqm_qiskit.quaternion import Quaternion
from rqm_qiskit.state import RQMState, spinor_embed
from rqm_qiskit.gates import RQMGate, gate_h, gate_s, gate_t, gate_rx, gate_ry, gate_rz, match_gate
from rqm_qiskit.circuit import RQMCircuit
from rqm_qiskit.convert import (
    compiled_circuit_to_qiskit,
    state_to_quantum_circuit,
    gate_to_quantum_circuit,
)
from rqm_qiskit.results import summarize_counts, format_counts_summary

# New architecture components
from rqm_qiskit.translator import QiskitTranslator, compile_to_qiskit_circuit, to_backend_circuit, to_qiskit_circuit
from rqm_qiskit.execution import run_local, run_backend, run_qiskit, async_run_qiskit, execute_rqm_program
from rqm_qiskit.backend import QiskitBackend
from rqm_qiskit.result import QiskitResult
from rqm_qiskit.job import QiskitJob
from rqm_qiskit.bridges import spinor_to_circuit, bloch_to_circuit
from rqm_qiskit.ibm import get_ibmq_provider
from rqm_qiskit.errors import (
    RQMQiskitError,
    BackendNotFoundError,
    CredentialsError,
    JobFailedError,
    TranslationError,
)

__all__ = [
    # Tier 1 — Execution
    "run_qiskit",            # functional primary
    "async_run_qiskit",      # functional async
    "execute_rqm_program",   # high-level rqm-api integration
    "QiskitBackend",         # OO equivalent
    # Tier 2 — Translation
    "to_qiskit_circuit",     # functional primary
    "QiskitTranslator",      # OO equivalent
    # Tier 3 — Advanced / internal
    "QiskitResult",
    "QiskitJob",
    "get_ibmq_provider",
    "compiled_circuit_to_qiskit",
    "compile_to_qiskit_circuit",
    "to_backend_circuit",
    "run_local",
    "run_backend",
    "Quaternion",
    "spinor_to_circuit",
    "bloch_to_circuit",
    # Errors
    "RQMQiskitError",
    "BackendNotFoundError",
    "CredentialsError",
    "JobFailedError",
    "TranslationError",
    # Legacy / transitional
    "RQMState",
    "RQMGate",
    "RQMCircuit",
    "state_to_quantum_circuit",
    "gate_to_quantum_circuit",
    "summarize_counts",
    "format_counts_summary",
    "spinor_embed",
    "gate_h",
    "gate_s",
    "gate_t",
    "gate_rx",
    "gate_ry",
    "gate_rz",
    "match_gate",
]

__version__ = "0.2.0"
try:
    from importlib.metadata import version, PackageNotFoundError
    __version__ = version("rqm-qiskit")
except PackageNotFoundError:
    pass
