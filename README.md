# rqm-qiskit

**A Qiskit-compatible quaternionic explanation bridge for ordinary quantum computing.**

> Help the world understand ordinary quantum computing through quaternionic
> geometry while remaining compatible with Qiskit.

Receives compiler-optimized circuit representations and lowers them into Qiskit
`QuantumCircuit` objects for execution on Aer simulators or IBM Quantum hardware.
`rqm-qiskit` is downstream of both `rqm-circuits` (the public circuit IR) and
`rqm-compiler` (the optimization engine).

---

## RQM Technical Canon v2

This bridge lowers standard-compatible compiler semantics into Qiskit. It
preserves tested phase-sensitive `SU(2)` behavior and ordered composition; it
does not implement alternative mechanics or establish a quantum-hardware
advantage. See [RQM_TECHNICAL_CANON_V2.md](RQM_TECHNICAL_CANON_V2.md).

## Version 0.4 candidate status

The unreleased 0.4 candidate explains ordinary one- and two-qubit Qiskit
circuits through quaternion/SU(2), rotation, Bloch, phase, measurement,
SU(4)/Weyl, and entanglement geometry. Explanation uses Qiskit's public
`Operator` and `Statevector` interfaces and leaves the input circuit unchanged.
Optimization is an optional, narrower, independently verified workflow.

EXP-016 passed its 36-record local correctness, determinism, compatibility,
and absolute-responsiveness gate. The candidate is still **not released**:
fresh Python 3.11–3.13 wheel installs and Linux/macOS/Windows workflow runs must
also pass before release readiness is recorded. No publication or invitation is
authorized by this repository state.

EXP-014's `100%` versus `6.25%` canonical-convergence result remains valid.
EXP-015's failed `0.7427` native-adapter ratio also remains valid historical
engineering evidence, but comparative performance is not a 0.4 product gate.
See the [public evidence packet](benchmarks/rqm_geometric_lens_v0_4/).

---

## Architecture

`rqm-qiskit` occupies a single, well-defined layer in the RQM dependency spine:

```
rqm-core        (math foundation: Quaternion, SU(2), Bloch, spinor)
       ↓
rqm-circuits    (canonical external/public circuit IR: the ecosystem wire format)
       ↓
rqm-compiler    (internal optimization / rewriting engine)
       ↓
rqm-qiskit      (Qiskit / IBM lowering and execution bridge)   ← this package
       ↓
 Qiskit QuantumCircuit / transpilation / execution
```

`rqm-braket` sits alongside `rqm-qiskit` as the AWS / Braket equivalent.
`rqm-optimize` is an optional backend-adjacent optimization / compression layer
that can be applied before handing circuits to either bridge.

### Layer responsibilities

| Package | Responsibility |
|---------|----------------|
| `rqm-core` | Quaternion algebra, SU(2) matrices, Bloch conversions, spinor helpers |
| `rqm-circuits` | Canonical **external** circuit IR — the public schema used by Studio, API, and callers |
| `rqm-compiler` | Internal optimization and rewriting engine; produces compiler circuits consumed by bridge layers |
| `rqm-qiskit` | Qiskit-compatible quaternionic explanation; compiler circuit → Qiskit lowering; Aer/IBM execution; result shaping |

### Typical data flow

External callers (Studio, API, SDK users) build or receive circuits in
`rqm-circuits` format.  Those circuits are validated and parsed upstream, then
fed into `rqm-compiler` for optimization.  `rqm-qiskit` receives the
compiler-optimized output and translates it to Qiskit for execution:

```
Studio / API / SDK
      │  rqm-circuits payload
      ▼
rqm-compiler  (parse + optimize)
      │  compiler Circuit / CompiledCircuit
      ▼
rqm-qiskit  (lower + execute)
      │  QiskitResult / dict
      ▼
IBM Quantum / Aer
```

### What this repo owns

- Deterministic explanations of public-Qiskit-evaluable one- and two-qubit circuits
- Compiler circuit → Qiskit gate mapping
- Qiskit `QuantumCircuit` generation
- Qiskit/Aer execution
- Asynchronous job submission and polling
- IBM Quantum provider configuration
- Qiskit result normalization and caching

### What this repo does not own

- Physics math (quaternion / SU(2) — lives in `rqm-core`)
- Canonical **external** circuit schema (lives in `rqm-circuits`)
- Optimization pass design (lives in `rqm-compiler` or `rqm-optimize`)
- API wire format
- Studio payload format

---

## Installation

Install from PyPI:

```bash
pip install rqm-qiskit
```

Dependencies:
- `rqm-core` — quantum math foundation
- `rqm-compiler` — optimization engine (produces the circuit representation consumed here)
- `qiskit` — quantum circuit execution

> **Note:** `rqm-circuits` (the public circuit IR) is an upstream concern.
> `rqm-qiskit` works with compiler-lowered circuits, not raw `rqm-circuits` payloads directly.

To also run local simulations (recommended):

```bash
pip install "rqm-qiskit[simulator]"
```

To import and export OpenQASM 3:

```bash
pip install "rqm-qiskit[qasm3]"
```

After 0.4 is published, the five-minute circuit-lens installation will be:

```bash
pip install "rqm-qiskit[cli]"
rqm-qiskit explain circuit.qasm \
  --detail standard \
  --output EXPLANATION.md \
  --report REPORT.json
```

For the unreleased candidate, install this checkout with
`pip install -e ".[cli]"` instead.

To use real IBM Quantum backends:

```bash
pip install "rqm-qiskit[ibm]"
```

For development:

```bash
git clone https://github.com/RQM-Technologies-dev/rqm-qiskit.git
cd rqm-qiskit
pip install -e ".[dev,simulator]"
```

---

## Quickstart

### Geometric circuit lens

```python
from qiskit import QuantumCircuit
from rqm_qiskit import analyze_qiskit_circuit, canonical_su2_fingerprint

circuit = QuantumCircuit(1, 1)
circuit.rz(0.37, 0)
circuit.ry(-0.81, 0)
circuit.rz(1.13, 0)
circuit.measure(0, 0)

report = analyze_qiskit_circuit(circuit)
print(report.to_text(detail="standard"))

# The complete evidence remains available as deterministic JSON.
payload = report.to_dict()
print(payload["local_geometry"][0]["canonical_quaternion"])
print(canonical_su2_fingerprint(circuit))
```

The explanation answers what the quaternion is, which axis and angle it
represents, where the |0⟩ input ends on the Bloch sphere, how phase behaves,
and what ideal computational-basis measurements predict. For supported
two-qubit circuits it also explains SU(4), Weyl, local-equivalence, perfect-
entangler, concurrence, and entropy structure. The quaternionic wavefunction
is a geometric regrouping of the standard complex spinor; the report does not
claim additional information, a new observable, or new physics.

### Existing execution bridge

```python
from rqm_compiler import Circuit
from rqm_qiskit import run_qiskit, to_qiskit_circuit

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0)
c.measure(1)

# Tier 1 — run and get a JSON-compatible result dict
result = run_qiskit(c, shots=1024)
print(result["counts"])   # {"00": ~512, "11": ~512}

# Tier 2 — translate only (no execution)
qc = to_qiskit_circuit(c)
print(qc.draw(output="text"))
```

> **API / Studio users:** external callers typically begin with an `rqm-circuits`
> payload.  That payload is parsed and validated upstream (by `rqm-circuits`) and
> then optimized (by `rqm-compiler`) before a `Circuit` object reaches `rqm-qiskit`.
> The examples above show direct compiler circuit usage, which is correct for
> in-process or server-side code that has already gone through that upstream path.

See the [Public API](#public-api) section for the full tier breakdown.

---

## Fail-closed Qiskit and OpenQASM assurance

Whole-circuit dense verification accepts bound standalone unitary Qiskit
circuits on one to three qubits. Larger circuits are split into deterministic
contiguous regions of at most three qubits; all changes are withheld unless
every changed region verifies. Terminal measurements and their original
quantum/classical register mapping are preserved exactly. A changed circuit is
returned only after proof-gated compiler verification.

```python
from qiskit import QuantumCircuit, qasm3
from rqm_qiskit import assure_openqasm3, assure_qiskit_circuit

source = QuantumCircuit(2)
source.h(0)
source.cx(0, 1)

result = assure_qiskit_circuit(source)
assert result.assurance_status in {"VERIFIED", "FALLBACK_ORIGINAL"}

# One-step OpenQASM assurance returns the exact source on fallback.
openqasm_source = qasm3.dumps(source)
qasm_result = assure_openqasm3(openqasm_source)
```

Supported gates are `id`, `x`, `y`, `z`, `h`, `s`, `t`, `rx`, `ry`, `rz`,
`p`, `cx`, `cy`, `cz`, `swap`, `iswap`, `rxx`, `ryy`, `rzz`, and barriers.
The bridge rejects symbolic parameters, non-finite values, nonzero or symbolic
global phase, reset, delay, mid-circuit measurement, classical control flow,
initialization, custom/unitary instructions, and unsupported gates. It never
silently drops an instruction.

Verification is bounded canonical or numerical verification of standalone
unitary semantics up to global phase. It is not theorem-prover formal
verification, execution evidence, or permission to embed a returned circuit as
a coherently controlled subcircuit where exact global phase can become
observable.

The frozen local v0.1 corpus and bounded baseline are in
[`benchmarks/qiskit_openqasm_v0_1`](benchmarks/qiskit_openqasm_v0_1/).
Coverage hardening is recorded in
[`benchmarks/qiskit_openqasm_v0_2`](benchmarks/qiskit_openqasm_v0_2/), and the
final preregistered latency result is in
[`benchmarks/qiskit_openqasm_v0_3`](benchmarks/qiskit_openqasm_v0_3/).
The v0.3 run retained 100% eligible verification coverage and every fail-closed
gate, but its `191.19%` median adapter overhead still exceeds the frozen `25%`
release gate. Version 0.3.0 therefore remains unreleased.

EXP-015 retained the unchanged 0.4 performance cohort and failed its native
acceleration gate at a `0.7427` adapter/compiler ratio versus `0.25`. That
negative result remains preserved. The C accelerator and private packed-Qiskit
access are not part of the explanation product. Version 0.4 uses public Qiskit
interfaces and is judged on correctness, explanatory usefulness,
compatibility, fail-closed behavior, packaging, and absolute responsiveness.

---

## Public API

```python
from rqm_qiskit import (
    QiskitBackend,          # OO entry point
    QiskitTranslator,       # translation class
    to_qiskit_circuit,      # functional translation API
    run_qiskit,             # functional execution API
    async_run_qiskit,       # async functional execution API
    execute_rqm_program,    # high-level canonical API integration
    get_ibmq_provider,      # IBM Quantum provider
    QiskitJob,              # async job handle
    QiskitResult,           # structured result wrapper
    analyze_qiskit_circuit, # versioned quaternion/SU(2)/SU(4) report
    analyze_qiskit_state,   # bounded one- and two-qubit state report
    canonical_su2_fingerprint,
    assure_openqasm3,
    async_assure_openqasm3,
)
```

The API is organized into three explicit tiers.  **Start with the highest tier
that covers your use case.**

---

### Tier 1 — Execution  *(start here)*

| Style | Entry point | Returns |
|-------|-------------|---------|
| **Functional (sync)** | `run_qiskit(circuit, *, shots, backend, optimize, include_report)` | `dict` (JSON-compatible) |
| **Functional (async)** | `async_run_qiskit(circuit, *, shots, backend, optimize, ...)` | `QiskitJob` |
| **High-level** | `execute_rqm_program(descriptor, *, backend, shots, optimize)` | `dict` (JSON-compatible) |
| **OO (sync)** | `QiskitBackend().run(circuit, *, shots, optimize, include_report)` | `QiskitResult` |
| **OO (async)** | `QiskitBackend().async_run(circuit, *, shots, backend, optimize, ...)` | `QiskitJob` |

#### Synchronous execution (`run_qiskit`)

Returns a plain `dict` ready for APIs and serialization:

```python
from rqm_compiler import Circuit
from rqm_qiskit import run_qiskit

c = Circuit(2)
c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)

result = run_qiskit(c, shots=1024)
# {
#   "counts":   {"00": 512, "11": 512},
#   "shots":    1024,
#   "backend":  "aer_simulator",
#   "metadata": {"outcomes": 2, "most_likely": "00"},
# }
```

With compiler report:

```python
result = run_qiskit(c, optimize=True, shots=1024, include_report=True)
# metadata gains: {"optimized": True, "compiler_report": {...}}
```

#### Asynchronous execution (`async_run_qiskit`)

Submits a circuit and returns a `QiskitJob` handle immediately.
For local Aer runs the job is already complete; for IBM backends it runs
asynchronously.

```python
from rqm_compiler import Circuit
from rqm_qiskit import async_run_qiskit

c = Circuit(1)
c.h(0); c.measure(0)

# Submit (returns immediately)
job = async_run_qiskit(c, shots=1024)
print(job.job_id())   # e.g. "local-a3f9c12b4d67"
print(job.status())   # "DONE" for local Aer, "RUNNING" for IBM

# Retrieve result (blocks until done for IBM backends)
result = job.result()
print(result.counts)

# JSON-serializable job summary
print(job.to_dict())
```

For real IBM Quantum backends (requires credentials – see below):

```python
import os
os.environ["QISKIT_IBM_TOKEN"] = "my-api-token"

job = async_run_qiskit(c, shots=1024, backend="ibm_brisbane")
print(job.job_id())             # IBM job ID (returned immediately)
result = job.result(timeout=300)  # blocks until done or timeout
```

#### High-level canonical API integration (`execute_rqm_program`)

Accepts a compiler-compatible program descriptor dict.  In the full RQM stack,
API and Studio traffic originates as `rqm-circuits` payloads; those are parsed
and validated upstream before reaching this layer as descriptor dicts.  If you
are integrating directly with `quantum-compiler-api`, the API layer handles the
`rqm-circuits` → descriptor conversion for you.

```python
from rqm_qiskit import execute_rqm_program

descriptor = {
    "num_qubits": 2,
    "operations": [
        {"gate": "h",       "targets": [0], "controls": [],  "params": {}},
        {"gate": "cx",      "targets": [1], "controls": [0], "params": {}},
        {"gate": "measure", "targets": [0], "controls": [],  "params": {"key": "m0"}},
        {"gate": "measure", "targets": [1], "controls": [],  "params": {"key": "m1"}},
    ],
}

result = execute_rqm_program(descriptor, shots=1024)
print(result["counts"])  # {"00": ~512, "11": ~512}
```

From `cURL` via the RQM API (example):

```bash
curl -X POST https://api.rqm.example/run \
  -H "Content-Type: application/json" \
  -d '{"num_qubits": 1, "operations": [{"gate": "h", "targets": [0], "controls": [], "params": {}}, {"gate": "measure", "targets": [0], "controls": [], "params": {"key": "m0"}}], "shots": 1024}'
```

#### OO interface (`QiskitBackend`)

```python
from rqm_compiler import Circuit
from rqm_qiskit import QiskitBackend

c = Circuit(2)
c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)

backend = QiskitBackend()

# Synchronous
result = backend.run(c, shots=1024)
print(result.counts)
print(result.most_likely_bitstring())
print(result.to_dict())  # JSON-compatible dict

# Asynchronous
job = backend.async_run(c, shots=1024)
print(job.status())
result = job.result()
```

---

### Tier 2 — Translation

Use these when you need the `QuantumCircuit` object itself (for inspection,
custom execution, serialization, or third-party tooling).

| Style | Entry point | Returns |
|-------|-------------|---------|
| **Functional** | `to_qiskit_circuit(circuit, *, optimize, include_report)` | `QuantumCircuit` (or tuple) |
| **OO** | `QiskitTranslator().to_quantum_circuit(circuit, *, optimize, include_report)` | `QuantumCircuit` (or tuple) |

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_qiskit_circuit

c = Circuit(2)
c.h(0); c.cx(0, 1)

qc = to_qiskit_circuit(c)
print(qc.draw(output="text"))

# With report tuple
qc, report = to_qiskit_circuit(c, optimize=True, include_report=True)
```

Internal compiler `su4q` blocks are lowered through the same
`compiled_circuit_to_qiskit()` path. Pass a two-qubit Qiskit `Target` to make
selection target-local, and request the JSON-safe synthesis audit separately:

```python
qc, synthesis_reports = to_qiskit_circuit(
    compiled,
    target=target,
    include_synthesis_report=True,
)
```

For each `su4q` block the bridge generates five candidates:

| Path | Candidate |
|------|-----------|
| `Q3` | Qiskit level-3 transpilation |
| `QF` | Fractional-target level-3 transpilation; requires parameterized `rx` and `rzz` |
| `QC` | Controlled-U decomposition using `RZZGate` |
| `QX` | Exact CX-basis two-qubit decomposition |
| `RQ` | Direct quaternion-local / Cartan-interaction construction |

Every candidate is rejected unless it is phase-equivalent to the source block
within `1e-10`, target-compatible, and free of generic two-qubit `unitary`
instructions. `best_native` then minimizes, in order: two-qubit count,
scheduled duration, total native gates, two-qubit depth, full depth,
compilation latency, and QPY size. The report records every candidate metric,
failure reason, Weyl class, nonlocal fingerprint, selected path, and selection
reason.

`RQ` is deliberately a candidate, not a preferred default. It uses exact
single-qubit Euler synthesis plus basis-changed, positive-angle `rzz`
interactions; it wins only when the same target-local hierarchy selects it.
Targets outside the current two-qubit scope fail closed.

The editable-local eight-workload integration gate and exact source commits are
recorded in [CROSS_STACK_SU4_CONFORMANCE.md](CROSS_STACK_SU4_CONFORMANCE.md).

`QiskitTranslator` also exposes `apply_gate(qc, descriptor)` for applying
a single canonical gate descriptor to an existing `QuantumCircuit`.

---

### Tier 3 — Advanced / Internal

Reach for these only when Tiers 1–2 are not enough.

| Entry point | Purpose |
|-------------|---------|
| `QiskitBackend().compile(circuit, *, optimize, include_report)` | Translate only (OO alias for Tier 2) |
| `QiskitBackend().run_local(circuit, shots, optimize)` | Run on local Aer (returns `QiskitResult`) |
| `compiled_circuit_to_qiskit(source)` | Core lowering path (all Tier 1–2 routes through this) |
| `synthesize_su4_block(block, *, target, strategy, include_report)` | Generate, verify, and select local SU(4) candidates |
| `direct_rq_circuit(block)` | Build the exact direct quaternion-Cartan candidate |
| `run_local(circuit, shots, optimize)` | Raw Aer execution (returns `dict[str, int]`) |
| `run_backend(circuit, backend, shots)` | Raw real-backend execution |
| `get_ibmq_provider(token, instance, channel)` | Obtain authenticated IBM Quantum provider |
| `spinor_to_circuit(α, β, target)` | Spinor → `QuantumCircuit` (delegates math to `rqm-core`) |
| `bloch_to_circuit(θ, φ, target)` | Bloch angles → `QuantumCircuit` |
| `QiskitResult` | Structured result wrapper (`counts`, `probabilities`, `to_dict()`, `from_dict()`) |
| `QiskitJob` | Async job handle (`job_id()`, `status()`, `result()`, `to_dict()`) |
| `RQMState`, `RQMGate`, `RQMCircuit` | Legacy / transitional helpers *(subject to removal)* |

#### Custom errors (all subclass `RuntimeError`)

| Exception | When raised |
|-----------|-------------|
| `RQMQiskitError` | Base class for all rqm-qiskit errors |
| `BackendNotFoundError` | Backend name cannot be found or resolved |
| `CredentialsError` | IBM Quantum credentials missing or invalid |
| `JobFailedError` | Quantum job failed during or after execution |
| `TranslationError` | Circuit cannot be translated to Qiskit IR |

---

## IBM Quantum Configuration

`rqm-qiskit` can target real IBM Quantum backends via `qiskit-ibm-runtime`.

### Credentials

Set the following environment variables **before** calling any IBM-backed function:

| Variable | Description | Default |
|----------|-------------|---------|
| `QISKIT_IBM_TOKEN` | Your IBM Quantum API token (**required**) | — |
| `QISKIT_IBM_INSTANCE` | Service instance, e.g. `"ibm-q/open/main"` | provider default |
| `QISKIT_IBM_CHANNEL` | Channel: `"ibm_quantum"` or `"ibm_cloud"` | `"ibm_quantum"` |

Alternatively, pass credentials directly:

```python
from rqm_qiskit import get_ibmq_provider

provider = get_ibmq_provider(token="my-api-token", instance="ibm-q/open/main")
backend = provider.backend("ibm_brisbane")
result = run_qiskit(c, shots=1024, backend=backend)
```

### String backend resolution

Pass a backend name string directly to `run_qiskit` or `async_run_qiskit`;
credentials must be set via environment variables:

```python
import os
os.environ["QISKIT_IBM_TOKEN"] = "my-api-token"

result = run_qiskit(c, shots=1024, backend="ibm_brisbane")
# or
job = async_run_qiskit(c, shots=1024, backend="ibm_brisbane")
```

The string `"aer_simulator"`, `"local"`, or `"aer"` always maps to the local
Aer simulator (no credentials needed).

---

## Result Caching

`QiskitResult` supports JSON serialization for caching in databases or the
RQM API:

```python
from rqm_qiskit import QiskitResult

# Serialize to dict / JSON
result = QiskitResult({"00": 512, "11": 512}, shots=1024, job_id="local-abc123")
d = result.to_dict(backend="aer_simulator")
# {
#   "counts": {"00": 512, "11": 512},
#   "shots": 1024,
#   "backend": "aer_simulator",
#   "metadata": {
#       "outcomes": 2,
#       "most_likely": "00",
#       "job_id": "local-abc123",
#       "timestamp": "2026-03-22T18:00:00+00:00",
#   },
# }
json_str = result.to_json()

# Deserialize from dict / JSON
restored = QiskitResult.from_dict(d)
restored = QiskitResult.from_json(json_str)
```

The `metadata` dict always includes `timestamp` (ISO 8601 UTC) and `job_id`
(when available), enabling full audit trails for RQM Studio job history.

---

## Supported Gates

All gates supported by the rqm-compiler internal circuit model that `rqm-qiskit`
can lower to Qiskit.  Gate semantics are owned by `rqm-compiler`; this package
only maps them to Qiskit primitives.

| Category | Gates |
|----------|-------|
| Single-qubit named | `i`, `x`, `y`, `z`, `h`, `s`, `t` |
| Single-qubit parametric | `rx`, `ry`, `rz`, `phaseshift` |
| Canonical SU(2) | `u1q` (quaternion → `UnitaryGate`) |
| Two-qubit | `cx`, `cy`, `cz`, `swap`, `iswap`, `rxx`, `ryy`, `rzz` |
| Internal compiler block | `su4q` (target-local verified candidate synthesis) |
| Other | `measure`, `barrier` |

### `u1q` Translation

`u1q` is the canonical single-qubit unitary from `rqm-compiler`, parameterized
as a unit quaternion `(w, x, y, z)`.  This package converts it to a 2×2 SU(2)
matrix via `rqm_core.Quaternion.to_su2_matrix()` and passes it to Qiskit's
`UnitaryGate` — no local quaternion math is implemented here.

## Convenience Bridges

Two thin bridge functions map physical state representations to Qiskit circuits.
**All physics is delegated to rqm-core.**

### `spinor_to_circuit(alpha, beta, target=0)`

Converts a spinor `(α, β)` to a `QuantumCircuit` via:
1. Normalize via `rqm_core.spinor.normalize_spinor`
2. Convert to Bloch vector via `rqm_core.bloch.state_to_bloch`
3. Map `(θ, φ)` → `RY(θ) RZ(φ)` Qiskit gates

### `bloch_to_circuit(theta, phi, target=0)`

Converts Bloch angles `(θ, φ)` to `RY(θ) RZ(φ)` Qiskit gates.

---

## Optimization (Optional)

`rqm-qiskit` exposes the `optimize=True` flag, which delegates to
`rqm_compiler.optimize_circuit`.  If that function is not yet available in
the installed `rqm-compiler` version, an `ImportError` is raised.

For external optimization (e.g. `rqm-optimize`), apply it **before** passing
the circuit to `rqm-qiskit`:

```python
from rqm_compiler import Circuit
from rqm_qiskit import to_qiskit_circuit
from rqm_optimize import optimize_circuit  # installed separately

c = Circuit(2)
c.h(0)
c.cx(0, 1)

optimized, report = optimize_circuit(c)
qc = to_qiskit_circuit(optimized)
```

> **Important:** Do **not** add `rqm-optimize` as a dependency of `rqm-qiskit`.

---

## Package Structure

```
rqm-qiskit/
├── src/
│   └── rqm_qiskit/
│       ├── __init__.py       – public API exports
│       ├── translator.py     – QiskitTranslator, to_qiskit_circuit
│       ├── backend.py        – QiskitBackend (sync + async)
│       ├── execution.py      – run_qiskit, async_run_qiskit, execute_rqm_program
│       ├── job.py            – QiskitJob (async job handle)
│       ├── result.py         – QiskitResult (with to_dict/from_dict caching)
│       ├── ibm.py            – get_ibmq_provider, resolve_backend, IBM execution
│       ├── errors.py         – RQMQiskitError hierarchy
│       ├── convert.py        – compiled_circuit_to_qiskit (core lowering)
│       ├── bridges.py        – spinor_to_circuit, bloch_to_circuit
│       └── ...               – legacy/transitional helpers
└── tests/
    ├── test_translation.py
    ├── test_execution.py
    ├── test_async_execution.py
    ├── test_execute_rqm_program.py
    ├── test_ibm_config.py
    ├── test_error_handling.py
    ├── test_result_caching.py
    ├── test_optimize_toggle.py
    ├── test_u1q.py
    └── test_api_shape.py
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
