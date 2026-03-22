"""
backend.py – QiskitBackend: unified entry point for Qiskit execution.

Mirrors the BraketBackend design: hides the translator and execution
layers behind a single class with ``compile_to_circuit``, ``run_local``,
and ``run_backend`` methods.

Examples
--------
>>> from rqm_compiler import Circuit
>>> from rqm_qiskit.backend import QiskitBackend
>>> c = Circuit(2)
>>> c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)
>>> backend = QiskitBackend()
>>> result = backend.run_local(c, shots=200)
>>> print(result.counts)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from qiskit import QuantumCircuit

from rqm_qiskit.result import QiskitResult
from rqm_qiskit.translator import QiskitTranslator

if TYPE_CHECKING:
    import rqm_qiskit.job


class QiskitBackend:
    """Unified entry point for Qiskit circuit compilation and execution.

    Wraps :class:`~rqm_qiskit.translator.QiskitTranslator` and the
    execution helpers in :mod:`rqm_qiskit.execution`.

    All methods accept the full range of program representations:

    * :class:`rqm_compiler.Circuit` / :class:`rqm_compiler.CompiledCircuit`
      (preferred – compiler-first path)
    * :class:`~qiskit.QuantumCircuit` (pass-through)
    * ``list`` of :class:`~rqm_qiskit.gates.RQMGate` objects (transitional)

    Examples
    --------
    >>> from rqm_compiler import Circuit
    >>> from rqm_qiskit import QiskitBackend
    >>> c = Circuit(2)
    >>> c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)
    >>> backend = QiskitBackend()
    >>> result = backend.run_local(c, shots=1024)
    >>> print(result.most_likely_bitstring())
    """

    def __init__(self) -> None:
        self._translator = QiskitTranslator()

    def compile_to_circuit(self, circuit_or_program, optimize: bool = False) -> QuantumCircuit:
        """Translate a program representation to a Qiskit QuantumCircuit.

        Parameters
        ----------
        circuit_or_program:
            One of:

            * :class:`rqm_compiler.Circuit` / :class:`rqm_compiler.CompiledCircuit`
            * :class:`~qiskit.QuantumCircuit`
            * ``list`` of :class:`~rqm_qiskit.gates.RQMGate` objects
        optimize:
            If ``True``, apply optimization passes before lowering.
            Defaults to ``False``.

        Returns
        -------
        qiskit.QuantumCircuit
        """
        return self._translator.compile_to_circuit(circuit_or_program, optimize=optimize)

    def compile(
        self,
        circuit,
        *,
        optimize: bool = False,
        include_report: bool = False,
    ) -> "Union[QuantumCircuit, tuple]":
        """Compile an rqm-compiler circuit to a Qiskit QuantumCircuit.

        Alias for :meth:`compile_to_circuit` following the canonical
        ``Backend.compile()`` API convention.

        Parameters
        ----------
        circuit:
            An :class:`rqm_compiler.Circuit` or
            :class:`rqm_compiler.CompiledCircuit`.
        optimize:
            If ``True``, apply optimization passes before lowering.
            Defaults to ``False``.
        include_report:
            If ``True``, return a ``(QuantumCircuit, report)`` tuple.
            Defaults to ``False``.

        Returns
        -------
        qiskit.QuantumCircuit
            When ``include_report=False``.
        (qiskit.QuantumCircuit, report)
            When ``include_report=True``.
        """
        return self._translator.to_quantum_circuit(
            circuit, optimize=optimize, include_report=include_report
        )

    def run(
        self,
        circuit,
        *,
        optimize: bool = False,
        shots: int = 1024,
        backend=None,
        include_report: bool = False,
        **kwargs,
    ) -> "Union[QiskitResult, tuple]":
        """Compile and run a circuit; return a QiskitResult.

        This is the canonical ``Backend.run()`` API entry point for
        API-ready usage (``POST /run``).

        Parameters
        ----------
        circuit:
            An :class:`rqm_compiler.Circuit`,
            :class:`rqm_compiler.CompiledCircuit`, or
            :class:`~qiskit.QuantumCircuit`.
        optimize:
            If ``True``, apply optimization passes before execution.
            Defaults to ``False``.
        shots:
            Number of measurement shots (default 1024).
        backend:
            A Qiskit backend object, or ``None`` to use the local Aer
            simulator.
        include_report:
            If ``True``, return a ``(QiskitResult, report)`` tuple where
            ``report`` is the compiler report (or ``None``).
            Defaults to ``False``.
        **kwargs:
            Reserved for future backend-specific options.

        Returns
        -------
        :class:`~rqm_qiskit.result.QiskitResult`
            When ``include_report=False``.
        (:class:`~rqm_qiskit.result.QiskitResult`, report)
            When ``include_report=True``.

        Raises
        ------
        ImportError
            If ``qiskit-aer`` is not installed.
        """
        from rqm_qiskit.execution import run_local

        report = None
        if include_report:
            qc, report = self._translator.to_quantum_circuit(
                circuit, optimize=optimize, include_report=True
            )
            from rqm_qiskit.execution import _ensure_measurements
            from rqm_qiskit.ibm import run_on_aer_sampler
            qc = _ensure_measurements(qc)
            counts = run_on_aer_sampler(qc, shots=shots)
            result = QiskitResult(counts, shots=shots)
            return result, report

        counts = run_local(circuit, shots=shots, optimize=optimize)
        return QiskitResult(counts, shots=shots)

    def run_local(
        self,
        circuit_or_program,
        shots: int = 100,
        optimize: bool = False,
    ) -> QiskitResult:
        """Run a program on the local Aer simulator and return a QiskitResult.

        Parameters
        ----------
        circuit_or_program:
            Program to execute (see :meth:`compile_to_circuit`).
        shots:
            Number of measurement shots (default 100).
        optimize:
            If ``True``, apply optimization passes before execution.
            Defaults to ``False``.

        Returns
        -------
        :class:`~rqm_qiskit.result.QiskitResult`

        Raises
        ------
        ImportError
            If ``qiskit-aer`` is not installed.
        """
        from rqm_qiskit.execution import run_local

        counts = run_local(circuit_or_program, shots=shots, optimize=optimize)
        return QiskitResult(counts, shots=shots)

    def run_backend(
        self,
        circuit_or_program,
        backend,
        shots: int = 100,
    ) -> QiskitResult:
        """Run a program on a real Qiskit backend and return a QiskitResult.

        Parameters
        ----------
        circuit_or_program:
            Program to execute (see :meth:`compile_to_circuit`).
        backend:
            A Qiskit backend object.
        shots:
            Number of measurement shots (default 100).

        Returns
        -------
        :class:`~rqm_qiskit.result.QiskitResult`
        """
        from rqm_qiskit.execution import run_backend

        counts = run_backend(circuit_or_program, backend, shots=shots)
        return QiskitResult(counts, shots=shots)

    def async_run(
        self,
        circuit,
        *,
        optimize: bool = False,
        shots: int = 1024,
        backend=None,
        include_report: bool = False,
        poll_interval: float = 2.0,
        timeout: "Union[float, None]" = None,
        **kwargs,
    ) -> "rqm_qiskit.job.QiskitJob":
        """Submit a circuit asynchronously and return a :class:`~rqm_qiskit.job.QiskitJob`.

        For local Aer simulation the job is already complete when returned.
        For real IBM Quantum backends the job is submitted and the handle
        is returned immediately; call :meth:`~rqm_qiskit.job.QiskitJob.result`
        to block and retrieve results.

        Parameters
        ----------
        circuit:
            An :class:`rqm_compiler.Circuit`,
            :class:`rqm_compiler.CompiledCircuit`, or
            :class:`~qiskit.QuantumCircuit`.
        optimize:
            If ``True``, apply optimization passes before execution.
            Defaults to ``False``.
        shots:
            Number of measurement shots (default 1024).
        backend:
            A Qiskit backend object, a backend name string (e.g.
            ``"ibm_brisbane"``), or ``None`` to use the local Aer
            simulator.
        include_report:
            If ``True``, the compiler report is embedded in job metadata.
            Defaults to ``False``.
        poll_interval:
            Reserved – seconds between status polls.
        timeout:
            Reserved – maximum seconds to wait in :meth:`~rqm_qiskit.job.QiskitJob.result`.
        **kwargs:
            Reserved for future backend-specific options.

        Returns
        -------
        :class:`~rqm_qiskit.job.QiskitJob`

        Raises
        ------
        rqm_qiskit.errors.BackendNotFoundError
            If the backend string cannot be resolved.
        rqm_qiskit.errors.CredentialsError
            If IBM credentials are required but unavailable.
        rqm_qiskit.errors.TranslationError
            If the circuit cannot be translated.

        Examples
        --------
        >>> from rqm_compiler import Circuit
        >>> from rqm_qiskit import QiskitBackend
        >>> c = Circuit(1); c.h(0); c.measure(0)
        >>> backend = QiskitBackend()
        >>> job = backend.async_run(c, shots=512)
        >>> print(job.status())
        DONE
        >>> result = job.result()
        >>> print(result.counts)
        """
        from rqm_qiskit.execution import async_run_qiskit

        return async_run_qiskit(
            circuit,
            optimize=optimize,
            shots=shots,
            backend=backend,
            include_report=include_report,
            poll_interval=poll_interval,
            timeout=timeout,
            **kwargs,
        )

    def __repr__(self) -> str:
        return "QiskitBackend()"
