# Examples

This directory contains runnable Python examples for **rqm-qiskit**.

## Prerequisites

Install the package with the simulator extras:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,simulator]"
```

## Running the Examples

All examples can be run from the project root directory:

```bash
# Canonical path demo: build with rqm-compiler, lower via rqm-qiskit, run on Aer
python examples/canonical_lowering_path.py

# Quickstart: prepare |+>, rotate, measure on Aer
python examples/basic_single_qubit.py

# Quaternion demo: show quaternion representations of qubit states
python examples/quaternion_state_demo.py

# Bloch vs quaternion: compare Bloch-vector and quaternion descriptions
python examples/bloch_vs_quaternion_demo.py

# Simulator counts demo: run circuits on Aer, print formatted summaries
python examples/simulator_counts_demo.py
```

## What Each Example Does

### `canonical_lowering_path.py` ⭐ start here
Demonstrates the **canonical RQM stack workflow**:

1. Build a backend-neutral circuit directly with `rqm_compiler.Circuit`.
2. Lower it to a Qiskit `QuantumCircuit` via `compiled_circuit_to_qiskit()` —
   the single dominant lowering path in `rqm-qiskit`.
3. Optionally pass a `rqm_compiler.CompiledCircuit` to the same function
   (both types are accepted).
4. Execute on the local Aer simulator and inspect the results.

Covers: single-qubit rotation, compiled-circuit lowering, and a two-qubit
Bell-state preparation.  This is the preferred pattern for new code.

### `basic_single_qubit.py`
- Quickstart: prepare the `|+>` state, apply R_y(π/4), measure, run on Aer.
- Uses `RQMCircuit`, which delegates to `compiled_circuit_to_qiskit()` internally.

### `quaternion_state_demo.py`
- Shows each standard qubit state (|0>, |1>, |+>, |->) as a unit quaternion
- Demonstrates quaternion composition as gate composition
- Verifies that the quaternion's SU(2) matrix produces the correct state from |0>

### `bloch_vs_quaternion_demo.py`
- Compares the Bloch-vector and quaternion representations of the same state
- Applies R_y and R_z gates and shows both descriptions before and after
- Demonstrates how quaternion multiplication composes two rotations exactly

### `simulator_counts_demo.py`
- Runs three different 1-qubit circuits on the Aer sampler
- Demonstrates deterministic and probabilistic measurement outcomes
- Shows how |0>, |+>, and Bloch-angle states behave under measurement

