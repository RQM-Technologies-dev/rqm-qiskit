"""
Tests for API shape and JSON-compatibility of all public outputs.

Covers:
- to_qiskit_circuit is importable from rqm_qiskit
- run_qiskit is importable from rqm_qiskit
- QiskitResult.to_dict() has all required keys
- QiskitResult.to_dict() is JSON-serializable
- run_qiskit output is JSON-serializable
- run_qiskit output has required top-level keys
- run_qiskit metadata has required keys
- QiskitBackend.run result is a QiskitResult
- QiskitBackend.run result.to_dict() is JSON-serializable
- QiskitTranslator.to_quantum_circuit is callable
- QiskitTranslator.apply_gate is callable
"""

import json
import pytest
from qiskit import QuantumCircuit


def _bell_circuit():
    from rqm_compiler import Circuit

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0)
    c.measure(1)
    return c


def _single_qubit_circuit():
    from rqm_compiler import Circuit

    c = Circuit(1)
    c.h(0)
    c.measure(0)
    return c


# ---------------------------------------------------------------------------
# Public API imports
# ---------------------------------------------------------------------------


def test_to_qiskit_circuit_importable():
    """to_qiskit_circuit must be importable from rqm_qiskit."""
    from rqm_qiskit import to_qiskit_circuit
    assert callable(to_qiskit_circuit)


def test_run_qiskit_importable():
    """run_qiskit must be importable from rqm_qiskit."""
    from rqm_qiskit import run_qiskit
    assert callable(run_qiskit)


def test_qiskit_backend_importable():
    """QiskitBackend must be importable from rqm_qiskit."""
    from rqm_qiskit import QiskitBackend
    assert callable(QiskitBackend)


def test_qiskit_translator_importable():
    """QiskitTranslator must be importable from rqm_qiskit."""
    from rqm_qiskit import QiskitTranslator
    assert callable(QiskitTranslator)


def test_qiskit_result_importable():
    """QiskitResult must be importable from rqm_qiskit."""
    from rqm_qiskit import QiskitResult
    assert callable(QiskitResult)


# ---------------------------------------------------------------------------
# QiskitTranslator.to_quantum_circuit
# ---------------------------------------------------------------------------


def test_translator_to_quantum_circuit_callable():
    """QiskitTranslator.to_quantum_circuit must be a callable method."""
    from rqm_qiskit import QiskitTranslator
    t = QiskitTranslator()
    assert callable(t.to_quantum_circuit)


def test_translator_to_quantum_circuit_returns_circuit():
    """QiskitTranslator.to_quantum_circuit must return a QuantumCircuit."""
    from rqm_qiskit import QiskitTranslator
    t = QiskitTranslator()
    qc = t.to_quantum_circuit(_bell_circuit())
    assert isinstance(qc, QuantumCircuit)


def test_translator_to_quantum_circuit_include_report_returns_tuple():
    """QiskitTranslator.to_quantum_circuit(include_report=True) must return a tuple."""
    from rqm_qiskit import QiskitTranslator
    t = QiskitTranslator()
    result = t.to_quantum_circuit(_bell_circuit(), include_report=True)
    assert isinstance(result, tuple)
    assert len(result) == 2
    qc, report = result
    assert isinstance(qc, QuantumCircuit)


# ---------------------------------------------------------------------------
# QiskitTranslator.apply_gate
# ---------------------------------------------------------------------------


def test_translator_apply_gate_callable():
    """QiskitTranslator.apply_gate must be a callable method."""
    from rqm_qiskit import QiskitTranslator
    t = QiskitTranslator()
    assert callable(t.apply_gate)


def test_translator_apply_gate_h():
    """QiskitTranslator.apply_gate must apply an H gate descriptor."""
    from rqm_qiskit import QiskitTranslator
    t = QiskitTranslator()
    qc = QuantumCircuit(1)
    descriptor = {"gate": "h", "targets": [0], "controls": [], "params": {}}
    t.apply_gate(qc, descriptor)
    gate_names = [inst.operation.name for inst in qc.data]
    assert "h" in gate_names


def test_translator_apply_gate_x():
    """QiskitTranslator.apply_gate must apply an X gate descriptor."""
    from rqm_qiskit import QiskitTranslator
    t = QiskitTranslator()
    qc = QuantumCircuit(1)
    descriptor = {"gate": "x", "targets": [0], "controls": [], "params": {}}
    t.apply_gate(qc, descriptor)
    gate_names = [inst.operation.name for inst in qc.data]
    assert "x" in gate_names


def test_translator_apply_gate_rx():
    """QiskitTranslator.apply_gate must apply an Rx gate descriptor."""
    import math
    from rqm_qiskit import QiskitTranslator
    t = QiskitTranslator()
    qc = QuantumCircuit(1)
    descriptor = {"gate": "rx", "targets": [0], "controls": [], "params": {"angle": math.pi / 2}}
    t.apply_gate(qc, descriptor)
    gate_names = [inst.operation.name for inst in qc.data]
    assert "rx" in gate_names


# ---------------------------------------------------------------------------
# QiskitResult.to_dict() API shape
# ---------------------------------------------------------------------------


def test_qiskit_result_to_dict_required_keys():
    """QiskitResult.to_dict() must contain counts, shots, backend, metadata."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"00": 512, "11": 512}, shots=1024)
    d = result.to_dict()
    assert "counts" in d
    assert "shots" in d
    assert "backend" in d
    assert "metadata" in d


def test_qiskit_result_to_dict_counts_is_dict():
    """QiskitResult.to_dict() counts must be a dict."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"00": 512, "11": 512}, shots=1024)
    d = result.to_dict()
    assert isinstance(d["counts"], dict)


def test_qiskit_result_to_dict_shots_is_int():
    """QiskitResult.to_dict() shots must be an int."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"0": 1024}, shots=1024)
    d = result.to_dict()
    assert isinstance(d["shots"], int)


def test_qiskit_result_to_dict_backend_is_str():
    """QiskitResult.to_dict() backend must be a string."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"0": 1024}, shots=1024)
    d = result.to_dict()
    assert isinstance(d["backend"], str)


def test_qiskit_result_to_dict_metadata_is_dict():
    """QiskitResult.to_dict() metadata must be a dict."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"0": 1024}, shots=1024)
    d = result.to_dict()
    assert isinstance(d["metadata"], dict)


def test_qiskit_result_to_dict_metadata_has_most_likely():
    """QiskitResult.to_dict() metadata must include most_likely."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"00": 512, "11": 512}, shots=1024)
    d = result.to_dict()
    assert "most_likely" in d["metadata"]


def test_qiskit_result_to_dict_is_json_serializable():
    """QiskitResult.to_dict() output must be JSON-serializable."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"00": 512, "11": 512}, shots=1024)
    d = result.to_dict()
    serialized = json.dumps(d)
    assert isinstance(serialized, str)


def test_qiskit_result_to_dict_custom_backend():
    """QiskitResult.to_dict(backend=...) must use provided backend name."""
    from rqm_qiskit import QiskitResult
    result = QiskitResult({"0": 100}, shots=100)
    d = result.to_dict(backend="my_backend")
    assert d["backend"] == "my_backend"


# ---------------------------------------------------------------------------
# run_qiskit output shape
# ---------------------------------------------------------------------------


def test_run_qiskit_output_is_dict():
    """run_qiskit must return a dict."""
    from rqm_qiskit import run_qiskit
    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(result, dict)


def test_run_qiskit_output_has_required_keys():
    """run_qiskit output must contain counts, shots, backend, metadata."""
    from rqm_qiskit import run_qiskit
    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert "counts" in result
    assert "shots" in result
    assert "backend" in result
    assert "metadata" in result


def test_run_qiskit_output_counts_is_dict():
    """run_qiskit counts must be a dict."""
    from rqm_qiskit import run_qiskit
    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(result["counts"], dict)


def test_run_qiskit_output_shots_is_int():
    """run_qiskit shots must be an int."""
    from rqm_qiskit import run_qiskit
    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(result["shots"], int)


def test_run_qiskit_output_backend_is_str():
    """run_qiskit backend must be a string."""
    from rqm_qiskit import run_qiskit
    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(result["backend"], str)


def test_run_qiskit_output_is_json_serializable():
    """run_qiskit output must be JSON-serializable."""
    from rqm_qiskit import run_qiskit
    result = run_qiskit(_single_qubit_circuit(), shots=64)
    serialized = json.dumps(result)
    assert isinstance(serialized, str)


def test_run_qiskit_output_metadata_has_most_likely():
    """run_qiskit metadata must include most_likely."""
    from rqm_qiskit import run_qiskit
    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert "most_likely" in result["metadata"]


# ---------------------------------------------------------------------------
# QiskitBackend.run result shape
# ---------------------------------------------------------------------------


def test_backend_run_result_is_qiskit_result():
    """QiskitBackend.run must return a QiskitResult."""
    from rqm_qiskit import QiskitBackend, QiskitResult
    backend = QiskitBackend()
    result = backend.run(_single_qubit_circuit(), shots=64)
    assert isinstance(result, QiskitResult)


def test_backend_run_result_to_dict_is_json_serializable():
    """QiskitBackend.run result.to_dict() must be JSON-serializable."""
    from rqm_qiskit import QiskitBackend
    backend = QiskitBackend()
    result = backend.run(_single_qubit_circuit(), shots=64)
    d = result.to_dict()
    serialized = json.dumps(d)
    assert isinstance(serialized, str)


def test_backend_run_result_to_dict_has_counts():
    """QiskitBackend.run result.to_dict() must have counts key."""
    from rqm_qiskit import QiskitBackend
    backend = QiskitBackend()
    result = backend.run(_single_qubit_circuit(), shots=64)
    d = result.to_dict()
    assert "counts" in d


def test_backend_run_result_to_dict_has_shots():
    """QiskitBackend.run result.to_dict() must have shots key."""
    from rqm_qiskit import QiskitBackend
    backend = QiskitBackend()
    result = backend.run(_single_qubit_circuit(), shots=64)
    d = result.to_dict()
    assert "shots" in d
