"""
results.py – Utilities for summarizing quantum measurement counts.

These helpers make it easy to interpret the raw ``{bitstring: count}``
dictionaries returned by Qiskit samplers and simulators.
"""

from __future__ import annotations


def summarize_counts(counts: dict[str, int]) -> dict:
    """Summarize a measurement counts dictionary.

    Parameters
    ----------
    counts:
        A mapping of bitstring → count, e.g. ``{"0": 512, "1": 512}``.

    Returns
    -------
    dict
        A summary dictionary with keys:

        * ``"total_shots"`` – total number of shots.
        * ``"probabilities"`` – ``{bitstring: probability}`` mapping.
        * ``"most_likely"`` – the bitstring with the highest count.
        * ``"counts"`` – the original counts dict (preserved for convenience).

    Raises
    ------
    ValueError
        If ``counts`` is empty.

    Examples
    --------
    >>> summarize_counts({"0": 600, "1": 400})
    {'total_shots': 1000, 'probabilities': {'0': 0.6, '1': 0.4},
     'most_likely': '0', 'counts': {'0': 600, '1': 400}}
    """
    if not counts:
        raise ValueError("counts dictionary is empty.")

    total: int = sum(counts.values())
    probabilities: dict[str, float] = {k: v / total for k, v in counts.items()}
    most_likely: str = max(counts, key=lambda k: counts[k])

    return {
        "total_shots": total,
        "probabilities": probabilities,
        "most_likely": most_likely,
        "counts": counts,
    }


def format_counts_summary(counts: dict[str, int]) -> str:
    """Return a human-readable summary of measurement counts.

    Parameters
    ----------
    counts:
        A mapping of bitstring → count, e.g. ``{"0": 512, "1": 512}``.

    Returns
    -------
    str
        A multi-line formatted summary string.

    Examples
    --------
    >>> print(format_counts_summary({"0": 600, "1": 400}))
    Measurement Results (1000 shots)
    ─────────────────────────────────
      |0>  600 shots  (60.00%)  ████████████████████████
      |1>  400 shots  (40.00%)  ████████████████
    Most likely outcome: |0>  (60.00%)
    """
    summary = summarize_counts(counts)
    total = summary["total_shots"]
    probs = summary["probabilities"]
    most_likely = summary["most_likely"]

    lines = [f"Measurement Results ({total} shots)", "─" * 35]

    # Sort by bitstring for consistent output.
    for bitstring in sorted(counts):
        count = counts[bitstring]
        prob = probs[bitstring]
        bar_len = int(prob * 40)
        bar = "█" * bar_len
        lines.append(
            f"  |{bitstring}>  {count:5d} shots  ({prob * 100:5.2f}%)  {bar}"
        )

    lines.append(
        f"Most likely outcome: |{most_likely}>  ({probs[most_likely] * 100:.2f}%)"
    )
    return "\n".join(lines)
