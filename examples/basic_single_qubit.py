"""
basic_single_qubit.py – Quickstart example: prepare |+>, rotate, measure.

Run with:
    python examples/basic_single_qubit.py
"""

import math

from rqm_qiskit import RQMState, RQMGate, RQMCircuit, format_counts_summary
from rqm_qiskit.ibm import run_on_aer_sampler


def main() -> None:
    # 1. Create the |+> state.
    state = RQMState.plus()
    print("Initial state:")
    print(" ", state.pretty())
    print()

    # 2. Define a rotation gate: R_y(π/4).
    gate = RQMGate.ry(math.pi / 4)
    print("Gate to apply:")
    print(" ", gate.pretty())
    print()

    # 3. Build and draw the circuit.
    circ = RQMCircuit(1)
    circ.prepare_state(state)
    circ.apply_gate(gate)
    circ.measure_all()

    print("Circuit:")
    print(circ.draw_text())
    print()

    # 4. Run on the local Aer simulator.
    qc = circ.to_qiskit()
    counts = run_on_aer_sampler(qc, shots=2048)

    print(format_counts_summary(counts))


if __name__ == "__main__":
    main()
