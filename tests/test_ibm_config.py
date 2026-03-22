"""
Tests for IBM Quantum provider configuration and credential loading.

Covers:
- get_ibmq_provider is importable
- get_ibmq_provider raises ImportError when qiskit-ibm-runtime is not installed
- get_ibmq_provider raises CredentialsError when no token is found
- resolve_backend(None) returns None
- resolve_backend("aer_simulator") returns None
- resolve_backend("local") returns None
- resolve_backend with unknown string raises BackendNotFoundError
- resolve_backend with a real backend object returns it unchanged
- CredentialsError contains useful message
- BackendNotFoundError contains backend name
"""

import os
import pytest


# ---------------------------------------------------------------------------
# get_ibmq_provider – importability
# ---------------------------------------------------------------------------


def test_get_ibmq_provider_importable():
    """get_ibmq_provider must be importable from rqm_qiskit."""
    from rqm_qiskit import get_ibmq_provider

    assert callable(get_ibmq_provider)


def test_get_ibmq_provider_importable_from_ibm_module():
    """get_ibmq_provider must be importable from rqm_qiskit.ibm."""
    from rqm_qiskit.ibm import get_ibmq_provider

    assert callable(get_ibmq_provider)


# ---------------------------------------------------------------------------
# get_ibmq_provider – error cases without credentials
# ---------------------------------------------------------------------------


def test_get_ibmq_provider_no_credentials_raises():
    """get_ibmq_provider must raise CredentialsError or ImportError with no credentials."""
    from rqm_qiskit import get_ibmq_provider
    from rqm_qiskit.errors import CredentialsError

    # Remove any IBM token from env for this test
    env_backup = os.environ.pop("QISKIT_IBM_TOKEN", None)
    try:
        with pytest.raises((CredentialsError, ImportError)):
            get_ibmq_provider()
    finally:
        if env_backup is not None:
            os.environ["QISKIT_IBM_TOKEN"] = env_backup


def test_get_ibmq_provider_empty_token_raises():
    """get_ibmq_provider with empty token must raise CredentialsError or ImportError."""
    from rqm_qiskit import get_ibmq_provider
    from rqm_qiskit.errors import CredentialsError

    env_backup = os.environ.pop("QISKIT_IBM_TOKEN", None)
    try:
        with pytest.raises((CredentialsError, ImportError)):
            get_ibmq_provider(token="")
    finally:
        if env_backup is not None:
            os.environ["QISKIT_IBM_TOKEN"] = env_backup


# ---------------------------------------------------------------------------
# resolve_backend
# ---------------------------------------------------------------------------


def test_resolve_backend_none_returns_none():
    """resolve_backend(None) must return None (use local Aer)."""
    from rqm_qiskit.ibm import resolve_backend

    assert resolve_backend(None) is None


def test_resolve_backend_aer_simulator_string_returns_none():
    """resolve_backend('aer_simulator') must return None."""
    from rqm_qiskit.ibm import resolve_backend

    assert resolve_backend("aer_simulator") is None


def test_resolve_backend_local_string_returns_none():
    """resolve_backend('local') must return None."""
    from rqm_qiskit.ibm import resolve_backend

    assert resolve_backend("local") is None


def test_resolve_backend_aer_case_insensitive():
    """resolve_backend('AER') must return None (case-insensitive)."""
    from rqm_qiskit.ibm import resolve_backend

    assert resolve_backend("AER") is None


def test_resolve_backend_unknown_string_raises():
    """resolve_backend with unknown IBM backend string must raise BackendNotFoundError."""
    from rqm_qiskit.ibm import resolve_backend
    from rqm_qiskit.errors import BackendNotFoundError

    env_backup = os.environ.pop("QISKIT_IBM_TOKEN", None)
    try:
        with pytest.raises((BackendNotFoundError, ImportError)):
            resolve_backend("ibm_brisbane")
    finally:
        if env_backup is not None:
            os.environ["QISKIT_IBM_TOKEN"] = env_backup


def test_resolve_backend_object_returned_unchanged():
    """resolve_backend with a backend object must return it unchanged."""
    from rqm_qiskit.ibm import resolve_backend

    # Use a mock object as the "backend"
    class FakeBackend:
        pass

    fake = FakeBackend()
    result = resolve_backend(fake)
    assert result is fake


# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------


def test_credentials_error_is_runtime_error():
    """CredentialsError must be a RuntimeError subclass."""
    from rqm_qiskit.errors import CredentialsError, RQMQiskitError

    exc = CredentialsError("test reason")
    assert isinstance(exc, RuntimeError)
    assert isinstance(exc, RQMQiskitError)


def test_credentials_error_message_contains_env_var():
    """CredentialsError message must mention the QISKIT_IBM_TOKEN env var."""
    from rqm_qiskit.errors import CredentialsError

    exc = CredentialsError("bad token")
    assert "QISKIT_IBM_TOKEN" in str(exc)


def test_backend_not_found_error_is_runtime_error():
    """BackendNotFoundError must be a RuntimeError subclass."""
    from rqm_qiskit.errors import BackendNotFoundError, RQMQiskitError

    exc = BackendNotFoundError("ibm_brisbane")
    assert isinstance(exc, RuntimeError)
    assert isinstance(exc, RQMQiskitError)


def test_backend_not_found_error_contains_name():
    """BackendNotFoundError message must contain the backend name."""
    from rqm_qiskit.errors import BackendNotFoundError

    exc = BackendNotFoundError("ibm_brisbane", detail="not found")
    assert "ibm_brisbane" in str(exc)


def test_backend_not_found_error_stores_name():
    """BackendNotFoundError must expose the backend_name attribute."""
    from rqm_qiskit.errors import BackendNotFoundError

    exc = BackendNotFoundError("ibm_brisbane")
    assert exc.backend_name == "ibm_brisbane"


def test_job_failed_error_is_runtime_error():
    """JobFailedError must be a RuntimeError subclass."""
    from rqm_qiskit.errors import JobFailedError, RQMQiskitError

    exc = JobFailedError(job_id="abc123", detail="timeout")
    assert isinstance(exc, RuntimeError)
    assert isinstance(exc, RQMQiskitError)


def test_job_failed_error_contains_job_id():
    """JobFailedError message must contain the job_id."""
    from rqm_qiskit.errors import JobFailedError

    exc = JobFailedError(job_id="abc123", detail="timeout")
    assert "abc123" in str(exc)


def test_job_failed_error_stores_job_id():
    """JobFailedError must expose the job_id attribute."""
    from rqm_qiskit.errors import JobFailedError

    exc = JobFailedError(job_id="abc123")
    assert exc.job_id == "abc123"


def test_translation_error_is_runtime_error():
    """TranslationError must be a RuntimeError subclass."""
    from rqm_qiskit.errors import TranslationError, RQMQiskitError

    exc = TranslationError("bad gate")
    assert isinstance(exc, RuntimeError)
    assert isinstance(exc, RQMQiskitError)


def test_translation_error_contains_detail():
    """TranslationError message must contain the detail string."""
    from rqm_qiskit.errors import TranslationError

    exc = TranslationError("Unsupported gate: toffoli")
    assert "Unsupported gate" in str(exc)


def test_all_errors_importable_from_rqm_qiskit():
    """All custom errors must be importable directly from rqm_qiskit."""
    from rqm_qiskit import (
        RQMQiskitError,
        BackendNotFoundError,
        CredentialsError,
        JobFailedError,
        TranslationError,
    )

    for cls in [RQMQiskitError, BackendNotFoundError, CredentialsError,
                JobFailedError, TranslationError]:
        assert issubclass(cls, RuntimeError)
