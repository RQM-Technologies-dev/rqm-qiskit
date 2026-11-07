# Selected-strategy dispatch replay

This is a separate follow-on to the frozen
[SIM-030 synthesis study](https://github.com/RQM-Technologies-dev/rqm-experiments/tree/main/IBM/simulation_studies/SIM-030-conventional-baseline-gates).
The original study, corpus, source, and results were not modified.

## Change and contract

An explicit `Q3`, `QF`, `QC`, `QX`, or `RQ` request now runs and verifies only
that candidate. Explicit reports contain only the evaluated path, and invalid
requests still raise rather than fall back. `best_native` still runs all five
factories with the same validation and selection hierarchy. This is dispatch
overhead removal, not a new synthesis algorithm or Qiskit capability parity.

The baseline is `rqm-qiskit` main commit
`5d67721f19be462fca718e2fafa83b885e2a38ef`. Its `synthesis.py` is byte-identical
to frozen SIM-030 commit `54ef52dfc585388d0a127b62d771966c9d38d4c7`.
The candidate source SHA-256 is
`3b25abbd139d28ad1cbfb1fa1c36dce9878dbea343918c2dda5ff19c25166581`.

## Design

- All 26 original synthesis inputs: two legacy fixtures and 24 held-out cases.
- Both original synthetic targets, CX and RZZ: 52 workload/target pairs.
- Baseline and candidate for each explicit strategy and `best_native`, plus
  all three original conventional Qiskit methods. No best-of-five timing oracle.
- One warmup, seven measured repetitions, deterministic rotating method order.
- End-to-end timing includes raw-descriptor conversion, source matrix, RQM
  decomposition where applicable, synthesis, and full-operator/native-target checks.
- Every successful output must have phase-aligned operator error at most `1e-10`.
  Explicit baseline/candidate instruction digests must match across all samples.
- Unsupported requests remain visible as unavailable, never counted as wins.
- Local software only. No backend, calibration, provider, or hardware execution.

The recorded plan is [PRE_EXECUTION.json](PRE_EXECUTION.json), including the
review-driven timeout correction. The first exploratory replay was rerun after
fixing the inherited exception-swallowing timeout issue; no cases, methods, or
performance thresholds were changed based on results. The replay's alarm now
unwinds synthesis before converting to `TimeoutError`. Python signal handling
can still be delayed inside native code, so this is an interruptible timeout,
not a process-level hard deadline. No method timed out in the reported run.

## Result

Median speedup is the median of the paired baseline/candidate median-latency
ratios over supported rows, not the ratio of the two aggregate latency medians.

| Strategy | Supported pairs | Before median (ms) | After median (ms) | Median speedup |
|---|---:|---:|---:|---:|
| Q3 | 52 | 27.14 | 10.84 | 2.69x |
| QF | 26 | 32.68 | 10.63 | 3.12x |
| QC | 26 | 32.77 | 10.17 | 3.17x |
| QX | 52 | 27.77 | 10.52 | 2.50x |
| RQ | 52 | 27.88 | 9.00 | 2.89x |
| best_native | 52 | 28.38 | 27.94 | 1.01x |

- 208 supported explicit pairs had identical instruction digests.
- 676 successful method series, 5,408 successful output checks, maximum operator
  error `8.34e-14`. All successful outputs were target-compatible.
- 104 unavailable method series were exactly the expected baseline/candidate
  QF and QC requests on CX-only targets. No availability changes.
- `best_native` had no two-qubit-count changes; its timing is effectively unchanged.
- The chosen RQM routes remain roughly **1.27–1.54x slower than dedicated Qiskit**
  on the per-strategy median comparison, and automatic mode is about 3.84x slower.
  This change does not reverse the earlier conventional-baseline conclusion.

Timings are local measurements, not a speed guarantee. Seven repetitions only
partially rotate fifteen methods, so this is not fully counterbalanced evidence.
The source-compatibility replay preserves SIM-030's Qiskit 2.5.1 and dependency
environment; separate package tests used freshly resolved dependencies, including
Qiskit 2.5.2. This is not a new release-lock or hardware qualification.

## Evidence and reproduction

- [summary.json](summary.json) defines the aggregation formulas and all ranges.
- [results.json.gz](results.json.gz) contains every raw timing, output check,
  unavailable reason, input/source/script hash, and dependency version.
  Decompressed SHA-256:
  `09c7e6c2cb5c788a0c6b3c3b49fbdfc5e68ad9d0422c74a4c8d7ec1c5dc80234`.
- `replay.py` fails closed if any frozen input hash, baseline source hash, or
  Qiskit version differs. It refuses to overwrite an existing result.

Run in the original SIM-030 environment with this checkout's `src` on
`PYTHONPATH`, and a baseline `synthesis.py` from either commit above:

```sh
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python \
  benchmarks/selected_synthesis_dispatch_v0_1/replay.py \
  --sim030-root /path/to/SIM-030-conventional-baseline-gates \
  --baseline-source /path/to/baseline/synthesis.py \
  --output /path/to/new-replay.json
```

The replay uses POSIX `SIGALRM`. Runtime package tests remain platform-neutral;
the two timeout-harness tests skip on platforms without this signal.
