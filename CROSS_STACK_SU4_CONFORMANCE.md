# Cross-Stack Quaternion-Cartan SU(4) Conformance

Date: 2026-07-18

This offline gate used editable local installations of the promoted repositories
with Qiskit 2.3.0. No IBM credentials, account state, job submission, or quantum
hardware were accessed.

## Exact implementation baseline

- `rqm-core`: `1be6a4fd3b8701251c756a4bfd69371d73486e9e`
- `rqm-entanglement`: `f2105bb694764d8d73798d3f482a598db39226e0`
- `rqm-circuits`: `a688d0b749551cb00df5a925df330f9d74c5be0c`
- `rqm-compiler`: `fcc1a0bc67c62a26ab3fffdbf2c51b96100b39f1`
- `rqm-qiskit` synthesis implementation: `559f722d3019932f0a860dca93e50767c98f690a`
- immutable EXP-012 evidence source: `615de9f5143ed603ca732b33a287e3e4f654c4c9`

## Required flow

Each workload completed this exact path:

```text
4x4 SU(4) unitary
-> rqm-entanglement decomposition
-> QuaternionCartanBlock
-> rqm-compiler su4q operation
-> JSON descriptor serialization round trip
-> rqm-qiskit candidate generation and selection
-> selected Qiskit QuantumCircuit
-> Qiskit Operator
-> phase-aligned comparison with the source unitary
```

## Results

| Workload | Weyl class | Selected path | Phase-aligned operator error |
|---|---|---:|---:|
| identity | `local_identity` | `QX` | `0.0` |
| CNOT class | `cnot_cz_class` | `QX` | `5.978733960281817e-16` |
| iSWAP class | `iswap_class` | `QC` | `4.577566798522236e-16` |
| sqrt-SWAP class | `sqrt_swap_class` | `Q3` | `4.926614671774131e-16` |
| SWAP class | `swap_class` | `QX` | `5.551115123125785e-16` |
| generic interior | `generic_interior` | `Q3` | `4.107918958879418e-15` |
| QAOA RZZ | `generic_interior` | `RQ` | `5.551115123125783e-16` |
| mixed XX+YY+ZZ Hamiltonian | `generic_interior` | `QC` | `7.026466286077214e-15` |

Summary:

- maximum operator error: `7.026466286077214e-15`
- ordering failures: `0`
- serialization failures: `0`
- invalid selected candidates: `0`
- generic `UnitaryGate` instructions in selected native paths: `0`
- locally equivalent pair shared one nonlocal fingerprint: passed
- the same locally equivalent pair retained different full canonical hashes: passed
- focused cross-stack tests: `10 passed`

The selected paths demonstrate the required policy boundary: direct `RQ` can
win for a target-local workload, but it is not privileged and lost to `Q3`,
`QC`, or `QX` on seven of the eight fixtures.

## Claim boundary

This is software conformance within standard complex quantum mechanics. It does
not establish unique information, native quaternionic composite mechanics,
general synthesis or runtime superiority, or IBM hardware superiority.
