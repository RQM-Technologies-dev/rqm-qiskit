"""Process-isolated OpenQASM import/export worker used by server adapters."""

from __future__ import annotations

import json
import sys
from typing import Any

from rqm_compiler import Circuit

from rqm_qiskit.assurance import assure_openqasm3, export_openqasm3, import_openqasm3


def _execute(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    if action == "import":
        result = import_openqasm3(str(request.get("source", "")))
        circuit = (
            {
                "num_qubits": result.circuit.num_qubits,
                "descriptors": result.circuit.to_descriptors(),
            }
            if result.circuit is not None
            else None
        )
        return {"report": result.report.to_dict(), "circuit": circuit}
    if action == "export":
        circuit_payload = request["circuit"]
        circuit = Circuit.from_descriptors(
            circuit_payload["descriptors"],
            num_qubits=int(circuit_payload["num_qubits"]),
        )
        return export_openqasm3(circuit).to_dict()
    if action == "assure":
        return assure_openqasm3(str(request.get("source", ""))).to_dict()
    raise ValueError(f"Unsupported worker action: {action!r}")


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        response = _execute(request)
        sys.stdout.write(
            json.dumps(
                response,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - process boundary must serialize all failures
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
