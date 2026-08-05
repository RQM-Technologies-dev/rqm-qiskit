# EXP-016 Results

Decision: **pass** for the frozen local hybrid explanation gate.

Execution date: `2026-08-05`

Corpus digest: `a1e511885f42ea526ca4406f28d58797a3c4de5480e76ac96b629dd2aebae14e`

## Correctness and explanation

| Gate | Result | Required | Verdict |
| --- | ---: | ---: | --- |
| Frozen records | `36` | `36` unchanged records | pass |
| Expected complete records | `28/28` | all | pass |
| Expected partial/boundary records | `8/8` | explicit partial or unsupported | pass |
| Five-run deterministic JSON and text | `36/36` | all | pass |
| Input mutation | `0/36` | zero | pass |
| Explanatory coverage | `36/36` | all applicable/bounded sections | pass |
| Numeric agreement | maximum error `7.22e-16` | `<=1e-9` | pass |
| Private Qiskit API violations | `0` | zero | pass |

All complete one-qubit records answered quaternion, rotation, Bloch, phase,
measurement, and limitation questions. All complete two-qubit records included
verified SU(4)/Weyl, local-equivalence, perfect-entangler, final-state
entanglement, measurement, and limitation sections. Boundary cases explicitly
recorded unavailable geometry and did not narrate it as computed.

The reversed terminal-measurement record retained `q[0] -> c[1]` and
`q[1] -> c[0]`. Numeric public `UnitaryGate` records were explained through
Qiskit's public operator interface without broadening compiler optimization.

## Absolute responsiveness

| Metric | Result | Required | Verdict |
| --- | ---: | ---: | --- |
| Direct one-/two-qubit explanation p95 | `15.8722 ms` | `<=50 ms` | pass |
| Direct median | `6.1347 ms` | descriptive | — |
| OpenQASM explanation p95 | `25.1224 ms` | `<=100 ms` | pass |
| OpenQASM median | `9.0291 ms` | descriptive | — |

The implementation removed repeated package-metadata parsing and redundant
nested report construction. This is ordinary projection work, not a circuit,
gate, matrix, fingerprint, or report cache.

## Packaging status

`rqm-core` 0.2.2, `rqm-compiler` 0.3.0, and `rqm-qiskit` 0.4.0 pure-Python
sdists and `py3-none-any` wheels built and passed `twine check`. Fresh local
macOS wheel environments on Python 3.11.15, 3.12.2, and 3.13.14 passed Python
and `rqm-qiskit explain` smoke tests with Qiskit 2.5.1.

Hosted Linux, macOS, and Windows workflow results are still pending because no
branch was pushed. EXP-016 is complete, but full package release readiness is
not recorded and no publication is authorized.

## Preserved prior evidence

- EXP-014 remains `100%` RQM convergence versus `6.25%` exact Qiskit
  serialization convergence in its frozen workflow.
- EXP-015 remains failed at a `0.7427` adapter/compiler ratio versus `0.25`.

Neither result is reclassified. EXP-015 is non-promoted engineering evidence,
not a current product criterion. No general performance, compiler-quality,
hardware, circuit-quality, information, physics, or Qiskit-superiority claim
is supported.
