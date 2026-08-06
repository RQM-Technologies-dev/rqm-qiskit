# EXP-014 Preregistration Amendment 01

Status: frozen before extension measurement
Primary result status: immutable

## Reason

A plan-conformance audit after the primary EXP-014 run found that the frozen
advantage cohort covered generated equivalent `SU(2)` families, inequivalent
controls, Bell-like inputs, and fixed-pair `SU(4)` windows, but did not include
the named GHZ, QFT-style, VQE-style, and QAOA-style representative circuits or
the complete fail-closed boundary set.

This amendment adds an independent validation extension. It does not add
families to the discovery or held-out advantage cohorts, does not change any
threshold, and cannot turn a failed primary gate into a passing gate. The
primary raw result and semantic digest remain unchanged.

## Frozen extension

- eight exploratory and sixteen held-out generated noncommuting one-qubit
  chains, each paired with an exactly equivalent split-angle spelling and a
  reversed-order counterexample;
- Bell, GHZ, QFT-style, VQE-style, and QAOA-style circuits using only the
  declared supported gate boundary;
- terminal measurement with a reversed classical mapping;
- mid-circuit measurement, reset, symbolic parameter, custom instruction, and
  unsupported controlled-phase boundaries; and
- a `q`/`-q` control showing identical standalone measurement probabilities
  but different controlled operators.

## Extension gates

- all generated equivalent pairs have identical canonical fingerprints and
  phase-aligned operator error at most `1e-9`;
- every reversed-order noncommuting counterexample has a different
  fingerprint;
- every supported representative is `VERIFIED`;
- every declared unsupported boundary returns the exact original circuit;
- the terminal measurement register names and reversed mapping are exact; and
- standalone `q`/`-q` probability error is at most `1e-12`, while their
  controlled operators are not equal up to global phase.

These are correctness and coverage gates only. They support no new performance,
circuit-quality, hardware, or physics claim.
