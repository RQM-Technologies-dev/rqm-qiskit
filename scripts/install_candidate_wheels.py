#!/usr/bin/env python3
"""Validate and install the exact pure-Python 0.4 candidate wheelhouse."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile


EXPECTED_WHEELS = {
    "rqm-core": ("0.2.2", "rqm_core-0.2.2-py3-none-any.whl"),
    "rqm-compiler": ("0.3.0", "rqm_compiler-0.3.0-py3-none-any.whl"),
    "rqm-qiskit": ("0.4.0", "rqm_qiskit-0.4.0-py3-none-any.whl"),
}
NATIVE_SUFFIXES = (".so", ".pyd", ".dylib", ".dll")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wheel_metadata(path: Path) -> tuple[str, str]:
    with ZipFile(path) as archive:
        names = archive.namelist()
        native = [name for name in names if name.lower().endswith(NATIVE_SUFFIXES)]
        if native:
            raise RuntimeError(f"{path.name} contains native files: {native}")
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        wheel_names = [name for name in names if name.endswith(".dist-info/WHEEL")]
        if len(metadata_names) != 1 or len(wheel_names) != 1:
            raise RuntimeError(f"{path.name} has invalid distribution metadata")
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        wheel_metadata = archive.read(wheel_names[0]).decode("utf-8")
    if "Root-Is-Purelib: true" not in wheel_metadata:
        raise RuntimeError(f"{path.name} is not marked as a pure-Python wheel")
    if "Tag: py3-none-any" not in wheel_metadata:
        raise RuntimeError(f"{path.name} does not contain the py3-none-any tag")
    return str(metadata["Name"]), str(metadata["Version"])


def discover_wheels(wheelhouse: Path) -> dict[str, Path]:
    wheelhouse = wheelhouse.resolve()
    found = sorted(wheelhouse.glob("*.whl"))
    expected_filenames = {value[1] for value in EXPECTED_WHEELS.values()}
    if {path.name for path in found} != expected_filenames:
        raise RuntimeError(
            "candidate wheelhouse must contain exactly "
            f"{sorted(expected_filenames)}; found {[path.name for path in found]}"
        )
    wheels: dict[str, Path] = {}
    for project, (version, filename) in EXPECTED_WHEELS.items():
        path = wheelhouse / filename
        metadata_name, metadata_version = _wheel_metadata(path)
        if metadata_name.lower() != project or metadata_version != version:
            raise RuntimeError(
                f"{filename} metadata is {metadata_name} {metadata_version}, "
                f"expected {project} {version}"
            )
        wheels[project] = path
    return wheels


def _manifest_payload(
    wheels: dict[str, Path], *, qiskit: str, core: str, compiler: str
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "source_commits": {
            "rqm-qiskit": qiskit,
            "rqm-core": core,
            "rqm-compiler": compiler,
        },
        "wheels": [
            {
                "project": project,
                "version": EXPECTED_WHEELS[project][0],
                "filename": path.name,
                "sha256": _sha256(path),
            }
            for project, path in sorted(wheels.items())
        ],
    }


def write_manifest(
    wheelhouse: Path,
    wheels: dict[str, Path],
    *,
    qiskit: str,
    core: str,
    compiler: str,
) -> None:
    payload = _manifest_payload(
        wheels, qiskit=qiskit, core=core, compiler=compiler
    )
    (wheelhouse / "candidate-wheelhouse.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksum_lines = [
        f"{item['sha256']}  {item['filename']}" for item in payload["wheels"]
    ]
    (wheelhouse / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )


def verify_manifest(wheelhouse: Path, wheels: dict[str, Path]) -> dict[str, object]:
    manifest_path = wheelhouse / "candidate-wheelhouse.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = payload.get("wheels")
    if not isinstance(records, list) or len(records) != len(wheels):
        raise RuntimeError("candidate-wheelhouse.json does not describe three wheels")
    by_project = {str(record.get("project")): record for record in records}
    if set(by_project) != set(wheels):
        raise RuntimeError("candidate-wheelhouse.json project set is invalid")
    for project, path in wheels.items():
        record = by_project[project]
        if record.get("filename") != path.name or record.get("sha256") != _sha256(path):
            raise RuntimeError(f"checksum or filename mismatch for {project}")
    return payload


def install(wheelhouse: Path, wheels: dict[str, Path], *, extra: str) -> None:
    verify_manifest(wheelhouse, wheels)
    requirements = [
        f"rqm-core @ {wheels['rqm-core'].resolve().as_uri()}",
        f"rqm-compiler @ {wheels['rqm-compiler'].resolve().as_uri()}",
        f"rqm-qiskit[{extra}] @ {wheels['rqm-qiskit'].resolve().as_uri()}",
        "qiskit==2.5.1",
        "qiskit-qasm3-import==0.6.0",
        "rqm-entanglement==0.2.1",
    ]
    subprocess.run(
        [sys.executable, "-m", "pip", "install", *requirements], check=True
    )
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheelhouse", type=Path)
    parser.add_argument("--extra", choices=("cli", "dev"))
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--qiskit-commit")
    parser.add_argument("--core-commit")
    parser.add_argument("--compiler-commit")
    return parser


def main() -> int:
    args = _parser().parse_args()
    wheelhouse = args.wheelhouse.resolve()
    wheels = discover_wheels(wheelhouse)
    if args.write_manifest:
        commits = (args.qiskit_commit, args.core_commit, args.compiler_commit)
        if not all(commits):
            raise RuntimeError("all three source commits are required for the manifest")
        write_manifest(
            wheelhouse,
            wheels,
            qiskit=args.qiskit_commit,
            core=args.core_commit,
            compiler=args.compiler_commit,
        )
    elif args.extra:
        install(wheelhouse, wheels, extra=args.extra)
    else:
        verify_manifest(wheelhouse, wheels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
