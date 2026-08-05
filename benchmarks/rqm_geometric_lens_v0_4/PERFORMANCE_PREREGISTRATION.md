# RQM-Qiskit 0.4 Performance Gate

The frozen EXP-014 held-out one-qubit corpus is used without changing its
angles or variants.

Required gates:

- median `(import + canonical lowering + report serialization) / compiler
  optimize-and-verify` no greater than `0.25`;
- complete direct Qiskit assurance p95 no greater than `5 ms`; and
- OpenQASM parse/import, Qiskit assurance, export, and complete end-to-end p95
  each no greater than `25 ms`.

All timing samples are retained. A failed relative-overhead gate blocks release
but does not invalidate the semantic EXP-014 fingerprint result.
