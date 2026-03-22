"""
Tests for async_run_qiskit and QiskitBackend.async_run.

Covers:
- async_run_qiskit returns a QiskitJob
- QiskitJob.status() returns "DONE" for local Aer runs
- QiskitJob.job_id() returns a string
- QiskitJob.result() returns a QiskitResult with correct keys
- QiskitJob.to_dict() returns a JSON-serializable dict
- QiskitBackend.async_run works the same as async_run_qiskit
- async_run_qiskit with include_report=True
- async_run_qiskit with string backend raises BackendNotFoundError
"""

import json
import pytest


def _single_qubit_circuit():
    from rqm_compiler import Circuit

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    return c


def _bell_circuit():
    from rqm_compiler import Circuit

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0)
    c.measure(1)
    return c


# ---------------------------------------------------------------------------
# async_run_qiskit – importability and return type
# ---------------------------------------------------------------------------


def test_async_run_qiskit_importable():
    """async_run_qiskit must be importable from rqm_qiskit."""
    from rqm_qiskit import async_run_qiskit

    assert callable(async_run_qiskit)


def test_async_run_qiskit_returns_job():
    """async_run_qiskit must return a QiskitJob."""
    from rqm_qiskit import async_run_qiskit, QiskitJob

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(job, QiskitJob)


# ---------------------------------------------------------------------------
# QiskitJob – status
# ---------------------------------------------------------------------------


def test_async_run_qiskit_status_done():
    """Local Aer job status must be 'DONE' immediately."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    assert job.status() == "DONE"


def test_async_run_qiskit_bell_status_done():
    """Bell circuit local Aer job status must be 'DONE' immediately."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_bell_circuit(), shots=64)
    assert job.status() == "DONE"


# ---------------------------------------------------------------------------
# QiskitJob – job_id
# ---------------------------------------------------------------------------


def test_async_run_qiskit_job_id_is_string():
    """QiskitJob.job_id() must return a string."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(job.job_id(), str)


def test_async_run_qiskit_job_id_nonempty():
    """QiskitJob.job_id() must be non-empty."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    assert len(job.job_id()) > 0


# ---------------------------------------------------------------------------
# QiskitJob – result()
# ---------------------------------------------------------------------------


def test_async_run_qiskit_result_is_qiskit_result():
    """QiskitJob.result() must return a QiskitResult."""
    from rqm_qiskit import async_run_qiskit, QiskitResult

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    result = job.result()
    assert isinstance(result, QiskitResult)


def test_async_run_qiskit_result_has_counts():
    """QiskitJob.result() must have non-empty counts."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    result = job.result()
    assert len(result.counts) > 0


def test_async_run_qiskit_result_shots_match():
    """QiskitJob.result() shots must match requested shots."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=128)
    result = job.result()
    assert result.shots == 128


def test_async_run_qiskit_result_counts_sum_to_shots():
    """QiskitJob.result() counts must sum to shots."""
    from rqm_qiskit import async_run_qiskit

    shots = 256
    job = async_run_qiskit(_single_qubit_circuit(), shots=shots)
    result = job.result()
    assert sum(result.counts.values()) == shots


def test_async_run_qiskit_bell_only_00_11():
    """Bell circuit must produce only '00' and '11' outcomes."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_bell_circuit(), shots=256)
    result = job.result()
    for key in result.counts:
        assert key in ("00", "11"), f"Unexpected key: {key}"


# ---------------------------------------------------------------------------
# QiskitJob – to_dict()
# ---------------------------------------------------------------------------


def test_async_run_qiskit_to_dict_has_required_keys():
    """QiskitJob.to_dict() must have job_id, status, backend, shots."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    d = job.to_dict()
    assert "job_id" in d
    assert "status" in d
    assert "backend" in d
    assert "shots" in d
    assert "submitted_at" in d


def test_async_run_qiskit_to_dict_is_json_serializable():
    """QiskitJob.to_dict() must be JSON-serializable."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    d = job.to_dict()
    serialized = json.dumps(d)
    assert isinstance(serialized, str)


def test_async_run_qiskit_to_dict_has_result():
    """QiskitJob.to_dict() for a completed job must include result key."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    d = job.to_dict()
    assert "result" in d
    assert "counts" in d["result"]


def test_async_run_qiskit_to_dict_shots_value():
    """QiskitJob.to_dict() shots must match requested shots."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=128)
    d = job.to_dict()
    assert d["shots"] == 128


# ---------------------------------------------------------------------------
# QiskitJob – repr
# ---------------------------------------------------------------------------


def test_async_run_qiskit_job_repr():
    """QiskitJob repr must include key info."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64)
    r = repr(job)
    assert "QiskitJob" in r
    assert "DONE" in r


# ---------------------------------------------------------------------------
# async_run_qiskit – include_report
# ---------------------------------------------------------------------------


def test_async_run_qiskit_include_report_does_not_raise():
    """async_run_qiskit with include_report=True must not raise."""
    from rqm_qiskit import async_run_qiskit

    job = async_run_qiskit(_single_qubit_circuit(), shots=64, include_report=True)
    assert job is not None


def test_async_run_qiskit_include_report_result_is_valid():
    """async_run_qiskit with include_report=True must return a valid result."""
    from rqm_qiskit import async_run_qiskit, QiskitResult

    job = async_run_qiskit(_single_qubit_circuit(), shots=64, include_report=True)
    result = job.result()
    assert isinstance(result, QiskitResult)


# ---------------------------------------------------------------------------
# async_run_qiskit – string backend raises BackendNotFoundError
# ---------------------------------------------------------------------------


def test_async_run_qiskit_string_backend_raises():
    """async_run_qiskit with a string backend must raise BackendNotFoundError."""
    from rqm_qiskit import async_run_qiskit
    from rqm_qiskit.errors import BackendNotFoundError

    with pytest.raises((BackendNotFoundError, NotImplementedError)):
        async_run_qiskit(_single_qubit_circuit(), shots=64, backend="ibm_nairobi")


# ---------------------------------------------------------------------------
# QiskitBackend.async_run – OO interface
# ---------------------------------------------------------------------------


def test_backend_async_run_importable():
    """QiskitBackend.async_run must be a callable method."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    assert callable(backend.async_run)


def test_backend_async_run_returns_job():
    """QiskitBackend.async_run must return a QiskitJob."""
    from rqm_qiskit import QiskitBackend, QiskitJob

    backend = QiskitBackend()
    job = backend.async_run(_single_qubit_circuit(), shots=64)
    assert isinstance(job, QiskitJob)


def test_backend_async_run_status_done():
    """QiskitBackend.async_run local Aer job must be DONE immediately."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    job = backend.async_run(_single_qubit_circuit(), shots=64)
    assert job.status() == "DONE"


def test_backend_async_run_result_is_valid():
    """QiskitBackend.async_run result must be a QiskitResult."""
    from rqm_qiskit import QiskitBackend, QiskitResult

    backend = QiskitBackend()
    job = backend.async_run(_single_qubit_circuit(), shots=64)
    result = job.result()
    assert isinstance(result, QiskitResult)
    assert len(result.counts) > 0


def test_backend_async_run_shots_match():
    """QiskitBackend.async_run shots must match requested shots."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    job = backend.async_run(_single_qubit_circuit(), shots=200)
    assert job.result().shots == 200


# ---------------------------------------------------------------------------
# QiskitJob importability
# ---------------------------------------------------------------------------


def test_qiskit_job_importable():
    """QiskitJob must be importable from rqm_qiskit."""
    from rqm_qiskit import QiskitJob

    assert callable(QiskitJob)
