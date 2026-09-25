# TRUST-ROBOT SE1 Deterministic Multimodal Dataset Replay Freeze V1

Status: **SE1 deterministic TRAIN-only replay complete and prepared for checkpoint promotion.**

The frozen claim is intentionally limited:

**The exact 22 frozen M2DGR TRAIN trajectories were replayed deterministically as recorded virtual-sensor transport with trajectory, partition, stream, ordering, timestamp-field, payload, and bag provenance preserved. SE1 performed no health supervision, feature selection, model training, validation selection, confirmation access, synchronization inference, reference association, ATE/RPE, or final scoring.**

## Real TRAIN execution

The completed run processed:

- TRAIN trajectories: 22;
- selected replay messages: 2,907,971;
- serialized replay payload bytes: 103,450,808,700;
- full four-stream trajectories: 20;
- reduced two-stream trajectories: 2.

The reduced-stream trajectories are:

- `street_010`;
- `street_09`.

For those two trajectories the frozen replay evidence preserves only:

- `/handsfree/imu`;
- `/velodyne_points`.

It does not fabricate:

- `/camera/color/image_raw/compressed`;
- `/camera/imu`.

Availability remains evidence of stream presence/absence only. It is not a health label, and missing measurements are not represented by fabricated zero feature vectors.

## Deterministic replay semantics

SE1 preserves:

- trajectory identity;
- TRAIN partition identity;
- modality identity;
- source topic identity;
- selected `AnyReader` emission order;
- per-stream message order;
- raw serialized payload identity;
- ROS bag record time as transport/provenance;
- directly represented header timestamp when structurally present;
- source bag relative path and SHA-256 provenance.

SE1 does not infer that bag record time is physical sensor capture time.

SE1 does not infer that header timestamps prove a common physical clock.

No timestamp sorting, synchronization, fixed-offset fitting, interpolation, calibration repair, reference association, or scoring is performed.

## Empirical run bindings

- candidate contract file SHA-256:
  `866059a3f15a05b21f76acc9fafffa531aa460f55c4e4447a04ff2ad4b2ca53d`
- candidate contract content SHA-256:
  `3766fe64942f0d0c41890a46bb2b3fffeb9a3a7ddb78329be127530f3c259c14`
- run manifest file SHA-256:
  `3fcb3ce8a6698545be7b18774d3cf666bb3a8174e08321ca3a868ecd9f351d0f`
- run manifest content SHA-256:
  `1eeb1704a16631e9a47f4263a659ffcbdd6c8e3e6496f1d1f7924fb6559f7e37`
- SUCCESS file SHA-256:
  `4ec6ec05aa51188d1aa2938815f3da2c4e817b2f046bcd1187010b9c2a6d9d07`
- aggregate trajectory-record SHA-256:
  `28812bc95af309184aaa3530d4fbfa5ebcc83713589f81b143047cf1e544be3d`

The run completed atomically: the final output directory exists, the `.partial` directory is absent, all 22 trajectory artifacts exist, and the SUCCESS marker is present.

## Partition and scientific boundary

SE1 opened TRAIN only.

SE1 did not open VALIDATION_CALIBRATION.

SE1 did not open CONFIRMATION_TEST.

SE1 did not read reference data.

SE1 did not:

- assign health labels;
- infer health probabilities;
- select features;
- extract a new health feature contract;
- train a health model;
- fit probability calibration;
- select thresholds;
- compute ATE/RPE;
- compute final localization scores.

Clean data is not automatically a healthy label.

Synthetic corruption identity is not automatically a health label.

Final localization error may not define health supervision.

## Next stage

SE2 `health_supervision_protocol` is the next software-evidence stage.

SE2 may use TRAIN evidence.

SE2 may not open validation or confirmation.

SE2 may not train the health model, compute ATE/RPE, or compute final scores.

SE9 remains closed.

Confirmation cannot reopen selection after results.

## Implementation artifacts

- replay module:
  `0f73282a65367a22b49b38c5de0012172873f59d4744ac781edda218e3a25d28`
- replay artifact/run module:
  `599bbbf9626279d3841c5459ebca3d31a6c342bf72adfea236ff65e05b889ac5`
- execution runner:
  `2ea62d94f7cc44024b7d5c6c7d8c8e5c045367746ef59a7cbbc26e766a7e776a`
- replay tests:
  `b656d181e09ea0e457b5223584f75ed21711bb6c558214825f854c7bae263584`
- replay artifact tests:
  `086711637f75465ed33e9c34df7bd5f7f41583c1f4b831a53cc9949d18247589`

Pre-freeze full regression:

**1506 / 1506 PASS.**

## Freeze artifacts

- manifest SHA-256:
  `46224af94a07787883b9bd76e0df88cb43f60e834484add04b64933afdbafb02`
- manifest content SHA-256:
  `893809090b03d4bd02e18fbdfe3d91f972330650967cb9ff8a5bd95fddc2c65e`
- freeze-test SHA-256:
  `5c8968e1999583eac802e7e19ed6553f7ce1f1e668936c6c6d12e885fb875499`

The Git commit containing this freeze package will be the authoritative SE1 repository promotion checkpoint.
