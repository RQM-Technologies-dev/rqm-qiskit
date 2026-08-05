# RQM-Qiskit 0.4 Performance Results

Release gate: **failed**

| Metric | Result | Required | Verdict |
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
introduced. The remaining failure blocks
publication of 0.4 but does not change the EXP-014 semantic fingerprint verdict.
