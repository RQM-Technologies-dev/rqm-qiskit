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

### 2. No math duplication

`rqm-qiskit` **must not** implement or duplicate:

- Quaternion arithmetic
- Spinor normalization
- Bloch-vector conversion
- SU(2) decomposition
- Named gate definitions

All such logic must be imported from `rqm_core`.

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

The primary input type for `QiskitBackend`, `QiskitTranslator`, and
`compile_to_qiskit_circuit` is `rqm_compiler.Circuit` or
`rqm_compiler.CompiledCircuit`.

`RQMGate` and `dict` input are transitional paths and may be removed.
Do not add new code that depends on these transitional paths as primary usage.

### 6. Test coverage

Every new public function or class must have corresponding tests in `tests/`.
Tests must be offline-safe (no real IBM backend required).

### 7. Dependency boundaries

`rqm-qiskit` may depend on:
- `rqm-core` (canonical math)
- `rqm-compiler` (canonical IR)
- `qiskit` + `qiskit-aer` (execution)

`rqm-qiskit` must **not** depend on:
- `rqm-optimize` (keep optimization external and optional)
- Any physics package not already in `rqm-core`
