"""
canonical_lowering_path.py – Demonstrate the canonical rqm-compiler → Qiskit workflow.

This example teaches the preferred pattern for the full RQM stack:

  1. Build a backend-neutral circuit using rqm_compiler.Circuit
     (canonical circuit IR, no Qiskit dependency).
  2. Lower it to a Qiskit QuantumCircuit via compiled_circuit_to_qiskit()
     (the single dominant lowering path in rqm-qiskit).
  3. Optionally compile the circuit first with rqm_compiler.compile_circuit
     before lowering.
  4. Execute on the local Aer simulator and inspect the results.

Architecture note
-----------------
compiled_circuit_to_qiskit() is the ONLY lowering path from rqm-compiler IR
to Qiskit.  All other helpers in rqm-qiskit (e.g. RQMCircuit.to_qiskit(),
gate_to_quantum_circuit()) route through it internally.  Building circuits
directly with rqm_compiler.Circuit and lowering via compiled_circuit_to_qiskit()
is therefore the most transparent way to use this stack.

Run with:
    python examples/canonical_lowering_path.py
"""

import math

from rqm_compiler import Circuit, compile_circuit
from rqm_qiskit.convert import compiled_circuit_to_qiskit
from rqm_qiskit import format_counts_summary
from rqm_qiskit.ibm import run_on_aer_sampler


def demo_single_qubit() -> None:
    """Prepare |0>, rotate to |+> with R_y(π/2), then measure."""
    print("Demo 1: Single-qubit |+> preparation via canonical path")
    print("─" * 55)

    # Step 1: build the circuit in the rqm-compiler IR.
    c = Circuit(1)
    c.ry(0, math.pi / 2)   # R_y(π/2) rotates |0> to |+>
    c.measure(0)

    print(f"  rqm-compiler Circuit: {len(c)} operation(s)")

    # Step 2: lower to Qiskit via the single dominant lowering path.
    qc = compiled_circuit_to_qiskit(c)
    print("  Qiskit circuit:")
    print(qc.draw(output="text"))

    # Step 3: run on the local Aer simulator.
    counts = run_on_aer_sampler(qc, shots=2048)
    print(format_counts_summary(counts))
    print("  (Expected: ~50% |0>, ~50% |1>)\n")


def demo_compiled_circuit() -> None:
    """Show that CompiledCircuit also lowers cleanly through the same path."""
    print("Demo 2: Lowering a CompiledCircuit (compiled_circuit_to_qiskit accepts both)")
    print("─" * 55)

    # Step 1: build and compile.
    c = Circuit(1)
    c.rx(0, math.pi / 4)
    c.rz(0, math.pi / 2)
    c.measure(0)

    compiled = compile_circuit(c)
    print(f"  CompiledCircuit: {compiled.num_qubits} qubit(s), {len(compiled.descriptors)} descriptor(s)")

    # Step 2: lower the compiled form — same function, same path.
    qc = compiled_circuit_to_qiskit(compiled)
    print("  Qiskit circuit:")
    print(qc.draw(output="text"))

    counts = run_on_aer_sampler(qc, shots=2048)
    print(format_counts_summary(counts))
    print()


def demo_two_qubit_bell() -> None:
    """Build a Bell state circuit in rqm-compiler, lower, and run."""
    print("Demo 3: Two-qubit Bell state via canonical path")
    print("─" * 55)

    # Step 1: build the Bell-state circuit.
    c = Circuit(2)
    c.h(0)       # Hadamard on qubit 0
    c.cx(0, 1)   # CNOT: control=0, target=1
    c.measure(0)
    c.measure(1)

    print(f"  rqm-compiler Circuit: {len(c)} operation(s)")

    # Step 2: lower via the single dominant lowering path.
    qc = compiled_circuit_to_qiskit(c)
    print("  Qiskit circuit:")
    print(qc.draw(output="text"))

    # Step 3: run.
    counts = run_on_aer_sampler(qc, shots=4096)
    print(format_counts_summary(counts))
    print("  (Expected: ~50% |00>, ~50% |11>)\n")


def main() -> None:
    print("=" * 55)
    print("  Canonical Lowering Path Demo")
    print("  rqm_compiler.Circuit → compiled_circuit_to_qiskit()")
    print("=" * 55)
    print()
    print("This is the preferred pattern for the full RQM stack:")
    print("  build in rqm-compiler  →  lower via rqm-qiskit  →  run on Aer")
    print()

    demo_single_qubit()
    demo_compiled_circuit()
    demo_two_qubit_bell()

    print("=" * 55)
    print("  All demos complete.")
    print("=" * 55)


if __name__ == "__main__":
    main()
