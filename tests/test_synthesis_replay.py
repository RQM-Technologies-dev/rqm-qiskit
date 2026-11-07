"""Regression for the offline replay's timeout boundary, not provider execution."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import signal

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGALRM"), reason="SIM-030 replay uses POSIX SIGALRM",
)


def _replay():
    path = (Path(__file__).parents[1] / "benchmarks" /
            "selected_synthesis_dispatch_v0_1" / "replay.py")
    spec = importlib.util.spec_from_file_location("dispatch_replay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_replay_timeout_escapes_factory_exception_handler_and_restores_alarm() -> None:
    replay = _replay()
    previous = signal.getsignal(signal.SIGALRM)
    swallowed = []

    def candidate_factory():
        try:
            signal.raise_signal(signal.SIGALRM)
        except Exception:
            swallowed.append(True)

    with pytest.raises(TimeoutError, match="method exceeded 15s"):
        replay._preserve_deadline(candidate_factory)
    assert swallowed == []
    assert signal.getsignal(signal.SIGALRM) == previous


def test_replay_guard_preserves_success_and_ordinary_errors() -> None:
    replay = _replay()
    previous = signal.getsignal(signal.SIGALRM)
    assert replay._preserve_deadline(lambda: 42) == 42

    def fail():
        raise ValueError("ordinary failure")

    with pytest.raises(ValueError, match="ordinary failure"):
        replay._preserve_deadline(fail)
    assert signal.getsignal(signal.SIGALRM) == previous
