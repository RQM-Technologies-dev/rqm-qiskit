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
rqm-notebooks   (interactive notebooks and tutorials)
```

### Layer responsibilities

| Package | Responsibility |
|---------|----------------|
| `rqm-core` | Quaternion algebra, SU(2) matrices, Bloch conversions, spinor helpers |
| `rqm-compiler` | Canonical gate/circuit IR (`Circuit`, `Operation`), normalization, compilation pipeline |
| `rqm-qiskit` | Lower rqm-compiler IR to Qiskit `QuantumCircuit`; Aer/IBM execution helpers; thin user-facing wrappers |
| `rqm-notebooks` | Jupyter notebooks, tutorials, interactive demonstrations |

### What rqm-qiskit owns

- `compiled_circuit_to_qiskit()` — the primary bridge: translates an
  `rqm_compiler.Circuit` or `rqm_compiler.CompiledCircuit` into a Qiskit
  `QuantumCircuit`.
- `RQMCircuit` — a thin façade over `rqm_compiler.Circuit` that adds
  Qiskit-specific state preparation (`initialize`) and exposes
  `.to_qiskit()`.
- `RQMGate` — adds `.to_operation()` (→ `rqm_compiler.Operation`) and
  `.to_qiskit_gate()` (→ Qiskit gate object) on top of the rqm-core SU(2)
  matrix.
- `RQMState` — adds Qiskit-facing helpers (`.vector()`, `.as_statevector()`)
  on top of rqm-core spinor/Bloch math.
- `run_on_aer_sampler()` / IBM Runtime helpers in `ibm.py`.
- Result formatting in `results.py`.

### What rqm-qiskit does NOT own

`rqm-qiskit` contains **no** quaternion math, **no** spinor normalization,
**no** Bloch conversions, and **no** canonical gate/circuit semantics of its
own.  All canonical logic is delegated upward to rqm-core and rqm-compiler.

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

Since `rqm-core` and `rqm-compiler` are not yet published to PyPI, install
them from GitHub first:

```bash
pip install "git+https://github.com/RQM-Technologies-dev/rqm-core.git"
pip install "git+https://github.com/RQM-Technologies-dev/rqm-compiler.git"
```

Then install `rqm-qiskit` (which will pull both dependencies automatically):

```bash
pip install "git+https://github.com/RQM-Technologies-dev/rqm-qiskit.git"
```

To also run local simulations (recommended), clone the repo and install with extras:

```bash
git clone https://github.com/RQM-Technologies-dev/rqm-qiskit.git
cd rqm-qiskit
pip install ".[simulator]"
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

## Quickstart

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

Use the rqm-compiler circuit directly:

```python
from rqm_compiler import Circuit, compile_circuit
from rqm_qiskit.convert import compiled_circuit_to_qiskit

# Build a backend-neutral circuit in rqm-compiler
c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

# Lower to Qiskit
qc = compiled_circuit_to_qiskit(c)
print(qc.draw(output="text"))
```

Run on the local Aer simulator:

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
      gates.py       – RQMGate: to_operation() → rqm_compiler.Operation; to_qiskit_gate()
      circuit.py     – RQMCircuit: façade over rqm_compiler.Circuit + to_qiskit()
      convert.py     – compiled_circuit_to_qiskit(); state/gate convenience wrappers
      results.py     – summarize_counts, format_counts_summary
      ibm.py         – Aer sampler helper + IBM Runtime stub
      utils.py       – internal utilities
  tests/             – pytest test suite (137 tests)
  examples/          – runnable example scripts
```

---

## Current Scope (v0.1.0)

- ✅ `Quaternion` — thin re-export from rqm-core with `pretty()` convenience
- ✅ `RQMState` — normalized 1-qubit states; delegates math to rqm-core
- ✅ `RQMGate` — R_x, R_y, R_z gates; `to_operation()` → rqm-compiler IR
- ✅ `RQMCircuit` — façade over rqm-compiler `Circuit`; `to_qiskit()` lowers to Qiskit
- ✅ `compiled_circuit_to_qiskit()` — primary bridge: rqm-compiler IR → `QuantumCircuit`
- ✅ Measurement result summaries
- ✅ Local Aer simulation via `run_on_aer_sampler()`
- 🚧 IBM Runtime execution (placeholder, not yet implemented)
- 🚧 Multi-qubit support (future work)

---

## Roadmap

| Version | Features |
|---------|----------|
| 0.1.0   | 1-qubit states, gates, quaternion layer, local simulation; rqm-compiler bridge |
| 0.2.0   | IBM Runtime `SamplerV2` integration |
| 0.3.0   | 2-qubit entanglement, CNOT, Bell states |
| 0.4.0   | Noise models, density matrices |
| 1.0.0   | Stable public API, full documentation |

---

## Running Tests

```bash
# Install development dependencies (rqm-core and rqm-compiler from GitHub)
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

## License

MIT — see [LICENSE](LICENSE).
