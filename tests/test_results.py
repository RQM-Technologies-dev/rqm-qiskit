"""
Tests for result summary helpers (src/rqm_qiskit/results.py).
"""

import pytest

from rqm_qiskit import summarize_counts, format_counts_summary


# ---------------------------------------------------------------------------
# summarize_counts
# ---------------------------------------------------------------------------


def test_summarize_counts_total_shots():
    counts = {"0": 600, "1": 400}
    summary = summarize_counts(counts)
    assert summary["total_shots"] == 1000


def test_summarize_counts_probabilities():
    counts = {"0": 600, "1": 400}
    summary = summarize_counts(counts)
    assert abs(summary["probabilities"]["0"] - 0.6) < 1e-10
    assert abs(summary["probabilities"]["1"] - 0.4) < 1e-10


def test_summarize_counts_most_likely():
    counts = {"0": 600, "1": 400}
    summary = summarize_counts(counts)
    assert summary["most_likely"] == "0"


def test_summarize_counts_preserves_original():
    counts = {"0": 600, "1": 400}
    summary = summarize_counts(counts)
    assert summary["counts"] is counts


def test_summarize_counts_single_outcome():
    counts = {"0": 1024}
    summary = summarize_counts(counts)
    assert summary["most_likely"] == "0"
    assert abs(summary["probabilities"]["0"] - 1.0) < 1e-10


def test_summarize_counts_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        summarize_counts({})


def test_summarize_counts_equal_split():
    counts = {"0": 512, "1": 512}
    summary = summarize_counts(counts)
    assert summary["total_shots"] == 1024
    assert abs(summary["probabilities"]["0"] - 0.5) < 1e-10


# ---------------------------------------------------------------------------
# format_counts_summary
# ---------------------------------------------------------------------------


def test_format_counts_summary_returns_string():
    result = format_counts_summary({"0": 600, "1": 400})
    assert isinstance(result, str)


def test_format_counts_summary_contains_shots():
    result = format_counts_summary({"0": 600, "1": 400})
    assert "1000" in result


def test_format_counts_summary_contains_most_likely():
    result = format_counts_summary({"0": 600, "1": 400})
    assert "Most likely" in result
    assert "|0>" in result


def test_format_counts_summary_contains_all_bitstrings():
    counts = {"00": 512, "11": 512}
    result = format_counts_summary(counts)
    assert "|00>" in result
    assert "|11>" in result
