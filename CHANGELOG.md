# Changelog

All notable changes to **rqm-qiskit** are documented here.

---

## [0.4.0] — Unreleased candidate: Qiskit-Compatible Quaternionic Explanation Bridge

- Reframed the candidate mission: help the world understand ordinary quantum
  computing through quaternionic geometry while remaining compatible with
  Qiskit.
- Added deterministic `RQMExplanation` sections,
  `RQMGeometricReport.explanation`, and `to_text()` detail levels `summary`,
  `standard`, and `technical`, with evidence paths for every section.
- Added the offline `rqm-qiskit explain` command with optional Markdown and
  JSON outputs and safe complete/partial/error exit codes.
- Decoupled explanation from optimization. Public-Qiskit-evaluable bound
  one- and two-qubit numeric unitaries can be explained while unsupported
  optimization still returns the exact original circuit.
- Added explicit U(2) global-phase, quaternion-sign, controlled-context,
  rotation-degree/π, ideal measurement, SU(4)/Weyl, perfect-entangler, and
  final-state entanglement explanations.
- Removed the EXP-015 C accelerator, private packed-Qiskit access, native wheel
  requirements, and native-specific tests. The negative experiment remains
  permanently preserved as evidence.
- Added EXP-016's frozen 36-record hybrid explanation gate. The local run
  passed correctness, deterministic rendering, compatibility, fail-closed,
  public-interface, and absolute responsiveness criteria.

- Added EXP-014-backed canonical SU(2) fingerprints and versioned geometric
  reports for Qiskit circuits and bounded states.
- Added standard-compatible quaternionic-wavefunction, Bloch, ideal
  measurement, SU(4)/Weyl, and entanglement report sections by delegating math
  to `rqm-core`, `rqm-entanglement`, and `rqm-compiler`.
- Added terminal-measurement preservation and compiler-owned verified regional
  optimization for larger circuits.
- Added synchronous and process-isolated asynchronous OpenQASM assurance plus
  offline `analyze` and `assure` CLI commands.
- Updated the bounded compatibility target to Qiskit `>=2.5.1,<2.6` and Python
  3.11–3.13.
- Comparative adapter overhead is no longer a product criterion. EXP-015's
  failed `0.7427` ratio is retained as non-promoted engineering evidence.
- The candidate remains unreleased pending complete fresh-wheel validation on
  Python 3.11–3.13 and Linux, macOS, and Windows; no publication is authorized.

## [0.3.0] — Withdrawn, unreleased candidate

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
- This candidate was not published because its frozen adapter-overhead gate
  failed. Its evidence remains preserved under `benchmarks/`.

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
