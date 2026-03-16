"""
utils.py – Internal utility helpers for rqm_qiskit.

This module is intentionally minimal.  All shared quantum math (spinor
normalization, Bloch conversions, SU(2) matrices, quaternion algebra) lives
in ``rqm_core`` — the canonical source of truth for the RQM ecosystem.

Bridge-layer utilities are added here only if they are Qiskit-specific and
do not duplicate anything already in rqm-core.
"""
