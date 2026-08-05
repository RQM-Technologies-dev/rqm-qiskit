"""Offline command-line interface for the RQM Qiskit circuit lens."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from qiskit import qasm3

from rqm_qiskit.assurance import assure_openqasm3
from rqm_qiskit.geometry import analyze_qiskit_circuit


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assure(args: argparse.Namespace) -> int:
    try:
        source = _read_source(args.input)
        result = assure_openqasm3(source)
        _write_json(args.report, result.to_dict())
        args.output.write_text(result.returned_source, encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"rqm-qiskit: {exc}", file=sys.stderr)
        return 1
    if result.assurance_status == "VERIFIED":
        return 0
    return (
        1
        if result.fallback_reason
        in {"import_error", "export_error", "isolated_worker_error"}
        else 2
    )


def _analyze(args: argparse.Namespace) -> int:
    try:
        source = _read_source(args.input)
        circuit = qasm3.loads(source)
    except (OSError, UnicodeError) as exc:
        print(f"rqm-qiskit: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - parser diagnostics become CLI errors
        print(f"rqm-qiskit: OpenQASM 3 parse failed: {exc}", file=sys.stderr)
        return 1

    report = analyze_qiskit_circuit(circuit, optimize=args.optimize)
    try:
        _write_json(args.report, report.to_dict())
        if args.optimize:
            if args.output is None:
                print(
                    "rqm-qiskit: --output is required with --optimize", file=sys.stderr
                )
                return 1
            assured = assure_openqasm3(source)
            args.output.write_text(assured.returned_source, encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"rqm-qiskit: {exc}", file=sys.stderr)
        return 1

    if report.status == "complete":
        return 0
    if report.status in {"partial", "unsupported"}:
        return 2
    return 1


def _explain(args: argparse.Namespace) -> int:
    try:
        source = _read_source(args.input)
        circuit = qasm3.loads(source)
    except (OSError, UnicodeError) as exc:
        print(f"rqm-qiskit: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - parser diagnostics become CLI errors
        print(f"rqm-qiskit: OpenQASM 3 parse failed: {exc}", file=sys.stderr)
        return 1

    report = analyze_qiskit_circuit(circuit)
    try:
        explanation = report.to_text(detail=args.detail)
        if args.output is None:
            sys.stdout.write(explanation)
        else:
            args.output.write_text(explanation, encoding="utf-8")
        if args.report is not None:
            _write_json(args.report, report.to_dict())
    except (OSError, UnicodeError) as exc:
        print(f"rqm-qiskit: {exc}", file=sys.stderr)
        return 1

    if report.status == "complete":
        return 0
    if report.status in {"partial", "unsupported"}:
        return 2
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rqm-qiskit",
        description="Analyze and assure Qiskit/OpenQASM circuits through the RQM geometric lens.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze", help="Create a geometric circuit report."
    )
    analyze.add_argument("input", type=Path)
    analyze.add_argument("--report", type=Path, required=True)
    analyze.add_argument("--output", type=Path)
    analyze.add_argument("--optimize", action="store_true")
    analyze.set_defaults(handler=_analyze)

    explain = subparsers.add_parser(
        "explain",
        help="Create a readable, evidence-linked quaternionic explanation.",
    )
    explain.add_argument("input", type=Path)
    explain.add_argument(
        "--detail",
        choices=("summary", "standard", "technical"),
        default="standard",
    )
    explain.add_argument("--output", type=Path)
    explain.add_argument("--report", type=Path)
    explain.set_defaults(handler=_explain)

    assure = subparsers.add_parser("assure", help="Run fail-closed circuit assurance.")
    assure.add_argument("input", type=Path)
    assure.add_argument("--report", type=Path, required=True)
    assure.add_argument("--output", type=Path, required=True)
    assure.set_defaults(handler=_assure)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
