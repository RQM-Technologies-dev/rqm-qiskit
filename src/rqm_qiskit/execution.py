"""
execution.py – Thin execution helpers for local and remote quantum backends.

These functions accept a flexible program representation (QuantumCircuit,
rqm-compiler Circuit, or RQMGate sequence), translate it to a QuantumCircuit
via the translator layer, add measurements if needed, and run it.

Functions
---------
- ``run_local``   : run on the local Aer simulator (offline-safe)
- ``run_backend`` : run on a real Qiskit backend (optional)
- ``run_qiskit``  : new primary API; compile, translate, and run with optional report
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

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


def _to_circuit(circuit_or_program, optimize: bool = False) -> QuantumCircuit:
    """Convert any supported program representation to a QuantumCircuit."""
    from rqm_qiskit.translator import QiskitTranslator

    return QiskitTranslator().compile_to_circuit(circuit_or_program, optimize=optimize)


def run_qiskit(
    circuit,
    *,
    optimize: bool = False,
    shots: int = 1024,
    backend=None,
    include_report: bool = False,
    **kwargs,
) -> "dict[str, Any]":
    """Compile, translate, and run a circuit; return a standardized result dict.

    This is the new primary execution API for API-ready usage.  All compilation
    is delegated to rqm-compiler; this function only translates and runs.

    Parameters
    ----------
    circuit:
        An :class:`rqm_compiler.Circuit` or :class:`rqm_compiler.CompiledCircuit`.
    optimize:
        If ``True``, apply optimization passes before execution via
        ``rqm_compiler.optimize_circuit``.  Raises :exc:`ImportError` if not
        available.  Defaults to ``False``.
    shots:
        Number of measurement shots (default 1024).
    backend:
        A Qiskit backend object, or ``None`` to use the local Aer simulator.
    include_report:
        If ``True``, include compiler/optimization metadata in the result dict.
        Defaults to ``False``.
    **kwargs:
        Reserved for future backend-specific options.

    Returns
    -------
    dict
        JSON-compatible result dictionary:

        .. code-block:: python

            {
                "counts": {"00": 512, "11": 512},
                "shots": 1024,
                "backend": "aer_simulator",
                "metadata": {"outcomes": 2, "most_likely": "00"},
            }

        When ``include_report=True`` and ``optimize=True``, ``metadata``
        additionally contains:

        .. code-block:: python

            {
                "optimized": True,
                "compiler_report": {...},
            }

    Raises
    ------
    ImportError
        If ``optimize=True`` but ``rqm_compiler.optimize_circuit`` is not
        available, or if ``qiskit-aer`` is not installed.
    """
    from rqm_qiskit.translator import to_qiskit_circuit

    report = None
    if include_report:
        qc, report = to_qiskit_circuit(circuit, optimize=optimize, include_report=True)
    else:
        qc = to_qiskit_circuit(circuit, optimize=optimize, include_report=False)

    qc = _ensure_measurements(qc)

    backend_name = "aer_simulator"
    if backend is not None and hasattr(backend, "name"):
        backend_name = backend.name() if callable(backend.name) else backend.name

    if backend is None:
        from rqm_qiskit.ibm import run_on_aer_sampler
        counts = run_on_aer_sampler(qc, shots=shots)
    else:
        if isinstance(backend, str):
            raise NotImplementedError(
                "Pass a real Qiskit backend object, not a string name. "
                "See qiskit_ibm_runtime for IBM Quantum backends."
            )
        try:
            from qiskit_aer import AerSimulator
            if isinstance(backend, AerSimulator) or type(backend).__name__.startswith("Aer"):
                from rqm_qiskit.ibm import run_on_aer_sampler
                counts = run_on_aer_sampler(qc, shots=shots)
            else:
                raise NotImplementedError(
                    "Real IBM Quantum backend execution requires qiskit_ibm_runtime. "
                    "Install it separately."
                )
        except ImportError:
            raise NotImplementedError(
                "Real IBM Quantum backend execution requires qiskit_ibm_runtime. "
                "Install it separately."
            )

    most_likely = max(counts, key=lambda k: counts[k]) if counts else None
    metadata: dict[str, Any] = {
        "outcomes": len(counts),
        "most_likely": most_likely,
    }
    if include_report:
        metadata["optimized"] = optimize
        metadata["compiler_report"] = (
            report.__dict__ if report is not None and hasattr(report, "__dict__") else None
        )

    return {
        "counts": counts,
        "shots": shots,
        "backend": backend_name,
        "metadata": metadata,
    }


def run_local(
    circuit_or_program,
    shots: int = 100,
    optimize: bool = False,
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
    optimize:
        If ``True``, apply optimization passes before execution.
        Defaults to ``False``.

    Returns
    -------
    dict[str, int]
        Bitstring → count mapping.

    Raises
    ------
    ImportError
        If ``qiskit-aer`` is not installed.
    """
    qc = _to_circuit(circuit_or_program, optimize=optimize)
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
    qc = _to_circuit(circuit_or_program, optimize=False)
    qc = _ensure_measurements(qc)

    if isinstance(backend, str):
        raise NotImplementedError(
            "Pass a real Qiskit backend object, not a string name. "
            "See qiskit_ibm_runtime for IBM Quantum backends."
        )

    # Try to use the provided backend as an Aer simulator
    try:
        from qiskit_aer import AerSimulator

        if isinstance(backend, AerSimulator) or type(backend).__name__.startswith("Aer"):
            from rqm_qiskit.ibm import run_on_aer_sampler

            return run_on_aer_sampler(qc, shots=shots)
    except ImportError:
        pass

    # Real IBM backends require qiskit_ibm_runtime – raise with helpful guidance
    raise NotImplementedError(
        "Real IBM Quantum backend execution requires qiskit_ibm_runtime. "
        "Install it separately and use SamplerV2(backend).run([circuit], shots=shots). "
        "rqm-qiskit does not bundle IBM Runtime as a dependency."
    )
