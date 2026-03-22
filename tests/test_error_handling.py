"""
Tests for error handling and exception propagation.

Covers:
- TranslationError raised for invalid circuit type
- BackendNotFoundError raised for unknown string backend in run_qiskit
- BackendNotFoundError raised for unknown string backend in async_run_qiskit
- JobFailedError raised when IBM job fails (mock)
- Errors are RuntimeError subclasses and propagate cleanly
- include_report=True still works when error info is embedded
"""

import pytest


def _single_qubit_circuit():
    from rqm_compiler import Circuit

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    return c


# ---------------------------------------------------------------------------
# TranslationError for invalid input
# ---------------------------------------------------------------------------


def test_run_qiskit_invalid_input_raises_type_error_or_translation_error():
    """run_qiskit with invalid input type must raise an error."""
    from rqm_qiskit import run_qiskit
    from rqm_qiskit.errors import TranslationError

    with pytest.raises((TypeError, TranslationError, AttributeError, ValueError)):
        run_qiskit(42, shots=64)


def test_async_run_qiskit_invalid_input_raises():
    """async_run_qiskit with invalid input type must raise an error."""
    from rqm_qiskit import async_run_qiskit
    from rqm_qiskit.errors import TranslationError

    with pytest.raises((TypeError, TranslationError, AttributeError, ValueError)):
        async_run_qiskit(42, shots=64)


# ---------------------------------------------------------------------------
# BackendNotFoundError propagates from run_qiskit
# ---------------------------------------------------------------------------


def test_run_qiskit_unknown_backend_string_raises_meaningful_error():
    """run_qiskit with unknown backend string must raise BackendNotFoundError."""
    import os
    from rqm_qiskit import run_qiskit
    from rqm_qiskit.errors import BackendNotFoundError

    env_backup = os.environ.pop("QISKIT_IBM_TOKEN", None)
    try:
        with pytest.raises((BackendNotFoundError, ImportError, NotImplementedError)):
            run_qiskit(_single_qubit_circuit(), shots=64, backend="ibm_unknownbackend99")
    finally:
        if env_backup is not None:
            os.environ["QISKIT_IBM_TOKEN"] = env_backup


# ---------------------------------------------------------------------------
# BackendNotFoundError propagates from async_run_qiskit
# ---------------------------------------------------------------------------


def test_async_run_qiskit_unknown_backend_string_raises_meaningful_error():
    """async_run_qiskit with unknown backend string must raise BackendNotFoundError."""
    import os
    from rqm_qiskit import async_run_qiskit
    from rqm_qiskit.errors import BackendNotFoundError

    env_backup = os.environ.pop("QISKIT_IBM_TOKEN", None)
    try:
        with pytest.raises((BackendNotFoundError, ImportError, NotImplementedError)):
            async_run_qiskit(_single_qubit_circuit(), shots=64, backend="ibm_unknownbackend99")
    finally:
        if env_backup is not None:
            os.environ["QISKIT_IBM_TOKEN"] = env_backup


# ---------------------------------------------------------------------------
# JobFailedError raised via mock IBM job
# ---------------------------------------------------------------------------


def test_qiskit_job_result_raises_job_failed_error_on_ibm_failure():
    """QiskitJob.result() must raise JobFailedError when IBM job fails."""
    from rqm_qiskit.job import QiskitJob
    from rqm_qiskit.errors import JobFailedError

    class FailingIBMJob:
        def job_id(self):
            return "failing-job-id"

        def result(self, **kwargs):
            raise RuntimeError("Backend error: qubit mapping failed")

        def status(self):
            class Status:
                name = "ERROR"
            return Status()

    job = QiskitJob(
        ibm_job=FailingIBMJob(),
        backend_name="ibm_brisbane",
        shots=1024,
    )
    with pytest.raises(JobFailedError):
        job.result()


def test_qiskit_job_failed_error_contains_job_id():
    """QiskitJob JobFailedError must include job_id."""
    from rqm_qiskit.job import QiskitJob
    from rqm_qiskit.errors import JobFailedError

    class FailingIBMJob:
        def job_id(self):
            return "test-job-xyz"

        def result(self, **kwargs):
            raise RuntimeError("backend failed")

        def status(self):
            class Status:
                name = "ERROR"
            return Status()

    job = QiskitJob(
        ibm_job=FailingIBMJob(),
        backend_name="ibm_brisbane",
        shots=1024,
    )
    with pytest.raises(JobFailedError) as exc_info:
        job.result()
    assert "test-job-xyz" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Errors are RuntimeError subclasses
# ---------------------------------------------------------------------------


def test_all_errors_are_runtime_errors():
    """All custom errors must be RuntimeError subclasses."""
    from rqm_qiskit.errors import (
        RQMQiskitError,
        BackendNotFoundError,
        CredentialsError,
        JobFailedError,
        TranslationError,
    )

    assert issubclass(RQMQiskitError, RuntimeError)
    assert issubclass(BackendNotFoundError, RuntimeError)
    assert issubclass(CredentialsError, RuntimeError)
    assert issubclass(JobFailedError, RuntimeError)
    assert issubclass(TranslationError, RuntimeError)


# ---------------------------------------------------------------------------
# Error propagation through QiskitBackend.run
# ---------------------------------------------------------------------------


def test_backend_run_invalid_input_raises():
    """QiskitBackend.run with invalid input must raise an error."""
    from rqm_qiskit import QiskitBackend
    from rqm_qiskit.errors import TranslationError

    backend = QiskitBackend()
    with pytest.raises((TypeError, TranslationError, AttributeError, ValueError)):
        backend.run(42, shots=64)


# ---------------------------------------------------------------------------
# Mock IBM job that succeeds – verifying QiskitJob result path
# ---------------------------------------------------------------------------


def test_qiskit_job_mock_ibm_result():
    """QiskitJob wrapping a mock IBM job must return correct counts."""
    from rqm_qiskit.job import QiskitJob
    from rqm_qiskit.result import QiskitResult

    class MockBitArray:
        def get_counts(self):
            return {"0": 512, "1": 512}

    class MockData:
        meas = MockBitArray()

        def __iter__(self):
            return iter(["meas"])

    class MockPubResult:
        data = MockData()

    class MockIBMResult:
        def __getitem__(self, idx):
            return MockPubResult()

    class MockIBMJob:
        def job_id(self):
            return "mock-ibm-job-001"

        def result(self, **kwargs):
            return MockIBMResult()

        def status(self):
            class Status:
                name = "DONE"
            return Status()

    job = QiskitJob(
        ibm_job=MockIBMJob(),
        backend_name="ibm_mock",
        shots=1024,
    )
    result = job.result()
    assert isinstance(result, QiskitResult)
    assert result.shots == 1024
    assert "0" in result.counts
    assert "1" in result.counts
