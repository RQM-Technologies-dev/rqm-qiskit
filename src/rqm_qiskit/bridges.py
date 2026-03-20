"""
bridges.py – Convenience bridge functions that delegate to rqm-core.

These thin wrappers make it easy to prepare qubits directly from spinor
amplitudes or Bloch-sphere angles without constructing intermediate objects.

All physics / math (Bloch conversions, spinor normalization) is delegated
to rqm-core.  The only Qiskit-specific logic here is mapping (θ, φ) → gates.

Functions
---------
- ``spinor_to_circuit`` : spinor (α, β) → QuantumCircuit via rqm-core Bloch math
- ``bloch_to_circuit``  : Bloch angles (θ, φ) → QuantumCircuit via RY(θ) RZ(φ)
- ``quaternion_to_circuit`` : raises NotImplementedError (SU(2) decomposition
  belongs in rqm-core, not here)
"""

from __future__ import annotations

import math

from qiskit import QuantumCircuit


def spinor_to_circuit(
    alpha: complex,
    beta: complex,
    target: int = 0,
) -> QuantumCircuit:
    """Prepare a qubit in the state (α, β) using RY(θ) RZ(φ) gates.

    Delegates Bloch conversion to :func:`rqm_core.bloch.state_to_bloch`
    (via :func:`rqm_core.spinor.normalize_spinor`), then maps the result
    to Qiskit rotation gates.

    The Bloch-sphere angles are derived from the Cartesian Bloch vector
    ``(x, y, z)`` returned by rqm-core:

    * ``θ = arccos(z)``
    * ``φ = arctan2(y, x)``

    Parameters
    ----------
    alpha:
        Amplitude for |0⟩ (may be unnormalized).
    beta:
        Amplitude for |1⟩ (may be unnormalized).
    target:
        Target qubit index in the returned circuit (default 0).

    Returns
    -------
    qiskit.QuantumCircuit
        A circuit that prepares qubit ``target`` in state (α, β).

    Raises
    ------
    ValueError
        If the spinor is zero (no valid state).
    """
    from rqm_core.spinor import spinor_norm, normalize_spinor
    from rqm_core.bloch import state_to_bloch

    norm = spinor_norm(alpha, beta)
    if norm < 1e-10:
        raise ValueError("Cannot prepare zero spinor: at least one amplitude must be non-zero.")
    a, b = normalize_spinor(alpha, beta)

    # Delegate Bloch conversion to rqm-core
    bx, by, bz = state_to_bloch(a, b)

    # Convert Cartesian Bloch vector to spherical angles
    # θ = arccos(z), φ = arctan2(y, x)
    bz_clamped = max(-1.0, min(1.0, float(bz)))
    theta = math.acos(bz_clamped)
    phi = math.atan2(float(by), float(bx))

    return bloch_to_circuit(theta, phi, target=target)


def bloch_to_circuit(
    theta: float,
    phi: float,
    target: int = 0,
) -> QuantumCircuit:
    """Prepare a qubit at Bloch angles (θ, φ) using RY(θ) RZ(φ) gates.

    Maps the standard Bloch parameterization directly to Qiskit rotation
    gates without any local Bloch math:

    * RY(θ) sets the polar angle
    * RZ(φ) sets the azimuthal angle

    Parameters
    ----------
    theta:
        Polar angle in radians (0 = |0⟩, π = |1⟩).
    phi:
        Azimuthal angle in radians.
    target:
        Target qubit index in the returned circuit (default 0).

    Returns
    -------
    qiskit.QuantumCircuit
        A circuit with RY(θ) and RZ(φ) applied to qubit ``target``.
    """
    num_qubits = target + 1
    qc = QuantumCircuit(num_qubits)
    qc.ry(theta, target)
    qc.rz(phi, target)
    return qc


def quaternion_to_circuit(target: int = 0) -> QuantumCircuit:
    """[NOT IMPLEMENTED] Convert a quaternion to a Qiskit QuantumCircuit.

    SU(2) decomposition belongs in rqm-core, not in the rqm-qiskit bridge
    layer.  This function will always raise :exc:`NotImplementedError`.

    Raises
    ------
    NotImplementedError
        Always – SU(2) decomposition belongs in rqm-core.
    """
    raise NotImplementedError(
        "SU(2) decomposition belongs in rqm-core. "
        "quaternion_to_circuit() is not implemented in rqm-qiskit. "
        "Use rqm-core when SU(2) → gate decomposition is available."
    )
