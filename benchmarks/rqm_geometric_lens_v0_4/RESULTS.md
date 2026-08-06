# EXP-014 Results

Execution status: complete
Scientific status: quaternionic circuit lens gate complete
Verdict: `canonical_assurance_workflow_advantage_supported`

## Primary held-out result

| Metric | Discovery | Held out | Gate |
| --- | ---: | ---: | --- |
| RQM canonical convergence | 32/32 (100%) | 64/64 (100%) | pass |
| Exact Qiskit level-3 serialization convergence | 2/32 (6.25%) | 4/64 (6.25%) | comparator |
| Convergence advantage | 93.75 points | 93.75 points | pass, required 20 points |
| Inequivalent-control collisions | 0 | 0 | pass |
| Non-VERIFIED variants | 0 | 0 | pass |
| Maximum phase-aligned operator error | `4.85e-16` | `5.93e-16` | pass, limit `1e-9` |

The supported advantage is narrow: RQM supplies a deterministic, phase-aware
SU(2) fingerprint for multiple equivalent gate spellings. Exact Qiskit
transpiler serialization is used as a workflow baseline; Qiskit does not claim
that serialized transpiler output is a canonical semantic fingerprint.

## Other tracks

- Target-native one-qubit cost was parity: median source-minus-RQM cost delta
  was `0`, median fractional improvement was `0`, and the deterministic paired
  bootstrap 95% interval was `[0, 0]`. No circuit-quality advantage is
  supported.
- RQM direct assurance was descriptively faster than the full Qiskit level-3
  transpilation measurement in this process, but the outputs are at different
  lowering stages. It is not promoted as a matched speed advantage.
- Quaternionic-wavefunction ideal Z-basis probabilities agreed with Qiskit to
  maximum error `4.44e-16`; exact `q`/`-q` state-representative negation error
  was `0`. This is conformance, not new quantum information.
- Four SU(4) controls reconstructed with maximum error `8.18e-16`; median
  two-qubit cost improvement was `0`. SU(4) cost was parity in this bounded
  sample.

## Product authorization

The primary gate authorizes productization of the canonical SU(2) fingerprint
and geometric report in an unreleased `rqm-qiskit` 0.4 candidate. It does not
waive the separate adapter-overhead, fresh-install, CLI, or package-release
gates.

## Representative and boundary extension

Preregistration amendment `EXP-014-A01` preserves the primary cohort and adds
the coverage omitted from its first freeze. All six extension checks passed:

- all 24 generated noncommuting chains converged with their equivalent
  split-angle spelling, with maximum phase-aligned error `6.48e-16`;
- all 24 reversed-order counterexamples produced distinct fingerprints;
- Bell, GHZ, QFT-style, VQE-style, and QAOA-style circuits were verified and
  returned bounded geometric reports;
- mid-circuit measurement, reset, symbolic parameter, custom instruction, and
  controlled-phase inputs returned the exact original circuit;
- terminal measurement preserved the `science`/`readout` registers and mapping
  `q[0] -> c[1]`, `q[1] -> c[0]`; and
- `q` and `-q` standalone probabilities agreed exactly, while the controlled
  operators remained separated by `1.8382` after phase alignment.

This extension is correctness coverage only. It did not contribute another
advantage claim or change the primary semantic digest.

## Non-claims

EXP-014 does not establish general Qiskit superiority, lower circuit cost,
hardware advantage, a new physical observable, additional quantum information,
or nonstandard quantum mechanics. No provider, credential, remote simulator, or
quantum hardware was used.

Semantic digest: `ba6e08f81cbefa0f35e6eeb811ca1f2190efaf54d457f4c7af261447f9da376c`
