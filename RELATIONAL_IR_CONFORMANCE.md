# Adaptive relational IR conformance

`rqm-entanglement` owns the relational hierarchy and `rqm-compiler` owns routing policy. `rqm-qiskit` does not duplicate that mathematics.

Backend contract:

1. `AxisHinge(xx|yy|zz, theta)` is materialized by the compiler as one canonical `rxx`/`ryy`/`rzz`; this bridge already lowers those to Qiskit native pair rotations.
2. `CartanRelation(c1,c2,c3)` is materialized as the minimal nonzero ordered subset of `rxx(c1)`, `ryy(c2)`, `rzz(c3)`.
3. `QuaternionCartanBlock` continues through the existing verified `su4q` synthesis path.
4. Bell-state compression is state-analysis metadata and is not a backend gate.
5. Generic 4x4 materialization is a verified fallback, not the preferred path.

The cross-stack rule is: stay geometric/relational until backend lowering requires a conventional representation.
