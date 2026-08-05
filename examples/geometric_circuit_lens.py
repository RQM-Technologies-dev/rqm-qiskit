"""Five-minute, offline demonstration of the rqm-qiskit geometric lens."""

from __future__ import annotations

import math

from qiskit import QuantumCircuit

from rqm_qiskit import analyze_qiskit_circuit, canonical_su2_fingerprint


single = QuantumCircuit(1, 1, name="measured_rotation")
single.rz(0.37, 0)
single.ry(-0.81, 0)
single.rz(1.13, 0)
single.measure(0, 0)

print("Canonical SU(2) fingerprint:", canonical_su2_fingerprint(single))
print(analyze_qiskit_circuit(single).to_text(detail="standard"))

bell = QuantumCircuit(2, name="bell")
bell.ry(math.pi / 2, 0)
bell.cx(0, 1)
print(analyze_qiskit_circuit(bell).to_text(detail="standard"))
