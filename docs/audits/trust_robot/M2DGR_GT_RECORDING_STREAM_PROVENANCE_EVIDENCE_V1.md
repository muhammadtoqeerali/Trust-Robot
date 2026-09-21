# M2DGR GT Recording and Released-Stream Provenance Evidence V1

## Status

`blocked_pending_physical_evidence`

This additive checkpoint records later public maintainer provenance about the
M2DGR ground-truth source and recording procedure, together with a released
train-bag inventory for the author-mentioned `/data/imu` Xsens stream.

Permanent evidence:

`manifests/m2dgr_gt_recording_stream_provenance_evidence_v1.json`

Content SHA256:

`48d3bac20d621d98e0846fd44545efec9080b0795d55682c9494979bae8b9464`

File SHA256:

`f8cbf76663a027e5487737afb6753eeaed1bc75debbc7c1151d949e809aff814`

This evidence does not authorize ATE/RPE or any estimator scoring.

## Author GT-source provenance

Several later public M2DGR maintainer replies provide useful provenance.

### Issue 62

The question asks whose pose the dataset GT represents and how it relates to
HandsFree IMU or other sensors.

The maintainer states that GT is the pose of the Xsens 680G or the Leica
prism, and additionally states that the Xsens-to-HandsFree IMU rotation can be
treated as identity.

For this checkpoint:

- the Xsens/Leica GT-source statement is author provenance;
- issue 62 alone does not map the two source types to scene families;
- the exact physical Xsens measurement origin remains unverified;
- the exact Leica prism reference point remains unverified;
- the approximate rotation statement is not promoted to independent physical
  calibration.

The previously frozen outdoor-Xsens scene-family mapping remains inherited from
the separate predecessor evidence, not from issue 62 alone.

### Issue 4

The maintainer states that Xsens IMU information was used to generate the GT
pose.

This is consistent with the separate author description of the outdoor
reference as an Xsens MTi-680G GNSS-IMU solution.

It is source provenance, not a released timestamp chain.

### Issues 40 and 77

The maintainer states that no RTK output was obtained through the ROS path and
that Xsens RTK was recorded using software.

In issue 77, the dataset organization further states:

- hardware triggering under ROS was attempted;
- that hardware-trigger attempt was unsuccessful;
- MT Manager was used;
- GT is the algorithmic result of fusing IMU and RTK;
- timestamp differences were calibrated.

The statement that timestamp differences were calibrated is important
provenance, but the public evidence inspected here does not provide:

- the calibration method;
- the numerical offset or mapping;
- a sign convention;
- whether the calibration was global, per recording, or per sequence;
- a reproducible mapping from released GT timestamps to released SLAM/sensor
  timestamps.

Therefore this statement does not support inventing or selecting one fixed
reference offset or an evaluator association tolerance.

### Issue 123

A later maintainer reply states that `/data/imu` is the Xsens IMU result and
that raw RTK data were not recorded.

This statement was tested against the released frozen-train RTK/INS bags.

## Released frozen-train `/data/imu` inventory

The following ten RTK/INS-family trajectories belong to the already frozen
training split:

- `Circle_01`
- `gate_01`
- `street_01`
- `street_03`
- `street_04`
- `street_05`
- `street_07`
- `street_09`
- `street_010`
- `walk_01`

All ten released train bags were opened and their topic inventories were read.

Result:

- train RTK/INS bag count: `10`
- `/data/imu` present count: `0`
- `/data/imu` absent count: `10`

The observed IMU-like topics were limited to combinations of:

- `/camera/imu`
- `/dvs/imu`
- `/handsfree/imu`

No `/data/imu` topic was present in any of these ten frozen-train RTK/INS
bags.

This is a train-split result only.

It is not promoted to a dataset-wide `/data/imu` absence statement because
confirmation trajectories were not inspected and no dataset-wide scan was
authorized for this checkpoint.

## Provenance chronology

The issue snapshots are hash-bound and preserve the public issue metadata.

They are treated as later public author/maintainer provenance.

They are not treated as contemporaneous acquisition logs, MT Manager runtime
configuration exports, hardware-trigger logs, or timestamp-calibration logs.

The issue creation dates include:

- issue 4: 2021-12-30
- issue 40: 2022-08-26
- issue 62: 2023-01-03
- issue 77: 2023-04-19
- issue 123: 2026-04-07

These dates are provenance chronology only. They do not demonstrate that the
replies were contemporaneous with the original data collection.

## Scientific interpretation

Positive author/release provenance:

- outdoor GT described as Xsens 680G pose by author: TRUE;
- Leica GT described as prism pose by author: TRUE;
- Xsens IMU used for GT generation according to author: TRUE;
- GT described as algorithmic IMU+RTK fusion: TRUE;
- MT Manager recording supported by author statement: TRUE;
- author reports timestamp differences were calibrated: TRUE;
- all ten frozen-train RTK/INS bags lack `/data/imu`: TRUE.

Important limitations:

- issue 62 alone maps Xsens/Leica to scene families: FALSE;
- exact Xsens physical measurement origin verified: FALSE;
- exact Leica prism center verified: FALSE;
- timestamp-calibration method verified: FALSE;
- timestamp-calibration value verified: FALSE;
- timestamp-calibration sign convention verified: FALSE;
- timestamp-calibration global/per-sequence scope verified: FALSE;
- author timing claim reproducible from released material: FALSE;
- author timing claim supports one fixed evaluator offset: FALSE;
- author timing claim supports an evaluator tolerance: FALSE;
- released train `/data/imu` stream available: FALSE;
- raw RTK stream available under the author statement: FALSE;
- GT timestamp physical measurement event verified: FALSE;
- GT timestamp timebase/export semantics verified: FALSE;
- reference-to-estimator temporal association verified: FALSE;
- reference interpolation authorized: FALSE;
- nearest-neighbor association authorized: FALSE;
- association tolerance supported: FALSE;
- evaluation interval authorized: FALSE;
- alignment mode selected: FALSE;
- estimator scoring authorized: FALSE;
- dataset calibration verified: FALSE;
- synchronization verified: FALSE;
- evaluation ready: FALSE.

## Confirmation-test handling

No confirmation-test trajectory was inspected for `/data/imu` presence.

No confirmation-test outcome was used for:

- association selection;
- tolerance selection;
- calibration selection;
- timing selection;
- alignment selection;
- protocol selection.

The prospective confirmation boundary remains intact for model/protocol
selection.

## Frozen-evidence handling

This checkpoint is additive.

The following remain byte-identical for their original scopes:

- `configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json`
- `manifests/m2dgr_reference_physical_semantics_evidence_v1.json`
- `manifests/m2dgr_rtk_reference_geometry_timing_semantics_evidence_v1.json`
- `manifests/m2dgr_reference_temporal_association_evidence_v1.json`
- `manifests/m2dgr_calibration_evidence_v1.json`
- `manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`
- `manifests/m2dgr_split_freeze_evidence_v1.json`

## Current blocker

The public evidence now supports that M2DGR maintainers performed some
timestamp-difference calibration between the separately recorded GT path and
the SLAM/sensor path.

However, the method and mapping remain unavailable.

Until a reproducible timing mapping or equivalent physical evidence is
recovered, no evaluator timing offset, association tolerance, interpolation
rule, or synchronization verdict is authorized.
