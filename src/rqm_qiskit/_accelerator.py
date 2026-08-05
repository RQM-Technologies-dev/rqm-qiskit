"""Guarded access to the optional Qiskit 2.5 native adapter.

The extension is an implementation detail. It does not own quantum math,
compiler transformations, verification, or circuit-dependent caches.
"""

from __future__ import annotations

import os
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import Any

_REQUIRE_NATIVE_ENV = "RQM_QISKIT_REQUIRE_NATIVE"
_EXPECTED_NATIVE_API = 1
_native: Any

try:
    _native = import_module("rqm_qiskit._rqm_adapter_native")
except ImportError as exc:  # pragma: no cover - exercised in wheel/fallback tests
    _native = None
    _IMPORT_ERROR: Exception | None = exc
else:
    _IMPORT_ERROR = None


def _qiskit_25_supported() -> bool:
    try:
        release = version("qiskit").split("+", 1)[0].split(".")
        return len(release) >= 2 and (int(release[0]), int(release[1])) == (2, 5)
    except (PackageNotFoundError, TypeError, ValueError):
        return False


def _native_api_supported() -> bool:
    if _native is None or not _qiskit_25_supported():
        return False
    try:
        info = _native.build_info()
    except Exception:  # noqa: BLE001 - capability errors select the safe fallback
        return False
    return bool(
        isinstance(info, dict)
        and info.get("api_version") == _EXPECTED_NATIVE_API
        and callable(getattr(_native, "extract_1q_operations", None))
        and callable(getattr(_native, "build_1q_circuit", None))
    )


_NATIVE_AVAILABLE = _native_api_supported()


def _required() -> bool:
    return os.environ.get(_REQUIRE_NATIVE_ENV) == "1"


def _unavailable_error(action: str) -> RuntimeError:
    detail = f": {_IMPORT_ERROR}" if _IMPORT_ERROR is not None else ""
    return RuntimeError(
        f"Native RQM-Qiskit adapter required for {action}, but its Qiskit 2.5 "
        f"capability is unavailable{detail}"
    )


def extract_1q_operations(circuit: Any) -> list[tuple[str, float | None]] | None:
    """Return canonical one-qubit records, or select the reference fallback."""

    if not _NATIVE_AVAILABLE:
        if _required():
            raise _unavailable_error("import")
        return None
    try:
        records = _native.extract_1q_operations(circuit)
    except Exception as exc:  # noqa: BLE001 - normal mode must fall back safely
        if _required():
            raise RuntimeError("Native one-qubit import failed") from exc
        return None
    if records is None and _required():
        raise RuntimeError("Native one-qubit import declined an evidence-mode circuit")
    return records


def build_1q_circuit(unitary_gate: Any) -> Any | None:
    """Pack one fresh Qiskit circuit, or select the reference fallback."""

    if not _NATIVE_AVAILABLE:
        if _required():
            raise _unavailable_error("lowering")
        return None
    try:
        circuit = _native.build_1q_circuit(unitary_gate)
    except Exception as exc:  # noqa: BLE001 - normal mode must fall back safely
        if _required():
            raise RuntimeError("Native one-qubit lowering failed") from exc
        return None
    if circuit is None and _required():
        raise RuntimeError("Native one-qubit lowering declined an evidence-mode circuit")
    return circuit


def native_build_info() -> dict[str, Any]:
    """Return JSON-safe capability provenance for evidence artifacts."""

    if not _NATIVE_AVAILABLE:
        return {
            "available": False,
            "api_version": None,
            "require_native_environment_variable": _REQUIRE_NATIVE_ENV,
        }
    return {
        "available": True,
        **dict(_native.build_info()),
        "require_native_environment_variable": _REQUIRE_NATIVE_ENV,
    }
