"""
execution.py – Thin execution helpers for local and remote quantum backends.

These functions accept a flexible program representation (QuantumCircuit,
rqm-compiler Circuit, or RQMGate sequence), translate it to a QuantumCircuit
via the translator layer, add measurements if needed, and run it.

Functions
---------
- ``run_local``   : run on the local Aer simulator (offline-safe)
- ``run_backend`` : run on a real Qiskit backend (optional)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from qiskit import QuantumCircuit

if TYPE_CHECKING:
    pass


def _ensure_measurements(qc: QuantumCircuit) -> QuantumCircuit:
    """Return a copy of ``qc`` with measurements on all qubits if none exist."""
    if qc.num_clbits > 0:
        return qc  # already has classical bits / measurements
    measured = qc.copy()
    measured.measure_all()
    return measured


def _to_circuit(circuit_or_program) -> QuantumCircuit:
    """Convert any supported program representation to a QuantumCircuit."""
    from rqm_qiskit.translator import QiskitTranslator

    return QiskitTranslator().compile_to_circuit(circuit_or_program)


def run_local(
    circuit_or_program,
    shots: int = 100,
) -> "dict[str, int]":
    """Run a circuit or program on the local Aer simulator.

    Parameters
    ----------
    circuit_or_program:
        One of:

        * :class:`~qiskit.QuantumCircuit`
        * :class:`rqm_compiler.Circuit` / :class:`rqm_compiler.CompiledCircuit`
        * ``list`` of :class:`~rqm_qiskit.gates.RQMGate` objects

    shots:
        Number of measurement shots (default 100).

    Returns
    -------
    dict[str, int]
        Bitstring → count mapping.

    Raises
    ------
    ImportError
        If ``qiskit-aer`` is not installed.
    """
    qc = _to_circuit(circuit_or_program)
    qc = _ensure_measurements(qc)
    from rqm_qiskit.ibm import run_on_aer_sampler

    return run_on_aer_sampler(qc, shots=shots)


def run_backend(
    circuit_or_program,
    backend,
    shots: int = 100,
) -> "dict[str, int]":
    """Run a circuit or program on a real Qiskit backend.

    Parameters
    ----------
    circuit_or_program:
        One of:

        * :class:`~qiskit.QuantumCircuit`
        * :class:`rqm_compiler.Circuit` / :class:`rqm_compiler.CompiledCircuit`
        * ``list`` of :class:`~rqm_qiskit.gates.RQMGate` objects

    backend:
        A Qiskit backend object (e.g., from IBM Quantum).
    shots:
        Number of measurement shots (default 100).

    Returns
    -------
    dict[str, int]
        Bitstring → count mapping.

    Raises
    ------
    NotImplementedError
        If ``backend`` is a string name – use a real backend object.
    """
    qc = _to_circuit(circuit_or_program)
    qc = _ensure_measurements(qc)

    if isinstance(backend, str):
        raise NotImplementedError(
            "Pass a real Qiskit backend object, not a string name. "
            "See qiskit_ibm_runtime for IBM Quantum backends."
        )

    from qiskit.primitives import StatevectorSampler

    sampler = StatevectorSampler()
    job = sampler.run([qc], shots=shots)
    result = job.result()
    pub_result = result[0]

    counts: dict[str, int] = {}
    for reg_name in pub_result.data:
        bit_array = getattr(pub_result.data, reg_name)
        for bitstring, count in bit_array.get_counts().items():
            counts[bitstring] = counts.get(bitstring, 0) + count
    return counts
