# TRUST-ROBOT R135-A50-22 — Synthetic OS process supervisor checkpoint

## Status and provenance

A50-20 published baseline `ef2307c2b82c9f11ab7119ed7706c86c55dc7e68`.
A50-21 privately exercised a fixed-case synthetic process supervisor with
12 new tests and 119 selected earlier tests (131 passed on KIOS).
The published candidate is a copy of the verified A50-21 code, with only
its test import adjusted for repository packaging.

## Scope

Only five fixed Python mock cases are permitted: CLEAN_EXIT, NONZERO_EXIT,
SLEEP, IGNORE_TERM and CHILD_REMAINS. The parent uses an OS monotonic clock,
new session/process group, signal escalation and process-table confirmation.
No arbitrary command path or command-line arguments can be supplied by callers.

The tests use short-lived synthetic subprocesses on KIOS. No ROS client,
ROS driver, Jetson contact, robot command, dataset, or real sensor payload.
The code remains a synthetic supervisor, NOT a ROS wrapper or certified
independent safety monitor. It does not safely supervise processes that
escape the original process group, and does not guarantee cleanup after
host failure, caller termination, or uncatchable failure. Process-table
inspection may be unavailable and must be interpreted as unverified.

## Unchanged boundaries

A50-16 schema and ingress adapters remain metadata-only.
A50-20 bounded session uses an injected clock, not a process watchdog.
Neither module provides real factor admission, operational sensor-health
weighting, physical localization, motor control, or safe charging behavior.
The original A23 evidence receipts remain unqualified and all eleven
M2DGR scientific gates remain closed. No independent clock, extrinsics,
fault labels, or physical pose reference is established.

## Next steps

Review source, test and audit hashes. Obtain separate operator approval
before a normal Git commit and non-forced push from KIOS. Any future ROS
integration needs a separate hardware-aware design, independent process
supervision, ROS callback-bound checks, and onsite authorization.
