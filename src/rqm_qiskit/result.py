"""
result.py – QiskitResult: structured wrapper for quantum measurement results.

Provides a minimal, consistent interface for accessing measurement outcomes
returned by Qiskit backends and simulators.
"""

from __future__ import annotations


class QiskitResult:
    """Structured result from a quantum circuit execution.

    Wraps the raw ``{bitstring: count}`` dictionary returned by Qiskit
    samplers and exposes counts, shot totals, probabilities, and the
    most-likely bitstring.

    Parameters
    ----------
    counts:
        Mapping of bitstring → count, e.g. ``{"00": 512, "11": 512}``.
    shots:
        Total number of shots (inferred from ``counts`` if not provided).

    Examples
    --------
    >>> result = QiskitResult({"00": 512, "11": 512})
    >>> result.most_likely_bitstring()
    '00'
    >>> result.probabilities["00"]
    0.5
    """

    def __init__(
        self,
        counts: "dict[str, int]",
        shots: "int | None" = None,
    ) -> None:
        if not counts:
            raise ValueError("counts dictionary must not be empty.")
        self._counts: dict[str, int] = dict(counts)
        self._shots: int = shots if shots is not None else sum(counts.values())

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def counts(self) -> "dict[str, int]":
        """Raw bitstring → count mapping."""
        return self._counts

    @property
    def shots(self) -> int:
        """Total number of measurement shots."""
        return self._shots

    @property
    def probabilities(self) -> "dict[str, float]":
        """Bitstring → estimated probability mapping.

        Computed as ``count / shots`` for each bitstring.
        """
        return {bs: c / self._shots for bs, c in self._counts.items()}

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def most_likely_bitstring(self) -> str:
        """Return the bitstring with the highest count.

        Returns
        -------
        str
            The most frequently measured bitstring.
        """
        return max(self._counts, key=lambda k: self._counts[k])

    def to_dict(self, backend: str = "qiskit") -> "dict":
        """Return a standardized, API-ready result dictionary.

        The returned dictionary is JSON-serializable and follows the
        canonical RQM result format required for API compatibility:

        .. code-block:: python

            {
                "counts": {"00": 512, "11": 512},
                "shots": 1024,
                "backend": "qiskit",
                "metadata": {"outcomes": 2},
            }

        Parameters
        ----------
        backend:
            Backend identifier string to include in the result
            (default ``"qiskit"``).

        Returns
        -------
        dict
            JSON-serializable result mapping.
        """
        return {
            "counts": dict(self._counts),
            "shots": self._shots,
            "backend": backend,
            "metadata": {
                "outcomes": len(self._counts),
                "most_likely": self.most_likely_bitstring(),
            },
        }

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"QiskitResult(shots={self._shots}, "
            f"outcomes={len(self._counts)}, "
            f"most_likely={self.most_likely_bitstring()!r})"
        )
