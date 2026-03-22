"""
job.py – QiskitJob: a thin wrapper around a submitted quantum job.

``QiskitJob`` provides a uniform handle returned by ``async_run_qiskit``
and ``QiskitBackend.async_run``.  For local Aer runs the job is
immediately complete; for real IBM backends it delegates to the
underlying Qiskit IBM Runtime job.

Public API
----------
- ``QiskitJob`` : job handle with status / result / job_id
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rqm_qiskit.result import QiskitResult


class QiskitJob:
    """A handle for a submitted quantum circuit job.

    Returned by :func:`~rqm_qiskit.execution.async_run_qiskit` and
    :meth:`~rqm_qiskit.backend.QiskitBackend.async_run`.

    For local Aer simulations the execution is synchronous, so the job
    is already complete when this object is constructed.  For real IBM
    Quantum backends the underlying IBM job is stored and polled on
    demand.

    Parameters
    ----------
    result:
        Pre-computed :class:`~rqm_qiskit.result.QiskitResult` for
        immediately-completed (Aer) jobs.  Pass ``None`` for IBM jobs
        where ``ibm_job`` is provided.
    ibm_job:
        The underlying Qiskit IBM Runtime job object (duck-typed).
        When provided, :meth:`result` delegates to it.
    job_id:
        An explicit job identifier string.  If omitted, inferred from
        ``ibm_job.job_id()`` or generated locally.
    backend_name:
        Name of the backend that executed the job.
    shots:
        Number of shots requested for this job.
    submitted_at:
        Timestamp when the job was submitted (UTC).  Defaults to now.

    Examples
    --------
    >>> from rqm_qiskit import async_run_qiskit
    >>> from rqm_compiler import Circuit
    >>> c = Circuit(1); c.h(0); c.measure(0)
    >>> job = async_run_qiskit(c, shots=512)
    >>> print(job.job_id())
    >>> result = job.result()
    >>> print(result.counts)
    """

    def __init__(
        self,
        result: "QiskitResult | None" = None,
        *,
        ibm_job: Any = None,
        job_id: "str | None" = None,
        backend_name: str = "aer_simulator",
        shots: int = 1024,
        submitted_at: "datetime.datetime | None" = None,
    ) -> None:
        self._result = result
        self._ibm_job = ibm_job
        self._backend_name = backend_name
        self._shots = shots
        self._submitted_at = submitted_at or datetime.datetime.now(datetime.timezone.utc)

        if job_id is not None:
            self._job_id = job_id
        elif ibm_job is not None and hasattr(ibm_job, "job_id"):
            try:
                raw = ibm_job.job_id()
                self._job_id = raw if isinstance(raw, str) else str(raw)
            except Exception:
                self._job_id = _generate_local_id()
        else:
            self._job_id = _generate_local_id()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def job_id(self) -> str:
        """Return the unique job identifier.

        Returns
        -------
        str
        """
        return self._job_id

    def status(self) -> str:
        """Return a status string for this job.

        Returns ``"DONE"`` for completed local (Aer) jobs.  For IBM
        jobs, delegates to ``ibm_job.status()`` if available.

        Returns
        -------
        str
            One of ``"DONE"``, ``"RUNNING"``, ``"QUEUED"``,
            ``"CANCELLED"``, ``"ERROR"``.
        """
        if self._result is not None:
            return "DONE"
        if self._ibm_job is not None:
            try:
                st = self._ibm_job.status()
                # IBM Runtime returns an enum; convert to string
                return str(st.name) if hasattr(st, "name") else str(st)
            except Exception:
                return "UNKNOWN"
        return "UNKNOWN"

    def result(
        self,
        timeout: "float | None" = None,
        poll_interval: float = 2.0,
    ) -> "QiskitResult":
        """Block until the job is complete and return a :class:`~rqm_qiskit.result.QiskitResult`.

        For local Aer jobs this returns immediately.  For IBM jobs it
        calls ``ibm_job.result()`` with an optional timeout.

        Parameters
        ----------
        timeout:
            Maximum number of seconds to wait.  ``None`` means wait
            indefinitely.  Ignored for already-complete local jobs.
        poll_interval:
            Seconds between status polls (currently unused; reserved for
            future implementations that do not block on ``ibm_job.result()``).

        Returns
        -------
        :class:`~rqm_qiskit.result.QiskitResult`

        Raises
        ------
        rqm_qiskit.errors.JobFailedError
            If the underlying IBM job reports an error.
        TimeoutError
            If the job does not complete within ``timeout`` seconds.
        """
        from rqm_qiskit.result import QiskitResult

        if self._result is not None:
            return self._result

        if self._ibm_job is not None:
            return self._collect_ibm_result(timeout=timeout)

        raise RuntimeError(
            "QiskitJob has neither a pre-computed result nor an IBM job object. "
            "This is an internal error; please report it."
        )

    def to_dict(self) -> "dict[str, Any]":
        """Return a JSON-serializable summary of this job.

        Returns
        -------
        dict
            Keys: ``job_id``, ``status``, ``backend``, ``shots``,
            ``submitted_at``.  If the job is complete the ``result``
            key is also included.
        """
        d: dict[str, Any] = {
            "job_id": self._job_id,
            "status": self.status(),
            "backend": self._backend_name,
            "shots": self._shots,
            "submitted_at": self._submitted_at.isoformat(),
        }
        if self._result is not None:
            d["result"] = self._result.to_dict(
                backend=self._backend_name,
                job_id=self._job_id,
            )
        return d

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_ibm_result(self, timeout: "float | None") -> "QiskitResult":
        """Collect the result from an IBM Runtime job."""
        from rqm_qiskit.errors import JobFailedError
        from rqm_qiskit.result import QiskitResult

        try:
            if timeout is not None:
                ibm_result = self._ibm_job.result(timeout=timeout)
            else:
                ibm_result = self._ibm_job.result()
        except TimeoutError:
            raise
        except Exception as exc:
            raise JobFailedError(job_id=self._job_id, detail=str(exc)) from exc

        # Extract counts from IBM SamplerV2 PubResult
        counts: dict[str, int] = {}
        try:
            pub_result = ibm_result[0]
            for reg_name in pub_result.data:
                bit_array = getattr(pub_result.data, reg_name)
                for bitstring, count in bit_array.get_counts().items():
                    counts[bitstring] = counts.get(bitstring, 0) + count
        except Exception as exc:
            raise JobFailedError(
                job_id=self._job_id,
                detail=f"Could not parse IBM result: {exc}",
            ) from exc

        self._result = QiskitResult(counts, shots=self._shots)
        return self._result

    def __repr__(self) -> str:
        return (
            f"QiskitJob(job_id={self._job_id!r}, "
            f"status={self.status()!r}, "
            f"backend={self._backend_name!r})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_local_id() -> str:
    """Generate a unique local job identifier."""
    import uuid

    return f"local-{uuid.uuid4().hex[:12]}"
