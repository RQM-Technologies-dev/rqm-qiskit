"""
rqm_qiskit – Thin Qiskit bridge layer for the RQM ecosystem.

Architecture
------------
rqm-core        (canonical math: Quaternion, SU(2), Bloch, spinor, named gates)
       ↓
rqm-compiler    (canonical gate/circuit IR: Circuit, Operation, compilation)
       ↓
rqm-qiskit      (Qiskit bridge: circuit lowering, IBM execution helpers)
       ↓
rqm-notebooks   (interactive notebooks and tutorials)

rqm-qiskit does not implement canonical math.  It delegates all math
operations to rqm-core.

Public API
----------
Compiler-first (primary):
- QiskitBackend           : unified entry point (compile + run)
- QiskitTranslator        : compiler IR → QuantumCircuit
- compile_to_qiskit_circuit : convenience function
- run_local               : run on Aer simulator
- run_backend             : run on real backend
- QiskitResult            : structured result wrapper

Math delegation (re-exports from rqm-core):
- Quaternion              : unit quaternion shim with bridge-layer extras

Convenience bridges (delegate to rqm-core):
- spinor_to_circuit       : (α, β) → QuantumCircuit via rqm-core Bloch math
- bloch_to_circuit        : (θ, φ) → QuantumCircuit via RY(θ) RZ(φ)

Legacy / transitional (may be removed in a future release):
- RQMState       : normalized 1-qubit state
- RQMGate        : dual-mode gate (rotation or named gate)
- RQMCircuit     : thin façade over rqm_compiler.Circuit
- compiled_circuit_to_qiskit : primary bridge function
- state_to_quantum_circuit   : convenience Qiskit state prep
- gate_to_quantum_circuit    : convenience Qiskit gate circuit
- summarize_counts, format_counts_summary : result helpers
- spinor_embed             : spinor-to-quaternion embedding
- gate_h, gate_s, gate_t   : named gate quaternions
- gate_rx, gate_ry, gate_rz : parametric rotation quaternion factories
- match_gate               : identify a named gate from a quaternion
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
from rqm_qiskit.translator import QiskitTranslator, compile_to_qiskit_circuit
from rqm_qiskit.execution import run_local, run_backend
from rqm_qiskit.backend import QiskitBackend
from rqm_qiskit.result import QiskitResult
from rqm_qiskit.bridges import spinor_to_circuit, bloch_to_circuit

__all__ = [
    # Compiler-first (primary)
    "QiskitBackend",
    "QiskitTranslator",
    "compile_to_qiskit_circuit",
    "run_local",
    "run_backend",
    "QiskitResult",
    # Math delegation
    "Quaternion",
    # Convenience bridges
    "spinor_to_circuit",
    "bloch_to_circuit",
    # Legacy / transitional
    "RQMState",
    "RQMGate",
    "RQMCircuit",
    "compiled_circuit_to_qiskit",
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
