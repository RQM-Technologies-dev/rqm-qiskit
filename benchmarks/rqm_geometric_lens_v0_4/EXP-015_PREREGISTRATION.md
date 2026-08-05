# EXP-015 Native Adapter Preregistration Mirror

Status: frozen before native implementation measurement

EXP-015 reused the exact EXP-014 corpus digest
`d244cfaa87ca2775c79845ae546e57e0931d5828aaee0d9b079bd12b51c16459`:
64 held-out families, the existing four variants, and 256 samples in manifest
order.

The decision metric remained median per-sample
`(import + lowering + complete report serialization) / compiler
optimize-and-verify <= 0.25`. Direct assurance p95 remained bounded at `5 ms`,
and every OpenQASM stage and end-to-end p95 remained bounded at `25 ms`.
Absolute adapter time also had to improve over the frozen `274.994 us` median,
so slowing the compiler could not create a pass.

Native and Python paths were required to produce identical descriptors,
registers, operator semantics, reports, fallback behavior, and independent
mutable report copies. Any native capability mismatch selected the complete
Python reference path; the decision runner instead failed if native execution
was unavailable. Circuit-dependent caches, cohort changes, verification
changes, and work moved into the compiler denominator were prohibited.

A failed ratio preserves the raw result and blocks release. A pass would have
supported only a bounded software-overhead claim on the measured local stack.
