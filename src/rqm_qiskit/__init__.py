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

Public API
----------
- Quaternion     : unit quaternion shim (re-exports rqm-core; inherits
                   from_axis_angle_vec, to_axis_angle, canonicalize,
                   rotate_vector from rqm-core)
- RQMState       : normalized 1-qubit state; delegates math to rqm-core
- RQMGate        : SU(2) rotation gate with to_operation() → rqm_compiler.Operation
- RQMCircuit     : thin façade over rqm_compiler.Circuit with to_qiskit()
- compiled_circuit_to_qiskit : primary bridge: rqm-compiler IR → QuantumCircuit
- state_to_quantum_circuit   : convenience: RQMState → QuantumCircuit
- gate_to_quantum_circuit    : convenience: RQMGate → QuantumCircuit
- summarize_counts           : summarize measurement counts dict
- format_counts_summary      : human-readable summary string
- spinor_embed               : spinor-to-quaternion embedding (re-exported from rqm-core)
- gate_h, gate_s, gate_t     : named gate quaternions (re-exported from rqm-core)
- gate_rx, gate_ry, gate_rz  : parametric rotation quaternion factories (rqm-core)
- match_gate                 : identify a named gate from a quaternion (rqm-core)
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

__all__ = [
    "Quaternion",
    "RQMState",
    "RQMGate",
    "RQMCircuit",
    "compiled_circuit_to_qiskit",
    "state_to_quantum_circuit",
    "gate_to_quantum_circuit",
    "summarize_counts",
    "format_counts_summary",
    # rqm-core re-exports: spinor
    "spinor_embed",
    # rqm-core re-exports: named gate quaternions
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
