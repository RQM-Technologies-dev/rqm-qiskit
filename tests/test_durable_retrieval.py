from types import SimpleNamespace
import pytest
from rqm_qiskit import retrieve_ibm_job
from rqm_qiskit.ibm import resolve_backend
from rqm_qiskit.job import QiskitJob


def test_retrieve_uses_injected_service_without_submission():
    calls = []
    raw = SimpleNamespace(status=lambda: 'RUNNING')
    service = SimpleNamespace(job=lambda identifier: calls.append(identifier) or raw)
    first = retrieve_ibm_job('saved-id', service=service, shots=512)
    second = retrieve_ibm_job('saved-id', service=service, shots=512)
    assert first.job_id() == second.job_id() == 'saved-id'
    assert second.status() == 'RUNNING'
    assert calls == ['saved-id', 'saved-id']


def test_resolve_uses_injected_service(monkeypatch):
    monkeypatch.setenv('QISKIT_IBM_TOKEN', 'must-not-use')
    assert resolve_backend('ibm_test', service=SimpleNamespace(backend=lambda n: n)) == 'ibm_test'


@pytest.mark.parametrize('value', [None, '', 3])
def test_no_synthetic_ibm_identifier(value):
    with pytest.raises(RuntimeError):
        QiskitJob(ibm_job=SimpleNamespace(job_id=lambda: value))


def test_timeout_preserved():
    def timeout(**kwargs):
        raise TimeoutError('bounded')
    job = retrieve_ibm_job('saved', service=SimpleNamespace(job=lambda _: SimpleNamespace(result=timeout)))
    with pytest.raises(TimeoutError):
        job.result(timeout=1)
