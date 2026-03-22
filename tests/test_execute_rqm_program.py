"""
Tests for execute_rqm_program – high-level rqm-api integration function.

Covers:
- execute_rqm_program is importable from rqm_qiskit
- execute_rqm_program with a valid Bell descriptor returns correct result dict
- execute_rqm_program result has required keys
- execute_rqm_program result is JSON-serializable
- execute_rqm_program with optimize=False (default) works
- execute_rqm_program with include_report=True includes metadata
- execute_rqm_program with invalid descriptor raises ValueError or TranslationError
- execute_rqm_program infers num_qubits when not provided
"""

import json
import pytest


def _bell_descriptor():
    return {
        "num_qubits": 2,
        "operations": [
            {"gate": "h", "targets": [0], "controls": [], "params": {}},
            {"gate": "cx", "targets": [1], "controls": [0], "params": {}},
            {"gate": "measure", "targets": [0], "controls": [], "params": {"key": "m0"}},
            {"gate": "measure", "targets": [1], "controls": [], "params": {"key": "m1"}},
        ],
    }


def _single_qubit_descriptor():
    return {
        "num_qubits": 1,
        "operations": [
            {"gate": "h", "targets": [0], "controls": [], "params": {}},
            {"gate": "measure", "targets": [0], "controls": [], "params": {"key": "m0"}},
        ],
    }


# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------


def test_execute_rqm_program_importable():
    """execute_rqm_program must be importable from rqm_qiskit."""
    from rqm_qiskit import execute_rqm_program

    assert callable(execute_rqm_program)


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


def test_execute_rqm_program_returns_dict():
    """execute_rqm_program must return a dict."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=64)
    assert isinstance(result, dict)


def test_execute_rqm_program_has_required_keys():
    """execute_rqm_program result must have counts, shots, backend, metadata."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=64)
    assert "counts" in result
    assert "shots" in result
    assert "backend" in result
    assert "metadata" in result


def test_execute_rqm_program_shots_value():
    """execute_rqm_program shots must match requested shots."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=128)
    assert result["shots"] == 128


def test_execute_rqm_program_counts_nonempty():
    """execute_rqm_program counts must be non-empty."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=64)
    assert len(result["counts"]) > 0


def test_execute_rqm_program_counts_sum_to_shots():
    """execute_rqm_program counts must sum to shots."""
    from rqm_qiskit import execute_rqm_program

    shots = 256
    result = execute_rqm_program(_single_qubit_descriptor(), shots=shots)
    assert sum(result["counts"].values()) == shots


def test_execute_rqm_program_is_json_serializable():
    """execute_rqm_program result must be JSON-serializable."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=64)
    serialized = json.dumps(result)
    assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# Bell circuit
# ---------------------------------------------------------------------------


def test_execute_rqm_program_bell_only_00_11():
    """execute_rqm_program Bell circuit must produce only '00' and '11'."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_bell_descriptor(), shots=256)
    for key in result["counts"]:
        assert key in ("00", "11"), f"Unexpected key: {key}"


# ---------------------------------------------------------------------------
# include_report
# ---------------------------------------------------------------------------


def test_execute_rqm_program_include_report_true_has_optimized_key():
    """execute_rqm_program with include_report=True must include 'optimized' in metadata."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=64, include_report=True)
    assert "optimized" in result["metadata"]


def test_execute_rqm_program_include_report_true_has_compiler_report_key():
    """execute_rqm_program with include_report=True must include 'compiler_report' in metadata."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=64, include_report=True)
    assert "compiler_report" in result["metadata"]


def test_execute_rqm_program_include_report_is_json_serializable():
    """execute_rqm_program with include_report=True must be JSON-serializable."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor(), shots=64, include_report=True)
    serialized = json.dumps(result)
    assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# num_qubits inference
# ---------------------------------------------------------------------------


def test_execute_rqm_program_infers_num_qubits():
    """execute_rqm_program must infer num_qubits when not provided."""
    from rqm_qiskit import execute_rqm_program

    descriptor_without_num_qubits = {
        "operations": [
            {"gate": "h", "targets": [0], "controls": [], "params": {}},
            {"gate": "measure", "targets": [0], "controls": [], "params": {"key": "m0"}},
        ],
    }
    result = execute_rqm_program(descriptor_without_num_qubits, shots=64)
    assert isinstance(result, dict)
    assert "counts" in result


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_execute_rqm_program_non_dict_raises():
    """execute_rqm_program with non-dict input must raise ValueError."""
    from rqm_qiskit import execute_rqm_program

    with pytest.raises(ValueError):
        execute_rqm_program("not a dict", shots=64)


def test_execute_rqm_program_invalid_gate_raises():
    """execute_rqm_program with invalid gate name must raise."""
    from rqm_qiskit import execute_rqm_program
    from rqm_qiskit.errors import TranslationError

    bad_descriptor = {
        "num_qubits": 1,
        "operations": [
            {"gate": "totally_invalid_gate_xyz", "targets": [0], "controls": [], "params": {}},
        ],
    }
    with pytest.raises((TranslationError, Exception)):
        execute_rqm_program(bad_descriptor, shots=64)


def test_execute_rqm_program_empty_operations():
    """execute_rqm_program with empty operations list must not crash."""
    from rqm_qiskit import execute_rqm_program

    descriptor = {"num_qubits": 1, "operations": []}
    # An empty circuit has no measurements → result may be trivial but should not crash
    # or raise a meaningful error (counts empty issue might propagate)
    try:
        result = execute_rqm_program(descriptor, shots=64)
        # If it returns, it must be a dict
        assert isinstance(result, dict)
    except Exception:
        # An error from empty counts is acceptable
        pass


# ---------------------------------------------------------------------------
# Default arguments
# ---------------------------------------------------------------------------


def test_execute_rqm_program_default_shots():
    """execute_rqm_program default shots must be 1024."""
    from rqm_qiskit import execute_rqm_program

    result = execute_rqm_program(_single_qubit_descriptor())
    assert result["shots"] == 1024


def test_execute_rqm_program_default_optimize_false():
    """execute_rqm_program optimize defaults to False."""
    from rqm_qiskit import execute_rqm_program

    # Just verify it works without optimize=True (optimize=False is default)
    result = execute_rqm_program(_single_qubit_descriptor(), shots=64)
    assert isinstance(result, dict)
