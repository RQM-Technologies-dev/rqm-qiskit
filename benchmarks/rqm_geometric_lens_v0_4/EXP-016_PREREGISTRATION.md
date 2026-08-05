# EXP-016 Preregistration

Status: frozen before implementation measurement

Date: `2026-08-05`

## Mission

Help the world understand ordinary quantum computing through quaternionic
geometry while remaining compatible with Qiskit.

The product is an educational and analytical bridge, not a replacement
compiler or a Qiskit performance competitor.

## Frozen corpus

The corpus contains exactly 36 records in `PREREGISTRATION.json` order:

- 13 one-qubit circuits covering named gates, axis rotations, noncommuting and
  ZYZ composition, explicit global phase, terminal measurement, and a public
  `UnitaryGate`;
- 9 two-qubit circuits covering product, Bell, CZ, iSWAP, SWAP, RXX, local
  equivalence, a public unitary, and reversed terminal measurements;
- 6 statevectors covering basis, equatorial, general, and sign-negated
  representatives; and
- 8 partial/boundary cases covering symbolic parameters, reset,
  initialization, mid-circuit measurement, control flow, GHZ, QFT, and a
  larger regional circuit.

The record identifiers, category membership, counts, and gates may not change
after the first implementation measurement.

## Acceptance gates

- Every complete one-qubit explanation answers circuit purpose, quaternion,
  rotation, Bloch geometry, phase behavior, and ideal measurement questions.
- Every complete two-qubit explanation reports verified SU(4)/Weyl and
  entanglement structure.
- Numeric geometry agrees with Qiskit operators/statevectors and the existing
  RQM math authorities within `1e-9`.
- Five repeated JSON and text renders per record are byte-identical.
- Input circuits, registers, and terminal measurement mappings are unchanged.
- Unsupported or nonunitary geometry is marked `not_computed`; no unavailable
  quantity is narrated as computed.
- Released product code contains no Qiskit private-module, `_data`, or packed
  circuit dependency.
- Direct complete one- and two-qubit explanation p95 is at most `50 ms`.
- OpenQASM explanation p95 is at most `100 ms`.
- Pure-wheel installs pass on Python 3.11–3.13; Linux, macOS, and Windows CI
  coverage must exist before release readiness is recorded.

There is no ratio-to-compiler gate and no Qiskit-superiority comparison.

## Stop rules

Any false mathematical statement, input mutation, non-deterministic report,
private-Qiskit dependency, or silent fabrication blocks the candidate. Missing
geometry narrows the explanation and becomes explicit; it does not weaken the
gate. A failed gate is retained as a negative result.

## Claim boundary

Passing supports a bounded claim that `rqm-qiskit` provides a deterministic,
standard-compatible quaternionic explanation of the frozen Qiskit corpus. It
does not support new physics, additional quantum information, hardware
evidence, compiler superiority, or general Qiskit superiority.
