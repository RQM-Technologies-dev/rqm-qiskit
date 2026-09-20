"""Offline checks for the real IBM canary's native gates and joint counts."""
from unittest.mock import Mock

from qiskit import QuantumCircuit
from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult


def test_async_ibm_submits_native_circuit(monkeypatch):
    from rqm_compiler import Circuit
    from rqm_qiskit import async_run_qiskit
    import qiskit_ibm_runtime

    backend = object()
    native = QuantumCircuit(2, 2)
    native.x(1)
    native.measure([0, 1], [0, 1])
    lower = Mock(return_value=native)
    sampler = Mock()
    sampler.run.return_value.job_id.return_value = "offline-job"
    monkeypatch.setattr("rqm_qiskit.ibm.resolve_backend", lambda _: backend)
    monkeypatch.setattr("qiskit.transpile", lower)
    monkeypatch.setattr(qiskit_ibm_runtime, "SamplerV2", Mock(return_value=sampler))
    circuit = Circuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    async_run_qiskit(circuit, backend="ibm_test", shots=100)
    assert lower.call_args.kwargs == {
        "backend": backend, "optimization_level": 1, "seed_transpiler": 17,
    }
    sampler.run.assert_called_once_with([native], shots=100)


def test_joint_counts_preserve_correlations_and_bit_order():
    from rqm_qiskit.job import QiskitJob

    # Include asymmetric shots: Bell-only data would hide a bit-order reversal.
    pub = SamplerPubResult(DataBin(
        m0=BitArray.from_samples(["0", "1", "0", "0"]),
        m1=BitArray.from_samples(["0", "1", "1", "1"]),
    ))
    raw_job = Mock()
    raw_job.job_id.return_value = 'saved-joint-counts-job'
    raw_job.result.return_value = [pub]
    job = QiskitJob(ibm_job=raw_job, shots=4)
    result = job.result()
    assert result.counts == {"00": 1, "11": 1, "10": 2}
    assert sum(result.counts.values()) == 4
