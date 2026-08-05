# EXP-014 Preregistration

Status: frozen before measurement

Seed: `20260805`

## Question

Can a standard-compatible quaternion/SU(2)/SU(4) lens provide at least one
reproducible, held-out workflow advantage for Qiskit users while preserving
exact fail-closed semantics?

## Candidate order

1. Phase-aware SU(2) fusion and canonical fingerprints.
2. Target-native single-qubit synthesis cost and direct-path latency.
3. Quaternionic-wavefunction geometry and measurement consistency.
4. SU(4)/Weyl fingerprints and verified fixed-pair optimization.

The first passing candidate may unlock productization. All measured later-track
losses or parity results remain in the result.

## Frozen corpus

- 32 exploratory and 64 held-out SU(2) families.
- Four semantically equivalent variants per family: direct ZYZ, split ZYZ,
  identity-inserted ZYZ, and a phase-equivalent `2*pi` form.
- One inequivalent angle-offset control per family.
- Representative two-qubit CX, Cartan-axis, Bell-like, and fixed-pair windows.
- Qiskit baseline: version 2.5.1, optimization level 3, basis
  `rz/sx/x/cx`, and seed `991`.

The concrete angles and corpus digest are written to `corpus_manifest.json`
before measurement and are not regenerated during an experiment run.

## Correctness gates

- Maximum phase-aligned operator error: `1e-9`.
- Assurance status: `VERIFIED` for every supported equivalent variant.
- False equivalence: zero.
- Canonical fingerprint collision against inequivalent controls: zero.
- Deterministic fingerprints, decisions, corpus identity, and semantic summary
  repeat exactly. Raw timing samples are retained and are expected to vary.

## Advantage gates

At least one held-out gate must pass:

- Canonical fingerprint: 100% RQM family convergence, zero inequivalent-control
  collisions, and at least a 20 percentage-point convergence advantage over
  exact Qiskit level-3 serialized output.
- Circuit efficiency: at least 10% lower median target-native one- or two-qubit
  cost/depth with a positive paired-bootstrap 95% lower bound.
- Latency: at least 20% lower median with no more than a 10% p95 regression.
- SU(4): at least 20% lower two-qubit cost on the frozen eligible class with
  every changed output verified.

## Claim discipline

A passing canonical-fingerprint gate supports only a deterministic
assurance/reproducibility workflow advantage. It does not support a general
compiler, circuit-quality, execution, hardware, physics, or Qiskit-superiority
claim. Feature absence in Qiskit is not by itself counted as a win; the frozen
equivalent-family convergence and collision controls must pass.
