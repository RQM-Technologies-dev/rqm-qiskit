# Qiskit/OpenQASM Assurance Bridge v0.3 Latency Results

Release verdict: **FAIL**.

The frozen 200-case corpus and all semantic gates were retained.

## Results

- Eligible verification coverage: 160/160 (100.0%).
- False-equivalence decisions: 0.
- Unsupported inputs failing closed: 20/20.
- Withheld-candidate disclosures: 0.
- Median adapter overhead versus compiler-only optimization: 191.2% (v0.2: 817.8%).

## Median stage timing

- qiskit import: 80.377 microseconds.
- normalization serialization: 31.012 microseconds.
- compiler optimize and verify: 765.391 microseconds.
- standalone semantic verification: 540.613 microseconds.
- qiskit lowering: 291.858 microseconds.
- openqasm export including lowering: 1602.304 microseconds.
- openqasm reparse: 6967.822 microseconds.
- adapter report serialization: 74.725 microseconds.
- complete qiskit assurance: 1260.017 microseconds.

## Registered gates

- PASS — verification coverage at least 95 percent.
- PASS — zero false equivalence.
- PASS — zero withheld candidate disclosures.
- PASS — all unsupported fail closed.
- PASS — deterministic evidence ids.
- FAIL — median adapter overhead no greater than 25 percent.

A failing latency gate keeps rqm-qiskit 0.3.0 unreleased. Correctness is not traded for speed.
