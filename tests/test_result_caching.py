"""
Tests for QiskitResult serialization/deserialization (result caching).

Covers:
- QiskitResult.to_dict() includes timestamp in metadata
- QiskitResult.to_dict() includes job_id when provided
- QiskitResult.to_dict(include_timestamp=False) omits timestamp
- QiskitResult.to_json() produces valid JSON
- QiskitResult.from_dict() reconstructs counts and shots
- QiskitResult.from_dict() round-trips with to_dict()
- QiskitResult.from_json() round-trips with to_json()
- QiskitResult.from_dict() with missing counts raises ValueError
- QiskitResult job_id property
- QiskitResult timestamp property is a datetime
"""

import json
import datetime
import pytest


def _make_result(counts=None, shots=None, job_id=None):
    from rqm_qiskit import QiskitResult

    counts = counts or {"00": 512, "11": 512}
    shots = shots or 1024
    return QiskitResult(counts, shots=shots, job_id=job_id)


# ---------------------------------------------------------------------------
# to_dict – timestamp
# ---------------------------------------------------------------------------


def test_to_dict_has_timestamp_by_default():
    """QiskitResult.to_dict() must include 'timestamp' in metadata by default."""
    result = _make_result()
    d = result.to_dict()
    assert "timestamp" in d["metadata"]


def test_to_dict_timestamp_is_iso_string():
    """QiskitResult.to_dict() timestamp must be an ISO 8601 string."""
    result = _make_result()
    d = result.to_dict()
    ts = d["metadata"]["timestamp"]
    assert isinstance(ts, str)
    # Must be parseable
    parsed = datetime.datetime.fromisoformat(ts)
    assert parsed is not None


def test_to_dict_include_timestamp_false_omits_timestamp():
    """QiskitResult.to_dict(include_timestamp=False) must omit timestamp."""
    result = _make_result()
    d = result.to_dict(include_timestamp=False)
    assert "timestamp" not in d["metadata"]


# ---------------------------------------------------------------------------
# to_dict – job_id
# ---------------------------------------------------------------------------


def test_to_dict_includes_job_id_when_set():
    """QiskitResult.to_dict() must include job_id when set on result."""
    result = _make_result(job_id="local-abc123")
    d = result.to_dict()
    assert "job_id" in d["metadata"]
    assert d["metadata"]["job_id"] == "local-abc123"


def test_to_dict_job_id_override_parameter():
    """QiskitResult.to_dict(job_id=...) must override with the given job_id."""
    result = _make_result(job_id="old-id")
    d = result.to_dict(job_id="new-id")
    assert d["metadata"]["job_id"] == "new-id"


def test_to_dict_no_job_id_omits_key():
    """QiskitResult.to_dict() must omit job_id when not set."""
    result = _make_result()  # no job_id
    d = result.to_dict(include_timestamp=False)
    assert "job_id" not in d["metadata"]


# ---------------------------------------------------------------------------
# to_dict – backward compatibility
# ---------------------------------------------------------------------------


def test_to_dict_still_has_required_keys():
    """QiskitResult.to_dict() must still have counts, shots, backend, metadata."""
    result = _make_result()
    d = result.to_dict()
    assert "counts" in d
    assert "shots" in d
    assert "backend" in d
    assert "metadata" in d


def test_to_dict_metadata_has_outcomes():
    """QiskitResult.to_dict() metadata must still have 'outcomes'."""
    result = _make_result()
    d = result.to_dict()
    assert "outcomes" in d["metadata"]


def test_to_dict_metadata_has_most_likely():
    """QiskitResult.to_dict() metadata must still have 'most_likely'."""
    result = _make_result()
    d = result.to_dict()
    assert "most_likely" in d["metadata"]


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------


def test_to_json_returns_string():
    """QiskitResult.to_json() must return a string."""
    result = _make_result()
    assert isinstance(result.to_json(), str)


def test_to_json_is_valid_json():
    """QiskitResult.to_json() must produce valid JSON."""
    result = _make_result()
    d = json.loads(result.to_json())
    assert isinstance(d, dict)


def test_to_json_has_counts():
    """QiskitResult.to_json() must include counts."""
    result = _make_result()
    d = json.loads(result.to_json())
    assert "counts" in d


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------


def test_from_dict_reconstructs_counts():
    """QiskitResult.from_dict() must reconstruct counts correctly."""
    from rqm_qiskit import QiskitResult

    d = {"counts": {"00": 500, "11": 524}, "shots": 1024, "metadata": {}}
    result = QiskitResult.from_dict(d)
    assert result.counts == {"00": 500, "11": 524}


def test_from_dict_reconstructs_shots():
    """QiskitResult.from_dict() must reconstruct shots correctly."""
    from rqm_qiskit import QiskitResult

    d = {"counts": {"0": 200}, "shots": 200, "metadata": {}}
    result = QiskitResult.from_dict(d)
    assert result.shots == 200


def test_from_dict_reconstructs_job_id():
    """QiskitResult.from_dict() must reconstruct job_id from metadata."""
    from rqm_qiskit import QiskitResult

    d = {
        "counts": {"0": 1024},
        "shots": 1024,
        "metadata": {"job_id": "local-xyz99"},
    }
    result = QiskitResult.from_dict(d)
    assert result.job_id == "local-xyz99"


def test_from_dict_missing_counts_raises():
    """QiskitResult.from_dict() must raise ValueError when counts is missing."""
    from rqm_qiskit import QiskitResult

    with pytest.raises(ValueError, match="counts"):
        QiskitResult.from_dict({"shots": 1024})


# ---------------------------------------------------------------------------
# Round-trip: to_dict → from_dict
# ---------------------------------------------------------------------------


def test_round_trip_to_from_dict():
    """QiskitResult round-trip via to_dict/from_dict must preserve counts and shots."""
    from rqm_qiskit import QiskitResult

    original = QiskitResult({"00": 600, "11": 424}, shots=1024, job_id="local-round")
    d = original.to_dict(backend="aer_simulator")
    restored = QiskitResult.from_dict(d)

    assert restored.counts == original.counts
    assert restored.shots == original.shots
    assert restored.job_id == original.job_id


# ---------------------------------------------------------------------------
# Round-trip: to_json → from_json
# ---------------------------------------------------------------------------


def test_round_trip_to_from_json():
    """QiskitResult round-trip via to_json/from_json must preserve counts and shots."""
    from rqm_qiskit import QiskitResult

    original = QiskitResult({"0": 300, "1": 724}, shots=1024, job_id="local-json")
    json_str = original.to_json()
    restored = QiskitResult.from_json(json_str)

    assert restored.counts == original.counts
    assert restored.shots == original.shots


# ---------------------------------------------------------------------------
# QiskitResult properties – job_id and timestamp
# ---------------------------------------------------------------------------


def test_result_job_id_property_none_by_default():
    """QiskitResult.job_id must be None when not provided."""
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"0": 100})
    assert result.job_id is None


def test_result_job_id_property_set():
    """QiskitResult.job_id must return the provided job ID."""
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"0": 100}, job_id="my-job-007")
    assert result.job_id == "my-job-007"


def test_result_timestamp_property_is_datetime():
    """QiskitResult.timestamp must be a datetime.datetime."""
    from rqm_qiskit import QiskitResult

    result = QiskitResult({"0": 100})
    assert isinstance(result.timestamp, datetime.datetime)


def test_result_timestamp_accepts_string():
    """QiskitResult(timestamp='...') must accept an ISO 8601 string."""
    from rqm_qiskit import QiskitResult

    ts_str = "2026-01-15T12:00:00+00:00"
    result = QiskitResult({"0": 100}, timestamp=ts_str)
    assert isinstance(result.timestamp, datetime.datetime)
    assert result.timestamp.year == 2026


def test_result_timestamp_accepts_datetime():
    """QiskitResult(timestamp=datetime) must accept a datetime object."""
    from rqm_qiskit import QiskitResult

    ts = datetime.datetime(2026, 3, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    result = QiskitResult({"0": 100}, timestamp=ts)
    assert result.timestamp == ts


# ---------------------------------------------------------------------------
# from_json
# ---------------------------------------------------------------------------


def test_from_json_importable():
    """QiskitResult.from_json must be a classmethod."""
    from rqm_qiskit import QiskitResult

    assert callable(QiskitResult.from_json)


def test_from_json_reconstructs_result():
    """QiskitResult.from_json must reconstruct a result from JSON."""
    from rqm_qiskit import QiskitResult

    json_str = json.dumps({
        "counts": {"00": 512, "11": 512},
        "shots": 1024,
        "backend": "aer_simulator",
        "metadata": {"most_likely": "00", "outcomes": 2},
    })
    result = QiskitResult.from_json(json_str)
    assert result.counts == {"00": 512, "11": 512}
    assert result.shots == 1024
