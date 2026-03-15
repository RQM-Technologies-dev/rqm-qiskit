# rqm-qiskit

**SU(2)-native geometric bridge layer for Qiskit** — describe quantum states and
gates in rotation-first language, then run them on Qiskit simulators and IBM Quantum.

---

## What Is This?

`rqm-qiskit` is a clean, beginner-friendly Python package that sits **on top of
Qiskit** and provides a geometric, SU(2)-native interface for 1-qubit quantum work.

Instead of building circuits gate-by-gate from scratch, you describe states and
rotations in the language of Bloch spheres and SU(2) matrices, then let the library
translate them into standard Qiskit `QuantumCircuit` objects for simulation or IBM
Quantum execution.

**This package is not trying to replace Qiskit.**  
It is a bridge layer — Qiskit does all the heavy lifting under the hood.

---

## Why Does This Exist?

- **Rotation-first thinking**: quantum computation on a single qubit is just rotations
  on the Bloch sphere.  `rqm-qiskit` makes that concrete.
- **Educational clarity**: fewer raw matrix operations, more geometric intuition.
- **IBM Quantum ready**: built on Qiskit so the path to real hardware is straightforward.

---

## Installation

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

## Quickstart

```python
from rqm_qiskit import RQMState, RQMGate, RQMCircuit

state = RQMState.plus()
gate = RQMGate.ry(0.5)

circ = RQMCircuit(1)
circ.prepare_state(state)
circ.apply_gate(gate)
circ.measure_all()

print(circ.draw_text())
```

Run the circuit on the local Aer simulator:

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
      state.py      – RQMState: normalized 1-qubit state
      gates.py      – RQMGate: SU(2) rotation gate (x, y, z)
      circuit.py    – RQMCircuit: thin wrapper around QuantumCircuit
      convert.py    – state_to_quantum_circuit, gate_to_quantum_circuit
      results.py    – summarize_counts, format_counts_summary
      ibm.py        – Aer sampler helper + IBM Runtime stub
      utils.py      – internal utilities
  tests/            – pytest test suite
  examples/         – runnable example scripts
```

---

## Current Scope (v0.1.0)

- ✅ `RQMState` — normalized 1-qubit states with Bloch-sphere helpers
- ✅ `RQMGate` — R_x, R_y, R_z rotation gates
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
| 0.1.0   | 1-qubit states, gates, circuits, local simulation |
| 0.2.0   | IBM Runtime `SamplerV2` integration |
| 0.3.0   | 2-qubit entanglement, CNOT, Bell states |
| 0.4.0   | Noise models, density matrices |
| 1.0.0   | Stable public API, full documentation |

---

## Running Tests

```bash
pytest
```

## Running Examples

```bash
python examples/basic_single_qubit.py
python examples/bloch_rotation_demo.py
python examples/simulator_counts_demo.py
```

---

## License

MIT — see [LICENSE](LICENSE).
