import json
import math
import numpy as np
import pytest
from qiskit.quantum_info import Operator
from rqm_compiler import Circuit
from rqm_compiler.io import circuit_to_dict, circuit_from_dict
from rqm_qiskit import to_qiskit_circuit

@pytest.mark.parametrize('axis',['rx','ry','rz'])
@pytest.mark.parametrize('angles',[(2*math.pi,),(-2*math.pi,),(math.pi,math.pi),(2*math.pi,.17,-.17),(.1,.2),(1e-8,2e-8)])
def test_exact_operator_inversion_control_and_json(axis,angles):
    c=Circuit(2)
    for a in angles:getattr(c,axis)(0,a)
    before=to_qiskit_circuit(c)
    after=to_qiskit_circuit(circuit_from_dict(json.loads(json.dumps(circuit_to_dict(c)))),optimize=True)
    for a,b in [(before,after),(before.inverse(),after.inverse())]:
        assert np.linalg.norm(Operator(a).data-Operator(b).data)/2<1e-10
        ca=Operator(a.to_gate().control()).data;cb=Operator(b.to_gate().control()).data
        assert np.linalg.norm(ca-cb)/np.sqrt(8)<1e-10

def test_rebuild_retains_lowered_scalar_phase():
    from qiskit import QuantumCircuit
    from rqm_qiskit.assurance import _rebuild_with_terminal_measurements
    original=QuantumCircuit(1,1);original.measure(0,0)
    lowered=QuantumCircuit(1,global_phase=math.pi)
    suffix=[(original.data[0].operation,[0],[0])]
    out=_rebuild_with_terminal_measurements(original,lowered,suffix)
    assert np.linalg.norm(Operator(out.remove_final_measurements(inplace=False)).data+np.eye(2))<1e-10


@pytest.mark.parametrize("axis", ["rx", "ry", "rz"])
@pytest.mark.parametrize("angle", [2 * math.pi, -2 * math.pi, 0.17, 1e-8])
def test_qasm_export_retains_exact_phase_and_control(axis, angle):
    from qiskit import qasm3
    from rqm_qiskit import export_openqasm3

    circuit = Circuit(1)
    getattr(circuit, axis)(0, angle)
    expected = to_qiskit_circuit(circuit, optimize=True)
    exported = export_openqasm3(circuit)
    assert exported.status == "EXPORTED", exported.error
    restored = qasm3.loads(exported.source)
    assert np.linalg.norm(Operator(expected).data - Operator(restored).data) < 1e-10
    assert np.linalg.norm(
        Operator(expected.to_gate().control()).data
        - Operator(restored.to_gate().control()).data
    ) < 1e-10


def test_qasm_export_rejects_scalar_phase_loss(monkeypatch):
    from rqm_qiskit import assurance

    circuit = Circuit(1)
    circuit.rx(0, 2 * math.pi)
    monkeypatch.setattr(
        assurance.qasm3, "dumps",
        lambda _: "OPENQASM 3.0; include \"stdgates.inc\"; qubit[1] q;",
    )
    result = assurance.export_openqasm3(circuit)
    assert result.status == "ERROR"
    assert result.source is None
    assert "phase-preserving" in result.error


@pytest.mark.parametrize("descriptor_only", [False, True])
@pytest.mark.parametrize("measured", [False, True])
def test_export_transport_and_terminal_measurement_contract(descriptor_only, measured):
    from qiskit import qasm3
    from rqm_compiler import CompiledCircuit, Operation
    from rqm_qiskit import export_openqasm3
    from rqm_qiskit.assurance import _terminal_measurement_split

    circuit = Circuit(2)
    circuit.rx(0, 2 * math.pi)
    circuit.ry(1, 0.2)
    if measured:
        for wire, key in [(1, "right"), (0, "left"), (1, "right")]:
            circuit.add(Operation(gate="measure", targets=[wire], params={"key": key}))
    source = CompiledCircuit(circuit.to_descriptors(), 2) if descriptor_only else circuit
    result = export_openqasm3(source)
    assert result.status == "EXPORTED", result.error
    expected = to_qiskit_circuit(circuit)
    restored = qasm3.loads(result.source)
    before, suffix, error = _terminal_measurement_split(expected)
    after, restored_suffix, restored_error = _terminal_measurement_split(restored)
    assert error is restored_error is None
    assert [(q, c) for _, q, c in suffix] == [(q, c) for _, q, c in restored_suffix]
    assert [(r.name, len(r)) for r in expected.cregs] == [(r.name, len(r)) for r in restored.cregs]
    assert np.max(abs(Operator(before).data - Operator(after).data)) < 1e-10


def test_export_rejects_mid_circuit_measurement():
    from rqm_qiskit import export_openqasm3

    circuit = Circuit(1)
    circuit.measure(0)
    circuit.x(0)
    result = export_openqasm3(circuit)
    assert result.status == "ERROR"
    assert "terminal" in result.error


def test_export_rejects_corrupted_measurement_mapping(monkeypatch):
    from qiskit import QuantumCircuit
    from rqm_qiskit import assurance

    circuit = Circuit(2)
    circuit.measure(1)
    replacement = QuantumCircuit(2, 1)
    replacement.measure(0, 0)
    text = assurance.qasm3.dumps(replacement)
    monkeypatch.setattr(assurance.qasm3, "dumps", lambda _: text)
    result = assurance.export_openqasm3(circuit)
    assert result.status == "ERROR"
    assert "mapping" in result.error


def test_export_rejects_invalid_descriptor_transport():
    from rqm_compiler import CompiledCircuit
    from rqm_qiskit import export_openqasm3

    result = export_openqasm3(CompiledCircuit([{"gate": "x", "targets": [9]}], 1))
    assert result.status == "ERROR"
    assert result.source is None


def test_export_rejects_control_flow_descriptor():
    from rqm_compiler import CompiledCircuit
    from rqm_qiskit import export_openqasm3

    result = export_openqasm3(CompiledCircuit([
        {"gate": "if_else", "targets": [0], "controls": [], "params": {}}
    ], 1))
    assert result.status == "ERROR"
    assert result.source is None
