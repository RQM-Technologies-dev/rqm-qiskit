# RQM Technical Canon v2 Alignment

`rqm-qiskit` is the Qiskit lowering and execution bridge. Quaternion algebra
belongs to `rqm-core`; compiler IR and optimization belong to `rqm-compiler`.

The bridge preserves phase-safe `SU(2)` semantics tested by EXP-001 through
EXP-003. It makes no claim of alternative quantum mechanics, extra quaternionic
information, improved hardware fidelity, or hardware acceleration.

EXP-009's narrow large-batch NumPy kernel result is not a Qiskit or IBM
hardware result.

Evidence authority:
`RQM-Technologies-dev/rqm-experiments/docs/RQM_TECHNICAL_CANON_V2.md`.
