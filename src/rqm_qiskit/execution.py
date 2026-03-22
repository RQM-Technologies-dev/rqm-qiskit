"""
execution.py – Thin execution helpers for local and remote quantum backends.

These functions accept a flexible program representation (QuantumCircuit,
rqm-compiler Circuit, or RQMGate sequence), translate it to a QuantumCircuit
via the translator layer, add measurements if needed, and run it.

Functions
---------
- ``run_local``          : run on the local Aer simulator (offline-safe)
- ``run_backend``        : run on a real Qiskit backend (optional)
- ``run_qiskit``         : primary API; compile, translate, and run with optional report
- ``async_run_qiskit``   : async API; submit and return a QiskitJob handle
- ``execute_rqm_program``: high-level API accepting a canonical program descriptor dict
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

    This is the primary execution API for API-ready usage.  All compilation
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
        A Qiskit backend object, a backend name string (e.g. ``"ibm_brisbane"``),
        or ``None`` to use the local Aer simulator.  String names are resolved
        via :func:`~rqm_qiskit.ibm.resolve_backend` (requires IBM credentials).
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
    rqm_qiskit.errors.BackendNotFoundError
        If the string ``backend`` name cannot be resolved.
    rqm_qiskit.errors.CredentialsError
        If IBM credentials are required but unavailable.
    rqm_qiskit.errors.TranslationError
        If the circuit cannot be translated to Qiskit IR.
    rqm_qiskit.errors.JobFailedError
        If the backend job fails.
    ImportError
        If ``optimize=True`` but ``rqm_compiler.optimize_circuit`` is not
        available, or if ``qiskit-aer`` is not installed.
    """
    from rqm_qiskit.errors import TranslationError
    from rqm_qiskit.ibm import resolve_backend
    from rqm_qiskit.translator import to_qiskit_circuit

    # Resolve backend (string → backend object or None)
    resolved_backend = resolve_backend(backend)

    try:
        report = None
        if include_report:
            qc, report = to_qiskit_circuit(circuit, optimize=optimize, include_report=True)
        else:
            qc = to_qiskit_circuit(circuit, optimize=optimize, include_report=False)
    except TypeError as exc:
        raise TranslationError(str(exc)) from exc

    qc = _ensure_measurements(qc)

    backend_name = _backend_name(resolved_backend)
    counts, _ = _run_on_resolved_backend(qc, resolved_backend, shots=shots)

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


# ---------------------------------------------------------------------------
# Async execution
# ---------------------------------------------------------------------------


def async_run_qiskit(
    circuit,
    *,
    optimize: bool = False,
    shots: int = 1024,
    backend=None,
    include_report: bool = False,
    poll_interval: float = 2.0,
    timeout: "float | None" = None,
    **kwargs,
) -> "rqm_qiskit.job.QiskitJob":
    """Submit a circuit for execution and return a :class:`~rqm_qiskit.job.QiskitJob` immediately.

    For local Aer simulation the job is already complete when returned.
    For real IBM Quantum backends the job is submitted asynchronously and
    results can be retrieved later via :meth:`~rqm_qiskit.job.QiskitJob.result`.

    Parameters
    ----------
    circuit:
        An :class:`rqm_compiler.Circuit` or :class:`rqm_compiler.CompiledCircuit`.
    optimize:
        If ``True``, apply optimization passes before execution.
        Defaults to ``False``.
    shots:
        Number of measurement shots (default 1024).
    backend:
        A Qiskit backend object, a backend name string (e.g.
        ``"ibm_brisbane"``), or ``None`` to use the local Aer simulator.
        String names are resolved via
        :func:`~rqm_qiskit.ibm.resolve_backend`.
    include_report:
        If ``True``, the compiler report is embedded in the job's result
        metadata.  Defaults to ``False``.
    poll_interval:
        Reserved – seconds between status polls for future polling loops.
    timeout:
        Reserved – maximum seconds to wait when calling
        :meth:`~rqm_qiskit.job.QiskitJob.result`.
    **kwargs:
        Reserved for future backend-specific options.

    Returns
    -------
    :class:`~rqm_qiskit.job.QiskitJob`
        A job handle with :meth:`~rqm_qiskit.job.QiskitJob.job_id`,
        :meth:`~rqm_qiskit.job.QiskitJob.status`, and
        :meth:`~rqm_qiskit.job.QiskitJob.result` methods.

    Raises
    ------
    rqm_qiskit.errors.BackendNotFoundError
        If the string ``backend`` name cannot be resolved.
    rqm_qiskit.errors.CredentialsError
        If IBM credentials are required but unavailable.
    rqm_qiskit.errors.TranslationError
        If the circuit cannot be translated to Qiskit IR.

    Examples
    --------
    Local Aer (returns immediately, result already complete):

    >>> from rqm_compiler import Circuit
    >>> from rqm_qiskit import async_run_qiskit
    >>> c = Circuit(1); c.h(0); c.measure(0)
    >>> job = async_run_qiskit(c, shots=512)
    >>> print(job.status())
    DONE
    >>> result = job.result()
    >>> print(result.counts)

    IBM Quantum (requires credentials):

    >>> import os
    >>> os.environ["QISKIT_IBM_TOKEN"] = "my-api-token"
    >>> job = async_run_qiskit(c, shots=1024, backend="ibm_brisbane")
    >>> print(job.job_id())   # returned immediately
    >>> result = job.result(timeout=300)
    """
    import datetime

    from rqm_qiskit.errors import TranslationError
    from rqm_qiskit.ibm import resolve_backend
    from rqm_qiskit.job import QiskitJob
    from rqm_qiskit.result import QiskitResult
    from rqm_qiskit.translator import to_qiskit_circuit

    submitted_at = datetime.datetime.now(datetime.timezone.utc)

    # Resolve backend
    resolved_backend = resolve_backend(backend)

    # Translate circuit
    try:
        report = None
        if include_report:
            qc, report = to_qiskit_circuit(circuit, optimize=optimize, include_report=True)
        else:
            qc = to_qiskit_circuit(circuit, optimize=optimize, include_report=False)
    except TypeError as exc:
        raise TranslationError(str(exc)) from exc

    qc = _ensure_measurements(qc)
    backend_name = _backend_name(resolved_backend)

    # Detect real IBM backend
    if resolved_backend is not None and not _is_aer_backend(resolved_backend):
        # Real IBM backend – submit asynchronously
        try:
            from qiskit_ibm_runtime import SamplerV2 as IBMSampler

            sampler = IBMSampler(resolved_backend)
            ibm_job = sampler.run([qc], shots=shots)
        except ImportError as exc:
            raise ImportError(
                "async_run_qiskit with a real IBM backend requires "
                "qiskit-ibm-runtime.  Install it with:  "
                "pip install qiskit-ibm-runtime"
            ) from exc

        return QiskitJob(
            ibm_job=ibm_job,
            backend_name=backend_name,
            shots=shots,
            submitted_at=submitted_at,
        )

    # Local Aer – run synchronously, wrap in a completed job
    counts, local_job_id = _run_on_resolved_backend(qc, resolved_backend, shots=shots)
    result = QiskitResult(counts, shots=shots)

    if include_report and report is not None:
        # Attach report to result metadata via to_dict metadata hook
        # (report stored on the result object for access via job.to_dict())
        result._compiler_report = report  # type: ignore[attr-defined]

    return QiskitJob(
        result=result,
        job_id=local_job_id,
        backend_name=backend_name,
        shots=shots,
        submitted_at=submitted_at,
    )


# ---------------------------------------------------------------------------
# High-level API for rqm-api integration
# ---------------------------------------------------------------------------


def execute_rqm_program(
    program_descriptor: "dict[str, Any]",
    *,
    backend: "str | Any | None" = None,
    shots: int = 1024,
    optimize: bool = False,
    include_report: bool = False,
) -> "dict[str, Any]":
    """Compile and run a canonical RQM program descriptor; return a result dict.

    This is the high-level entry point designed for use by ``rqm-api`` and
    RQM Studio.  It accepts the canonical dictionary representation used by
    ``rqm-api`` (as produced by the RQM compiler IR), compiles it, and runs
    it through :func:`run_qiskit`.

    All math and IR logic is delegated to ``rqm-compiler``; this function
    only orchestrates compilation and execution.

    Parameters
    ----------
    program_descriptor:
        A canonical RQM program descriptor dict.  Accepted forms:

        *Circuit descriptor* (preferred)::

            {
                "num_qubits": 2,
                "operations": [
                    {"gate": "h", "targets": [0], "controls": [], "params": {}},
                    {"gate": "cx", "targets": [1], "controls": [0], "params": {}},
                    {"gate": "measure", "targets": [0], "controls": [], "params": {}},
                    {"gate": "measure", "targets": [1], "controls": [], "params": {}},
                ]
            }

    backend:
        Backend specification: ``None`` (local Aer), a backend object, or
        a backend name string (e.g. ``"ibm_brisbane"``).
    shots:
        Number of measurement shots (default 1024).
    optimize:
        If ``True``, apply rqm-compiler optimization passes.
        Defaults to ``False``.
    include_report:
        If ``True``, include compiler report in result metadata.
        Defaults to ``False``.

    Returns
    -------
    dict
        JSON-compatible result dictionary (same shape as :func:`run_qiskit`).

    Raises
    ------
    ValueError
        If ``program_descriptor`` is missing required keys.
    rqm_qiskit.errors.TranslationError
        If the descriptor cannot be compiled or translated.
    rqm_qiskit.errors.BackendNotFoundError
        If the backend string cannot be resolved.

    Examples
    --------
    >>> from rqm_qiskit import execute_rqm_program
    >>> descriptor = {
    ...     "num_qubits": 2,
    ...     "operations": [
    ...         {"gate": "h", "targets": [0], "controls": [], "params": {}},
    ...         {"gate": "cx", "targets": [1], "controls": [0], "params": {}},
    ...         {"gate": "measure", "targets": [0], "controls": [], "params": {}},
    ...         {"gate": "measure", "targets": [1], "controls": [], "params": {}},
    ...     ],
    ... }
    >>> result = execute_rqm_program(descriptor, shots=1024)
    >>> print(result["counts"])
    """
    from rqm_qiskit.errors import TranslationError

    if not isinstance(program_descriptor, dict):
        raise ValueError(
            f"program_descriptor must be a dict, got {type(program_descriptor).__name__!r}."
        )

    # Build an rqm-compiler Circuit from the descriptor
    try:
        from rqm_compiler import Circuit
        from rqm_compiler.ops import Operation
    except ImportError as exc:
        raise ImportError(
            "execute_rqm_program requires rqm-compiler. "
            "Install it with:  pip install rqm-compiler"
        ) from exc

    try:
        num_qubits = program_descriptor.get("num_qubits")
        operations_raw = program_descriptor.get("operations", [])

        if num_qubits is None:
            # Infer num_qubits from max target qubit in operations
            max_qubit = 0
            for op_desc in operations_raw:
                for q in op_desc.get("targets", []):
                    max_qubit = max(max_qubit, q)
                for q in op_desc.get("controls", []):
                    max_qubit = max(max_qubit, q)
            num_qubits = max_qubit + 1 if operations_raw else 1

        circuit = Circuit(num_qubits)
        for op_desc in operations_raw:
            op = Operation.from_descriptor(op_desc)
            circuit.add(op)
    except Exception as exc:
        raise TranslationError(
            f"Could not build Circuit from program_descriptor: {exc}"
        ) from exc

    return run_qiskit(
        circuit,
        optimize=optimize,
        shots=shots,
        backend=backend,
        include_report=include_report,
    )


# ---------------------------------------------------------------------------
# Internal shared helpers
# ---------------------------------------------------------------------------


def _backend_name(backend: Any) -> str:
    """Return a string name for the given backend (or 'aer_simulator')."""
    if backend is None:
        return "aer_simulator"
    if hasattr(backend, "name"):
        return backend.name() if callable(backend.name) else backend.name
    return type(backend).__name__


def _is_aer_backend(backend: Any) -> bool:
    """Return True if *backend* is a local Aer simulator instance."""
    if backend is None:
        return True
    try:
        from qiskit_aer import AerSimulator

        if isinstance(backend, AerSimulator):
            return True
    except ImportError:
        pass
    return type(backend).__name__.startswith("Aer")


def _run_on_resolved_backend(
    qc: QuantumCircuit,
    resolved_backend: Any,
    shots: int,
) -> "tuple[dict[str, int], str | None]":
    """Run ``qc`` on the resolved backend; return ``(counts, job_id)``."""
    from rqm_qiskit.errors import JobFailedError

    if resolved_backend is None or _is_aer_backend(resolved_backend):
        from rqm_qiskit.ibm import run_on_aer_sampler

        try:
            counts = run_on_aer_sampler(qc, shots=shots)
        except Exception as exc:
            raise JobFailedError(detail=str(exc)) from exc
        return counts, None

    # Real IBM backend
    from rqm_qiskit.ibm import run_on_ibm_runtime

    counts, job_id = run_on_ibm_runtime(qc, resolved_backend, shots=shots)
    return counts, job_id
