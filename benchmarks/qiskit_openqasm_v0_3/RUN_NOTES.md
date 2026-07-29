# Qiskit/OpenQASM v0.3 Run Notes

- `2026-07-29T03:50:41Z`: the first harness invocation stopped during case
  `eligible-000` before writing any result, report, or manifest. The timing
  harness incorrectly called a nonexistent `CompilerReport.to_dict()` method.
  The instrumentation was corrected to use `dataclasses.asdict()` without
  changing the frozen corpus, timing protocol, implementation under test, or
  verdict gates.

This aborted instrumentation attempt is not a completed experimental run. It
is retained here so the evidence history does not hide an unfavorable
operational event.
