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
    pass


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

    def compile_to_circuit(self, circuit_or_program) -> QuantumCircuit:
        """Translate a program representation to a Qiskit QuantumCircuit.

        Parameters
        ----------
        circuit_or_program:
            One of:

            * :class:`rqm_compiler.Circuit` / :class:`rqm_compiler.CompiledCircuit`
            * :class:`~qiskit.QuantumCircuit`
            * ``list`` of :class:`~rqm_qiskit.gates.RQMGate` objects

        Returns
        -------
        qiskit.QuantumCircuit
        """
        return self._translator.compile_to_circuit(circuit_or_program)

    def run_local(
        self,
        circuit_or_program,
        shots: int = 100,
    ) -> QiskitResult:
        """Run a program on the local Aer simulator and return a QiskitResult.

        Parameters
        ----------
        circuit_or_program:
            Program to execute (see :meth:`compile_to_circuit`).
        shots:
            Number of measurement shots (default 100).

        Returns
        -------
        :class:`~rqm_qiskit.result.QiskitResult`

        Raises
        ------
        ImportError
            If ``qiskit-aer`` is not installed.
        """
        from rqm_qiskit.execution import run_local

        counts = run_local(circuit_or_program, shots=shots)
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

    def __repr__(self) -> str:
        return "QiskitBackend()"
