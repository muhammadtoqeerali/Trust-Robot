# KIOS L36-L40 Acquisition Witness Audit

Date: 2026-10-16
Parent commit: 0b542e8644f3c4b98ed92c0f83a7c82a4635ae52
Branch: kios-isaacsim-v15-integration

L36: offline preflight and sealing rules, 46 negative controls rejected. No authorized GPU launch.
L37: isolated nonexecuted candidate with two fail-closed hooks, original L29 acquisition source logic preserved except root and hooks, 12 mutations rejected.
L38: local SQLite nonce challenge/admission/seal lineage with replay denied across process restarts, 20 negative controls rejected.
L39: 20 simulated interrupted/corrupted registry scenarios, 1 verified sealed, 2 review required, 17 quarantined.
L40: SQLite transactional receipt outbox, 2 missing publication windows recovered from committed bytes, 7 corruption cases denied.

The checkpoint archives 23 pinned source/report files, five derived compact snapshot/receipt artifacts, README, verifier and documentation. Full SQLite databases and raw sensor evidence remain local and unmodified.

Research/security boundaries: no independent source authenticity, hardware attestation, verified physical exposure synchronization, independent 6DoF ground truth, real power-loss durability, multi-host replay proof, scientific ATE/RPE, sensor health labels or authorized localization pose factors.

L37 live execution explicitly denied. The historical L24/L31 verifiers must be run against their original Git commit's mutable documentation; new L36-L40 verifier implements commit-scoped documentation validation for future updates.

Next: L41 acquisition-time witness integration gap assessment, before another guarded GPU experiment.
