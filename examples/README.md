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
# Quickstart: prepare |+>, apply R_y rotation, measure
python examples/basic_single_qubit.py

# Bloch sphere demo: inspect Bloch vectors before and after a gate
python examples/bloch_rotation_demo.py

# Simulator counts demo: run multiple circuits, print formatted summaries
python examples/simulator_counts_demo.py
```

## What Each Example Does

### `basic_single_qubit.py`
- Creates the |+⟩ state
- Applies an R_y(π/4) rotation gate
- Measures the result using the Aer simulator (2048 shots)
- Prints a formatted counts summary

### `bloch_rotation_demo.py`
- Creates a state from Bloch angles (θ, φ)
- Prints the Bloch vector before and after applying gates
- Demonstrates both R_y and R_z rotations
- Shows the text-mode circuit diagram

### `simulator_counts_demo.py`
- Runs three different 1-qubit circuits on the Aer sampler
- Demonstrates deterministic and probabilistic measurement outcomes
- Shows how |0>, |+>, and Bloch-angle states behave under measurement
