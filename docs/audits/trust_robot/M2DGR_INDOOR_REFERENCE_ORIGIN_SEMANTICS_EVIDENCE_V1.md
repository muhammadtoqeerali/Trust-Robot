# M2DGR Indoor Reference-Origin Semantics Evidence V1

## Status

`blocked_pending_physical_evidence`

Permanent evidence:

`manifests/m2dgr_indoor_reference_origin_semantics_evidence_v1.json`

Content SHA256:

`a2044a4ca875618210843bc42ec0eedad0bc4026ebe258099b30cd6733153cd4`

File SHA256:

`1d08a9c164857c827016545e55d7a495f10557dba7e596d8c2fc071d30cd895d`

This additive checkpoint records author and manufacturer provenance relevant to
the Leica and motion-capture reference origins.

It does not create an indoor reference transform, choose a mocap filter, or
authorize trajectory scoring.

## Leica author provenance

Public maintainer evidence supports two narrow facts.

First, issue 62 describes dataset GT as the pose of the Xsens 680G or the Leica
prism.

Second, issue 10 states that Leica tracks 3D position rather than 6D position
and pose.

Accordingly:

- Leica-family released GT is treated as translation-only;
- the zero quaternion columns in Leica files are not treated as physical
  orientation;
- the Leica prism is author-supported as the reference object.

This does not yet identify the exact physical point represented by each
released Leica XYZ sample.

## Leica manufacturer semantics

The hash-bound Leica reflector document states generic reflector semantics in
which EDM measurements are referenced to the reflector standing axis.

For Leica reflector designs discussed in that document, the standing axis can
coincide with the central-symmetric or virtual prism center, and reflector
constants account for reflector geometry.

These are manufacturer semantics only.

M2DGR has not supplied, in the inspected evidence:

- reflector model;
- prism constant;
- reflector mount;
- standing-axis configuration;
- explicit mapping from released Leica XYZ to a particular physical reflector
  reference point.

Therefore the generic manufacturer description is not promoted to an exact
M2DGR Leica origin.

## Leica extrinsic question

Issue 84 directly asks for the extrinsic between Leica GT and HandsFree IMU.

No maintainer reply was recovered in the frozen issue snapshot.

The absence of an answer is not treated as proof that no such extrinsic exists.

The published Leica-to-LiDAR candidate transform remains author calibration
provenance whose applicability to the released Leica GT position is unverified.

## Mocap author provenance

Issue 9 confirms that Room and Roomdark trajectories use mocap ground truth.

The maintainer describes EVO `-a` alignment as the evaluation procedure and
states that they did not need to specially calibrate LiDAR-Mocap extrinsics for
that evaluation.

That statement is evaluation-procedure provenance.

It is not treated as physical verification of a mocap-to-LiDAR extrinsic.

## Mocap tracking failures

Issue 54 states that the mocap system can sometimes fail to track the robot,
leading to abrupt quaternion changes.

The maintainer recommends filtering for more accurate data.

However, the public reply does not specify:

- filter algorithm;
- threshold;
- window;
- quaternion-distance rule;
- prospective sample-rejection rule.

No filter or exclusion rule is therefore selected by this checkpoint.

## Vicon manufacturer semantics

The hash-bound Vicon Tracker guide documents that:

- tracked objects have local coordinate systems;
- an object's origin can be changed relative to its marker pattern;
- object alignment/orientation can be changed;
- the capture-volume origin/global coordinate system can be configured.

The snapshotted guide identifies itself as Tracker 4.1, dated 15 February 2024.

It is not asserted to be the exact M2DGR runtime software version or
configuration.

Its role is only to establish that these origins and alignments are
configuration-dependent in Vicon's tracking model.

No M2DGR `.vsk`, `.xcp`, rigid-body definition, marker-pattern file, object
origin, or volume-origin configuration was recovered from the inspected local
source metadata.

## Local source search

The local source/configuration search found relevant text only in the already
known upstream calibration and README material.

It did not recover a dedicated:

- Leica reflector configuration;
- Leica prism-constant configuration;
- Vicon object `.vsk`;
- Vicon camera/calibration `.xcp`;
- mocap marker-pattern definition;
- mocap object-origin configuration.

This searched-source absence is not treated as proof that such files never
existed outside the released/public material.

## Scientific conclusion

Positive narrow evidence:

- Leica GT is translation-only according to the maintainer: TRUE;
- Leica prism is named as a GT reference object by the maintainer: TRUE;
- Room/Roomdark GT comes from mocap according to the maintainer: TRUE;
- mocap tracking failures can cause abrupt quaternion changes: TRUE;
- Leica reflector standing-axis semantics are documented generically: TRUE;
- Vicon tracked-object origin/alignment are configuration-dependent: TRUE.

Still unverified:

- exact Leica prism reference point: FALSE;
- exact Leica reflector standing axis used by M2DGR: FALSE;
- M2DGR Leica reflector model: FALSE;
- M2DGR Leica prism constant: FALSE;
- Leica candidate-transform applicability: FALSE;
- mocap tracked-body origin: FALSE;
- mocap marker pattern: FALSE;
- mocap volume origin: FALSE;
- mocap-to-LiDAR transform: FALSE;
- scientifically specified mocap filter rule: FALSE;
- GT timestamp physical-event semantics: FALSE;
- GT timestamp export/timebase semantics: FALSE;
- temporal association: FALSE;
- interpolation authorization: FALSE;
- nearest-neighbor authorization: FALSE;
- association tolerance: FALSE;
- evaluation interval: FALSE;
- alignment selection: FALSE;
- estimator scoring authorization: FALSE;
- dataset calibration verification: FALSE;
- synchronization verification: FALSE;
- evaluation readiness: FALSE.

No ATE/RPE scoring is authorized.

## Frozen-evidence handling

This checkpoint is additive.

Evaluation Protocol V2 and all predecessor reference, timing, calibration,
split, GT-recording, RTK-geometry, and platform-geometry evidence remain
byte-identical.
