"""
bloch_vs_quaternion_demo.py – Compare Bloch-vector and quaternion descriptions
of the same qubit rotation.

The Bloch vector gives a 3-vector on the unit sphere.
The quaternion gives the rotation operator that moves the state.
Both describe the same physical information, but the quaternion form
composes rotations more naturally via multiplication.

Run with:
    python examples/bloch_vs_quaternion_demo.py
"""

import math

import numpy as np

from rqm_qiskit import RQMState, RQMGate


def apply_gate_to_state(state: RQMState, gate: RQMGate) -> RQMState:
    """Apply a gate matrix to a state and return the resulting RQMState."""
    mat = gate.to_matrix()
    vec = np.array([state.alpha, state.beta])
    new_vec = mat @ vec
    return RQMState(new_vec[0], new_vec[1])


def show_state_comparison(label: str, state: RQMState) -> None:
    """Print both Bloch-vector and quaternion representations side by side."""
    bv = state.bloch_vector()
    q = state.to_quaternion()
    print(f"  {label}")
    print(
        f"    Bloch vector: x={bv[0]:+.4f}  y={bv[1]:+.4f}  z={bv[2]:+.4f}"
    )
    print(f"    Quaternion:   {q.pretty()}")


def main() -> None:
    print("=" * 60)
    print("  Bloch Vector vs. Quaternion Representation")
    print("=" * 60)
    print()

    # ------------------------------------------------------------------ #
    # Demo 1: Start from |0>, rotate with R_y(π/2) toward the equator.
    # ------------------------------------------------------------------ #
    print("Demo 1: R_y(π/2) applied to |0>")
    print("─" * 40)
    gate = RQMGate.ry(math.pi / 2)
    print(f"  Gate: {gate.pretty()}")
    print(f"  Gate quaternion: {gate.quaternion.pretty()}")
    print()

    state_before = RQMState.zero()
    state_after = apply_gate_to_state(state_before, gate)

    show_state_comparison("Before:", state_before)
    show_state_comparison("After: ", state_after)
    print()

    # ------------------------------------------------------------------ #
    # Demo 2: Equatorial rotation — R_z(π) maps |+> to |-> on Bloch sphere.
    # ------------------------------------------------------------------ #
    print("Demo 2: R_z(π) applied to |+>")
    print("─" * 40)
    gate2 = RQMGate.rz(math.pi)
    print(f"  Gate: {gate2.pretty()}")
    print(f"  Gate quaternion: {gate2.quaternion.pretty()}")
    print()

    state2_before = RQMState.plus()
    state2_after = apply_gate_to_state(state2_before, gate2)

    show_state_comparison("Before:", state2_before)
    show_state_comparison("After: ", state2_after)
    print("  (|+> at Bloch x=+1 → |-> at Bloch x=−1, up to global phase)")
    print()

    # ------------------------------------------------------------------ #
    # Demo 3: Quaternion composition of two rotations.
    # ------------------------------------------------------------------ #
    print("Demo 3: Composing R_x(π/2) followed by R_z(π/2) via quaternions")
    print("─" * 40)

    gate_x = RQMGate.rx(math.pi / 2)
    gate_z = RQMGate.rz(math.pi / 2)
    q_composed = gate_z.quaternion * gate_x.quaternion  # apply Rx first, then Rz

    state3 = RQMState.from_bloch(math.pi / 3, math.pi / 4)
    state3_seq = apply_gate_to_state(
        apply_gate_to_state(state3, gate_x), gate_z
    )
    state3_via_q = RQMState(
        *(q_composed.to_su2_matrix() @ np.array([state3.alpha, state3.beta]))
    )

    print(f"  Starting state: {state3.pretty()}")
    show_state_comparison("After sequential gates:", state3_seq)
    show_state_comparison("After composed quaternion:", state3_via_q)
    print(
        f"  Bloch vectors match: "
        f"{np.allclose(state3_seq.bloch_vector(), state3_via_q.bloch_vector(), atol=1e-10)}"
    )
    print()

    # ------------------------------------------------------------------ #
    # Demo 4: Bloch-angle state with Bloch vector and quaternion printed.
    # ------------------------------------------------------------------ #
    print("Demo 4: A general Bloch-angle state (θ=π/3, φ=π/4)")
    print("─" * 40)
    theta = math.pi / 3
    phi = math.pi / 4
    state4 = RQMState.from_bloch(theta, phi)
    show_state_comparison(
        f"State (θ={math.degrees(theta):.0f}°, φ={math.degrees(phi):.0f}°):",
        state4,
    )


if __name__ == "__main__":
    main()
