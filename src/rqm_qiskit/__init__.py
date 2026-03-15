"""
rqm_qiskit – SU(2)-native geometric bridge layer for Qiskit.

Public API
----------
- RQMState      : normalized 1-qubit state with Bloch-sphere helpers
- RQMGate       : SU(2) rotation gate (x, y, z axes)
- RQMCircuit    : thin wrapper around Qiskit QuantumCircuit
- state_to_quantum_circuit  : convert RQMState to QuantumCircuit
- gate_to_quantum_circuit   : convert RQMGate to QuantumCircuit
- summarize_counts          : summarize measurement counts dict
- format_counts_summary     : human-readable summary string
"""

from rqm_qiskit.state import RQMState
from rqm_qiskit.gates import RQMGate
from rqm_qiskit.circuit import RQMCircuit
from rqm_qiskit.convert import state_to_quantum_circuit, gate_to_quantum_circuit
from rqm_qiskit.results import summarize_counts, format_counts_summary

__all__ = [
    "RQMState",
    "RQMGate",
    "RQMCircuit",
    "state_to_quantum_circuit",
    "gate_to_quantum_circuit",
    "summarize_counts",
    "format_counts_summary",
]

__version__ = "0.1.0"
