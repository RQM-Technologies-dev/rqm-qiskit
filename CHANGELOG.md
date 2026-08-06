# Changelog

All notable changes to **rqm-qiskit** are documented here.

---

## [0.4.0](https://github.com/RQM-Technologies-dev/rqm-qiskit/compare/v0.2.0...v0.4.0) (2026-08-06)


### Features

* add evidence-first geometric circuit lens ([f8de989](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/f8de989b9489d00faf0a6dff3672e1097876754a))
* add fail-closed Qiskit assurance bridge ([#17](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/17)) ([73c987e](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/73c987e6811da99ee0f6cc1e3bf0c83f9f3c4070))
* reframe 0.4 as quaternionic explanation bridge ([8101bb8](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/8101bb872eb7a26b6d1909b8c07730b47369b849))


### Bug Fixes

* dispatch release pull request CI reliably ([#23](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/23)) ([5f7fbdf](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/5f7fbdf1648de28b040c73703f30c1994048e11f))
* keep generated releases verifiable ([#24](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/24)) ([cb3c058](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/cb3c058e0656b7f66dcb4152b8d38c4288c1e74d))
* preserve serverless QASM worker imports ([#30](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/30)) ([3984c3c](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/3984c3cd868b6237b380c44f3e641ad8ba2d4510))
* repair latency evidence serialization ([#27](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/27)) ([ca9937c](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/ca9937c12a6c2d8de264826999244fc6758d1005))


### Performance engineering history

* preserve the guarded native Qiskit adapter as a failed experiment; the accelerator is not shipped ([206b4ce](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/206b4cef4820961bfb80b0fba71037efe6613e10))
* preregister Qiskit assurance latency hardening ([#26](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/26)) ([13da830](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/13da830d703b033e8d20150e1041453587ed76b0))
* remove repeated provenance metadata work ([1931ea2](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/1931ea247269d6ef7ee311e1c95dd547f41adff0))


### Documentation

* mirror EXP-016 explanation evidence ([b404100](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/b4041009e844c50763cda41f4b1aee2f30f111ba))
* name quantum-compiler-api as the canonical service ([#29](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/29)) ([ca03735](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/ca03735b6ba8a2d5857052c82bc52f76e683f7ed))
* publish Qiskit latency gate result ([#28](https://github.com/RQM-Technologies-dev/rqm-qiskit/issues/28)) ([a5a6f9f](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/a5a6f9f2eba6d1f01a2e7f9d715175307265d7c6))
* publish the sanitized 0.4 evidence packet ([a86e45e](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/a86e45ecbe4025bc1403d755598c772afc0a598f))
* record negative EXP-015 evidence ([1c83ed3](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/1c83ed3bd1dbaace680ca3392a97e2ea2a9102a1))
* record the candidate validation matrix ([23a67f1](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/23a67f1ef3b1406bb7ba46c2f1b72eb7fb23579a))


### Miscellaneous Chores

* close release evidence integrity checks ([81bd320](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/81bd32030def9ac8e8a8ee33c2103de508869eff))
* prepare 0.4.0 controlled release ([e037063](https://github.com/RQM-Technologies-dev/rqm-qiskit/commit/e03706340a3fb680abee7fe2444701901c17fcd2))

### Qiskit-Compatible Quaternionic Explanation Bridge summary and limitations

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
- Qualified one immutable pure-Python candidate wheel bundle on hosted Linux,
  macOS, and Windows runners with Python 3.11–3.13. Post-publication public-PyPI
  qualification is tracked separately from this candidate evidence.

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
