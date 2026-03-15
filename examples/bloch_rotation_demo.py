"""
bloch_rotation_demo.py – Show Bloch vectors before and after a gate.

Run with:
    python examples/bloch_rotation_demo.py
"""

import math

from rqm_qiskit import RQMState, RQMGate
from rqm_qiskit.circuit import RQMCircuit


def apply_gate_to_state(state: RQMState, gate: RQMGate) -> RQMState:
    """Apply a gate matrix to a state and return the resulting RQMState."""
    import numpy as np

    mat = gate.to_matrix()
    vec = np.array([state.alpha, state.beta])
    new_vec = mat @ vec
    return RQMState(new_vec[0], new_vec[1])


def print_bloch(label: str, state: RQMState) -> None:
    x, y, z = state.bloch_vector()
    print(f"  {label}")
    print(f"    {state.pretty()}")
    print(f"    Bloch vector: x={x:+.4f}  y={y:+.4f}  z={z:+.4f}")


def main() -> None:
    print("=== Bloch Rotation Demo ===\n")

    # 1. Create a state from Bloch angles (theta=pi/3, phi=pi/4).
    theta = math.pi / 3
    phi = math.pi / 4
    state = RQMState.from_bloch(theta, phi)
    print(f"Starting state (theta={math.degrees(theta):.1f}°, phi={math.degrees(phi):.1f}°):")
    print_bloch("Before gate", state)
    print()

    # 2. Apply R_y(pi/2) rotation.
    gate = RQMGate.ry(math.pi / 2)
    print(f"Applying: {gate.pretty()}")
    rotated = apply_gate_to_state(state, gate)
    print_bloch("After gate ", rotated)
    print()

    # 3. Apply R_z(pi) rotation on |+>.
    state2 = RQMState.plus()
    gate2 = RQMGate.rz(math.pi)
    print("Starting state: |+>")
    print_bloch("Before R_z(π)", state2)
    print()
    print(f"Applying: {gate2.pretty()}")
    rotated2 = apply_gate_to_state(state2, gate2)
    print_bloch("After  R_z(π)", rotated2)
    print()
    print("(|+> rotated by R_z(π) should become |-> up to global phase)\n")

    # 4. Show the text circuit.
    circ = RQMCircuit(1)
    circ.prepare_state(state)
    circ.apply_gate(gate)
    print("Circuit diagram:")
    print(circ.draw_text())


if __name__ == "__main__":
    main()
