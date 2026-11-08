# Artifact-bound OpenQASM handoff

`rqm_qiskit.handoff.assure_openqasm3_handoff_isolated(source,
phase_semantics="exact")` provides a bounded four-qubit interchange path.
The direct equivalent is `assure_openqasm3_handoff`; servers should use the
isolated entry point. `verify_openqasm3_artifact(source, artifact,
phase_semantics="exact")` checks independently supplied serialized artifacts.

The compiler owns regional optimization and equivalence; the adapter owns
format conversion, reloading, hashes, and terminal register/readout mapping.
The actual returned OpenQASM is reloaded and checked, not merely the compiler's
in-memory candidate. A failed candidate is withheld and the exact source is
returned with `FALLBACK_ORIGINAL`.

`exact` retains scalar phase at absolute tolerance 1e-10. `phase_invariant`
accepts equivalence up to scalar phase for standalone circuits. Only an exact,
verified, measurement-free result sets `controlled_reuse_eligible=true`; this
is bounded numerical evidence, not formal verification or hardware evidence.

Supported inputs: 1–4 qubits, bound supported named gates, zero declared global
phase, and optional terminal measurements. Maximums are 64 classical bits,
512 operations, and 65536 source bytes. The isolated worker times out after
30 seconds. The direct verifier rejects unsupported or malformed artifacts.
The isolated entry point raises on worker/transport failure so servers must
fail closed. Old compiler versions without explicit phase semantics are refused.

Input assurance starts at QASM bytes. In-memory Qiskit global phase omitted by
an upstream exporter is outside this contract. Nonzero declared global phase
is unsupported. Unsupported structured output exports are also withheld.

The existing assurance APIs keep their existing contracts; this is an explicit
new entry point. Tests are offline in `tests/test_handoff.py`.
