# KIOS L41-L45 Acquisition Falsification Audit

Date: 2026-10-16
Parent commit: 8d5a1701df3e9d755ac0a4b5adda2845873f52eb
Branch: kios-isaacsim-v15-integration

L41: 20 readiness gates and 26 denied unsupported claims. Scientific stages A-D closed.

L42: offline L37 hook and L40 transactional-outbox compatibility, 25 adversarial conditions rejected. No live acquisition-time binding.

L43: 50 synthetic session alterations rejected; 7 partial captures marked for review.

L44: 1 complete synthetic and 7 incomplete decisions, 36 event mutations quarantined, 8 database/receipt faults rejected; atomic decision/outbox and recovery exercised.

L45: 12 coherent internally valid but untrusted metadata transcripts, ZERO independently trusted source origins; 20 inconsistent changes denied, 12 receipt/database faults denied, 2 simulated publication recoveries.

The archive preserves 25 SHA-pinned source/report files and three compact synthetic receipt/SQLite summary artifacts.

No raw SQLite databases, sensor recordings or simulation assets are committed.

No trusted physical acquisition, independently verified source authenticity, hardware attestation, verified physical exposure synchronization, independent 6DoF reference, physical power-loss durability, calibrated health labels, or scientific pose-factor admission.

L37 live simulator execution remains unauthorized. M2DGR physical evidence and evaluation gates remain closed.

Next L46: offline independent-witness authority requirements and adversarial trust-boundary testing.
