"""
translator.py – QiskitTranslator: compiler IR → Qiskit QuantumCircuit.

# NOTE:
# Primary input type is rqm-compiler CompiledProgram.
# RQMGate and dict support are transitional and may be removed in a future release.

This module provides the core translation layer between the rqm-compiler
canonical IR and Qiskit QuantumCircuit objects.

Supported gate names (from rqm-compiler IR):
    Single-qubit (no params): i, x, y, z, h, s, t
    Single-qubit (parametric): rx, ry, rz, phaseshift, u1q
    Two-qubit: cx, cy, cz, swap, iswap
    Other: measure, barrier

Public API
----------
- ``QiskitTranslator`` : stateless translator class
- ``compile_to_qiskit_circuit`` : convenience function delegating to the translator
- ``to_backend_circuit`` : primary translation API (supports optimize toggle)
- ``to_qiskit_circuit`` : new primary API with include_report support
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from qiskit import QuantumCircuit

from rqm_qiskit.convert import compiled_circuit_to_qiskit

if TYPE_CHECKING:
    from rqm_compiler import Circuit, CompiledCircuit
    from rqm_qiskit.gates import RQMGate


class QiskitTranslator:
    """Stateless translator from rqm-compiler IR (or RQMGate sequences) to Qiskit.

    Primary input type is :class:`rqm_compiler.Circuit` or
    :class:`rqm_compiler.CompiledCircuit`.  RQMGate sequence support is
    a transitional path.

    Examples
    --------
    >>> from rqm_compiler import Circuit
    >>> from rqm_qiskit.translator import QiskitTranslator
    >>> c = Circuit(2)
    >>> c.h(0)
    >>> c.cx(0, 1)
    >>> c.measure(0); c.measure(1)
    >>> qc = QiskitTranslator().compile_to_circuit(c)
    """

    def to_quantum_circuit(
        self,
        circuit: "Union[Circuit, CompiledCircuit]",
        *,
        optimize: bool = False,
        include_report: bool = False,
    ) -> "Union[QuantumCircuit, tuple[QuantumCircuit, Any]]":
        """Translate an rqm-compiler circuit to a Qiskit QuantumCircuit.

        This is the canonical entry point for the new architecture.
        All compilation is delegated to rqm-compiler; this method only
        performs descriptor → Qiskit gate mapping.

        Parameters
        ----------
        circuit:
            An :class:`rqm_compiler.Circuit` or
            :class:`rqm_compiler.CompiledCircuit`.
        optimize:
            If ``True``, call ``optimize_circuit`` from rqm-compiler before
            lowering.  Raises :exc:`ImportError` if not available.
            Defaults to ``False``.
        include_report:
            If ``True``, return a ``(QuantumCircuit, report)`` tuple where
            ``report`` is the compiler report (or ``None`` when
            ``optimize=False``).
            Defaults to ``False``.

        Returns
        -------
        qiskit.QuantumCircuit
            When ``include_report=False`` (default).
        (qiskit.QuantumCircuit, report)
            When ``include_report=True``.

        Raises
        ------
        ImportError
            If ``optimize=True`` but ``rqm_compiler.optimize_circuit`` is
            not available.
        """
        from rqm_compiler import Circuit, CompiledCircuit, compile_circuit

        report = None

        if optimize:
            optimized_circuit, report = _apply_optimization_with_report(circuit)
            working = optimized_circuit
        else:
            if isinstance(circuit, CompiledCircuit):
                working = circuit
            else:
                compiled = compile_circuit(circuit)
                working = compiled

        qc = compiled_circuit_to_qiskit(working)

        if include_report:
            return qc, report
        return qc

    def apply_gate(
        self,
        qc: QuantumCircuit,
        descriptor: "dict[str, Any]",
    ) -> None:
        """Apply a single canonical gate descriptor to a Qiskit QuantumCircuit.

        Parameters
        ----------
        qc:
            The target :class:`qiskit.QuantumCircuit` (mutated in-place).
        descriptor:
            A canonical gate descriptor dict with keys:
            ``gate``, ``targets``, ``controls``, ``params``.
        """
        from rqm_compiler.ops import Operation
        from rqm_qiskit.convert import _apply_operation

        op = Operation.from_descriptor(descriptor)
        # Build a temporary key mapping for measure operations
        key_to_clbit: dict[str, int] = {}
        if op.gate == "measure":
            key = op.params.get("key", f"m{op.targets[0]}")
            if qc.num_clbits > 0:
                # Find the classical bit index by iterating existing registers
                clbit_idx = 0
                for reg in qc.cregs:
                    for i in range(reg.size):
                        key_to_clbit[f"m{clbit_idx}"] = clbit_idx
                        clbit_idx += 1
        _apply_operation(qc, op, key_to_clbit)

    def compile_to_circuit(
        self,
        source: "Union[Circuit, CompiledCircuit, list, QuantumCircuit]",
        optimize: bool = False,
    ) -> QuantumCircuit:
        """Translate a program representation to a Qiskit QuantumCircuit.

        Parameters
        ----------
        source:
            One of:

            * :class:`rqm_compiler.Circuit` (preferred)
            * :class:`rqm_compiler.CompiledCircuit` (preferred)
            * :class:`~qiskit.QuantumCircuit` (pass-through)
            * ``list`` of :class:`~rqm_qiskit.gates.RQMGate` objects
              (transitional, named gate mode)
        optimize:
            If ``True``, apply optimization passes via ``optimize_circuit``
            before lowering (requires ``rqm-optimize`` to be installed).
            Defaults to ``False``.

        Returns
        -------
        qiskit.QuantumCircuit
            A Qiskit circuit ready for simulation or execution.

        Raises
        ------
        TypeError
            If ``source`` is not a recognized program type.
        ImportError
            If ``optimize=True`` but no optimization backend is available.
        """
        if isinstance(source, QuantumCircuit):
            return source

        # Compiler IR: Circuit or CompiledCircuit
        try:
            from rqm_compiler import Circuit, CompiledCircuit

            is_compiler_ir = isinstance(source, (Circuit, CompiledCircuit))
        except ImportError:
            is_compiler_ir = False

        if is_compiler_ir:
            if optimize:
                source = _apply_optimization(source)
            return compiled_circuit_to_qiskit(source)

        # Transitional: list of RQMGate (named gate mode) or Operation
        if isinstance(source, list):
            return self._from_gate_sequence(source)

        raise TypeError(
            f"Unsupported program type: {type(source).__name__!r}. "
            "Expected rqm_compiler.Circuit, CompiledCircuit, QuantumCircuit, "
            "or a list of RQMGate / Operation objects."
        )

    def _from_gate_sequence(
        self,
        gates: list,
    ) -> QuantumCircuit:
        """Build a QuantumCircuit from a list of RQMGate or Operation objects.

        Automatically infers the number of qubits from the maximum qubit index
        found in the sequence.

        Parameters
        ----------
        gates:
            List of :class:`~rqm_qiskit.gates.RQMGate` objects (named gate
            mode) or :class:`rqm_compiler.ops.Operation` objects.

        Returns
        -------
        qiskit.QuantumCircuit
        """
        from rqm_compiler import Circuit
        from rqm_compiler.ops import Operation

        # Convert everything to Operations
        operations: list[Operation] = []
        for g in gates:
            if isinstance(g, Operation):
                operations.append(g)
            else:
                # Assume RQMGate (both rotation and named mode support to_operation())
                operations.append(g.to_operation())

        # Infer number of qubits from max qubit index
        max_qubit = 0
        for op in operations:
            for q in op.targets:
                max_qubit = max(max_qubit, q)
            for q in op.controls:
                max_qubit = max(max_qubit, q)
        num_qubits = max_qubit + 1

        # Build a compiler circuit and lower it
        c = Circuit(num_qubits)
        for op in operations:
            c.add(op)
        return compiled_circuit_to_qiskit(c)


def compile_to_qiskit_circuit(
    source: "Union[Circuit, CompiledCircuit, list, QuantumCircuit]",
    optimize: bool = False,
) -> QuantumCircuit:
    """Compile a program representation to a Qiskit QuantumCircuit.

    Convenience function that delegates to :class:`QiskitTranslator`.

    Parameters
    ----------
    source:
        One of:

        * :class:`rqm_compiler.Circuit` (preferred)
        * :class:`rqm_compiler.CompiledCircuit` (preferred)
        * :class:`~qiskit.QuantumCircuit` (pass-through)
        * ``list`` of :class:`~rqm_qiskit.gates.RQMGate` objects
    optimize:
        If ``True``, apply optimization passes before lowering.
        Defaults to ``False``.

    Returns
    -------
    qiskit.QuantumCircuit
    """
    return QiskitTranslator().compile_to_circuit(source, optimize=optimize)


def to_backend_circuit(
    circuit: "Union[Circuit, CompiledCircuit]",
    *,
    optimize: bool = False,
) -> QuantumCircuit:
    """Translate an rqm-compiler circuit to a Qiskit QuantumCircuit.

    This is the primary translation API.  It delegates all compilation and
    gate semantics to rqm-compiler and only maps descriptors to Qiskit
    primitives.

    Parameters
    ----------
    circuit:
        An :class:`rqm_compiler.Circuit` or :class:`rqm_compiler.CompiledCircuit`.
    optimize:
        If ``True``, apply optimization passes via ``optimize_circuit``
        before lowering.  Requires ``rqm-optimize`` to be installed.
        Defaults to ``False``.

    Returns
    -------
    qiskit.QuantumCircuit
        Backend-native circuit ready for simulation or execution.

    Raises
    ------
    ImportError
        If ``optimize=True`` but no optimization backend is available.

    Examples
    --------
    >>> from rqm_compiler import Circuit
    >>> from rqm_qiskit.translator import to_backend_circuit
    >>> c = Circuit(2)
    >>> c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)
    >>> qc = to_backend_circuit(c)
    """
    return QiskitTranslator().compile_to_circuit(circuit, optimize=optimize)


def to_qiskit_circuit(
    circuit: "Union[Circuit, CompiledCircuit]",
    *,
    optimize: bool = False,
    include_report: bool = False,
) -> "Union[QuantumCircuit, tuple[QuantumCircuit, Any]]":
    """Translate an rqm-compiler circuit to a Qiskit QuantumCircuit.

    This is the new primary translation API.  All compilation is delegated to
    rqm-compiler; this function only performs descriptor → Qiskit gate mapping.

    Parameters
    ----------
    circuit:
        An :class:`rqm_compiler.Circuit` or :class:`rqm_compiler.CompiledCircuit`.
    optimize:
        If ``True``, call ``optimize_circuit`` from rqm-compiler before lowering.
        Raises :exc:`ImportError` if not available in the installed rqm-compiler.
        Defaults to ``False``.
    include_report:
        If ``True``, return a ``(QuantumCircuit, report)`` tuple where ``report``
        is the compiler report (or ``None`` when ``optimize=False``).
        Defaults to ``False``.

    Returns
    -------
    qiskit.QuantumCircuit
        When ``include_report=False`` (default).
    (qiskit.QuantumCircuit, report)
        When ``include_report=True``.

    Raises
    ------
    ImportError
        If ``optimize=True`` but ``rqm_compiler.optimize_circuit`` is not
        available.

    Examples
    --------
    >>> from rqm_compiler import Circuit
    >>> from rqm_qiskit import to_qiskit_circuit
    >>> c = Circuit(2)
    >>> c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)
    >>> qc = to_qiskit_circuit(c)
    >>> qc, report = to_qiskit_circuit(c, optimize=True, include_report=True)
    """
    return QiskitTranslator().to_quantum_circuit(
        circuit,
        optimize=optimize,
        include_report=include_report,
    )


def _apply_optimization(
    source: "Union[Circuit, CompiledCircuit]",
) -> "Union[Circuit, CompiledCircuit]":
    """Apply optimization passes to a circuit via rqm-compiler's built-in passes.

    Raises :exc:`ImportError` if ``rqm_compiler.optimize_circuit`` is not
    available.  To use an external optimizer (e.g. ``rqm-optimize``), call
    that optimizer **before** passing the circuit to rqm-qiskit — do not
    import it inside this package.

    Parameters
    ----------
    source:
        The circuit to optimize.

    Returns
    -------
    Circuit or CompiledCircuit
        The optimized circuit.

    Raises
    ------
    ImportError
        If ``rqm_compiler.optimize_circuit`` is not available in the
        installed version of rqm-compiler.
    """
    optimized, _ = _apply_optimization_with_report(source)
    return optimized


def _apply_optimization_with_report(
    source: "Union[Circuit, CompiledCircuit]",
) -> "tuple[Union[Circuit, CompiledCircuit], Any]":
    """Apply optimization passes and return ``(optimized_circuit, report)``.

    Raises :exc:`ImportError` if ``rqm_compiler.optimize_circuit`` is not
    available.  To use an external optimizer (e.g. ``rqm-optimize``), call
    that optimizer **before** passing the circuit to rqm-qiskit — do not
    import it inside this package.

    Parameters
    ----------
    source:
        The circuit to optimize.

    Returns
    -------
    (Circuit | CompiledCircuit, report)
        The optimized circuit and compiler report.

    Raises
    ------
    ImportError
        If ``rqm_compiler.optimize_circuit`` is not available in the
        installed version of rqm-compiler.
    """
    # Attempt rqm_compiler built-in optimization passes only.
    # rqm-qiskit must not import rqm-optimize (architecture boundary).
    try:
        from rqm_compiler import optimize_circuit  # type: ignore[attr-defined]
        result = optimize_circuit(source)
        # Some versions return (circuit, report); accept both forms
        if isinstance(result, tuple):
            return result[0], result[1]
        return result, None
    except (ImportError, AttributeError):
        pass

    raise ImportError(
        "optimize=True requires rqm_compiler.optimize_circuit, which is not "
        "available in the installed version of rqm-compiler. "
        "To use an external optimizer, apply it before passing the circuit "
        "to rqm-qiskit (e.g. via rqm-optimize installed separately)."
    )
