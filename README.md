# rqm-qiskit

**Quaternion-native geometric bridge layer for Qiskit** — describe quantum states and
gates in the language of unit quaternions and SU(2) rotations, then run them on Qiskit
simulators and IBM Quantum hardware.

---

## Architecture

`rqm-qiskit` sits in the middle of a three-layer dependency chain:

```
rqm-core        (canonical math: Quaternion, SU(2), Bloch, spinor)
       ↓
rqm-qiskit      (Qiskit bridge: RQMState, RQMGate, RQMCircuit, IBM helpers)
       ↓
rqm-notebooks   (interactive notebooks and tutorials)
```

### Relationship to rqm-core

All canonical quaternion, SU(2), Bloch, and spinor mathematics lives in
**[rqm-core](https://github.com/RQM-Technologies-dev/rqm-core)**.  This is the
single source of truth for shared math across the RQM ecosystem.

`rqm-qiskit` is a **pure bridge layer** that:
- Imports and re-exports `Quaternion` from rqm-core (with `pretty()` added for
  convenience).
- Uses rqm-core's `spinor_to_quaternion` and `state_to_bloch` inside `RQMState`.
- Uses rqm-core's `axis_angle_to_su2` inside `RQMGate.to_matrix()`.
- Adds everything Qiskit-specific: `RQMState`, `RQMGate`, `RQMCircuit`,
  `QuantumCircuit` conversions, simulator/IBM bridge helpers, and result
  formatting.
- Contains **no duplicated quaternion, spinor, or Bloch math**.

This separation is **intentional** and keeps the ecosystem modular:

| Package | Responsibility |
|---------|----------------|
| `rqm-core` | Quaternion algebra, SU(2) matrices, Bloch conversions, spinor helpers |
| `rqm-qiskit` | Qiskit bridge, circuit building, IBM Quantum execution |
| `rqm-notebooks` | Jupyter notebooks, tutorials, interactive demonstrations |

---

## What Is This?

`rqm-qiskit` is a clean, beginner-friendly Python package that sits **on top of
Qiskit** and provides a quaternion-native interface for 1-qubit quantum work.

The key insight:

> A single-qubit state lives on the Bloch sphere.  
> Rotations of the Bloch sphere are SU(2) transformations.  
> SU(2) is isomorphic to the group of unit quaternions.

Therefore, **unit quaternions are the natural algebraic object for 1-qubit quantum
states and gates**.  `rqm-qiskit` exposes that geometry directly, while Qiskit
handles circuits, transpilation, simulation, and IBM Quantum execution.

The stack:

```
Quaternion / geometric representation
        ↓
SU(2) rotations
        ↓
Qiskit circuit representation
        ↓
Simulator or IBM Quantum hardware
```

**This package is not trying to replace Qiskit.**  
It is a bridge layer — Qiskit does all the heavy lifting under the hood.

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

Since `rqm-core` (the math dependency) is not yet published to PyPI, install
it from GitHub first:

```bash
pip install "git+https://github.com/RQM-Technologies-dev/rqm-core.git"
```

Then install `rqm-qiskit` (which will pull `rqm-core` from GitHub automatically):

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
      quaternion.py  – Quaternion: unit quaternion with SU(2) conversion
      state.py       – RQMState: normalized 1-qubit state + to_quaternion()
      gates.py       – RQMGate: SU(2) rotation (x, y, z) + quaternion property
      circuit.py     – RQMCircuit: thin wrapper around QuantumCircuit
      convert.py     – state_to_quantum_circuit, gate_to_quantum_circuit
      results.py     – summarize_counts, format_counts_summary
      ibm.py         – Aer sampler helper + IBM Runtime stub
      utils.py       – internal utilities
  tests/             – pytest test suite (114 tests)
  examples/          – runnable example scripts
```

---

## Current Scope (v0.1.0)

- ✅ `Quaternion` — unit quaternion with SU(2) matrix conversion and composition
- ✅ `RQMState` — normalized 1-qubit states; `to_quaternion()` gives the preparation rotation
- ✅ `RQMGate` — R_x, R_y, R_z gates; `gate.quaternion` exposes the quaternion form
- ✅ `RQMCircuit` — prepare, rotate, measure, draw
- ✅ Conversion helpers to/from Qiskit `QuantumCircuit`
- ✅ Measurement result summaries
- ✅ Local Aer simulation via `run_on_aer_sampler()`
- 🚧 IBM Runtime execution (placeholder, not yet implemented)
- 🚧 Multi-qubit support (future work)

---

## Roadmap

| Version | Features |
|---------|----------|
| 0.1.0   | 1-qubit states, gates, quaternion layer, local simulation |
| 0.2.0   | IBM Runtime `SamplerV2` integration |
| 0.3.0   | 2-qubit entanglement, CNOT, Bell states |
| 0.4.0   | Noise models, density matrices |
| 1.0.0   | Stable public API, full documentation |

---

## Running Tests

```bash
# Install development dependencies (rqm-core comes from GitHub automatically)
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
