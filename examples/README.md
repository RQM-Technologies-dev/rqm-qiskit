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
# Quaternion demo: show quaternion representations of qubit states
python examples/quaternion_state_demo.py

# Bloch vs quaternion: compare Bloch-vector and quaternion descriptions
python examples/bloch_vs_quaternion_demo.py

# Simulator counts demo: run circuits on Aer, print formatted summaries
python examples/simulator_counts_demo.py
```

## What Each Example Does

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
