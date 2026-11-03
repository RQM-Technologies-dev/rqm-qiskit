"""ATLAS regression tests for strict, explicit SU(4) synthesis."""
import numpy as np
import pytest
from qiskit.quantum_info import Operator
from rqm_entanglement import QuaternionCartanBlock
from rqm_qiskit import synthesis


def block():
    return QuaternionCartanBlock.from_components(
        left_q0=(-1., 0., 0., 0.), left_q1=(1., 0., 0., 0.),
        right_q0=(1., 0., 0., 0.), right_q1=(1., 0., 0., 0.),
        cartan_a=.61, cartan_b=.27, cartan_c=-.13,
        global_phase=.73,
    )


def test_explicit_rq_does_not_evaluate_other_candidates(monkeypatch):
    called = []
    def unwanted(*args, **kwargs):
        called.append(True)
        raise AssertionError('unrequested generic synthesis')
    for name in ['_synthesize_q3', '_synthesize_qf', '_synthesize_qc', '_synthesize_qx']:
        monkeypatch.setattr(synthesis, name, unwanted)
    result, report = synthesis.synthesize_su4_block(block(), strategy='RQ', include_report=True)
    assert not called
    assert set(report['candidates']) == {'RQ'}
    assert np.max(np.abs(Operator(result).data - block().to_unitary())) < 1e-10


def test_global_phase_corruption_is_rejected(monkeypatch):
    original = synthesis._synthesize_rq
    def corrupt(*args, **kwargs):
        circuit, latency, metadata = original(*args, **kwargs)
        circuit.global_phase += .125
        return circuit, latency, metadata
    monkeypatch.setattr(synthesis, '_synthesize_rq', corrupt)
    with pytest.raises(ValueError, match='semantic'):
        synthesis.synthesize_su4_block(block(), strategy='RQ')


def test_report_keeps_exact_and_phase_aligned_diagnostics():
    b = block()
    result, report = synthesis.synthesize_su4_block(b, strategy='RQ', include_report=True)
    candidate = report['candidates']['RQ']
    assert candidate['exact_operator_error'] < 1e-10
    assert candidate['phase_aligned_operator_error'] < 1e-10
    result.global_phase += .125
    error, valid = synthesis._semantic_error(b.to_unitary(), result)
    assert error > .01
    assert not valid
