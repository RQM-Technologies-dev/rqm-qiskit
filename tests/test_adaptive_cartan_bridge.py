from qiskit.quantum_info import Operator

from rqm_compiler import (
    AdaptiveCartanPolicy,
    Circuit,
    CompilationWorkBudget,
)
from rqm_qiskit import qiskit_two_qubit_cost_model, to_qiskit_circuit


def _source() -> Circuit:
    circuit = Circuit(2)
    for index in range(9):
        circuit.rzz(0, 1, 0.13 + 0.01 * index)
        circuit.rx(0, 0.02 * (index + 1))
    return circuit


def test_target_cost_model_is_pure_compiler_data() -> None:
    model = qiskit_two_qubit_cost_model()
    assert model.name == "cx_reference"
    assert model.generic_su4_ceiling == 6


def test_adaptive_bridge_reports_actual_source_comparison() -> None:
    source = _source()
    policy = AdaptiveCartanPolicy(
        mode="selective",
        budget=CompilationWorkBudget(1, 64),
    )
    original = to_qiskit_circuit(source)
    optimized, report = to_qiskit_circuit(
        source,
        optimize=True,
        include_report=True,
        include_synthesis_report=True,
        adaptive_policy=policy,
    )
    assert Operator(original).equiv(Operator(optimized))
    synthesis = report["synthesis_reports"]
    assert len(synthesis) == 1
    assert synthesis[0]["selected_strategy"] in {"su4q", "source_window"}
    assert synthesis[0]["source_two_qubit_count"] == 9
    if synthesis[0]["selected_strategy"] == "su4q":
        assert synthesis[0]["actual_two_qubit_count_reduction"] > 0
