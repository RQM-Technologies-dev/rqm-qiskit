"""
errors.py – Custom exception classes for rqm-qiskit.

These exceptions provide meaningful error messages for API consumers and
propagate cleanly through run_qiskit, async_run_qiskit, and QiskitBackend.run,
so that RQM API layers can return appropriate HTTP error responses.

Exception hierarchy
-------------------
RQMQiskitError          – base class for all rqm-qiskit errors
  BackendNotFoundError  – backend name not found or unavailable
  CredentialsError      – IBM Quantum credentials invalid or missing
  JobFailedError        – quantum job failed during execution
  TranslationError      – circuit could not be translated to Qiskit IR
"""

from __future__ import annotations


class RQMQiskitError(RuntimeError):
    """Base class for all rqm-qiskit errors.

    Inherits from :exc:`RuntimeError` so existing ``except RuntimeError``
    handlers continue to work.
    """


class BackendNotFoundError(RQMQiskitError):
    """Raised when a requested backend cannot be located.

    Examples
    --------
    >>> raise BackendNotFoundError("ibm_brisbane")
    BackendNotFoundError: Backend not found: 'ibm_brisbane'. ...
    """

    def __init__(self, backend_name: str, detail: str = "") -> None:
        msg = f"Backend not found: {backend_name!r}."
        if detail:
            msg = f"{msg} {detail}"
        super().__init__(msg)
        self.backend_name = backend_name


class CredentialsError(RQMQiskitError):
    """Raised when IBM Quantum credentials are missing or invalid.

    Examples
    --------
    >>> raise CredentialsError("Token is empty or None.")
    CredentialsError: Credentials invalid: Token is empty or None. ...
    """

    def __init__(self, detail: str = "") -> None:
        msg = "Credentials invalid."
        if detail:
            msg = f"Credentials invalid: {detail}"
        msg += (
            " Set the QISKIT_IBM_TOKEN environment variable or pass "
            "token= explicitly to get_ibmq_provider()."
        )
        super().__init__(msg)


class JobFailedError(RQMQiskitError):
    """Raised when a submitted quantum job fails during execution.

    Parameters
    ----------
    job_id:
        The identifier of the failed job, if available.
    detail:
        Additional context from the backend error.

    Examples
    --------
    >>> raise JobFailedError(job_id="abc123", detail="timeout on backend")
    JobFailedError: Job failed due to: timeout on backend (job_id='abc123').
    """

    def __init__(self, job_id: "str | None" = None, detail: str = "") -> None:
        if job_id is not None and detail:
            msg = f"Job {job_id!r} failed: {detail}."
        elif job_id is not None:
            msg = f"Job {job_id!r} failed."
        elif detail:
            msg = f"Job failed: {detail}."
        else:
            msg = "Job failed."
        super().__init__(msg)
        self.job_id = job_id


class TranslationError(RQMQiskitError):
    """Raised when a circuit cannot be translated to a Qiskit QuantumCircuit.

    Examples
    --------
    >>> raise TranslationError("Unsupported gate: 'toffoli'")
    TranslationError: Circuit translation failed: Unsupported gate: 'toffoli'.
    """

    def __init__(self, detail: str = "") -> None:
        msg = "Circuit translation failed."
        if detail:
            msg = f"Circuit translation failed: {detail}"
        super().__init__(msg)
