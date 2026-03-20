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
from rqm_qiskit import run_qiskit, to_qiskit_circuit

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

# Tier 1 — run and get a JSON-compatible result dict
result = run_qiskit(c, shots=1024)
print(result["counts"])   # {"00": ~512, "11": ~512}

# Tier 2 — translate only (no execution)
qc = to_qiskit_circuit(c)
print(qc.draw(output="text"))
```

See the [Public API](#public-api) section for the full tier breakdown.

---

## Public API

```python
from rqm_qiskit import (
    QiskitBackend,      # OO entry point
    QiskitTranslator,   # translation class
    to_qiskit_circuit,  # functional translation API
    run_qiskit,         # functional execution API
)
```

The API is organized into three explicit tiers.  **Start with the highest tier
that covers your use case.**

---

### Tier 1 — Execution  *(start here)*

Both surfaces do the same thing: compile, translate, and run a circuit,
returning a structured result.  Choose whichever style fits your code.

| Style | Entry point | Returns |
|-------|-------------|---------|
| **Functional** *(primary)* | `run_qiskit(circuit, *, shots, optimize, include_report)` | `dict` (JSON-compatible) |
| **OO** *(equivalent)* | `QiskitBackend().run(circuit, *, shots, optimize, include_report)` | `QiskitResult` |

**Functional** — returns a plain `dict` ready for APIs / serialization:

```python
from rqm_compiler import Circuit
from rqm_qiskit import run_qiskit

c = Circuit(2)
c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)

result = run_qiskit(c, shots=1024)
# {
#   "counts":   {"00": 512, "11": 512},
#   "shots":    1024,
#   "backend":  "aer_simulator",
#   "metadata": {"outcomes": 2, "most_likely": "00"},
# }
```

With compiler report (when `rqm_compiler.optimize_circuit` is available):

```python
result = run_qiskit(c, optimize=True, shots=1024, include_report=True)
# metadata gains: {"optimized": True, "compiler_report": {...}}
```

**OO** — returns a `QiskitResult` with convenience methods:

```python
from rqm_compiler import Circuit
from rqm_qiskit import QiskitBackend

c = Circuit(2)
c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)

result = QiskitBackend().run(c, shots=1024)
print(result.counts)                 # {"00": ~512, "11": ~512}
print(result.most_likely_bitstring())
print(result.to_dict())              # same JSON-compatible dict as run_qiskit
```

---

### Tier 2 — Translation

Use these when you need the `QuantumCircuit` object itself (for inspection,
custom execution, serialization, or third-party tooling).

| Style | Entry point | Returns |
|-------|-------------|---------|
| **Functional** | `to_qiskit_circuit(circuit, *, optimize, include_report)` | `QuantumCircuit` (or tuple) |
| **OO** | `QiskitTranslator().to_quantum_circuit(circuit, *, optimize, include_report)` | `QuantumCircuit` (or tuple) |

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_qiskit_circuit

c = Circuit(2)
c.h(0); c.cx(0, 1)

qc = to_qiskit_circuit(c)
print(qc.draw(output="text"))

# With report tuple
qc, report = to_qiskit_circuit(c, optimize=True, include_report=True)
```

`QiskitTranslator` also exposes `apply_gate(qc, descriptor)` for applying
a single canonical gate descriptor to an existing `QuantumCircuit`.

---

### Tier 3 — Advanced / Internal

Reach for these only when Tiers 1–2 are not enough.

| Entry point | Purpose |
|-------------|---------|
| `QiskitBackend().compile(circuit, *, optimize, include_report)` | Translate only (OO alias for Tier 2) |
| `QiskitBackend().run_local(circuit, shots, optimize)` | Run on local Aer (returns `QiskitResult`) |
| `compiled_circuit_to_qiskit(source)` | Core lowering path (all Tier 1–2 routes through this) |
| `run_local(circuit, shots, optimize)` | Raw Aer execution (returns `dict[str, int]`) |
| `run_backend(circuit, backend, shots)` | Raw real-backend execution |
| `spinor_to_circuit(α, β, target)` | Spinor → `QuantumCircuit` (delegates math to `rqm-core`) |
| `bloch_to_circuit(θ, φ, target)` | Bloch angles → `QuantumCircuit` |
| `QiskitResult` | Structured result wrapper (`counts`, `probabilities`, `to_dict()`) |
| `RQMState`, `RQMGate`, `RQMCircuit` | Legacy / transitional helpers |

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

