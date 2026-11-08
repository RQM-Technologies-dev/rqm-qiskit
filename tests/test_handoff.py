import hashlib
import io
import math

import numpy as np
import pytest
from qiskit import QuantumCircuit, qasm3, qpy
from qiskit.quantum_info import Operator

from rqm_qiskit.handoff import (
    assure_openqasm3_handoff,
    assure_openqasm3_handoff_isolated,
    verify_openqasm3_artifact,
)


def circuit(measured=False):
    qc = QuantumCircuit(4, 4 if measured else 0)
    qc.h(0)
    qc.rx(0.37, 3)
    qc.cx(3, 1)
    qc.rzz(0.23, 0, 2)
    qc.rx(0.1, 2)
    qc.rx(0.2, 2)
    if measured:
        qc.measure(range(4), [3, 1, 0, 2])
    return qc


@pytest.mark.parametrize("measured", [False, True])
def test_four_qubit_emitted_artifact_and_qpy(measured):
    original = circuit(measured)
    source = qasm3.dumps(original)
    result = assure_openqasm3_handoff_isolated(source)
    assert result["assurance_status"] == "VERIFIED", result
    artifact = result["returned_openqasm3"]
    assert (
        result["verification"]["artifact_sha256"]
        == hashlib.sha256(artifact.encode()).hexdigest()
    )
    assert result["verification"]["controlled_reuse_eligible"] is (not measured)
    restored = qasm3.loads(artifact)
    stream = io.BytesIO()
    qpy.dump(restored, stream)
    stream.seek(0)
    restored = qpy.load(stream)[0]
    np.testing.assert_allclose(
        Operator(original.remove_final_measurements(inplace=False)).data,
        Operator(restored.remove_final_measurements(inplace=False)).data,
        atol=1e-10,
        rtol=0,
    )
    assert (
        verify_openqasm3_artifact(source, qasm3.dumps(restored))["status"] == "VERIFIED"
    )


@pytest.mark.parametrize("mutation", ["angle", "wire", "phase", "readout", "syntax"])
def test_corrupt_artifacts_fail_closed(mutation):
    original = circuit(mutation == "readout")
    source = qasm3.dumps(original)
    artifact = source
    if mutation == "angle":
        artifact = source.replace("rx(0.37)", "rx(-0.37)")
    elif mutation == "wire":
        artifact = source.replace("cx q[3], q[1]", "cx q[1], q[3]")
    elif mutation == "phase":
        original.rz(2 * math.pi, 0)
        artifact = qasm3.dumps(original)
    elif mutation == "readout":
        artifact = source.replace("c[3] = measure q[0]", "c[2] = measure q[0]")
    else:
        artifact = "not OpenQASM"
    assert artifact != source
    proof = verify_openqasm3_artifact(source, artifact)
    assert proof["status"] != "VERIFIED", proof
    if mutation == "phase":
        terminal = verify_openqasm3_artifact(
            source, artifact, phase_semantics="phase_invariant"
        )
        assert terminal["status"] == "VERIFIED"
        assert terminal["controlled_reuse_eligible"] is False


@pytest.mark.parametrize(
    "kind", ["five", "mid", "global", "gate", "large", "phase_mode"]
)
def test_unsupported_original_preserved(kind):
    qc = circuit()
    if kind == "five":
        qc = QuantumCircuit(5)
    elif kind == "mid":
        qc = circuit(True)
        qc.x(0)
    elif kind == "global":
        qc.global_phase = 0.3
    elif kind == "gate":
        qc.ccx(0, 1, 2)
    elif kind == "large":
        for _ in range(513):
            qc.x(0)
    source = qasm3.dumps(qc)
    if kind == "global":
        # Qiskit's exporter can omit QuantumCircuit.global_phase; assert the
        # actual supplied document contains it rather than testing lost input.
        source += "gphase(0.3);\n"
    result = assure_openqasm3_handoff(
        source, phase_semantics="bogus" if kind == "phase_mode" else "exact"
    )
    assert result["assurance_status"] == "FALLBACK_ORIGINAL"
    assert result["returned_openqasm3"] == source


def test_export_corruption_is_checked(monkeypatch):
    from dataclasses import replace
    import rqm_qiskit.handoff as module

    real_export = module.export_openqasm3

    def corrupt(candidate):
        result = real_export(candidate)
        return replace(result, source=result.source + "x q[0];\n")

    monkeypatch.setattr(module, "export_openqasm3", corrupt)
    source = qasm3.dumps(circuit())
    result = assure_openqasm3_handoff(source)
    assert result["assurance_status"] == "FALLBACK_ORIGINAL"
    assert result["returned_openqasm3"] == source
    assert result["verification"]["status"] == "COUNTEREXAMPLE"


def test_legacy_phase_runtime_is_not_promoted(monkeypatch):
    import rqm_compiler

    def legacy_verifier(left, right):
        raise AssertionError(
            "Legacy verifier must not run for an explicit phase contract"
        )

    monkeypatch.setattr(rqm_compiler, "verify_equivalence", legacy_verifier)
    source = qasm3.dumps(circuit())
    result = assure_openqasm3_handoff(source)
    assert result["assurance_status"] == "FALLBACK_ORIGINAL"
    assert result["verification"]["status"] == "UNSUPPORTED"
    assert result["returned_openqasm3"] == source


@pytest.mark.parametrize("definition", [
    "gate h q { U(pi,0,pi) q; }",
    "gate h q { U(pi/2,0,pi) q; U(0,0,2*pi) q; U(2*pi,0,0) q; }",
])
def test_custom_named_gate_cannot_impersonate_standard_gate(definition):
    source = "OPENQASM 3.0; " + definition + " qubit[4] q; h q[0];"
    result = assure_openqasm3_handoff(source)
    assert result["assurance_status"] == "FALLBACK_ORIGINAL"
    assert result["verification"]["status"] == "UNSUPPORTED"
    assert result["returned_openqasm3"] == source


def test_corrupted_artifact_gate_definition_is_rejected():
    source = qasm3.dumps(circuit())
    artifact = "OPENQASM 3.0; gate h q { U(pi,0,pi) q; } qubit[4] q; h q[0];"
    assert verify_openqasm3_artifact(source, artifact)["status"] == "UNSUPPORTED"


def test_sdk_check_failure_cannot_retain_compiler_verified_status(monkeypatch):
    def failed(*args, **kwargs):
        raise ValueError("SDK comparison unavailable")

    monkeypatch.setattr(Operator, "equiv", failed)
    source = qasm3.dumps(circuit())
    result = verify_openqasm3_artifact(source, source, phase_semantics="phase_invariant")
    assert result["status"] == "UNSUPPORTED"
    assert result["equivalent"] is None
    assert result["controlled_reuse_eligible"] is False
