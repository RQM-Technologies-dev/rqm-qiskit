"""
Tests for the optimize toggle behavior.

Covers:
- to_qiskit_circuit with optimize=False (faithful compilation)
- to_qiskit_circuit with optimize=True raises ImportError when unavailable
- to_qiskit_circuit with include_report=True returns tuple
- QiskitBackend.compile with optimize flag
- QiskitBackend.run with optimize flag
- run_qiskit with optimize flag
"""

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
# to_qiskit_circuit – optimize=False (faithful compile)
# ---------------------------------------------------------------------------


def test_to_qiskit_circuit_optimize_false_returns_quantum_circuit():
    """to_qiskit_circuit(optimize=False) must return a QuantumCircuit."""
    from rqm_qiskit import to_qiskit_circuit

    qc = to_qiskit_circuit(_bell_circuit(), optimize=False)
    assert isinstance(qc, QuantumCircuit)


def test_to_qiskit_circuit_optimize_false_correct_qubit_count():
    """to_qiskit_circuit(optimize=False) must preserve qubit count."""
    from rqm_qiskit import to_qiskit_circuit

    qc = to_qiskit_circuit(_bell_circuit(), optimize=False)
    assert qc.num_qubits == 2


def test_to_qiskit_circuit_default_optimize_is_false():
    """to_qiskit_circuit default must behave as optimize=False."""
    from rqm_qiskit import to_qiskit_circuit

    qc = to_qiskit_circuit(_bell_circuit())
    assert isinstance(qc, QuantumCircuit)


# ---------------------------------------------------------------------------
# to_qiskit_circuit – include_report=False (default)
# ---------------------------------------------------------------------------


def test_to_qiskit_circuit_include_report_false_returns_circuit():
    """to_qiskit_circuit(include_report=False) must return just a QuantumCircuit."""
    from rqm_qiskit import to_qiskit_circuit

    result = to_qiskit_circuit(_bell_circuit(), include_report=False)
    assert isinstance(result, QuantumCircuit)


def test_to_qiskit_circuit_include_report_true_optimize_false_returns_tuple():
    """to_qiskit_circuit(include_report=True, optimize=False) must return a tuple."""
    from rqm_qiskit import to_qiskit_circuit

    result = to_qiskit_circuit(_bell_circuit(), optimize=False, include_report=True)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_to_qiskit_circuit_include_report_true_first_is_circuit():
    """to_qiskit_circuit(include_report=True) tuple first element must be QuantumCircuit."""
    from rqm_qiskit import to_qiskit_circuit

    qc, report = to_qiskit_circuit(_bell_circuit(), optimize=False, include_report=True)
    assert isinstance(qc, QuantumCircuit)


def test_to_qiskit_circuit_include_report_true_report_is_none_when_not_optimized():
    """to_qiskit_circuit(include_report=True, optimize=False) report must be None."""
    from rqm_qiskit import to_qiskit_circuit

    _, report = to_qiskit_circuit(_bell_circuit(), optimize=False, include_report=True)
    assert report is None


# ---------------------------------------------------------------------------
# to_qiskit_circuit – optimize=True (requires rqm_compiler.optimize_circuit)
# ---------------------------------------------------------------------------


def test_to_qiskit_circuit_optimize_true_raises_when_unavailable():
    """to_qiskit_circuit(optimize=True) must raise ImportError when optimize_circuit
    is not available in the installed rqm-compiler."""
    from rqm_qiskit import to_qiskit_circuit

    # rqm_compiler.optimize_circuit is not in the current release
    with pytest.raises(ImportError, match="optimize"):
        to_qiskit_circuit(_bell_circuit(), optimize=True)


# ---------------------------------------------------------------------------
# QiskitBackend.compile – optimize toggle
# ---------------------------------------------------------------------------


def test_backend_compile_optimize_false_returns_circuit():
    """QiskitBackend.compile(optimize=False) must return a QuantumCircuit."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    qc = backend.compile(_bell_circuit(), optimize=False)
    assert isinstance(qc, QuantumCircuit)


def test_backend_compile_include_report_false_returns_circuit():
    """QiskitBackend.compile(include_report=False) must return a plain QuantumCircuit."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    result = backend.compile(_bell_circuit(), optimize=False, include_report=False)
    assert isinstance(result, QuantumCircuit)


def test_backend_compile_include_report_true_returns_tuple():
    """QiskitBackend.compile(include_report=True) must return a tuple."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    result = backend.compile(_bell_circuit(), optimize=False, include_report=True)
    assert isinstance(result, tuple)
    assert len(result) == 2
    qc, report = result
    assert isinstance(qc, QuantumCircuit)


def test_backend_compile_optimize_true_raises_when_unavailable():
    """QiskitBackend.compile(optimize=True) must raise ImportError when unavailable."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    with pytest.raises(ImportError, match="optimize"):
        backend.compile(_bell_circuit(), optimize=True)


# ---------------------------------------------------------------------------
# QiskitBackend.run – optimize and include_report
# ---------------------------------------------------------------------------


def test_backend_run_optimize_false_returns_result():
    """QiskitBackend.run(optimize=False) must return a QiskitResult."""
    from rqm_qiskit import QiskitBackend, QiskitResult

    backend = QiskitBackend()
    result = backend.run(_bell_circuit(), shots=64, optimize=False)
    assert isinstance(result, QiskitResult)


def test_backend_run_include_report_false_returns_result():
    """QiskitBackend.run(include_report=False) must return a plain QiskitResult."""
    from rqm_qiskit import QiskitBackend, QiskitResult

    backend = QiskitBackend()
    result = backend.run(_single_qubit_circuit(), shots=64, include_report=False)
    assert isinstance(result, QiskitResult)


def test_backend_run_include_report_true_returns_tuple():
    """QiskitBackend.run(include_report=True) must return (QiskitResult, report)."""
    from rqm_qiskit import QiskitBackend, QiskitResult

    backend = QiskitBackend()
    result = backend.run(_single_qubit_circuit(), shots=64, include_report=True)
    assert isinstance(result, tuple)
    assert len(result) == 2
    qr, report = result
    assert isinstance(qr, QiskitResult)


def test_backend_run_optimize_true_raises_when_unavailable():
    """QiskitBackend.run(optimize=True) must raise ImportError when unavailable."""
    from rqm_qiskit import QiskitBackend

    backend = QiskitBackend()
    with pytest.raises(ImportError, match="optimize"):
        backend.run(_bell_circuit(), shots=64, optimize=True)


# ---------------------------------------------------------------------------
# run_qiskit – optimize toggle
# ---------------------------------------------------------------------------


def test_run_qiskit_optimize_false():
    """run_qiskit with optimize=False must return a valid result dict."""
    from rqm_qiskit import run_qiskit

    result = run_qiskit(_bell_circuit(), shots=64, optimize=False)
    assert isinstance(result, dict)
    assert "counts" in result


def test_run_qiskit_optimize_true_raises_when_unavailable():
    """run_qiskit with optimize=True must raise ImportError when unavailable."""
    from rqm_qiskit import run_qiskit

    with pytest.raises(ImportError, match="optimize"):
        run_qiskit(_bell_circuit(), shots=64, optimize=True)
