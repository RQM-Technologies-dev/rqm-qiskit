"""
ibm.py – Execution helpers for local Aer simulation and IBM Quantum.

This module provides:
- ``run_on_aer_sampler``: run a circuit on the local Aer simulator.
- ``run_on_ibm_runtime`` (stub): placeholder for future IBM Runtime support.

Only ``run_on_aer_sampler`` is fully implemented in v0.1.0.
IBM Runtime support is explicitly marked as a future work item.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


def run_on_aer_sampler(
    circuit: QuantumCircuit,
    shots: int = 1024,
) -> dict[str, int]:
    """Run a circuit on the local Aer simulator and return counts.

    This function uses :class:`qiskit_aer.primitives.Sampler` from the
    ``qiskit-aer`` package.  Install the simulator extras if needed::

        pip install "rqm-qiskit[simulator]"
        # or: pip install qiskit-aer

    Parameters
    ----------
    circuit:
        A fully measured :class:`~qiskit.QuantumCircuit`.
    shots:
        Number of measurement shots (default 1024).

    Returns
    -------
    dict[str, int]
        A mapping of bitstring → count, e.g. ``{"0": 512, "1": 512}``.

    Raises
    ------
    ImportError
        If ``qiskit-aer`` is not installed.

    Examples
    --------
    >>> from qiskit import QuantumCircuit
    >>> from rqm_qiskit.ibm import run_on_aer_sampler
    >>> qc = QuantumCircuit(1, 1)
    >>> qc.h(0)
    >>> qc.measure(0, 0)
    >>> counts = run_on_aer_sampler(qc, shots=1024)
    """
    try:
        from qiskit_aer.primitives import SamplerV2 as AerSampler

        sampler = AerSampler()
        job = sampler.run([circuit], shots=shots)
        result = job.result()
        pub_result = result[0]

        # Merge counts across all classical registers.
        counts: dict[str, int] = {}
        for reg_name in pub_result.data:
            bit_array = getattr(pub_result.data, reg_name)
            for bitstring, count in bit_array.get_counts().items():
                counts[bitstring] = counts.get(bitstring, 0) + count
        return counts

    except ImportError:
        pass  # fall through to legacy Sampler

    try:
        from qiskit_aer.primitives import Sampler as AerSamplerLegacy
    except ImportError as exc:
        raise ImportError(
            "qiskit-aer is required to run local simulations.\n"
            "Install it with:  pip install qiskit-aer\n"
            "Or install the simulator extras:  pip install 'rqm-qiskit[simulator]'"
        ) from exc

    sampler_legacy = AerSamplerLegacy()
    job_legacy = sampler_legacy.run(circuit, shots=shots)
    result_legacy = job_legacy.result()
    quasi_dist = result_legacy.quasi_dists[0]

    num_bits = circuit.num_clbits or 1
    counts_legacy: dict[str, int] = {}
    for state_int, quasi_prob in quasi_dist.items():
        bitstring = format(state_int, f"0{num_bits}b")
        counts_legacy[bitstring] = round(quasi_prob * shots)

    return counts_legacy


# ---------------------------------------------------------------------------
# IBM Runtime stub (future work)
# ---------------------------------------------------------------------------


def run_on_ibm_runtime(
    circuit: QuantumCircuit,
    backend_name: str,
    shots: int = 1024,
) -> dict[str, int]:
    """[STUB] Run a circuit on a real IBM Quantum backend via IBM Runtime.

    .. warning::
        This function is a **placeholder** for future IBM Runtime support.
        It is **not implemented** in v0.1.0 and will raise
        :exc:`NotImplementedError` if called.

    Future implementation will use :mod:`qiskit_ibm_runtime` with the
    ``SamplerV2`` primitive.  An IBM Quantum account and API token will
    be required.

    Parameters
    ----------
    circuit:
        The circuit to execute.
    backend_name:
        Target backend name, e.g. ``"ibm_brisbane"``.
    shots:
        Number of measurement shots.

    Raises
    ------
    NotImplementedError
        Always – this function is not yet implemented.
    """
    raise NotImplementedError(
        "IBM Runtime execution is not yet implemented in rqm-qiskit v0.1.0.\n"
        "Use run_on_aer_sampler() for local simulation in the meantime.\n"
        "IBM Runtime support is planned for a future release."
    )
