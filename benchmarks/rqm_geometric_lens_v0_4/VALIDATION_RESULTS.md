# RQM-Qiskit 0.4 Candidate Validation

Validation date: August 5, 2026  
Measured implementation: `126bde8311e1613db8888247e88b933253d92973`  
Compiler implementation: `f05ead9b56311947fd123f5e461412a83779a420`

## Source validation

- `rqm-qiskit`: `536` tests passed.
- `rqm-compiler`: `355` tests passed and one existing optional test skipped.
- Changed-scope Ruff passed in both repositories.
- Changed-source mypy passed with third-party imports skipped because Qiskit
  and the current RQM packages do not publish complete type information.
- Both evidence checksum manifests and the strategy validator passed.

## Distribution validation

The `rqm-compiler` `0.3.0` and `rqm-qiskit` `0.4.0` sdist/wheel pairs built
successfully and passed `twine check`. The `rqm-qiskit` wheel contains the
`rqm-qiskit` console entry point and requires Qiskit `>=2.5.1,<2.6`.

Fresh wheel installs and geometric/CLI smoke cases passed in isolated
environments on:

| Python | Qiskit | Result |
| --- | --- | --- |
| `3.11.15` | `2.5.1` | pass |
| `3.12.2` | `2.5.1` | pass |
| `3.13.14` | `2.5.1` | pass |

The Python smoke case verified exact reversed terminal-measurement mapping
`q[0] -> c[1]`, `q[1] -> c[0]`. Installed-wheel `analyze --optimize` and
`assure` commands produced `complete` and `VERIFIED` JSON reports.

## Release status

This validation does not authorize release. The frozen relative adapter
overhead is `98.62%` against the `25%` maximum, so `rqm-qiskit` `0.4.0`
remains an unreleased candidate. No credentials, remote simulator, provider,
or quantum hardware were used.

## EXP-015 native follow-up

- `rqm-qiskit`: `556` tests passed, including native/reference differential,
  fallback, mutation-isolation, register-preservation, `q`/`-q`, injected
  failure, and repeated reference-count cases.
- `rqm-compiler`: `357` tests passed and one existing optional test skipped.
- The native C source compiled with `-Wall -Wextra -Werror` on the local Clang
  toolchain.
- Native-required wheels built, installed, and completed assurance smoke tests
  on CPython `3.11.15`, `3.12.2`, and `3.13.14` with Qiskit `2.5.1`.
- A source install with the C compiler deliberately disabled selected the
  Python fallback and still returned `VERIFIED`.
- CPython 3.11–3.13 wheels and the sdist passed `twine check`.

The native follow-up did not pass the performance gate. Its decision-run ratio
was `0.7427`, and three fresh processes reproduced ratios from `0.7477` to
`0.7523`. Release remains blocked; no roadmap item or public performance claim
is promoted.
