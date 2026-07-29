# Qiskit/OpenQASM Assurance Bridge v0.2 Hardening Results

Coverage verdict: **PASS**.
Full release verdict: **FAIL**.

The frozen 200-case v0.1 corpus was reused byte-for-byte. The v0.1 result was not overwritten.

## Results

- Eligible verification coverage: 160/160 (100.0%), up from 91/160 (56.875%).
- False equivalence decisions: 0.
- Unsupported inputs failing closed: 20/20.
- Withheld-candidate disclosures: 0.
- Median adapter overhead versus compiler-only optimization: 817.8%.

The coverage improvement comes only from declaring iSWAP in the compiler verifier path whose unitary simulator already supported it. No tolerance, corpus, public gate boundary, or fail-closed rule changed.

## Registered gates

- PASS — verification coverage at least 95 percent.
- PASS — zero false equivalence.
- PASS — zero withheld candidate disclosures.
- PASS — all unsupported fail closed.
- PASS — deterministic evidence ids.
- FAIL — median adapter overhead no greater than 25 percent.

The semantic coverage defect is resolved. The bridge remains blocked from a full release-ready claim because adapter overhead still exceeds the original 25% gate.
