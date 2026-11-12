# TRUST-ROBOT | R135-A48-3 | Fixed-point camera information and physical uncertainty readiness

**Scope:** offline manufactured data and existing published KIOS repository documents only. This checkpoint does not authorize real-factor fusion, physical health inference, calibrated covariance, runtime weighting or robot actuation.

## A48-1R — fixed-point local camera information

The tested source computes a finite-difference **6-by-3 camera translation Jacobian** at manufactured 15D states for two conditions (clean, scripted LiDAR dropout), two random seeds (13, 31), two camera edges ((0,1), (2,3)) and three fixed camera residual-scale multipliers (0.5, 1.0, 2.0). The 24 manufactured cases produce 16 ratios comparing the 0.5x and 2.0x trace of **J-transpose-J** to the 1.0x trace. They reproduce 4x and 0.25x respectively. The original residual scales are restored after each bounded calculation. Camera-disabled factors contribute no camera-information block by factor absence.

The tested A48-1R private receipt SHA-256 is `186d899ef5edae896e38641e4046e061a08dac22d60531200a3cf6b5911bc29c` (282 selected tests); its report SHA-256 is `f842358bde08b64069fbe6e82c143699c48ffe4aa4c94924fa777d3fddfaceae`. These ratios follow the chosen numerical residual divisor: **they are not a measured noise covariance, a full 15D posterior, a calibrated reliability score or physical localization accuracy.** No uncertainty-weight selection was executed.

## A48-2RR — non-executable evidence-readiness crosswalk

A private source-correction aligned a document expectation with the published A22 line `- CONFIRMATION_TEST: 7.` without changing any publication or physical admission rule. A48-2RR passed 180 selected tests and independently verified five published documents, including A21, A22, A23, A47 and the Phase-6 calibration contract. Its private receipt SHA-256 is `ae42a839b9c8f9716ea74de8597e6b63f8fe2b2e3d4601927231d714295cda05`; report SHA-256 is `d59c3ee9ff8d7c4c620f55edb4a62ea56fcd9bf9a08eb39abd05b85fe1616300`.

Seven proposed research-readiness categories remain unresolved: capture provenance; capture-applicable timing/geometry; independent six-degree-of-freedom reference and time association; independent healthy/degraded/unusable supervision; empirical measurement noise and cross-source-dependence validation; validation-only uncertainty and health calibration (blocked by Phase-5 empirical inputs); and evaluation-protocol/confirmation-partition review. These seven categories **do not replace** the existing thirteen physical evidence requests or the eleven closed M2DGR admission gates.

The frozen M2DGR partition remains 22 TRAIN / 7 VALIDATION_CALIBRATION / 7 CONFIRMATION_TEST. Confirmation membership is prospectively closed for selection but cannot be described as pristine from all historical inspection. No recorded M2DGR bags, Nova or UNIVER devices, or robot-control systems were accessed in A48.

## Publication controls and scientific decision

A guarded KIOS-only publication copies the two tested A48 recovery sources byte-for-byte and adapts only the two tests' imports to `trust_robot`. The original 15D estimator, Phase-5 health interface, Phase-6 probability-calibration contract, Phase-8 factor-conditioning contract and M2DGR evidence remain unchanged. Seven Git paths are allowlisted. Publication requires **389 selected regression tests** using installed package imports, commit-tree/byte verification, explicit user authorization, a non-forced Git push, independently checked remote HEAD and a private SHA-256 publication receipt.

**No physical evidence has been admitted.** Real health ABSTAIN; fault attribution UNRESOLVED; operational factor weighting/selection DENIED; physical factor admission DENIED; robot actuation DENIED. The receipt or Git commit must never be presented as proof of physical sensor calibration, covariance, independent ground truth or a successful real-world robot trial.
