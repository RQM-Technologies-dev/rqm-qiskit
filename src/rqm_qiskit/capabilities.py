"""Qiskit target capabilities expressed as compiler-owned cost data."""

from __future__ import annotations

from qiskit.transpiler import Target

from rqm_compiler import TwoQubitCostModel


def qiskit_two_qubit_cost_model(target: Target | None = None) -> TwoQubitCostModel:
    """Return a pure-data cost model for adaptive compiler routing."""
    reference = dict(TwoQubitCostModel().gate_costs)
    if target is None:
        return TwoQubitCostModel()
    for name in tuple(reference):
        if name in target.operation_names:
            reference[name] = 1
    return TwoQubitCostModel(
        name="qiskit_target",
        gate_costs=tuple(sorted(reference.items())),
        generic_su4_ceiling=6,
    )

