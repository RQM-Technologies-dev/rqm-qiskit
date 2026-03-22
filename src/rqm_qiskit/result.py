"""
result.py – QiskitResult: structured wrapper for quantum measurement results.

Provides a minimal, consistent interface for accessing measurement outcomes
returned by Qiskit backends and simulators.  Supports JSON serialization and
deserialization for result caching in databases or the RQM API.
"""

from __future__ import annotations

import datetime
import json


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
    job_id:
        Optional job identifier, included in :meth:`to_dict` output.
    timestamp:
        Optional UTC timestamp (ISO 8601 string or :class:`datetime.datetime`).
        Defaults to the current UTC time when the result is created.

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
        *,
        job_id: "str | None" = None,
        timestamp: "str | datetime.datetime | None" = None,
    ) -> None:
        if not counts:
            raise ValueError("counts dictionary must not be empty.")
        self._counts: dict[str, int] = dict(counts)
        self._shots: int = shots if shots is not None else sum(counts.values())
        self._job_id = job_id
        if timestamp is None:
            self._timestamp = datetime.datetime.now(datetime.timezone.utc)
        elif isinstance(timestamp, str):
            self._timestamp = datetime.datetime.fromisoformat(timestamp)
        else:
            self._timestamp = timestamp

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
    def job_id(self) -> "str | None":
        """Job identifier, if available."""
        return self._job_id

    @property
    def timestamp(self) -> datetime.datetime:
        """UTC timestamp when this result was created."""
        return self._timestamp

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

    def to_dict(
        self,
        backend: str = "qiskit",
        *,
        job_id: "str | None" = None,
        include_timestamp: bool = True,
    ) -> "dict":
        """Return a standardized, API-ready result dictionary.

        The returned dictionary is JSON-serializable and follows the
        canonical RQM result format required for API compatibility:

        .. code-block:: python

            {
                "counts": {"00": 512, "11": 512},
                "shots": 1024,
                "backend": "qiskit",
                "metadata": {
                    "outcomes": 2,
                    "most_likely": "00",
                    "job_id": "local-abc123",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                },
            }

        Parameters
        ----------
        backend:
            Backend identifier string to include in the result
            (default ``"qiskit"``).
        job_id:
            Override the job identifier in the metadata.  Falls back to
            ``self.job_id`` if not provided.
        include_timestamp:
            If ``True`` (default), include the ``timestamp`` field in
            the metadata dict.

        Returns
        -------
        dict
            JSON-serializable result mapping.
        """
        resolved_job_id = job_id if job_id is not None else self._job_id
        metadata: dict = {
            "outcomes": len(self._counts),
            "most_likely": self.most_likely_bitstring(),
        }
        if resolved_job_id is not None:
            metadata["job_id"] = resolved_job_id
        if include_timestamp:
            metadata["timestamp"] = self._timestamp.isoformat()
        return {
            "counts": dict(self._counts),
            "shots": self._shots,
            "backend": backend,
            "metadata": metadata,
        }

    def to_json(self, backend: str = "qiskit", **kwargs) -> str:
        """Serialize this result to a JSON string.

        Convenience wrapper around :meth:`to_dict` + :func:`json.dumps`.

        Parameters
        ----------
        backend:
            Backend identifier passed to :meth:`to_dict`.
        **kwargs:
            Additional keyword arguments forwarded to :meth:`to_dict`.

        Returns
        -------
        str
            JSON string.
        """
        return json.dumps(self.to_dict(backend=backend, **kwargs))

    @classmethod
    def from_dict(cls, data: dict) -> "QiskitResult":
        """Deserialize a result dict produced by :meth:`to_dict`.

        Parameters
        ----------
        data:
            A dict with at minimum ``"counts"`` and ``"shots"`` keys.
            Optionally includes ``"metadata"`` with ``"job_id"`` and
            ``"timestamp"`` keys.

        Returns
        -------
        :class:`QiskitResult`

        Raises
        ------
        ValueError
            If ``data`` is missing required keys or contains invalid values.

        Examples
        --------
        >>> d = {"counts": {"00": 512, "11": 512}, "shots": 1024,
        ...      "backend": "aer_simulator", "metadata": {}}
        >>> result = QiskitResult.from_dict(d)
        >>> result.shots
        1024
        """
        if "counts" not in data:
            raise ValueError("Result dict must contain 'counts' key.")
        counts = data["counts"]
        shots = data.get("shots")
        metadata = data.get("metadata", {})
        job_id = metadata.get("job_id")
        timestamp = metadata.get("timestamp")
        return cls(counts, shots=shots, job_id=job_id, timestamp=timestamp)

    @classmethod
    def from_json(cls, json_str: str) -> "QiskitResult":
        """Deserialize a JSON string produced by :meth:`to_json`.

        Parameters
        ----------
        json_str:
            JSON string representation of a result dict.

        Returns
        -------
        :class:`QiskitResult`
        """
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"QiskitResult(shots={self._shots}, "
            f"outcomes={len(self._counts)}, "
            f"most_likely={self.most_likely_bitstring()!r})"
        )
