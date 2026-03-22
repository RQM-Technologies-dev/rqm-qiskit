"""
ibm.py – Execution helpers for local Aer simulation and IBM Quantum.

This module provides:
- ``run_on_aer_sampler``: run a circuit on the local Aer simulator.
- ``get_ibmq_provider``: return an authenticated IBM Quantum provider.
- ``resolve_backend``: resolve a backend name or object to a Qiskit backend.
- ``run_on_ibm_runtime``: submit a circuit to a real IBM Quantum backend.

IBM Quantum credentials
-----------------------
Set the following environment variables before calling ``get_ibmq_provider``
or passing a backend string to ``run_qiskit`` / ``async_run_qiskit``:

    QISKIT_IBM_TOKEN      IBM Quantum API token (required)
    QISKIT_IBM_INSTANCE   Service instance (optional, e.g. ``"ibm-q/open/main"``)
    QISKIT_IBM_CHANNEL    Channel (optional, default ``"ibm_quantum"``)

Alternatively pass ``token=``, ``instance=``, and ``channel=`` keyword
arguments directly to :func:`get_ibmq_provider`.
"""

from __future__ import annotations

import os
from typing import Any

from qiskit import QuantumCircuit


def run_on_aer_sampler(
    circuit: QuantumCircuit,
    shots: int = 1024,
) -> dict[str, int]:
    """Run a circuit on the local Aer simulator and return counts.

    This function uses :class:`qiskit_aer.primitives.Sampler` from the
    ``qiskit-aer`` package.  Install the simulator extras if needed::

        pip install "rqm-qiskit[simulator]"
        # or: pip install qiskit-aer

    Parameters
    ----------
    circuit:
        A fully measured :class:`~qiskit.QuantumCircuit`.
    shots:
        Number of measurement shots (default 1024).

    Returns
    -------
    dict[str, int]
        A mapping of bitstring → count, e.g. ``{"0": 512, "1": 512}``.

    Raises
    ------
    ImportError
        If ``qiskit-aer`` is not installed.

    Examples
    --------
    >>> from qiskit import QuantumCircuit
    >>> from rqm_qiskit.ibm import run_on_aer_sampler
    >>> qc = QuantumCircuit(1, 1)
    >>> qc.h(0)
    >>> qc.measure(0, 0)
    >>> counts = run_on_aer_sampler(qc, shots=1024)
    """
    try:
        from qiskit_aer.primitives import SamplerV2 as AerSampler

        sampler = AerSampler()
        job = sampler.run([circuit], shots=shots)
        result = job.result()
        pub_result = result[0]

        # Merge counts across all classical registers.
        counts: dict[str, int] = {}
        for reg_name in pub_result.data:
            bit_array = getattr(pub_result.data, reg_name)
            for bitstring, count in bit_array.get_counts().items():
                counts[bitstring] = counts.get(bitstring, 0) + count
        return counts

    except ImportError:
        pass  # fall through to legacy Sampler

    try:
        from qiskit_aer.primitives import Sampler as AerSamplerLegacy
    except ImportError as exc:
        raise ImportError(
            "qiskit-aer is required to run local simulations.\n"
            "Install it with:  pip install qiskit-aer\n"
            "Or install the simulator extras:  pip install 'rqm-qiskit[simulator]'"
        ) from exc

    sampler_legacy = AerSamplerLegacy()
    job_legacy = sampler_legacy.run(circuit, shots=shots)
    result_legacy = job_legacy.result()
    quasi_dist = result_legacy.quasi_dists[0]

    num_bits = circuit.num_clbits or 1
    counts_legacy: dict[str, int] = {}
    for state_int, quasi_prob in quasi_dist.items():
        bitstring = format(state_int, f"0{num_bits}b")
        counts_legacy[bitstring] = round(quasi_prob * shots)

    return counts_legacy


# ---------------------------------------------------------------------------
# IBM Quantum provider configuration
# ---------------------------------------------------------------------------


def get_ibmq_provider(
    token: "str | None" = None,
    instance: "str | None" = None,
    channel: "str | None" = None,
) -> Any:
    """Return an authenticated IBM Quantum ``QiskitRuntimeService``.

    Credentials are resolved in the following order:

    1. Keyword arguments (``token``, ``instance``, ``channel``).
    2. Environment variables ``QISKIT_IBM_TOKEN``, ``QISKIT_IBM_INSTANCE``,
       ``QISKIT_IBM_CHANNEL``.
    3. Saved account from ``QiskitRuntimeService.saved_accounts()``.

    Parameters
    ----------
    token:
        IBM Quantum API token.  If ``None``, read from
        ``QISKIT_IBM_TOKEN``.
    instance:
        Service instance string, e.g. ``"ibm-q/open/main"``.
        If ``None``, read from ``QISKIT_IBM_INSTANCE`` or use the
        provider default.
    channel:
        Channel name, e.g. ``"ibm_quantum"`` or ``"ibm_cloud"``.
        If ``None``, read from ``QISKIT_IBM_CHANNEL`` or use
        ``"ibm_quantum"``.

    Returns
    -------
    qiskit_ibm_runtime.QiskitRuntimeService
        An authenticated service object.

    Raises
    ------
    rqm_qiskit.errors.CredentialsError
        If no valid credentials are found.
    ImportError
        If ``qiskit-ibm-runtime`` is not installed.

    Examples
    --------
    >>> import os
    >>> os.environ["QISKIT_IBM_TOKEN"] = "my-api-token"
    >>> provider = get_ibmq_provider()
    >>> backend = provider.backend("ibm_brisbane")
    """
    from rqm_qiskit.errors import CredentialsError

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise ImportError(
            "get_ibmq_provider() requires qiskit-ibm-runtime.\n"
            "Install it with:  pip install qiskit-ibm-runtime"
        ) from exc

    resolved_token = token or os.environ.get("QISKIT_IBM_TOKEN", "")
    resolved_instance = instance or os.environ.get("QISKIT_IBM_INSTANCE") or None
    resolved_channel = channel or os.environ.get("QISKIT_IBM_CHANNEL") or "ibm_quantum"

    if resolved_token:
        try:
            return QiskitRuntimeService(
                channel=resolved_channel,
                token=resolved_token,
                instance=resolved_instance,
            )
        except Exception as exc:
            raise CredentialsError(str(exc)) from exc

    # Try saved account
    try:
        saved = QiskitRuntimeService.saved_accounts()
        if saved:
            try:
                return QiskitRuntimeService()
            except Exception as exc:
                raise CredentialsError(str(exc)) from exc
    except Exception:
        pass

    raise CredentialsError(
        "No IBM Quantum token found.  "
        "Set the QISKIT_IBM_TOKEN environment variable or pass token= explicitly."
    )


def resolve_backend(
    backend: "str | Any | None",
    *,
    token: "str | None" = None,
    instance: "str | None" = None,
    channel: "str | None" = None,
) -> "Any | None":
    """Resolve a backend argument to a Qiskit backend object.

    Accepts:
    - ``None`` → returns ``None`` (signals: use local Aer simulator)
    - A Qiskit backend object → returned unchanged
    - A string backend name, e.g. ``"ibm_brisbane"`` → resolved via
      :func:`get_ibmq_provider`
    - ``"aer_simulator"`` or ``"local"`` → returns ``None`` (Aer)

    Parameters
    ----------
    backend:
        Backend specification (string, object, or ``None``).
    token:
        Passed to :func:`get_ibmq_provider` when resolving a string name.
    instance:
        Passed to :func:`get_ibmq_provider`.
    channel:
        Passed to :func:`get_ibmq_provider`.

    Returns
    -------
    Qiskit backend object or ``None``
        ``None`` signals "use local Aer simulator".

    Raises
    ------
    rqm_qiskit.errors.BackendNotFoundError
        If the string backend name cannot be found.
    """
    from rqm_qiskit.errors import BackendNotFoundError

    if backend is None:
        return None

    if not isinstance(backend, str):
        # Already a backend object – return as-is
        return backend

    # String names that map to local Aer simulator
    if backend.lower() in ("aer_simulator", "local", "aer"):
        return None

    # Resolve IBM backend by name
    try:
        provider = get_ibmq_provider(token=token, instance=instance, channel=channel)
        try:
            return provider.backend(backend)
        except Exception as exc:
            raise BackendNotFoundError(backend, detail=str(exc)) from exc
    except BackendNotFoundError:
        raise
    except Exception as exc:
        raise BackendNotFoundError(
            backend,
            detail=f"Could not obtain IBM provider: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# IBM Runtime execution
# ---------------------------------------------------------------------------


def run_on_ibm_runtime(
    circuit: QuantumCircuit,
    backend: Any,
    shots: int = 1024,
) -> "tuple[dict[str, int], str]":
    """Run a circuit on a real IBM Quantum backend via IBM Runtime.

    Uses ``SamplerV2`` from :mod:`qiskit_ibm_runtime`.

    Parameters
    ----------
    circuit:
        A fully measured :class:`~qiskit.QuantumCircuit`.
    backend:
        An IBM Quantum backend object (e.g. from
        :func:`get_ibmq_provider`).
    shots:
        Number of measurement shots (default 1024).

    Returns
    -------
    (dict[str, int], str)
        ``(counts, job_id)`` where ``counts`` maps bitstrings to counts
        and ``job_id`` is the IBM job identifier string.

    Raises
    ------
    ImportError
        If ``qiskit-ibm-runtime`` is not installed.
    rqm_qiskit.errors.JobFailedError
        If the job fails.
    """
    from rqm_qiskit.errors import JobFailedError

    try:
        from qiskit_ibm_runtime import SamplerV2 as IBMSampler
    except ImportError as exc:
        raise ImportError(
            "run_on_ibm_runtime() requires qiskit-ibm-runtime.\n"
            "Install it with:  pip install qiskit-ibm-runtime"
        ) from exc

    try:
        sampler = IBMSampler(backend)
        job = sampler.run([circuit], shots=shots)
        job_id = job.job_id() if callable(getattr(job, "job_id", None)) else str(id(job))
        ibm_result = job.result()
    except Exception as exc:
        raise JobFailedError(detail=str(exc)) from exc

    counts: dict[str, int] = {}
    try:
        pub_result = ibm_result[0]
        for reg_name in pub_result.data:
            bit_array = getattr(pub_result.data, reg_name)
            for bitstring, count in bit_array.get_counts().items():
                counts[bitstring] = counts.get(bitstring, 0) + count
    except Exception as exc:
        raise JobFailedError(detail=f"Could not parse IBM result: {exc}") from exc

    return counts, job_id
