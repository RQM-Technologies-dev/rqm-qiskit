# EXP-014 — RQM-Qiskit quaternionic circuit lens

EXP-014 is the evidence gate for the proposed `rqm-qiskit` 0.4 geometric
circuit lens. It asks whether an RQM-owned quaternion/SU(2)/SU(4) capability
provides a reproducible operational benefit alongside Qiskit without changing
standard quantum semantics.

The first candidate is a phase-aware canonical SU(2) fingerprint. Later tracks
record target-native circuit cost, direct-path latency, quaternionic-wavefunction
measurement consistency, and SU(4)/Weyl conformance. A later track cannot be
promoted by redefining an earlier failed cohort.

This experiment is local-only. It uses no provider credentials, network
execution, paid service, remote simulator, or quantum hardware.

This directory is the sanitized public mirror of private evidence commit
`82cfd1d7b2c7886c5b6d83bf2362d592dc94741f`. The measured candidate
implementations are `rqm-qiskit`
`126bde8311e1613db8888247e88b933253d92973` and `rqm-compiler`
`f05ead9b56311947fd123f5e461412a83779a420`.

## Run

From an environment containing Qiskit 2.5.1, `rqm-core`, `rqm-entanglement`,
`rqm-compiler`, and `rqm-qiskit`:

```bash
python run_experiment.py
python run_coverage_extension.py
```

The checked-in corpus is already frozen. `--freeze-corpus` was the one-time
creation action and now refuses to overwrite it; the ordinary run reads and
validates the existing digest without generating or altering the corpus.

`PREREGISTRATION_AMENDMENT_01.md` and `coverage_manifest.json` freeze a
separate representative/boundary extension added after a conformance audit.
It does not alter the primary cohorts or advantage decision and cannot
authorize package release.

`VALIDATION_RESULTS.md` records the source, distribution, and fresh Python
3.11–3.13 wheel checks. The separate performance failure still blocks release.

## Boundary

The quaternionic wavefunction track is a standard-compatible regrouping of a
two-component complex spinor. The circuit lens does not add quantum information,
define a new physical observable, or establish a hardware advantage. Exact
Qiskit transpiler serialization is a workflow baseline, not a claim that Qiskit
promises canonical circuit text.
