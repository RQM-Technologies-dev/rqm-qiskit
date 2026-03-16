"""
state.py – RQMState: a normalized 1-qubit quantum state.

Internally stores the state as (alpha, beta) in the computational basis:
    |psi> = alpha|0> + beta|1>

All states are normalized automatically on construction.  Bloch-sphere
conversions and spinor-to-quaternion mapping delegate to rqm-core.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from rqm_core.bloch import state_to_bloch
from rqm_core.spinor import normalize_spinor, spinor_norm, spinor_to_quaternion

if TYPE_CHECKING:
    from qiskit.quantum_info import Statevector
    from rqm_qiskit.quaternion import Quaternion


class RQMState:
    """A normalized 1-qubit quantum state in the computational basis.

    The state is represented as:
        |psi> = alpha|0> + beta|1>

    Normalization is enforced automatically.  A ``ValueError`` is raised
    if the supplied amplitudes have zero (or near-zero) norm.
    """

    _NORM_TOLERANCE: float = 1e-10

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, alpha: complex, beta: complex) -> None:
        """Create an RQMState from raw amplitudes.

        Parameters
        ----------
        alpha:
            Amplitude for |0>.
        beta:
            Amplitude for |1>.

        Raises
        ------
        ValueError
            If the norm is zero or either amplitude is not a finite number.
        """
        alpha = complex(alpha)
        beta = complex(beta)

        norm = spinor_norm(alpha, beta)
        if norm < self._NORM_TOLERANCE:
            raise ValueError(
                "Cannot create an RQMState with zero norm. "
                "At least one amplitude must be non-zero."
            )

        self._alpha, self._beta = normalize_spinor(alpha, beta)

    @classmethod
    def from_bloch(cls, theta: float, phi: float) -> "RQMState":
        """Create a state from Bloch-sphere angles.

        The standard parameterization is:
            |psi> = cos(theta/2)|0> + e^{i*phi} * sin(theta/2)|1>

        Parameters
        ----------
        theta:
            Polar angle in radians (0 = |0>, pi = |1>).
        phi:
            Azimuthal angle in radians.
        """
        from rqm_core.bloch import bloch_to_state

        alpha, beta = bloch_to_state(theta, phi)
        return cls(alpha, beta)

    @classmethod
    def zero(cls) -> "RQMState":
        """Return the |0> computational basis state."""
        return cls(1.0, 0.0)

    @classmethod
    def one(cls) -> "RQMState":
        """Return the |1> computational basis state."""
        return cls(0.0, 1.0)

    @classmethod
    def plus(cls) -> "RQMState":
        """Return the |+> = (|0> + |1>) / sqrt(2) state."""
        s = 1.0 / math.sqrt(2)
        return cls(s, s)

    @classmethod
    def minus(cls) -> "RQMState":
        """Return the |-> = (|0> - |1>) / sqrt(2) state."""
        s = 1.0 / math.sqrt(2)
        return cls(s, -s)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def alpha(self) -> complex:
        """Amplitude for |0>."""
        return self._alpha

    @property
    def beta(self) -> complex:
        """Amplitude for |1>."""
        return self._beta

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def vector(self) -> tuple[complex, complex]:
        """Return the state as a (alpha, beta) tuple."""
        return (self._alpha, self._beta)

    def norm(self) -> float:
        """Return the norm of the state vector (always 1.0 after normalization)."""
        return spinor_norm(self._alpha, self._beta)

    def bloch_vector(self) -> tuple[float, float, float]:
        """Return the Bloch-sphere Cartesian coordinates (x, y, z).

        For a pure state |psi> = alpha|0> + beta|1>:
            x = 2 * Re(conj(alpha) * beta)
            y = 2 * Im(conj(alpha) * beta)
            z = |alpha|^2 - |beta|^2

        Delegates to :func:`rqm_core.bloch.state_to_bloch`.
        """
        return state_to_bloch(self._alpha, self._beta)

    def as_qiskit_statevector(self) -> "Statevector":
        """Return the state as a Qiskit :class:`~qiskit.quantum_info.Statevector`."""
        from qiskit.quantum_info import Statevector

        return Statevector([self._alpha, self._beta])

    def to_quaternion(self) -> "Quaternion":
        """Return the unit quaternion representing the rotation that prepares this state from |0>.

        Delegates to :func:`rqm_core.spinor.spinor_to_quaternion` and
        wraps the result in the rqm-qiskit :class:`~rqm_qiskit.Quaternion`
        bridge type for full API compatibility.

        Returns
        -------
        :class:`~rqm_qiskit.Quaternion`
            A unit quaternion.
        """
        from rqm_qiskit.quaternion import Quaternion

        core_q = spinor_to_quaternion(self._alpha, self._beta)
        return Quaternion(core_q.w, core_q.x, core_q.y, core_q.z)

    def pretty(self) -> str:
        """Return a human-readable string representation of the state."""

        def _fmt(c: complex) -> str:
            if c.imag == 0.0:
                return f"{c.real:.4f}"
            if c.real == 0.0:
                return f"{c.imag:.4f}j"
            return f"({c.real:.4f}{c.imag:+.4f}j)"

        bv = self.bloch_vector()
        return (
            f"RQMState |psi> = {_fmt(self._alpha)}|0> + {_fmt(self._beta)}|1>  "
            f"[Bloch: x={bv[0]:.4f}, y={bv[1]:.4f}, z={bv[2]:.4f}]"
        )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"RQMState(alpha={self._alpha!r}, beta={self._beta!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RQMState):
            return NotImplemented
        return np.isclose(self._alpha, other._alpha) and np.isclose(
            self._beta, other._beta
        )
