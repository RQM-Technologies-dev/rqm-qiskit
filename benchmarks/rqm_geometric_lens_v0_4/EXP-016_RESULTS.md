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

Hosted qualification
[run 31057445168](https://github.com/RQM-Technologies-dev/rqm-qiskit/actions/runs/31057445168)
passed all nine Linux, macOS, and Windows jobs on Python 3.11–3.13 from the
same immutable wheel bundle at candidate commit
`1db19ea8604008843846535dbd8fea50aee00b32`. Imports resolved outside the
checkout; `pip check`, the installed API and CLI, UTF-8 and space-containing
paths, Windows `.EXE` entry points, and OpenQASM round trips all passed.

The candidate wheelhouse artifact digest is
`sha256:4cc8b6899b7aab8fc967298ea2cc2f5c2afa8ba4e48ee3600de5f7b862a18127`;
the aggregate evidence artifact digest is
`sha256:385f90058a0429578216ec3106a9f1129fd7f57de417960dc62f0b9ce387b98a`.
The three wheel hashes were:

- `rqm_core-0.2.2-py3-none-any.whl`:
  `57f5a6ed7702b6b56b3ecc94c68034b21aabbff939d1a7cae6133594d94e4f26`
- `rqm_compiler-0.3.0-py3-none-any.whl`:
  `66b1db5b9e0fa5cccfbf038a0b77918bc8b50a0bea204c1169856afc6fd1005b`
- `rqm_qiskit-0.4.0-py3-none-any.whl`:
  `c6daba5b8991ce0d56bf40b4d0e3030a58f3e498d2bc0ca77a86fe08ceb14f86`

This completes candidate release readiness. Public-PyPI installation remains
a separate post-publication qualification gate and no package is represented
here as already published.

## Preserved prior evidence

- EXP-014 remains `100%` RQM convergence versus `6.25%` exact Qiskit
  serialization convergence in its frozen workflow.
- EXP-015 remains failed at a `0.7427` adapter/compiler ratio versus `0.25`.

Neither result is reclassified. EXP-015 is non-promoted engineering evidence,
not a current product criterion. No general performance, compiler-quality,
hardware, circuit-quality, information, physics, or Qiskit-superiority claim
is supported.
