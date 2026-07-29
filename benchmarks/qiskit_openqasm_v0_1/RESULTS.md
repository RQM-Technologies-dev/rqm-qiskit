# Qiskit/OpenQASM Assurance Bridge v0.1 Results

Verdict: **implemented but not release-ready**.

This is local SDK and numerical-operator evidence. It is not simulator, emulator, provider, or QPU execution evidence.

## Primary results

- Verified eligible circuits: 160/160 (100.0%).
- False equivalence decisions: 0.
- Unsupported inputs failing closed: 20/20.
- Withheld-candidate disclosures: 0.
- Median adapter overhead versus compiler-only optimization: 813.1%.
- Mean source/RQM/Qiskit-level-3 gate counts: 13.68 / 8.07 / 7.24.

The coverage change comes from recognizing `iSWAP` in the compiler verifier's existing supported-unitary path. No tolerance or verification boundary was relaxed.

## Release gates

- PASS — verification coverage at least 95 percent.
- PASS — zero false equivalence.
- PASS — zero withheld candidate disclosures.
- PASS — all unsupported fail closed.
- PASS — deterministic evidence ids.
- FAIL — median adapter overhead no greater than 25 percent.

The Qiskit comparison is descriptive. It does not establish universal compiler superiority. TKET remains a separate future comparison.
