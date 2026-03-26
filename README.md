# rqm-qiskit

**IBM Quantum / Qiskit execution bridge for the RQM ecosystem.**

Receives compiler-optimized circuit representations and lowers them into Qiskit
`QuantumCircuit` objects for execution on Aer simulators or IBM Quantum hardware.
`rqm-qiskit` is downstream of both `rqm-circuits` (the public circuit IR) and
`rqm-compiler` (the optimization engine).

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
| `rqm-qiskit` | Compiler circuit → Qiskit lowering; Aer/IBM execution; async job handling; result shaping |

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

## Public API

```python
from rqm_qiskit import (
    QiskitBackend,          # OO entry point
    QiskitTranslator,       # translation class
    to_qiskit_circuit,      # functional translation API
    run_qiskit,             # functional execution API
    async_run_qiskit,       # async functional execution API
    execute_rqm_program,    # high-level rqm-api integration
    get_ibmq_provider,      # IBM Quantum provider
    QiskitJob,              # async job handle
    QiskitResult,           # structured result wrapper
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

#### High-level rqm-api integration (`execute_rqm_program`)

Accepts a compiler-compatible program descriptor dict.  In the full RQM stack,
API and Studio traffic originates as `rqm-circuits` payloads; those are parsed
and validated upstream before reaching this layer as descriptor dicts.  If you
are integrating directly with `rqm-api`, the API layer handles the
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
| Two-qubit | `cx`, `cy`, `cz`, `swap`, `iswap` |
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

MIT — see [LICENSE](LICENSE).

