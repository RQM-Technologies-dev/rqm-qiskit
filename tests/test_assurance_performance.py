from __future__ import annotations

import statistics
import time

from qiskit import QuantumCircuit, qasm3

from rqm_qiskit import analyze_qiskit_circuit
from rqm_qiskit.cli import main as cli_main


def _p95(samples: list[float]) -> float:
    return sorted(samples)[max(0, int(len(samples) * 0.95) - 1)]


def test_direct_explanation_meets_absolute_responsiveness_gate() -> None:
    one_qubit = QuantumCircuit(1)
    one_qubit.rz(0.31, 0)
    one_qubit.ry(-0.47, 0)
    one_qubit.rz(0.83, 0)
    two_qubit = QuantumCircuit(2)
    two_qubit.h(0)
    two_qubit.cx(0, 1)
    circuits = [one_qubit, two_qubit]

    for circuit in circuits:
        assert analyze_qiskit_circuit(circuit).status == "complete"

    samples = []
    for index in range(40):
        start = time.perf_counter_ns()
        report = analyze_qiskit_circuit(circuits[index % len(circuits)])
        report.to_text("standard")
        samples.append((time.perf_counter_ns() - start) / 1_000_000)

    assert _p95(samples) <= 50.0, f"direct p95={_p95(samples):.3f} ms"


def test_openqasm_cli_explanation_meets_absolute_responsiveness_gate(tmp_path) -> None:
    circuit = QuantumCircuit(1)
    circuit.ry(0.42, 0)
    source = tmp_path / "input.qasm"
    source.write_text(qasm3.dumps(circuit), encoding="utf-8")

    assert (
        cli_main(["explain", str(source), "--output", str(tmp_path / "warm.md")]) == 0
    )
    samples = []
    for index in range(20):
        start = time.perf_counter_ns()
        assert (
            cli_main(
                ["explain", str(source), "--output", str(tmp_path / f"run-{index}.md")]
            )
            == 0
        )
        samples.append((time.perf_counter_ns() - start) / 1_000_000)

    assert _p95(samples) <= 100.0, f"OpenQASM CLI p95={_p95(samples):.3f} ms"
    assert statistics.median(samples) <= _p95(samples)
