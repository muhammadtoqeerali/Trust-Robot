# KIOS L41-L45 Acquisition-Witness Falsification Checkpoint

All activities were conducted offline on KIOS after the published L36-L40 checkpoint. These are software engineering tests, not new sensor acquisitions or scientific localization results.

- L41: 20 readiness gates assessed and 26 unsupported-readiness assertions rejected; qualification stages A-D remained closed.
- L42: L37 fail-closed runtime hooks and L40 separate-process outbox exercised offline; 25 adversarial controls rejected. No live acquisition-time bridge implemented.
- L43: 50 synthetic session/event mutations rejected; 7 incomplete captures required review.
- L44: 1 complete synthetic event set; 7 review-only partial sets; 36 invalid event mutations and 8 database/receipt faults rejected; SQLite decision/outbox publication recovery exercised.
- L45: 12 coherently regenerated metadata chains passed internal software checks, but ZERO acquired trusted provenance; 20 incoherent mutations and 12 faults rejected, 2 interrupted-publication cases recovered.

The archive contains SHA256-pinned source and compact JSON evidence, one synthetic complete-session receipt, one fabricated-session receipt, and a derived eight-case SQLite summary.

Raw SQLite databases, camera/LiDAR/IMU recordings, fault-copy databases and simulator assets are NOT archived. Original KIOS evidence remains unmodified.

A consistent hash chain or separate local software process does not establish independent recording origin.

No verified physical synchronization, independently qualified 6DoF ground truth, tamper-resistant witness, multi-host replay security, physical power-loss durability, scientific ATE/RPE, health labels, or authorized estimator pose factors.

Live L37 candidate execution remains denied.

Verification:

python3 -B experiments/isaacsim_v16_l41_l45_acquisition_falsification_v1/verify_checkpoint.py

Next: L46 independent-witness trust-boundary design and offline adversarial authority testing before any separately authorized GPU capture.
