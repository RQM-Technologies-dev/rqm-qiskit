"""
translator.py – QiskitTranslator: compiler IR → Qiskit QuantumCircuit.

# NOTE:
# Primary input type is rqm-compiler CompiledProgram.
# RQMGate and dict support are transitional and may be removed in a future release.

This module provides the core translation layer between the rqm-compiler
canonical IR and Qiskit QuantumCircuit objects.

Supported gate names (from rqm-compiler IR):
    Single-qubit (no params): i, x, y, z, h, s, t
    Single-qubit (parametric): rx, ry, rz, phaseshift
    Two-qubit: cx, cy, cz, swap, iswap
    Other: measure, barrier

Public API
----------
- ``QiskitTranslator`` : stateless translator class
- ``compile_to_qiskit_circuit`` : convenience function delegating to the translator
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

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

    def compile_to_circuit(
        self,
        source: "Union[Circuit, CompiledCircuit, list, QuantumCircuit]",
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

        Returns
        -------
        qiskit.QuantumCircuit
            A Qiskit circuit ready for simulation or execution.

        Raises
        ------
        TypeError
            If ``source`` is not a recognized program type.
        """
        if isinstance(source, QuantumCircuit):
            return source

        # Compiler IR: Circuit or CompiledCircuit
        try:
            from rqm_compiler import Circuit, CompiledCircuit

            if isinstance(source, (Circuit, CompiledCircuit)):
                return compiled_circuit_to_qiskit(source)
        except ImportError:
            pass

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

    Returns
    -------
    qiskit.QuantumCircuit
    """
    return QiskitTranslator().compile_to_circuit(source)
