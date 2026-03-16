"""
convert.py – Helpers to convert RQM and rqm-compiler objects to Qiskit QuantumCircuits.

This module is the heart of the rqm-qiskit bridge layer.  It consumes
canonical rqm-compiler IR (Circuit / CompiledCircuit / Operation) and
lowers it into Qiskit QuantumCircuit objects.  No gate semantics are
defined here — all canonical meaning belongs to rqm-compiler.

Public functions
----------------
- ``compiled_circuit_to_qiskit`` : lower an rqm-compiler Circuit or
  CompiledCircuit into a Qiskit QuantumCircuit.
- ``state_to_quantum_circuit``   : convenience wrapper for 1-qubit state prep.
- ``gate_to_quantum_circuit``    : convenience wrapper for a single-gate circuit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from qiskit import QuantumCircuit
from qiskit.circuit import ClassicalRegister

from rqm_qiskit.state import RQMState
from rqm_qiskit.gates import RQMGate

if TYPE_CHECKING:
    from rqm_compiler import Circuit, CompiledCircuit
    from rqm_compiler.ops import Operation


# ---------------------------------------------------------------------------
# Compiler-IR → QuantumCircuit bridge (the core of this module)
# ---------------------------------------------------------------------------


def compiled_circuit_to_qiskit(
    source: "Union[Circuit, CompiledCircuit]",
) -> QuantumCircuit:
    """Lower an rqm-compiler :class:`~rqm_compiler.Circuit` or
    :class:`~rqm_compiler.CompiledCircuit` into a Qiskit
    :class:`~qiskit.QuantumCircuit`.

    This function is the primary bridge from the rqm-compiler canonical IR to
    Qiskit.  Gate semantics and circuit structure are owned by rqm-compiler;
    this function only performs the translation into Qiskit primitives.

    Supported gates
    ---------------
    Single-qubit (no params): ``i``, ``x``, ``y``, ``z``, ``h``, ``s``, ``t``
    Single-qubit (parametric): ``rx``, ``ry``, ``rz``, ``phaseshift``
    Two-qubit: ``cx``, ``cy``, ``cz``, ``swap``, ``iswap``
    Other: ``measure``, ``barrier``

    Parameters
    ----------
    source:
        Either an :class:`rqm_compiler.Circuit` (operations list) or a
        :class:`rqm_compiler.CompiledCircuit` (descriptor list).

    Returns
    -------
    qiskit.QuantumCircuit
        A Qiskit circuit equivalent to the canonical rqm-compiler circuit.
        Classical registers are added automatically for any ``measure``
        operations present in the source circuit.

    Examples
    --------
    >>> from rqm_compiler import Circuit
    >>> from rqm_qiskit.convert import compiled_circuit_to_qiskit
    >>> c = Circuit(1)
    >>> c.ry(0, 1.57)
    >>> c.measure(0)
    >>> qc = compiled_circuit_to_qiskit(c)
    >>> print(qc.draw(output="text"))
    """
    from rqm_compiler import Circuit, CompiledCircuit
    from rqm_compiler.ops import Operation

    if isinstance(source, CompiledCircuit):
        num_qubits = source.num_qubits
        operations: list[Operation] = [
            Operation.from_descriptor(d) for d in source.descriptors
        ]
    else:
        num_qubits = source.num_qubits
        operations = list(source.operations)

    return _build_qiskit_from_ops(num_qubits, operations)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_qiskit_from_ops(
    num_qubits: int,
    operations: "list[Operation]",
) -> QuantumCircuit:
    """Build a Qiskit QuantumCircuit from a list of rqm-compiler Operations.

    This is a shared helper used by both :func:`compiled_circuit_to_qiskit`
    and :class:`~rqm_qiskit.circuit.RQMCircuit`.

    Parameters
    ----------
    num_qubits:
        Number of qubits in the circuit.
    operations:
        Ordered list of :class:`rqm_compiler.ops.Operation` objects.

    Returns
    -------
    qiskit.QuantumCircuit
    """
    # Collect measurement keys to size the classical register.
    measure_keys: list[str] = []
    for op in operations:
        if op.gate == "measure":
            key: str = op.params.get("key", f"m{op.targets[0]}")
            if key not in measure_keys:
                measure_keys.append(key)

    qc = QuantumCircuit(num_qubits)
    if measure_keys:
        qc.add_register(ClassicalRegister(len(measure_keys), "meas"))

    key_to_clbit: dict[str, int] = {k: i for i, k in enumerate(measure_keys)}

    for op in operations:
        _apply_operation(qc, op, key_to_clbit)

    return qc


def _apply_operation(
    qc: QuantumCircuit,
    op: "Operation",
    key_to_clbit: dict[str, int],
) -> None:
    """Apply a single rqm-compiler Operation to a Qiskit QuantumCircuit in-place.

    Parameters
    ----------
    qc:
        The target QuantumCircuit (mutated in-place).
    op:
        The rqm-compiler operation to translate.
    key_to_clbit:
        Mapping from measurement key strings to classical bit indices.
    """
    gate = op.gate
    targets = op.targets
    controls = op.controls
    params: dict[str, Any] = op.params

    if gate == "i":
        pass  # identity – no-op
    elif gate == "x":
        qc.x(targets[0])
    elif gate == "y":
        qc.y(targets[0])
    elif gate == "z":
        qc.z(targets[0])
    elif gate == "h":
        qc.h(targets[0])
    elif gate == "s":
        qc.s(targets[0])
    elif gate == "t":
        qc.t(targets[0])
    elif gate == "rx":
        qc.rx(params["angle"], targets[0])
    elif gate == "ry":
        qc.ry(params["angle"], targets[0])
    elif gate == "rz":
        qc.rz(params["angle"], targets[0])
    elif gate == "phaseshift":
        qc.p(params["angle"], targets[0])
    elif gate == "cx":
        qc.cx(controls[0], targets[0])
    elif gate == "cy":
        qc.cy(controls[0], targets[0])
    elif gate == "cz":
        qc.cz(controls[0], targets[0])
    elif gate == "swap":
        qc.swap(targets[0], targets[1])
    elif gate == "iswap":
        qc.iswap(targets[0], targets[1])
    elif gate == "measure":
        key = params.get("key", f"m{targets[0]}")
        qc.measure(targets[0], key_to_clbit[key])
    elif gate == "barrier":
        if targets:
            qc.barrier(targets)
        else:
            qc.barrier()
    # Unknown gates are silently ignored; validation is rqm-compiler's responsibility.


# ---------------------------------------------------------------------------
# Convenience wrappers (thin; preserved for public API compatibility)
# ---------------------------------------------------------------------------


def state_to_quantum_circuit(state: RQMState) -> QuantumCircuit:
    """Convert an :class:`~rqm_qiskit.RQMState` to a 1-qubit QuantumCircuit.

    The returned circuit uses Qiskit's ``initialize`` instruction to
    prepare the qubit in the given state.

    Parameters
    ----------
    state:
        The 1-qubit state to encode.

    Returns
    -------
    qiskit.QuantumCircuit
        A 1-qubit circuit that initializes the qubit to ``state``.

    Examples
    --------
    >>> from rqm_qiskit import RQMState, state_to_quantum_circuit
    >>> qc = state_to_quantum_circuit(RQMState.plus())
    >>> print(qc.draw(output="text"))
    """
    alpha, beta = state.vector()
    qc = QuantumCircuit(1)
    qc.initialize([alpha, beta], 0)
    return qc


def gate_to_quantum_circuit(gate: RQMGate) -> QuantumCircuit:
    """Convert an :class:`~rqm_qiskit.RQMGate` to a 1-qubit QuantumCircuit.

    The returned circuit applies the rotation gate to qubit 0.

    Parameters
    ----------
    gate:
        The rotation gate to apply.

    Returns
    -------
    qiskit.QuantumCircuit
        A 1-qubit circuit applying ``gate`` to qubit 0.

    Examples
    --------
    >>> from rqm_qiskit import RQMGate, gate_to_quantum_circuit
    >>> qc = gate_to_quantum_circuit(RQMGate.rx(1.57))
    >>> print(qc.draw(output="text"))
    """
    qc = QuantumCircuit(1)
    qc.append(gate.to_qiskit_gate(), [0])
    return qc
