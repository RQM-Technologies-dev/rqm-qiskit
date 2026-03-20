"""
Tests for the run_qiskit execution API.

Covers:
- run_qiskit returns standardized dict with required keys
- run_qiskit with optimize=False works
- run_qiskit with include_report=True includes metadata
- run_qiskit with backend=None uses local Aer simulator
- run_qiskit result is JSON-serializable
- run_qiskit with string backend raises NotImplementedError
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
# run_qiskit – basic execution
# ---------------------------------------------------------------------------


def test_run_qiskit_returns_dict():
    """run_qiskit must return a dict."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_bell_circuit(), shots=64)
    assert isinstance(result, dict)


def test_run_qiskit_has_required_keys():
    """run_qiskit result must contain counts, shots, backend, metadata."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_bell_circuit(), shots=64)
    assert "counts" in result
    assert "shots" in result
    assert "backend" in result
    assert "metadata" in result


def test_run_qiskit_shots_value():
    """run_qiskit shots value must match the requested shots."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=128)
    assert result["shots"] == 128


def test_run_qiskit_default_shots():
    """run_qiskit default shots must be 1024."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit())
    assert result["shots"] == 1024


def test_run_qiskit_counts_nonempty():
    """run_qiskit counts must be non-empty."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert len(result["counts"]) > 0


def test_run_qiskit_counts_sum_equals_shots():
    """run_qiskit counts must sum to shots."""
    from rqm_qiskit import run_qiskit

    shots = 256
    result = run_qiskit(_single_qubit_circuit(), shots=shots)
    assert sum(result["counts"].values()) == shots


def test_run_qiskit_backend_is_string():
    """run_qiskit backend field must be a string."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(result["backend"], str)


def test_run_qiskit_metadata_is_dict():
    """run_qiskit metadata must be a dict."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert isinstance(result["metadata"], dict)


def test_run_qiskit_metadata_most_likely():
    """run_qiskit metadata must include most_likely."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64)
    assert "most_likely" in result["metadata"]


def test_run_qiskit_optimize_false():
    """run_qiskit with optimize=False must succeed."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_bell_circuit(), shots=64, optimize=False)
    assert isinstance(result, dict)
    assert "counts" in result


def test_run_qiskit_is_json_serializable():
    """run_qiskit result must be JSON-serializable."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64)
    serialized = json.dumps(result)
    assert isinstance(serialized, str)


def test_run_qiskit_bell_state_counts():
    """run_qiskit with Bell circuit must produce only 00 and 11 outcomes."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_bell_circuit(), shots=256)
    for key in result["counts"]:
        assert key in ("00", "11"), f"Unexpected key: {key}"


def test_run_qiskit_backend_none_uses_aer():
    """run_qiskit with backend=None must use local Aer simulator."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64, backend=None)
    assert isinstance(result, dict)
    assert "counts" in result


def test_run_qiskit_string_backend_raises():
    """run_qiskit with string backend must raise NotImplementedError."""
    from rqm_qiskit import run_qiskit

    with pytest.raises(NotImplementedError):
        run_qiskit(_single_qubit_circuit(), shots=64, backend="ibm_nairobi")


# ---------------------------------------------------------------------------
# run_qiskit – include_report
# ---------------------------------------------------------------------------


def test_run_qiskit_include_report_false_returns_dict():
    """run_qiskit with include_report=False must return a plain dict."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64, include_report=False)
    assert isinstance(result, dict)


def test_run_qiskit_include_report_true_has_optimized_key():
    """run_qiskit with include_report=True must include 'optimized' in metadata."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64, include_report=True)
    assert "optimized" in result["metadata"]
    assert result["metadata"]["optimized"] is False  # optimize=False by default


def test_run_qiskit_include_report_true_has_compiler_report_key():
    """run_qiskit with include_report=True must include 'compiler_report' in metadata."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64, include_report=True)
    assert "compiler_report" in result["metadata"]


def test_run_qiskit_include_report_true_is_json_serializable():
    """run_qiskit with include_report=True result must be JSON-serializable."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_single_qubit_circuit(), shots=64, include_report=True)
    serialized = json.dumps(result)
    assert isinstance(serialized, str)
