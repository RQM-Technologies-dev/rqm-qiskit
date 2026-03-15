"""
simulator_counts_demo.py – Run a Bell-like 1-qubit circuit on the Aer simulator.

Run with:
    python examples/simulator_counts_demo.py
"""

import math

from rqm_qiskit import RQMState, RQMGate, RQMCircuit, format_counts_summary
from rqm_qiskit.ibm import run_on_aer_sampler


def main() -> None:
    print("=== Simulator Counts Demo ===\n")

    # Demo 1: Hadamard-like state (|+>) measured in Z basis.
    print("Demo 1: Prepare |+> and measure")
    print("─" * 40)
    circ1 = RQMCircuit(1)
    circ1.prepare_state(RQMState.plus())
    circ1.measure_all()

    counts1 = run_on_aer_sampler(circ1.to_qiskit(), shots=2048)
    print(format_counts_summary(counts1))
    print("(Expected: ~50% |0>, ~50% |1>)\n")

    # Demo 2: |0> rotated by R_y(π) should give |1> deterministically.
    print("Demo 2: Prepare |0>, apply R_y(π), and measure")
    print("─" * 40)
    circ2 = RQMCircuit(1)
    circ2.prepare_state(RQMState.zero())
    circ2.apply_gate(RQMGate.ry(math.pi))
    circ2.measure_all()

    counts2 = run_on_aer_sampler(circ2.to_qiskit(), shots=1024)
    print(format_counts_summary(counts2))
    print("(Expected: ~100% |1>)\n")

    # Demo 3: Biased state using Bloch angles.
    print("Demo 3: Prepare state biased toward |0> (theta=π/4) and measure")
    print("─" * 40)
    circ3 = RQMCircuit(1)
    circ3.prepare_state(RQMState.from_bloch(math.pi / 4, 0.0))
    circ3.measure_all()

    counts3 = run_on_aer_sampler(circ3.to_qiskit(), shots=4096)
    print(format_counts_summary(counts3))
    print("(Expected: ~85% |0>, ~15% |1>)\n")


if __name__ == "__main__":
    main()
