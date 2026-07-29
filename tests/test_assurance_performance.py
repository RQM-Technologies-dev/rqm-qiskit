from __future__ import annotations

import statistics
import time

from qiskit import QuantumCircuit, qasm3
from qiskit.quantum_info import Operator
from rqm_compiler import optimize_circuit

from rqm_qiskit import export_openqasm3, import_qiskit_circuit


def _representative_circuits() -> list[QuantumCircuit]:
    circuits: list[QuantumCircuit] = []
    for index in range(12):
        circuit = QuantumCircuit(3)
        circuit.rx(0.01 * (index + 1), 0)
        circuit.ry(-0.02 * (index + 1), 1)
        circuit.rz(0.03 * (index + 1), 2)
        circuit.cx(0, 1)
        circuit.iswap(1, 2)
        circuit.rxx(0.04 * (index + 1), 0, 2)
        circuit.ryy(-0.05 * (index + 1), 1, 2)
        circuit.rzz(0.06 * (index + 1), 0, 1)
        circuits.append(circuit)
    return circuits


def test_hot_adapter_path_stays_below_regression_ceiling() -> None:
    """Protect the latency hardening without pretending CI proves the release gate."""

    circuits = _representative_circuits()
    warm_import = import_qiskit_circuit(circuits[0])
    assert warm_import.circuit is not None
    warm_returned, _ = optimize_circuit(warm_import.circuit)
    assert export_openqasm3(warm_returned).status == "EXPORTED"

    ratios: list[float] = []
    for circuit in circuits:
        start = time.perf_counter_ns()
        imported = import_qiskit_circuit(circuit)
        after_import = time.perf_counter_ns()
        assert imported.circuit is not None

        returned, report = optimize_circuit(imported.circuit)
        after_compiler = time.perf_counter_ns()
        exported = export_openqasm3(returned)
        after_export = time.perf_counter_ns()

        assert report.equivalence_status == "VERIFIED"
        assert exported.status == "EXPORTED"
        assert exported.source is not None
        reparsed = qasm3.loads(exported.source)
        assert Operator(circuit).equiv(Operator(reparsed))

        compiler_ns = after_compiler - after_import
        adapter_ns = (after_import - start) + (after_export - after_compiler)
        ratios.append(adapter_ns / compiler_ns)

    # This is a broad cross-run regression ceiling, not the frozen 25% release
    # gate. The release verdict comes only from the preregistered 160-case run.
    assert statistics.median(ratios) <= 4.0
