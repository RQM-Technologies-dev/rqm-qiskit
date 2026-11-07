# Released science stack compatibility

The next bridge candidate requires the published exact-phase fixes:

| Package | Qualified baseline | Source tag commit |
| --- | --- | --- |
| rqm-core | 0.3.1 | `8c3e62d5318eb869bd22afe11092faf3eb48147b` |
| rqm-compiler | 0.3.8 | `0feb4af3a9e6f6ff19f5e59b568ce923a7971644` |
| rqm-entanglement | 0.2.3 | Public PyPI wheel |
| Qiskit | 2.5.1 | Public PyPI wheel |

The published rqm-qiskit 0.4.1 wheel requires core below 0.3. It cannot be
installed with compiler 0.3.8, which requires core at least 0.3.1. This change
fixes the next bridge candidate; it does not modify any published wheel.
Downstream applications must keep their production locks unchanged until the
updated bridge is released and qualified. Do not use `--no-deps`, edit installed
metadata, or point production at an unversioned branch to bypass the conflict.

Candidate CI builds against the immutable core/compiler release commits and
uses `scripts/release_stack.py` for exact qualification versions. The bridge
version follows pyproject.toml so the normal release process can assign its next
version without stale wheel filenames. Existing compiler upper-bound support
is retained, but this qualification proves 0.3.8, not an unpublished 0.4 release.

The separately named historical public-PyPI workflow continues to qualify the
published 0.4.1/core 0.2.2/compiler 0.3.7/entanglement 0.2.2 bundle. It pins all
four packages explicitly and does not claim to validate the next candidate.
After a new bridge publication, update that profile and its workflow together.

Compiler 0.3.8 keeps named U(2) gates when rewriting them as bare quaternions
would lose scalar phase. A verified no-op rewrite is expected for H–iSWAP–H.
Regression coverage compares exact Qiskit operators, including signed 2π
rotations, JSON roundtrips, named gates, and controlled reuse. Phase-aligned
comparison alone is insufficient for a composable compiler/bridge contract.
