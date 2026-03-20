# rqm-qiskit

**Qiskit translation and execution layer for the RQM compiler ecosystem.**

Translates canonical RQM circuits (defined by `rqm-compiler`) into Qiskit
`QuantumCircuit` objects and runs them on Aer simulators or IBM Quantum hardware.

---

## Architecture

`rqm-qiskit` occupies a single, well-defined layer in the RQM dependency spine:

```
rqm-core        (canonical math: Quaternion, SU(2), Bloch, spinor)
       ↓
rqm-compiler    (canonical gate/circuit IR: Circuit, Operation, compile_circuit)
       ↓
rqm-qiskit      (Qiskit translation + execution)
       ↓
 Qiskit QuantumCircuit / transpilation / execution
```

### Layer responsibilities

| Package | Responsibility |
|---------|----------------|
| `rqm-core` | Quaternion algebra, SU(2) matrices, Bloch conversions, spinor helpers |
| `rqm-compiler` | Canonical gate/circuit IR (`Circuit`, `Operation`), normalization, compilation pipeline |
| `rqm-qiskit` | Descriptor translation to Qiskit; Aer/IBM execution; API-ready result shaping |

### What this repo owns

- Descriptor → Qiskit gate mapping
- Qiskit `QuantumCircuit` generation
- Qiskit/Aer execution
- API-ready result shaping

### What this repo does not own

- Physics math
- Quaternion algebra
- Compiler passes
- Optimization logic
- IR schema

---

## Installation

Install from PyPI:

```bash
pip install rqm-qiskit
```

Dependencies:
- `rqm-core` — canonical quantum math
- `rqm-compiler` — canonical IR and compilation
- `qiskit` — quantum circuit execution

To also run local simulations (recommended):

```bash
pip install "rqm-qiskit[simulator]"
```

For development:

```bash
git clone https://github.com/RQM-Technologies-dev/rqm-qiskit.git
cd rqm-qiskit
pip install -e ".[dev,simulator]"
```

---

## Quickstart

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_qiskit_circuit, run_qiskit

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

# Translate to a Qiskit QuantumCircuit
qc = to_qiskit_circuit(c)
print(qc.draw(output="text"))

# Run and get a standardized result dict
result = run_qiskit(c, shots=1024)
print(result["counts"])    # {"00": ~512, "11": ~512}
print(result["backend"])   # "aer_simulator"

# With compiler report (when optimization is available)
qc, report = to_qiskit_circuit(c, optimize=True, include_report=True)
result = run_qiskit(c, optimize=True, shots=1024, include_report=True)
```

---

## Required Public API

```python
from rqm_qiskit import (
    QiskitBackend,
    QiskitTranslator,
    to_qiskit_circuit,
    run_qiskit,
)
```

### `to_qiskit_circuit(circuit, *, optimize=False, include_report=False)`

Translate an `rqm_compiler.Circuit` to a Qiskit `QuantumCircuit`.

- `optimize=False` → calls `compile_circuit(circuit)` (faithful compile)
- `optimize=True` → calls `optimize_circuit(circuit)` (requires rqm-compiler support)
- `include_report=True` → returns `(QuantumCircuit, report)` tuple

### `run_qiskit(circuit, *, optimize=False, shots=1024, backend=None, include_report=False, **kwargs)`

Compile, translate, and run; return a standardized JSON-compatible dict:

```python
{
    "counts": {"00": 512, "11": 512},
    "shots": 1024,
    "backend": "aer_simulator",
    "metadata": {"outcomes": 2, "most_likely": "00"},
}
```

With `include_report=True`:

```python
{
    "counts": {...},
    "shots": 1024,
    "backend": "aer_simulator",
    "metadata": {
        "optimized": True,
        "compiler_report": {...},
    },
}
```

### `QiskitTranslator`

```python
class QiskitTranslator:
    def to_quantum_circuit(self, circuit, *, optimize=False, include_report=False): ...
    def apply_gate(self, qc, descriptor): ...
    def compile_to_circuit(self, source, optimize=False): ...  # legacy alias
```

### `QiskitBackend`

```python
class QiskitBackend:
    def compile(self, circuit, *, optimize=False, include_report=False): ...
    def run(self, circuit, *, optimize=False, shots=1024, backend=None, include_report=False, **kwargs): ...
    def run_local(self, circuit_or_program, shots=100, optimize=False): ...
```

---

## Supported Gates

All canonical gates from `rqm-compiler`:

| Category | Gates |
|----------|-------|
| Single-qubit named | `i`, `x`, `y`, `z`, `h`, `s`, `t` |
| Single-qubit parametric | `rx`, `ry`, `rz`, `phaseshift` |
| Canonical SU(2) | `u1q` (quaternion → `UnitaryGate`) |
| Two-qubit | `cx`, `cy`, `cz`, `swap`, `iswap` |
| Other | `measure`, `barrier` |

### `u1q` Translation

`u1q` is the canonical single-qubit unitary from `rqm-compiler`, parameterized
as a unit quaternion `(w, x, y, z)`.  This package converts it to a 2×2 SU(2)
matrix via `rqm_core.Quaternion.to_su2_matrix()` and passes it to Qiskit's
`UnitaryGate` — no local quaternion math is implemented here.

---

## Object-Oriented API

```python
from rqm_compiler import Circuit
from rqm_qiskit import QiskitBackend

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

backend = QiskitBackend()

# Translate only
qc = backend.compile(c)

# Translate + run
result = backend.run(c, shots=1024)
print(result.counts)
print(result.most_likely_bitstring())
print(result.to_dict())   # JSON-serialisable API-ready dict
```

---

## Convenience Bridges

Two thin bridge functions map physical state representations to Qiskit circuits.
**All physics is delegated to rqm-core.**

### `spinor_to_circuit(alpha, beta, target=0)`

Converts a spinor `(α, β)` to a `QuantumCircuit` via:
1. Normalize via `rqm_core.spinor.normalize_spinor`
2. Convert to Bloch vector via `rqm_core.bloch.state_to_bloch`
3. Map `(θ, φ)` → `RY(θ) RZ(φ)` Qiskit gates

### `bloch_to_circuit(theta, phi, target=0)`

Converts Bloch angles `(θ, φ)` to `RY(θ) RZ(φ)` Qiskit gates.

---

## Optimization (Optional)

`rqm-qiskit` exposes the `optimize=True` flag, which delegates to
`rqm_compiler.optimize_circuit`.  If that function is not yet available in
the installed `rqm-compiler` version, an `ImportError` is raised.

For external optimization (e.g. `rqm-optimize`), apply it **before** passing
the circuit to `rqm-qiskit`:

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_qiskit_circuit
from rqm_optimize import optimize_circuit  # installed separately

c = Circuit(2)
c.h(0)
c.cx(0, 1)

optimized, report = optimize_circuit(c)
qc = to_qiskit_circuit(optimized)
```

> **Important:** Do **not** add `rqm-optimize` as a dependency of `rqm-qiskit`.

---

## Package Structure

```
rqm-qiskit/
├── src/
│   └── rqm_qiskit/
│       ├── __init__.py       – public API exports
│       ├── translator.py     – QiskitTranslator, to_qiskit_circuit
│       ├── backend.py        – QiskitBackend
│       ├── execution.py      – run_qiskit, run_local, run_backend
│       ├── result.py         – QiskitResult
│       ├── convert.py        – compiled_circuit_to_qiskit (core lowering)
│       ├── bridges.py        – spinor_to_circuit, bloch_to_circuit
│       ├── utils.py          – internal utilities
│       └── ...               – legacy/transitional helpers
└── tests/
    ├── test_translation.py
    ├── test_execution.py
    ├── test_optimize_toggle.py
    ├── test_u1q.py
    └── test_api_shape.py
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

