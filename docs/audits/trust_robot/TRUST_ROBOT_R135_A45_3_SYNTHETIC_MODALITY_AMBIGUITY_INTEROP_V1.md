# TRUST-ROBOT | R135-A45-3 | Synthetic cross-modal ambiguity and separated factor interoperability

**Scope:** offline manufactured-input integration; no operational robot controller, physical fusion or real sensor-health classifier.

## Reused implementations

This checkpoint publishes two privately tested A45 modules with unchanged source bytes: `synthetic_cross_modal_ambiguity_v1.py` and `synthetic_separated_modality_interop_v1.py`. Both call established `trust_robot` synthetic interfaces. In particular, `analytic_three_modality_bridge.py` uses the legacy one-relative-pose-slot-per-edge camera-substitution adapter, whereas **the existing** `analytic_separated_modalities.py` already implements separate camera and LiDAR residual blocks on overlapping edges, distinct measurement identities, Schur consumption accounting and fixed manufactured numerical residual scales. No second solver is created or existing frozen estimator altered.

A45-1 privately passed 16 new and 136 selected published tests (152 total), with receipt SHA-256 `8e3330d3b79da1366cf6bcdf1342bb4095b9b397980fee1ac08f0726e1813c72`. A45-2 privately passed 16 new and 148 selected frozen tests (164 total), receipt SHA-256 `b2b2b31f51d9c78987319403157161890a4bf05337523d7c63a2978109c5176d`. Published tests change private imports to installed package imports and add four additional synthetic end-to-end checks; the guarded KIOS publication script requires 184 tests across the combined suites before Git staging.

## Factor-count and attribution findings

| Manufactured control | Legacy relative-pose slots | Separated pose factors | Camera/LiDAR overlapping edges |
|---|---:|---:|---:|
| Clean, camera off | 7 | 7 | 0 |
| Clean, camera on | 7 | 9 | 2 |
| LiDAR frame-4 dropout, camera off | 3 | 3 | 0 |
| LiDAR frame-4 dropout, camera on | 4 | 5 | 1 |

Two fixed synthetic camera seeds (13 and 31) were used in the camera-enabled controls. These are **factor-ownership** counts, not empirical evidence of accuracy, statistical independence or real trajectory reliability. The dropout still triggers the synthetic LiDAR scan-availability shadow hold for windows 2 and 3. The separated solver's camera residual denominators are fixed development values, not fitted physical covariance, and its additional factors cannot support real-world improvement claims.

For the same manufactured pairwise camera/LiDAR discrepancy, two opposite hypothetical faulty-source assignments remain compatible with the observation. The illustrative 0.125 m symmetric counterexample does not estimate calibrated failure likelihood or distinguish actual camera from LiDAR faults. The physical responsible modality remains `UNRESOLVED`, and the Phase-7 source-attribution and factor-conditioning gates stay closed.

## Safety and evidence limits

No Nova/UNIVER communication, new rosbag capture, recorded sensor measurement, M2DGR train/validation/sealed data opening, independent capture-time or extrinsic qualification, physical 6DoF reference, accepted real health labels, health-conditioned factor admission or robot actuation. Existing robot evidence remains preserved separately. The M2DGR 22 TRAIN / 7 validation_calibration / 7 SEALED confirmation_test split is frozen, eleven physical evidence gates remain CLOSED, and 13 prospective evidence requests remain open. Private source experiments, private receipts and hardware payloads stay off GitHub.

**Next research:** offline cross-modal joint fault non-identifiability, sensitivity to synthetic residual scales, factor-information ownership and independent validation prerequisites. Physical factor admission and control require separate explicit scientific and safety approval.
