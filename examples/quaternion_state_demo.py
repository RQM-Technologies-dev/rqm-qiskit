"""
quaternion_state_demo.py – Show the quaternion representation of qubit states.

Every normalized 1-qubit state |psi> = alpha|0> + beta|1> corresponds to a unit
quaternion that encodes the SU(2) rotation taking |0> to |psi>.

This demo makes that correspondence concrete.

Run with:
    python examples/quaternion_state_demo.py
"""

import math

from rqm_qiskit import Quaternion, RQMState, RQMGate


def show_state(label: str, state: RQMState) -> None:
    """Print state info alongside its quaternion representation."""
    q = state.to_quaternion()
    bv = state.bloch_vector()
    print(f"  State:       {state.pretty()}")
    print(f"  Quaternion:  {q.pretty()}")
    print(
        f"  Bloch:       x={bv[0]:+.4f}  y={bv[1]:+.4f}  z={bv[2]:+.4f}"
    )
    print()


def main() -> None:
    print("=" * 58)
    print("  Qubit States as Unit Quaternions")
    print("=" * 58)
    print()
    print("Every 1-qubit state |psi> = alpha|0> + beta|1> maps to")
    print("a unit quaternion q such that:")
    print("  q.to_su2_matrix() @ |0>  =  |psi>")
    print()
    print("─" * 58)

    # Standard basis states.
    print("Standard basis states:")
    show_state("|0>", RQMState.zero())
    show_state("|1>", RQMState.one())

    print("Equatorial (Hadamard) states:")
    show_state("|+>", RQMState.plus())
    show_state("|->", RQMState.minus())

    print("Bloch-angle state  (θ=π/3, φ=π/4):")
    show_state("Bloch(π/3, π/4)", RQMState.from_bloch(math.pi / 3, math.pi / 4))

    # Show quaternion multiplication representing gate application.
    print("=" * 58)
    print("  Quaternion composition = rotation composition")
    print("=" * 58)
    print()
    print("Applying R_y(π/2) then R_z(π/4) can be composed as")
    print("a single quaternion product:  q_total = q_z * q_y")
    print()

    gate_y = RQMGate.ry(math.pi / 2)
    gate_z = RQMGate.rz(math.pi / 4)

    q_y = gate_y.quaternion
    q_z = gate_z.quaternion
    q_total = q_z * q_y  # right-to-left: apply Ry first, then Rz

    print(f"  q_y  = {q_y.pretty()}")
    print(f"  q_z  = {q_z.pretty()}")
    print(f"  q_z * q_y = {q_total.pretty()}")
    print()

    # Verify: apply both gates sequentially to |0> and compare.
    import numpy as np

    state_0 = np.array([1.0, 0.0])
    sequential = gate_z.to_matrix() @ gate_y.to_matrix() @ state_0
    composed = q_total.to_su2_matrix() @ state_0

    print("Verification (should match):")
    print(f"  Sequential gate application: {sequential}")
    print(f"  Quaternion product matrix:   {composed}")
    print(
        f"  Results match: {np.allclose(sequential, composed, atol=1e-12)}"
    )


if __name__ == "__main__":
    main()
