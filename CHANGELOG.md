# Changelog

All notable changes to **rqm-qiskit** are documented here.

---

## [0.3.0](https://github.com/RQM-Technologies-dev/rqm-qiskit/compare/v0.2.0...v0.3.0) (2026-07-29)


### Features

* add fail-closed Qiskit assurance bridge ([#17](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/17)) ([73c987e](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/73c987e6811da99ee0f6cc1e3bf0c83f9f3c4070))


### Bug Fixes

* dispatch release pull request CI reliably ([#23](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/23)) ([5f7fbdf](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/5f7fbdf1648de28b040c73703f30c1994048e11f))
* keep generated releases verifiable ([#24](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/24)) ([cb3c058](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/cb3c058e0656b7f66dcb4152b8d38c4288c1e74d))
* preserve serverless QASM worker imports ([#30](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/30)) ([3984c3c](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/3984c3cd868b6237b380c44f3e641ad8ba2d4510))
* repair latency evidence serialization ([#27](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/27)) ([ca9937c](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/ca9937c12a6c2d8de264826999244fc6758d1005))


### Performance Improvements

* preregister Qiskit assurance latency hardening ([#26](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/26)) ([13da830](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/13da830d703b033e8d20150e1041453587ed76b0))


### Documentation

* name quantum-compiler-api as the canonical service ([#29](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/29)) ([ca03735](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/ca03735b6ba8a2d5857052c82bc52f76e683f7ed))
* publish Qiskit latency gate result ([#28](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/28)) ([a5a6f9f](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/a5a6f9f2eba6d1f01a2e7f9d715175307265d7c6))

## [0.3.0] — EXP-012 Quaternion-Cartan SU(4) Promotion

- Added target-local `Q3`, `QF`, `QC`, `QX`, and direct `RQ` synthesis
  candidates for compiler-owned internal `su4q` blocks.
- Added phase-aligned semantic verification, target compatibility checks, and
  an auditable selection hierarchy. Generic two-qubit `UnitaryGate` fallbacks
  cannot qualify as native candidates.
- Added standard `rxx`, `ryy`, and `rzz` lowering through the canonical
  `compiled_circuit_to_qiskit()` path.
- Added optional JSON-compatible synthesis reports to the functional and OO
  translation APIs without changing their default return types.
- Pinned the reproducible Qiskit 2.3.0 / Aer 0.17.2 / QASM 3 Import 0.6.0 /
  IBM Runtime 0.45.0 compatibility baseline and exact upstream RQM commits.
- Added offline generic-block, target-selection, direct-RQ, standard-gate,
  descriptor, and Weyl-landmark tests. No IBM hardware was used.

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
