# RQM Technical Canon v2 Alignment

`rqm-qiskit` is the Qiskit lowering and execution bridge. Quaternion algebra
belongs to `rqm-core`; compiler IR and optimization belong to `rqm-compiler`.

The bridge preserves phase-safe `SU(2)` semantics tested by EXP-001 through
EXP-003. It makes no claim of alternative quantum mechanics, extra quaternionic
information, improved hardware fidelity, or hardware acceleration.

The validated EXP-012 quaternion-Cartan `SU(4)` result is promoted here only as
a standard-compatible translation capability. Quaternion-Cartan analysis and
source-unitary reconstruction remain owned by `rqm-entanglement`; proof-gated
internal `su4q` blocks remain owned by `rqm-compiler`. This bridge generates
Qiskit candidates, verifies phase-aligned operator equivalence, checks target
compatibility, and applies an explicit target-local selection hierarchy. The
direct `RQ` construction is not privileged and is never described as a
hardware advantage.

The reproducible integration baseline pins Qiskit 2.3.0, Qiskit Aer 0.17.2,
Qiskit QASM 3 Import 0.6.0, and Qiskit IBM Runtime 0.45.0. All promotion tests
are offline; no IBM credentials, jobs, or hardware evidence are involved.

EXP-009's narrow large-batch NumPy kernel result is not a Qiskit or IBM
hardware result.

Evidence authority:
`RQM-Technologies-dev/rqm-experiments/docs/RQM_TECHNICAL_CANON_V2.md`.
