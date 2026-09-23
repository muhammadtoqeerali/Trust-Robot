# TRUST-ROBOT Phase-5 Camera / IMU Diagnostic Channel Contract V1

Status: implemented locally; not promoted.

## Scientific conclusion from the feature-basis audit

The project architecture requires persistent modality health to consume:

1. appropriate low-level signal summaries;
2. front-end diagnostics;
3. residual-history evidence.

The current repository/project basis does not specify a defensible exact
numeric low-level camera or IMU feature vector.

Accordingly, this contract freezes the evidence-channel architecture without
inventing scalar features.

## Camera

Persistent-health channel interfaces are:

- low-level signal summary;
- visual front-end diagnostic;
- residual history.

The project names visual relative-motion / reprojection information, but the
current TRUST-ROBOT frontier does not yet contain a validated visual front-end
diagnostic implementation.

Phase-3 camera blur and camera exposure degradation remain controlled stressor
families only. They are not diagnostic features and are not health labels.

## IMU

Persistent-health channel interfaces are:

- low-level signal summary;
- IMU front-end diagnostic;
- residual history.

The project names IMU preintegration and gyroscope/accelerometer bias states.
Neither the bias state nor covariance fields are automatically promoted to
health features by this contract.

The Phase-3 bias/drift corruption family remains a controlled stressor only.

## Current innovation

Current standardized innovation belongs to the short-horizon factor-conditioning
pathway and remains explicitly separate from persistent modality health.

This contract does not select a numeric innovation definition and does not feed
innovation into persistent health.

## Frozen boundaries

No exact camera feature names are selected.

No exact IMU feature names are selected.

No visual-front-end, IMU-preintegration, or residual-history diagnostics are
falsely claimed as implemented.

The Phase-4 LiDAR five-feature diagnostic contract is untouched.

No health label, probability, threshold, model, calibration parameter or
classifier training is enabled.

Validation, confirmation-test, reference data, ATE/RPE and final scoring remain
unused.

## Artifact hashes

- config: `de6656d35e24162dcd3ff489f21b735396c2457dae526a13be9790bb88bdf485`
- module: `72dd6e4a945dbd90eb84366248bcb4d3460f934b4c5875a541166aaef3282fbf`
- tests: `161fceb7c3b6498413e7ea247217405b4e181f7da5857f0544023c3ba521b3c8`
- frozen TRAIN source evidence:
  `d4d2a73ddbcf73102cec0d0d4556fa65786a408217fefe1dece0f4d402cce675`
- feature-basis audit report:
  `3acf4739e53f7c832c46fe29f6be1537c4e511618437959545c178c31a03d1bd`
- feature-basis audit JSON:
  `508814c7978e62edfd18c14c8369e700889871f1588b8e668ab983d97a6fb6e9`
- Phase-3 corruption taxonomy:
  `f8a572fc3c25b0effc9f5d0f5fd084a69fc712953f5ae51c0ad3a06a773c02a7`
- Phase-4 diagnostic freeze:
  `09a05d8491c7af7cd8122ee58d9f485d21f03d2cd50f44764d57d48726d08e88`
