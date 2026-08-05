# Geometric Circuit Lens

`rqm-qiskit` 0.4 accepts ordinary Qiskit circuits and returns a versioned,
JSON-safe view assembled from existing RQM authorities:

- `rqm-core`: quaternionic wavefunction, quaternion/SU(2), axis-angle, Bloch,
  and ideal Z-basis probabilities;
- `rqm-entanglement`: SU(4)/Weyl classification, nonlocal fingerprints,
  concurrence, and entropy;
- `rqm-compiler`: fail-closed whole-circuit or regional optimization; and
- `rqm-qiskit`: Qiskit/OpenQASM adaptation, register preservation, and report
  shaping.

## Analysis boundary

| Input | Result |
| --- | --- |
| One-qubit circuit/state | Complete quaternion, SU(2), fingerprint, axis-angle, Bloch, and ideal measurement report |
| Two-qubit circuit | Complete SU(4)/Weyl, local-equivalence, entanglement, and ideal computational-basis report |
| Two-qubit state | Complete entanglement and ideal computational-basis report; an input state is not an SU(4) operator |
| Three-qubit circuit | Partial structural report with bounded whole-circuit assurance; no dense global geometry |
| More than three qubits | Partial structural and independently verified-regional report; no dense global state or unitary |
| Terminal measurements | Preserved exactly, including register layout and qubit-to-clbit mapping |
| Mid-circuit measurement, reset, control flow, symbolic/custom operations | Optimization fails closed and the exact original is returned |

`not_computed` is explicit. A partial report never fabricates missing global
state, measurement, or entanglement data.

## Report contract

`RQMGeometricReport.to_dict()` contains:

- `schema_version` and `status`;
- `circuit_summary`;
- `local_geometry` and `nonlocal_geometry`;
- `measurement_predictions`;
- `optimization` and `assurance` evidence;
- `not_computed` and `limitations`; and
- dependency and fingerprint `provenance`.

The quaternionic wavefunction is a regrouping of the same four real
coefficients in a standard two-component complex spinor. The lens adds a useful
coordinate system and reproducibility artifact, not additional quantum
information or a new physical measurement.

## CLI

```bash
rqm-qiskit analyze examples/terminal_measurement.qasm \
  --optimize \
  --report report.json \
  --output optimized.qasm

rqm-qiskit assure examples/terminal_measurement.qasm \
  --report assurance.json \
  --output assured.qasm
```

Exit `0` means complete/verified, `2` means safe partial/fallback, and `1`
means invalid input or processing failure. Both commands are offline and do not
use IBM credentials or quantum hardware.
