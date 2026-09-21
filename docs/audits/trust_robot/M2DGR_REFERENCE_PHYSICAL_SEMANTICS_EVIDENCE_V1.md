# M2DGR Reference Physical Semantics Evidence V1

## Status

`blocked_pending_physical_evidence`

This additive checkpoint records public author provenance that narrows the
physical interpretation of the released M2DGR reference trajectories.

It does **not** modify or supersede the frozen Phase-3E reference-temporal
evidence, calibration evidence, split membership, or Evaluation Protocol V2.

Permanent evidence:

`manifests/m2dgr_reference_physical_semantics_evidence_v1.json`

Content SHA256:

`559598c00c8246c1626ae2e01279b59d7baad724a7919df3d4c7a5d5b96ca0a0`

File SHA256:

`afbc2c50b0facd9c51af2768aba1a3436b32c9102182a9cb886479714e4b7e2a`

## Outdoor RTK/INS reference semantics

The M2DGR maintainer states in issue 13 that outdoor GT coordinates are in
ECEF rather than ENU.

The M2DGR maintainer states in issue 107 that, for all outdoor scenes, the GT
frame refers to the Xsens frame.

The maintainer separately states in issue 23 that the outdoor ground truth
comes from the Xsens MTi 680G GNSS-IMU suite.

These statements support the following author-provenance interpretation:

- outdoor GT world-coordinate representation: ECEF;
- outdoor GT frame: Xsens frame;
- outdoor GT source device: Xsens MTi 680G.

They do **not** establish:

- the exact physical Xsens measurement origin represented by each released
  position;
- whether the author-published `UBLOX,Xsens GNSS` or `Xsens IMU` calibration
  entry is the applicable reference-origin-to-LiDAR transform for the released
  pose fields;
- whether any such lever-arm correction was already applied in the released
  GT;
- the required transform direction/convention for evaluation;
- the physical event or timebase represented by each released GT timestamp.

Issue 16 directly asks whether poses are world-to-sensor or sensor-to-world,
but contains no maintainer answer.

The RTK/INS reference-origin and temporal-association requirements therefore
remain unresolved.

## Leica reference semantics

The dataset paper states that a prism reflector was mounted on the robot for
Leica tracking, and the author calibration file contains a `leica` extrinsic
entry labeled `[to LIDAR]`.

However, the available evidence does not explicitly establish:

- that each released Leica position is exactly the prism-center coordinate;
- that the published Leica-to-LiDAR candidate transform applies to the released
  reference position fields;
- whether that transform was already incorporated in the released GT;
- the physical measurement event represented by each released Leica timestamp;
- the released Leica timestamp timebase/export convention.

The Leica reference-origin and temporal-association requirements therefore
remain unresolved.

## Mocap reference semantics

The maintainer confirms in issue 9 that Room and Roomdark ground-truth
trajectories are obtained by mocap.

No published mocap-to-LiDAR transform was identified.

The maintainer also confirms in issue 54 that the mocap system can occasionally
lose tracking and produce abrupt quaternion changes, and recommends filtering.

That recommendation is evidence of a real reference-quality issue but does not
define a prospective filter, threshold, exclusion rule, or repair procedure.

Therefore:

- tracked mocap body/origin semantics remain unresolved;
- mocap-to-LiDAR geometry remains unresolved;
- mocap timestamp semantics remain unresolved;
- no automatic filter or exclusion rule is authorized.

## Author toolkit inspection

The author-linked toolkit was snapshotted at:

- commit:
  `46e75065b45c640e7018443656514c8fbe1bf88b`
- tree:
  `043390ad06e79534a98667d46bcd9ce23c55452c`

The inspected `export_tum.py` SHA256 is:

`19bb1face5803367f747d527bff1af28fccded3af6c7d10876730bd78e97166e`

The script exports camera images using `msg.header.stamp.to_sec()`.

It does not export ground-truth poses and therefore does not establish released
GT timestamp semantics.

This toolkit snapshot is recorded as public author-tool provenance; it is not
asserted to be contemporaneous with the original dataset release unless
separately established.

No GT-generation/export path was identified in the inspected author toolkit or
the frozen M2DGR repository snapshot.

## Release identity check

The `hall_03.txt` file stored in the upstream repository and the downloaded
released reference file are byte-identical.

SHA256:

`679f821e27f253fc8655f4232aaa39eb635705d42c87e9062cc1d5410940abab`

This establishes identity of that public sample with the downloaded release.
It does not establish its physical timestamp or tracked-origin semantics.

## Scientific conclusion

The new public author evidence narrows outdoor reference frame semantics but
does not resolve the physical facts needed for scoring.

Current conclusions remain:

- exact RTK/INS physical reference origin verified: FALSE
- RTK/INS candidate transform applicability verified: FALSE
- Leica physical tracked-point semantics verified: FALSE
- Leica candidate transform applicability verified: FALSE
- mocap tracked-body origin verified: FALSE
- mocap-to-LiDAR transform verified: FALSE
- reference timestamp physical-event semantics verified: FALSE
- reference-to-estimator temporal association verified: FALSE
- reference interpolation authorized: FALSE
- nearest-neighbor pose association authorized: FALSE
- association tolerance selected: FALSE
- evaluation interval created: FALSE
- alignment mode selected: FALSE
- estimator scoring authorized: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

No ATE/RPE scoring is authorized.

## Frozen-evidence handling

The following existing evidence remains byte-identical and authoritative for
its original scope:

- `manifests/m2dgr_reference_temporal_association_evidence_v1.json`
- `manifests/m2dgr_calibration_evidence_v1.json`
- `manifests/m2dgr_split_freeze_evidence_v1.json`
- `manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`
- `configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json`

This checkpoint is additive only.
