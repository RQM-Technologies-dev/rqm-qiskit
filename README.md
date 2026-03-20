# rqm-qiskit

**Thin Qiskit bridge layer for the RQM quantum ecosystem** — translates
canonical RQM circuits and gates (owned by rqm-compiler) into Qiskit
primitives and runs them on Aer simulators or IBM Quantum hardware.

---

## Architecture

`rqm-qiskit` occupies a single, well-defined layer in the RQM dependency
spine:

```
rqm-core        (canonical math: Quaternion, SU(2), Bloch, spinor)
       ↓
rqm-compiler    (canonical gate/circuit IR: Circuit, Operation, compilation)
       ↓
rqm-qiskit      (Qiskit bridge: circuit lowering, IBM execution helpers)
       ↓
[rqm-optimize]  (optional: circuit optimization — see Optimization section)
       ↓
rqm-notebooks   (interactive notebooks and tutorials)
```

The full pipeline with optional optimization:

```
compile → lower → optimize → run
```

### Layer responsibilities

| Package | Responsibility |
|---------|----------------|
| `rqm-core` | Quaternion algebra, SU(2) matrices, Bloch conversions, spinor helpers |
| `rqm-compiler` | Canonical gate/circuit IR (`Circuit`, `Operation`), normalization, compilation pipeline |
| `rqm-qiskit` | Lower rqm-compiler IR to Qiskit `QuantumCircuit`; Aer/IBM execution helpers; thin user-facing wrappers |
| `rqm-notebooks` | Jupyter notebooks, tutorials, interactive demonstrations |

### What rqm-qiskit owns

**Primary entrypoints (prefer these):**
- `QiskitBackend.run()` — one-call compile-and-execute; the canonical entry
  point for running circuits.
- `to_backend_circuit()` — translate an `rqm_compiler.Circuit` to a Qiskit
  `QuantumCircuit` without executing it; use when you only need the circuit
  object.

**Internal lowering path (used by the entrypoints above):**
- `compiled_circuit_to_qiskit()` — the core bridge function that all
  translation helpers route through.

**Compatibility helpers (use when the primary entrypoints are not enough):**
- `RQMCircuit` — thin façade over `rqm_compiler.Circuit`; adds Qiskit-specific
  state preparation (`initialize`) and `.to_qiskit()`.
- `RQMGate` — adds `.to_operation()` and `.to_qiskit_gate()` on top of the
  rqm-core SU(2) matrix.
- `RQMState` — Qiskit-facing helpers (`.vector()`, `.as_statevector()`) on top
  of rqm-core spinor/Bloch math.
- `run_on_aer_sampler()` / IBM Runtime helpers in `ibm.py`.
- Result formatting in `results.py`.

### What rqm-qiskit does NOT own

`rqm-qiskit` does not implement canonical math.  It delegates all math
operations to rqm-core.

Specifically, `rqm-qiskit` contains **no** quaternion math, **no** spinor
normalization, **no** Bloch conversions, and **no** SU(2) decomposition of its
own.  All canonical logic is delegated to rqm-core and rqm-compiler.

### Architecture Guarantees

These invariants are stable and hold across all public helpers in this package:

| Guarantee | Detail |
|-----------|--------|
| **Canonical math lives in rqm-core** | Quaternion algebra, SU(2) matrices, Bloch-vector conversions, and spinor normalization are owned exclusively by `rqm-core`.  `rqm-qiskit` never reimplements them. |
| **Canonical circuit IR lives in rqm-compiler** | `rqm_compiler.Circuit`, `rqm_compiler.Operation`, and the compilation pipeline are the single source of truth for gate and circuit semantics. |
| **`compiled_circuit_to_qiskit()` is the primary lowering path** | Every helper that converts a gate or circuit to a Qiskit `QuantumCircuit` routes through `compiled_circuit_to_qiskit()`.  There is no second, parallel lowering path. |
| **`state_to_quantum_circuit()` is the only documented exception** | State preparation uses Qiskit's `initialize` instruction, which has no equivalent in the rqm-compiler IR.  It therefore cannot route through the main lowering path and is explicitly documented as the sole exception. |

In practice this means:
- `RQMCircuit.to_qiskit()` calls `compiled_circuit_to_qiskit()` internally.
- `gate_to_quantum_circuit()` builds a 1-op `rqm_compiler.Circuit` and calls `compiled_circuit_to_qiskit()`.
- New helpers added in future versions **must** route through `compiled_circuit_to_qiskit()` unless there is an explicit, documented reason not to.

---

## What Is This?

`rqm-qiskit` is a clean, beginner-friendly Python package that bridges
**rqm-compiler** (the canonical RQM circuit layer) and **Qiskit** (the
execution engine).

The key insight:

> A single-qubit state lives on the Bloch sphere.  
> Rotations of the Bloch sphere are SU(2) transformations.  
> SU(2) is isomorphic to the group of unit quaternions.

Therefore, **unit quaternions are the natural algebraic object for 1-qubit
quantum states and gates**.  rqm-core owns that algebra; rqm-compiler owns
circuit structure; rqm-qiskit exposes the geometry to Qiskit users and
handles execution.

**This package is not trying to replace Qiskit.**  
It is a thin bridge — Qiskit does all the heavy lifting under the hood.

---

## Quaternion Intuition for Qubits

A unit quaternion `q = w + x·i + y·j + z·k` (with `|q| = 1`) corresponds to an
SU(2) matrix via:

```
U = [[w − i·z,  −(y + i·x)],
     [y − i·x,   w + i·z  ]]
```

This means:

| Operation | Quaternion form |
|-----------|----------------|
| Identity (no rotation) | `q = 1` |
| R_x(θ) | `q = cos(θ/2) + sin(θ/2)·i` |
| R_y(θ) | `q = cos(θ/2) + sin(θ/2)·j` |
| R_z(θ) | `q = cos(θ/2) + sin(θ/2)·k` |
| Compose two gates | `q_total = q2 * q1` (right-to-left) |

Every `RQMGate` exposes its `quaternion` property.  Every `RQMState` exposes
`to_quaternion()` — the rotation that prepares it from `|0>`.

---

## Why Does This Exist?

- **Geometric intuition**: unit quaternions make SU(2) rotations concrete and composable.
- **Quaternionic quantum mechanics**: a foundation for richer RQM educational tooling.
- **Educational clarity**: fewer raw matrix operations, more geometric understanding.
- **IBM Quantum ready**: built on Qiskit so the path to real hardware is direct.

---

## Installation

Install from PyPI:

```bash
pip install rqm-qiskit
```

To also run local simulations (recommended):

```bash
pip install "rqm-qiskit[simulator]"
```

For development:

```bash
git clone https://github.com/RQM-Technologies-dev/rqm-qiskit.git
cd rqm-qiskit
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,simulator]"
```

---

## Public API Hierarchy

When in doubt, use the **highest-level entrypoint that fits your use case**.
This keeps your code simple, readable, and forward-compatible.

| Tier | Entrypoint | When to use |
|------|-----------|-------------|
| **1 — Run** | `QiskitBackend().run(circuit, shots=1024)` | Execute a circuit and get a result. **Start here.** |
| **2 — Translate** | `to_backend_circuit(circuit)` | Get a Qiskit `QuantumCircuit` without running it (e.g. for inspection, serialisation, or custom execution). |
| **3 — Compat helpers** | `compiled_circuit_to_qiskit()`, `compile_to_qiskit_circuit()`, `spinor_to_circuit()`, `bloch_to_circuit()`, `RQMCircuit`, `RQMGate`, `RQMState` | Lower-level access and educational / physics-oriented workflows. Reach for these only when Tiers 1–2 are not enough. |

### Tier 1 — `QiskitBackend.run()`

```python
from rqm_compiler import Circuit
from rqm_qiskit import QiskitBackend

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

result = QiskitBackend().run(c, shots=1024)
print(result.counts)               # {"00": ~512, "11": ~512}
print(result.most_likely_bitstring())
print(result.to_dict())            # JSON-serialisable API-ready dict
```

### Tier 2 — `to_backend_circuit()`

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_backend_circuit

c = Circuit(2)
c.h(0)
c.cx(0, 1)

qc = to_backend_circuit(c)        # returns qiskit.QuantumCircuit
print(qc.draw(output="text"))
```

### Tier 3 — Compatibility helpers

Use the lower-level helpers when you need fine-grained control, are working
with physical state representations (spinors, Bloch angles), or are following
an educational / exploration workflow:

```python
# Physical-state preparation (bridge functions)
from rqm_qiskit import spinor_to_circuit, bloch_to_circuit
import math

qc = bloch_to_circuit(math.pi / 2, 0.0)   # |+⟩ on Bloch equator

# Named-gate / rotation-gate facades
from rqm_qiskit import RQMState, RQMGate, RQMCircuit

state = RQMState.plus()
gate  = RQMGate.ry(0.6)
circ  = RQMCircuit(1)
circ.prepare_state(state)
circ.apply_gate(gate)
circ.measure_all()
print(circ.draw_text())
```

---

## Quickstart

The fastest path to a result:

```python
from rqm_compiler import Circuit
from rqm_qiskit import QiskitBackend

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

result = QiskitBackend().run(c, shots=1024)
print(result.counts)               # {"00": ~512, "11": ~512}
print(result.most_likely_bitstring())
print(result.to_dict())            # JSON-serialisable result for APIs
```

If you only need the translated `QuantumCircuit` (not execution):

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_backend_circuit

c = Circuit(2)
c.h(0)
c.cx(0, 1)

qc = to_backend_circuit(c)
print(qc.draw(output="text"))
```

For physics-oriented / educational workflows (Tier 3 helpers):

```python
from rqm_qiskit import RQMState, RQMGate, RQMCircuit

state = RQMState.plus()
gate = RQMGate.ry(0.6)

circ = RQMCircuit(1)
circ.prepare_state(state)
circ.apply_gate(gate)
circ.measure_all()

print(circ.draw_text())
```

Inspect the quaternion geometry:

```python
# State as a unit quaternion
q_state = state.to_quaternion()
print(q_state.pretty())           # Quaternion(0.7071 +0.0000i +0.7071j +0.0000k)  |q| = 1.000000

# Gate as a unit quaternion
q_gate = gate.quaternion
print(q_gate.pretty())

# Compose two gates as a single quaternion product
gate2 = RQMGate.rz(0.3)
q_composed = gate2.quaternion * gate.quaternion  # apply gate first, then gate2
print(q_composed.to_su2_matrix())  # the combined 2×2 SU(2) matrix
```

Run on the local Aer simulator (lower-level path):

```python
from rqm_qiskit import format_counts_summary
from rqm_qiskit.ibm import run_on_aer_sampler

counts = run_on_aer_sampler(circ.to_qiskit(), shots=1024)
print(format_counts_summary(counts))
```

---

## Package Structure

```
rqm-qiskit/
  src/
    rqm_qiskit/
      quaternion.py  – Quaternion: thin shim re-exporting from rqm-core
      state.py       – RQMState: Qiskit-bridge wrapper over rqm-core spinor math
      gates.py       – RQMGate: dual-mode gate; re-exports gate factories from rqm-core
      circuit.py     – RQMCircuit: façade over rqm_compiler.Circuit + to_qiskit()
      convert.py     – compiled_circuit_to_qiskit(); state/gate convenience wrappers
      translator.py  – QiskitTranslator, compile_to_qiskit_circuit, to_backend_circuit
      execution.py   – run_local, run_backend
      backend.py     – QiskitBackend: unified entry point
      result.py      – QiskitResult: structured result wrapper
      bridges.py     – spinor_to_circuit, bloch_to_circuit (bridge functions)
      results.py     – summarize_counts, format_counts_summary
      ibm.py         – Aer sampler helper + IBM Runtime stub
      utils.py       – internal utilities
  tests/             – pytest test suite (256 tests)
  examples/          – runnable example scripts
  AGENTS.md          – coding agent rules
```

---

## Convenience Bridges

Two thin bridge functions map physical state representations to Qiskit circuits.
**All physics is delegated to rqm-core; these functions own only the gate mapping.**

### `spinor_to_circuit(alpha, beta, target=0)`

Converts a spinor `(α, β)` to a `QuantumCircuit` that prepares qubit `target`
in the corresponding state.

Steps:
1. Normalize `(α, β)` via `rqm_core.spinor.normalize_spinor`
2. Convert to Bloch vector via `rqm_core.bloch.state_to_bloch`
3. Map `(θ, φ)` → `RY(θ) RZ(φ)` Qiskit gates

```python
from rqm_qiskit import spinor_to_circuit
import math

s = 1 / math.sqrt(2)
qc = spinor_to_circuit(s + 0j, s + 0j)   # |+⟩ state
print(qc.draw())
```

### `bloch_to_circuit(theta, phi, target=0)`

Converts Bloch angles `(θ, φ)` directly to a `QuantumCircuit`:
- `RY(θ)` sets the polar angle
- `RZ(φ)` sets the azimuthal angle

```python
from rqm_qiskit import bloch_to_circuit
import math

qc = bloch_to_circuit(math.pi / 2, 0.0)   # |+⟩ on Bloch equator
print(qc.draw())
```

### `Quaternion` re-export

`Quaternion` is re-exported from rqm-core.  Users can access it via either:

```python
from rqm_qiskit import Quaternion
# or
from rqm_core import Quaternion
```

Both refer to the same canonical implementation.

---

## Usage Modes

See [Public API Hierarchy](#public-api-hierarchy) for the preferred entrypoint
table.  The sections below expand on each tier with more context.

### Tier 1 — Execute (preferred)

Use `QiskitBackend.run()` whenever you want to compile **and** run a circuit
in one step.  The result is a `QiskitResult` with `.counts`, `.probabilities`,
`.most_likely_bitstring()`, and `.to_dict()` (JSON-serialisable for APIs):

```python
from rqm_compiler import Circuit
from rqm_qiskit import QiskitBackend

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

result = QiskitBackend().run(c, shots=1024)
print(result.counts)              # {"00": ~512, "11": ~512}
print(result.to_dict())           # {"counts": ..., "shots": 1024, "backend": "qiskit", ...}
```

### Tier 2 — Translate only

Use `to_backend_circuit()` when you only need the `QuantumCircuit` object
(e.g. to inspect it, serialise it, or hand it to a custom execution pipeline):

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_backend_circuit

c = Circuit(2)
c.h(0)
c.cx(0, 1)

qc = to_backend_circuit(c)
print(qc.draw(output="text"))
```

### Tier 3 — Compatibility helpers (educational / experimental)

Use `spinor_to_circuit`, `bloch_to_circuit`, `RQMCircuit`, `RQMGate`, or
`RQMState` for state preparation directly from physical parameters, or for
educational / exploration workflows where geometric intuition is the focus:

```python
from rqm_qiskit import spinor_to_circuit, QiskitBackend
import math

# Prepare |+⟩ state from spinor
s = 1 / math.sqrt(2)
qc = spinor_to_circuit(s + 0j, s + 0j)
qc.measure_all()

result = QiskitBackend().run_local(qc, shots=1024)
print(result.counts)    # approximately {"0": 512, "1": 512}
```

---

## Current Scope (v0.1.0)

**Tier 1 — Execute:**
- ✅ `QiskitBackend.run()` — one-call compile-and-execute; returns `QiskitResult`
- ✅ `QiskitResult` — structured result wrapper (counts, probabilities, most-likely, `.to_dict()`)

**Tier 2 — Translate:**
- ✅ `to_backend_circuit()` — primary translation function; rqm-compiler IR → `QuantumCircuit`
- ✅ `QiskitBackend.compile()` — alias on the backend class
- ✅ `QiskitTranslator` — stateless translator class
- ✅ `compile_to_qiskit_circuit()` — convenience function

**Tier 3 — Compatibility helpers:**
- ✅ `Quaternion` — thin re-export from rqm-core with `pretty()` convenience
- ✅ `RQMState` — normalized 1-qubit states; delegates math to rqm-core
- ✅ `RQMGate` — dual-mode: rotation (R_x, R_y, R_z) or named gate (H, CNOT, …)
- ✅ `RQMCircuit` — façade over rqm-compiler `Circuit`; `to_qiskit()` lowers to Qiskit
- ✅ `run_local()` / `run_backend()` — lower-level execution helpers
- ✅ `spinor_to_circuit` / `bloch_to_circuit` — bridge functions (delegate to rqm-core)
- ✅ `compiled_circuit_to_qiskit()` — internal lowering path (also public)
- ✅ Local Aer simulation via `run_on_aer_sampler()` and `run_local()`
- 🚧 IBM Runtime execution (placeholder, not yet implemented)

---

## Roadmap

| Version | Features |
|---------|----------|
| 0.1.0   | Full architecture; compiler-first design; bridge functions; QiskitBackend/Translator/Result |
| 0.2.0   | IBM Runtime `SamplerV2` integration |
| 0.3.0   | Noise models, density matrices |
| 1.0.0   | Stable public API, full documentation |

---

## Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"
pytest
```

## Running Examples

```bash
python examples/quaternion_state_demo.py
python examples/bloch_vs_quaternion_demo.py
python examples/simulator_counts_demo.py
```


---

## Optimization (Optional)

For improved circuit performance, use [`rqm-optimize`](https://github.com/RQM-Technologies-dev/rqm-optimize).
Because `rqm-optimize` is outside the `rqm-qiskit` dependency boundary, apply
it **before** passing the circuit to `rqm-qiskit` — do not expect
`rqm-qiskit` to call it internally:

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_backend_circuit
from rqm_optimize import optimize_circuit  # installed separately

c = Circuit(2)
c.h(0)
c.cx(0, 1)

# Optimize externally, then translate
optimized, report = optimize_circuit(c)
qc = to_backend_circuit(optimized)
print(qc.draw(output="text"))
```

`rqm-optimize` is a **completely separate, optional package**.  `rqm-qiskit`
does **not** depend on it, import it, or couple to it in any way.  Install it
only when you need it:

```bash
pip install "git+https://github.com/RQM-Technologies-dev/rqm-optimize.git"
```

> **Important boundaries:**
> - ❌ Do **not** add `rqm-optimize` as a dependency of `rqm-qiskit`
> - ❌ Do **not** import `rqm_optimize` inside `rqm-qiskit` source code
> - ❌ Do **not** couple the two repositories
>
> Keep optimization **optional and external**.

---

## License

MIT — see [LICENSE](LICENSE).
