"""
rqm_qiskit – Qiskit translation and execution layer for the RQM compiler ecosystem.

Architecture
------------
rqm-core        (canonical math: Quaternion, SU(2), Bloch, spinor, named gates)
       ↓
rqm-compiler    (canonical gate/circuit IR: Circuit, Operation, compilation)
       ↓
rqm-qiskit      (Qiskit translation + execution)
       ↓
 Qiskit QuantumCircuit / transpilation / execution

rqm-qiskit does not implement canonical math or compiler logic.  It delegates
all math operations to rqm-core and all compilation to rqm-compiler.

Public API — three tiers
------------------------

Tier 1 — Execution  (start here)
  Functional (primary):
    run_qiskit(circuit, *, shots, optimize, include_report)
        → dict  (JSON-compatible: counts, shots, backend, metadata)

  OO (equivalent):
    QiskitBackend().run(circuit, *, shots, optimize, include_report)
        → QiskitResult

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
  Quaternion                      : re-export from rqm-core

Legacy / transitional (may be removed in a future release):
  RQMState, RQMGate, RQMCircuit
  compiled_circuit_to_qiskit, state_to_quantum_circuit, gate_to_quantum_circuit
  summarize_counts, format_counts_summary
  spinor_embed, gate_h, gate_s, gate_t, gate_rx, gate_ry, gate_rz, match_gate
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
from rqm_qiskit.execution import run_local, run_backend, run_qiskit
from rqm_qiskit.backend import QiskitBackend
from rqm_qiskit.result import QiskitResult
from rqm_qiskit.bridges import spinor_to_circuit, bloch_to_circuit

__all__ = [
    # Tier 1 — Execution
    "run_qiskit",        # functional primary
    "QiskitBackend",     # OO equivalent
    # Tier 2 — Translation
    "to_qiskit_circuit", # functional primary
    "QiskitTranslator",  # OO equivalent
    # Tier 3 — Advanced / internal
    "QiskitResult",
    "compiled_circuit_to_qiskit",
    "compile_to_qiskit_circuit",
    "to_backend_circuit",
    "run_local",
    "run_backend",
    "Quaternion",
    "spinor_to_circuit",
    "bloch_to_circuit",
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

__version__ = "0.1.0"
try:
    from importlib.metadata import version, PackageNotFoundError
    __version__ = version("rqm-qiskit")
except PackageNotFoundError:
    pass
