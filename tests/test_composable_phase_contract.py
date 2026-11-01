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
