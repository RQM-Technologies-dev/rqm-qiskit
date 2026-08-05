# Qiskit-Compatible Quaternionic Explanation Bridge

`rqm-qiskit` 0.4 helps people understand ordinary quantum computing through
quaternionic geometry while remaining compatible with Qiskit. It analyzes the
same operators and statevectors that Qiskit exposes through its public APIs;
it does not introduce alternative mechanics or additional quantum information.

## Five-minute path

After publication, install the CLI extra:

```bash
pip install "rqm-qiskit[cli]"
```

Explain an OpenQASM 3 circuit offline:

```bash
rqm-qiskit explain INPUT.qasm \
  --detail standard \
  --output EXPLANATION.md \
  --report REPORT.json
```

Omit `--output` to write the explanation to stdout. `--report` is optional;
when present it receives the complete JSON evidence. Exit `0` means complete,
`2` means a safe partial explanation, and `1` means invalid input or a
processing failure.

The same workflow is available in Python:

```python
from qiskit import QuantumCircuit
from rqm_qiskit import analyze_qiskit_circuit

circuit = QuantumCircuit(1)
circuit.rz(0.37, 0)
circuit.ry(-0.81, 0)
circuit.rz(1.13, 0)

report = analyze_qiskit_circuit(circuit)
print(report.to_text(detail="standard"))
evidence = report.to_dict()
```

`summary` leads with intuition, `standard` adds numerical facts, and
`technical` adds matrices and fingerprints. All three are deterministic and
every section carries `evidence_paths` into the JSON report.

## What a complete one-qubit explanation answers

- What is the quaternion `q = w + xi + yj + zk`?
- What rotation axis and angle does it represent, in radians, degrees, and a
  recognizable multiple of π?
- Where does an ordinary |0⟩ input end on the Bloch sphere?
- Which operator global phase was factored from U(2) to obtain SU(2)?
- Why do `q` and `−q` give the same isolated Bloch and measurement behavior?
- Why must a coherently controlled context preserve the original U(2) phase?
- What are the ideal computational-basis probabilities?

## Supported boundary

| Input | Explanation result | Optimization result |
| --- | --- | --- |
| Bound one-qubit public-Qiskit unitary | Complete quaternion, phase, axis-angle, Bloch, and measurement explanation | Changed only if the narrower compiler path verifies it |
| Bound two-qubit public-Qiskit unitary | Complete verified SU(4)/Weyl, local-equivalence, perfect-entangler, final-state entanglement, and measurement explanation | Changed only if independently verified |
| One- or two-qubit statevector | Complete bounded state and measurement explanation | Not applicable |
| Numeric public `UnitaryGate` | Complete explanation | Safe original fallback when not compiler-supported |
| Terminal measurements | Unitary prefix explained; registers and qubit-to-clbit mapping recorded exactly | Mapping preserved exactly |
| Symbolic parameters, reset, initialization, control flow, or mid-circuit measurement | Useful structural partial report; unavailable geometry is `not_computed` | Exact original fallback |
| Three or more qubits | Structural and verified-region partial report; no dense global simulation | Bounded whole/region verification only |

Analysis never mutates the supplied Qiskit circuit. The explanation path uses
only public Qiskit `Operator`, `Statevector`, circuit, and OpenQASM interfaces.

## Report contract

`RQMGeometricReport.to_dict()` preserves the existing versioned fields and adds
`explanation`:

- `circuit_summary` records shape, operations, phase, and measurement mapping;
- `local_geometry` records U(2) phase, SU(2), quaternion, rotation, Bloch, and
  one-qubit state evidence;
- `nonlocal_geometry` records verified SU(4), Weyl, local-equivalence, and
  entanglement evidence;
- `measurement_predictions` records ideal computational-basis probabilities;
- `optimization` and `assurance` remain optional and independent;
- `not_computed` and `limitations` make the boundary explicit; and
- `explanation.sections[*].evidence_paths` links every prose section back to
  its numerical source fields.

## Evidence boundary

EXP-016 freezes 36 one-qubit, two-qubit, state, and boundary records. Its local
decision run passed exact Qiskit agreement within `1e-9`, five-run text/JSON
determinism, input immutability, explanatory coverage, public-API architecture,
direct p95 `≤50 ms`, and OpenQASM p95 `≤100 ms`.

EXP-014's `100%` versus `6.25%` phase-aware canonical convergence remains a
separate semantic result. EXP-015's `0.7427` ratio remains a failed performance
experiment and is not reclassified. Neither result implies general compiler,
hardware, circuit-quality, or Qiskit superiority.
