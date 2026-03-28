"""Tests for IBM Runtime execution behavior."""

from __future__ import annotations

import sys
import types
from unittest.mock import Mock

from qiskit import QuantumCircuit


class _FakeBitArray:
    def get_counts(self):
        return {"0": 7, "1": 5}


class _FakeData:
    def __iter__(self):
        return iter(["c"])

    c = _FakeBitArray()


class _FakePubResult:
    data = _FakeData()


class _FakeJob:
    def job_id(self):
        return "job-123"

    def result(self):
        return [_FakePubResult()]


def test_run_on_ibm_runtime_transpiles_and_submits_transpiled(monkeypatch):
    """IBM runtime path must transpile and submit the transpiled circuit."""
    from rqm_qiskit.ibm import run_on_ibm_runtime

    original = QuantumCircuit(1, 1)
    original.h(0)
    original.measure(0, 0)

    backend = object()
    transpiled = QuantumCircuit(1, 1)
    transpiled.x(0)
    transpiled.measure(0, 0)

    transpile_mock = Mock(return_value=transpiled)
    monkeypatch.setattr("rqm_qiskit.ibm.transpile", transpile_mock)

    sampler_instance = Mock()
    sampler_instance.run.return_value = _FakeJob()
    sampler_cls = Mock(return_value=sampler_instance)

    fake_runtime_module = types.SimpleNamespace(SamplerV2=sampler_cls)
    monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", fake_runtime_module)

    counts, job_id = run_on_ibm_runtime(original, backend, shots=12)

    transpile_mock.assert_called_once_with(original, backend=backend)
    sampler_cls.assert_called_once_with(backend)
    sampler_instance.run.assert_called_once_with([transpiled], shots=12)
    assert sampler_instance.run.call_args.args[0][0] is not original
    assert counts == {"0": 7, "1": 5}
    assert job_id == "job-123"


def test_run_on_resolved_backend_none_uses_aer_path(monkeypatch):
    """Resolved None backend should continue to use local Aer execution."""
    from rqm_qiskit.execution import _run_on_resolved_backend

    qc = QuantumCircuit(1, 1)
    qc.measure(0, 0)

    run_on_aer_sampler = Mock(return_value={"0": 3})
    run_on_ibm_runtime = Mock(side_effect=AssertionError("IBM path should not be used"))
    monkeypatch.setattr("rqm_qiskit.ibm.run_on_aer_sampler", run_on_aer_sampler)
    monkeypatch.setattr("rqm_qiskit.ibm.run_on_ibm_runtime", run_on_ibm_runtime)

    counts, job_id = _run_on_resolved_backend(qc, None, shots=3)

    run_on_aer_sampler.assert_called_once_with(qc, shots=3)
    run_on_ibm_runtime.assert_not_called()
    assert counts == {"0": 3}
    assert job_id is None
