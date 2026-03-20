# AGENTS.md – Coding agent rules for rqm-qiskit

This file contains permanent rules for AI coding agents (GitHub Copilot,
Claude, etc.) working in this repository.

---

## Architecture rules

### 1. Layer ownership

| Layer | Package | Owns |
|-------|---------|------|
| Math | `rqm-core` | Quaternion algebra, SU(2), Bloch, spinor, named gate quaternions |
| IR | `rqm-compiler` | Canonical gate/circuit IR (`Circuit`, `Operation`, `compile_circuit`) |
| Bridge | `rqm-qiskit` | Qiskit lowering, Aer/IBM execution, result wrappers |

### 2. This repo is a translator/execution layer only

`rqm-qiskit` must **not** implement or duplicate:

- Quaternion arithmetic
- Spinor normalization
- Bloch-vector conversion
- SU(2) decomposition
- Named gate definitions
- Compiler passes
- Optimization logic
- IR schema

All such logic must be imported from `rqm_core` or `rqm_compiler`.

### 3. Bridge functions are convenience-only

`spinor_to_circuit` and `bloch_to_circuit` are **thin convenience bridges**.
They must:

- Delegate all physics/math to `rqm_core` (e.g. `state_to_bloch`, `normalize_spinor`)
- Only own the mapping from Bloch angles `(θ, φ)` → Qiskit gates `RY(θ) RZ(φ)`

Bridge functions **must not** evolve into alternative compilation paths.
They must not grow their own physics, IR, or gate decomposition logic.

### 4. Single lowering path

All gate/circuit lowering to Qiskit `QuantumCircuit` must route through
`compiled_circuit_to_qiskit()` in `convert.py`.

The only documented exception is `state_to_quantum_circuit()`, which uses
Qiskit's `initialize` instruction (no rqm-compiler IR equivalent).

### 5. Compiler-first design

The primary input type for `QiskitBackend`, `QiskitTranslator`,
`to_qiskit_circuit`, and `run_qiskit` is `rqm_compiler.Circuit` or
`rqm_compiler.CompiledCircuit`.

`RQMGate` and `dict` input are transitional paths and may be removed.
Do not add new code that depends on these transitional paths as primary usage.

### 6. Do not modify canonical descriptor schema

The descriptor schema `{"gate": str, "targets": list[int], "controls": list[int], "params": dict}`
is owned by `rqm-compiler`. Do not reinterpret or extend it here.

### 7. Do not add optimization passes

All optimization logic belongs in `rqm-compiler` (or the external
`rqm-optimize` package). `rqm-qiskit` only consumes
`rqm_compiler.optimize_circuit()` via the `optimize=True` flag.

### 8. Prefer thin wrappers over duplicated helper logic

If existing logic in `rqm-core` or `rqm-compiler` covers a use case,
import and delegate — do not re-implement.

### 9. Test coverage

Every new public function or class must have corresponding tests in `tests/`.
Tests must be offline-safe (no real IBM backend required).

### 10. Dependency boundaries

`rqm-qiskit` may depend on:
- `rqm-core` (canonical math)
- `rqm-compiler` (canonical IR)
- `qiskit` + `qiskit-aer` (execution)

`rqm-qiskit` must **not** depend on:
- `rqm-optimize` (keep optimization external and optional)
- Any physics package not already in `rqm-core`

---

## Primary public API

The canonical entry points are:

```python
from rqm_qiskit import (
    QiskitBackend,     # unified OO entry point
    QiskitTranslator,  # descriptor → QuantumCircuit
    to_qiskit_circuit, # functional translation API
    run_qiskit,        # functional execution API
)
```

All other exports are legacy/compatibility helpers.
