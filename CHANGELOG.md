# Changelog

All notable changes to **rqm-qiskit** are documented here.

---

## [0.1.0] — Architecture Spine Validated

### Milestone summary

This release establishes the stable architecture spine of the RQM stack and
locks in the single lowering path from rqm-compiler IR to Qiskit.

### Architecture guarantees established

- **Canonical math from rqm-core.**  Quaternion algebra, SU(2) matrices, Bloch
  conversions, and spinor normalization are owned exclusively by `rqm-core`.
  `rqm-qiskit` never reimplements them.

- **Canonical circuit IR from rqm-compiler.**  `rqm_compiler.Circuit`,
  `rqm_compiler.Operation`, and the compilation pipeline are the single source
  of truth for gate and circuit semantics.  `rqm-qiskit` is a pure translation
  layer on top of them.

- **`compiled_circuit_to_qiskit()` is the single dominant lowering path.**
  All helpers that produce a Qiskit `QuantumCircuit` route through this
  function.  There is no second, parallel lowering path.  Specifically:
  - `RQMCircuit.to_qiskit()` delegates to `compiled_circuit_to_qiskit()`.
  - `gate_to_quantum_circuit()` builds a 1-op `rqm_compiler.Circuit` and
    calls `compiled_circuit_to_qiskit()` — it no longer calls
    `gate.to_qiskit_gate()` / `qc.append()` directly.

- **`state_to_quantum_circuit()` is the only documented exception.**  State
  preparation uses Qiskit's `initialize` instruction, which has no equivalent
  in the rqm-compiler IR.  It is explicitly documented as the sole case that
  stays outside the main lowering path.

### What this means for downstream consumers

- `rqm-compiler` is no longer experimental glue; it is part of the spine.
  Its public API (`Circuit`, `CompiledCircuit`, `Operation`, `compile_circuit`)
  should now be treated as stable.
- Any future helper added to `rqm-qiskit` that converts circuits or gates to
  Qiskit **must** route through `compiled_circuit_to_qiskit()`.

### Changes in this release

- `src/rqm_qiskit/convert.py` — `gate_to_quantum_circuit()` now routes through
  `compiled_circuit_to_qiskit()` instead of calling Qiskit gate constructors
  directly.
- `README.md` — added "Architecture Guarantees" table documenting the four
  invariants above.
- `examples/canonical_lowering_path.py` — new example demonstrating the
  canonical `rqm_compiler.Circuit` → `compiled_circuit_to_qiskit()` → Aer
  workflow.
- `tests/test_convert.py` — added
  `test_gate_to_quantum_circuit_routes_through_compiled_circuit_to_qiskit` to
  assert the single-path contract holds.

---

*For the full commit history see the
[GitHub repository](https://github.com/RQM-Technologies-dev/rqm-qiskit).*
