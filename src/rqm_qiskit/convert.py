"""
convert.py – Helpers to convert RQM and rqm-compiler objects to Qiskit QuantumCircuits.

This module is the heart of the rqm-qiskit bridge layer.  It consumes
canonical rqm-compiler IR (Circuit / CompiledCircuit / Operation) and
lowers it into Qiskit QuantumCircuit objects.  No gate semantics are
defined here — all canonical meaning belongs to rqm-compiler.

Single lowering path
--------------------
``compiled_circuit_to_qiskit`` is the **only** lowering path from compiler IR
to Qiskit.  All other public helpers in this module route through it:

- ``gate_to_quantum_circuit``  builds a 1-operation rqm-compiler Circuit and
  calls ``compiled_circuit_to_qiskit``.  It does NOT call Qiskit rotation-gate
  constructors directly.

The sole exception is ``state_to_quantum_circuit``, which must stay outside
this path because Qiskit's ``initialize`` instruction is not represented in the
rqm-compiler IR.  It is therefore inherently Qiskit-specific.

Public functions
----------------
- ``compiled_circuit_to_qiskit`` : lower an rqm-compiler Circuit or
  CompiledCircuit into a Qiskit QuantumCircuit.
- ``state_to_quantum_circuit`` : Qiskit-specific 1-qubit state prep via
  ``initialize`` (intentionally outside the main lowering path).
- ``gate_to_quantum_circuit`` : convenience wrapper; routes through
  ``compiled_circuit_to_qiskit``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from qiskit import QuantumCircuit
from qiskit.circuit import ClassicalRegister
from qiskit.transpiler import Target

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
    *,
    target: Target | None = None,
    include_synthesis_report: bool = False,
) -> QuantumCircuit | tuple[QuantumCircuit, list[dict[str, Any]]]:
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
    from rqm_compiler import CompiledCircuit
    from rqm_compiler.ops import Operation

    if isinstance(source, CompiledCircuit):
        num_qubits = source.num_qubits
        operations: list[Operation] = [
            Operation.from_descriptor(d) for d in source.descriptors
        ]
    else:
        num_qubits = source.num_qubits
        operations = list(source.operations)

    synthesis_reports: list[dict[str, Any]] = []
    circuit = _build_qiskit_from_ops(
        num_qubits,
        operations,
        target=target,
        synthesis_reports=synthesis_reports,
    )
    if synthesis_reports:
        circuit.metadata = dict(circuit.metadata or {})
        circuit.metadata["rqm_su4_synthesis"] = synthesis_reports
    return (circuit, synthesis_reports) if include_synthesis_report else circuit


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _u1q_unitary_gate(op: "Operation") -> Any:
    """Create the Qiskit gate for one compiler-owned quaternion operation."""

    if op.controls:
        raise ValueError(
            "controlled 'u1q' lowering is unsupported; refusing to drop a "
            "phase that may be observable under coherent control"
        )
    from rqm_core import Quaternion
    from qiskit.circuit.library import UnitaryGate

    params = op.params
    matrix = Quaternion(
        params.get("w", 1.0),
        params.get("x", 0.0),
        params.get("y", 0.0),
        params.get("z", 0.0),
    ).to_su2_matrix()
    # The compiler has already validated the unit quaternion and rqm-core
    # constructs the corresponding SU(2) matrix. Avoid repeating Qiskit's
    # generic matrix validation on this proof-carrying hot path.
    return UnitaryGate(matrix, check_input=False)


def _build_qiskit_from_ops(
    num_qubits: int,
    operations: "list[Operation]",
    *,
    target: Target | None = None,
    synthesis_reports: list[dict[str, Any]] | None = None,
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
        _apply_operation(
            qc,
            op,
            key_to_clbit,
            target=target,
            synthesis_reports=synthesis_reports,
        )

    return qc


def _apply_operation(
    qc: QuantumCircuit,
    op: "Operation",
    key_to_clbit: dict[str, int],
    *,
    target: Target | None = None,
    synthesis_reports: list[dict[str, Any]] | None = None,
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
    elif gate == "rxx":
        qc.rxx(params["angle"], targets[0], targets[1])
    elif gate == "ryy":
        qc.ryy(params["angle"], targets[0], targets[1])
    elif gate == "rzz":
        qc.rzz(params["angle"], targets[0], targets[1])
    elif gate == "su4q":
        from rqm_entanglement import QuaternionCartanBlock
        from rqm_qiskit.synthesis import synthesize_su4_block

        block = QuaternionCartanBlock.from_dict(params["block"])
        selected, report = synthesize_su4_block(
            block,
            target=target,
            strategy="best_native",
            include_report=True,
        )
        fallback_payload = params.get("fallback_operations")
        selected_strategy = "su4q"
        selected_two_qubit_count = sum(
            item.operation.num_qubits == 2 for item in selected.data
        )
        selected_two_qubit_depth = int(
            selected.depth(filter_function=lambda item: item.operation.num_qubits == 2)
            or 0
        )
        source_two_qubit_count: int | None = None
        source_two_qubit_depth: int | None = None
        source_circuit = None
        if isinstance(fallback_payload, list):
            from rqm_compiler.ops import Operation

            pair_map = {physical: local for local, physical in enumerate(targets)}
            fallback_operations = []
            for descriptor in fallback_payload:
                if not isinstance(descriptor, dict):
                    continue
                fallback = Operation.from_descriptor(descriptor)
                fallback.targets = [pair_map[index] for index in fallback.targets]
                fallback.controls = [pair_map[index] for index in fallback.controls]
                fallback_operations.append(fallback)
            source_circuit = _build_qiskit_from_ops(
                2,
                fallback_operations,
                target=target,
                synthesis_reports=None,
            )
            source_two_qubit_count = sum(
                item.operation.num_qubits == 2 for item in source_circuit.data
            )
            source_two_qubit_depth = int(
                source_circuit.depth(
                    filter_function=lambda item: item.operation.num_qubits == 2
                )
                or 0
            )
            improves = (
                selected_two_qubit_count < source_two_qubit_count
                or selected_two_qubit_depth < source_two_qubit_depth
            )
            if not improves:
                selected_strategy = "source_window"
                selected = source_circuit
                selected_two_qubit_count = source_two_qubit_count
                selected_two_qubit_depth = source_two_qubit_depth
        qc.compose(selected, qubits=targets, inplace=True)
        routing = params.get("routing")
        report["source_hash"] = (
            routing.get("source_hash")
            if isinstance(routing, dict)
            else block.source_hash
        )
        report["window_id"] = (
            routing.get("window_id") if isinstance(routing, dict) else None
        )
        report["selected_strategy"] = selected_strategy
        report["source_two_qubit_count"] = source_two_qubit_count
        report["source_two_qubit_depth"] = source_two_qubit_depth
        report["selected_two_qubit_count"] = selected_two_qubit_count
        report["selected_two_qubit_depth"] = selected_two_qubit_depth
        report["actual_two_qubit_count_reduction"] = (
            None
            if source_two_qubit_count is None
            else max(0, source_two_qubit_count - selected_two_qubit_count)
        )
        if synthesis_reports is not None:
            synthesis_reports.append(report)
    elif gate == "measure":
        key = params.get("key", f"m{targets[0]}")
        qc.measure(targets[0], key_to_clbit[key])
    elif gate == "u1q":
        qc.append(_u1q_unitary_gate(op), [targets[0]])
    elif gate == "barrier":
        if targets:
            qc.barrier(targets)
        else:
            qc.barrier()
    else:
        from rqm_qiskit.errors import TranslationError

        raise TranslationError(
            f"Unsupported compiler operation {gate!r}; refusing to omit it."
        )


# ---------------------------------------------------------------------------
# Convenience wrappers (thin; preserved for public API compatibility)
# ---------------------------------------------------------------------------


def state_to_quantum_circuit(state: RQMState) -> QuantumCircuit:
    """Convert an :class:`~rqm_qiskit.RQMState` to a 1-qubit QuantumCircuit.

    The returned circuit uses Qiskit's ``initialize`` instruction to
    prepare the qubit in the given state.

    .. note::
        This helper intentionally does **not** route through
        :func:`compiled_circuit_to_qiskit`.  Qiskit's ``initialize``
        instruction is not represented in the rqm-compiler IR, so state
        preparation is inherently Qiskit-specific and cannot be expressed
        as a canonical ``rqm_compiler.Operation``.

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

    Routing
    -------
    This helper converts ``gate`` to an :class:`rqm_compiler.Operation` via
    :meth:`~rqm_qiskit.RQMGate.to_operation`, wraps it in a 1-qubit
    :class:`rqm_compiler.Circuit`, and lowers it through
    :func:`compiled_circuit_to_qiskit`.  There is no separate Qiskit
    gate-construction path.

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
    from rqm_compiler import Circuit

    c = Circuit(1)
    c.add(gate.to_operation(qubit=0))
    return compiled_circuit_to_qiskit(c)
