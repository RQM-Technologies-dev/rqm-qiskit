# RQM-Qiskit 0.4 Performance Results

Historical EXP-014/EXP-015 performance gate: **failed**

Current lifecycle note: this failure is retained exactly and is not
reclassified. After the 0.4 mission was formally reframed as a Qiskit-compatible
quaternionic explanation bridge, relative adapter/compiler performance ceased
to be a product release criterion. The measurements below remain non-promoted
engineering evidence and support no Qiskit-superiority claim.

## Frozen EXP-014 baseline

| Metric | Baseline | Required | Verdict |
| --- | ---: | ---: | --- |
| Median adapter/compiler ratio | `0.9862` | `<= 0.25` | fail |
| Direct assurance p95 | `0.9374 ms` | `<= 5 ms` | pass |
| OpenQASM import p95 | `3.1894 ms` | `<= 25 ms` | pass |
| OpenQASM assurance p95 | `0.8374 ms` | `<= 25 ms` | pass |
| OpenQASM export p95 | `0.7676 ms` | `<= 25 ms` | pass |
| Complete OpenQASM p95 | `4.7638 ms` | `<= 25 ms` | pass |

Median stage times across 256 frozen held-out samples were approximately
`84.1 us` import, `279.4 us` compiler optimize-and-verify, `100.6 us` lowering,
and `85.8 us` report serialization. All 256 raw samples are retained in the
machine-readable result.

Using Qiskit's `UnitaryGate(..., check_input=False)` only after compiler
quaternion validation and `rqm-core` matrix construction reduced an exploratory
ratio from about `1.24`; the final frozen measurement was `0.9862`. No cache was
introduced. The failure blocked the then-specified performance-led candidate
but does not change the EXP-014 semantic fingerprint verdict.

## EXP-015 guarded-native follow-up

The native-required decision run kept the same corpus digest, 64 held-out
families, four variants, 256-sample order, timing boundaries, compiler, and
verification policy.

| Metric | Result | Required | Verdict |
| --- | ---: | ---: | --- |
| Median adapter/compiler ratio | `0.7427` | `<= 0.25` | fail |
| Median absolute adapter time | `517.3345 us` | `< 274.994 us` | fail |
| Direct assurance p95 | `3.0540 ms` | `<= 5 ms` | pass |
| OpenQASM import p95 | `9.9791 ms` | `<= 25 ms` | pass |
| OpenQASM assurance p95 | `2.9249 ms` | `<= 25 ms` | pass |
| OpenQASM export p95 | `2.7414 ms` | `<= 25 ms` | pass |
| Complete OpenQASM p95 | `15.4728 ms` | `<= 25 ms` | pass |

Three additional fresh processes produced median ratios from `0.7477` to
`0.7523`, with a process median of `0.7508`. None passed the `0.25` gate.
System load was materially higher than for the original absolute-time run, so
EXP-015 does not use these measurements to claim an absolute regression or
improvement. The relative failure reproduced consistently and is the release
decision.

The measured implementation preserved the Python reference path, required the
native path during evidence collection, constructed fresh output objects, and
added no circuit-dependent cache. The negative result remains public. The
native implementation is not shipped by the explanation-led candidate.
EXP-014's `100%` versus `6.25%` canonical-convergence result remains a separate
semantic workflow result, not a performance claim.
