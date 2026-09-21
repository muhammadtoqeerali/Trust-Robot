# M2DGR RTK Reference Geometry and Timing Semantics Evidence V1

## Status

`blocked_pending_physical_evidence`

This additive checkpoint records a narrow author cross-file transform-convention
result together with manufacturer-level MTi-680G lever-arm and timestamp
semantics.

It does **not** verify the RTK/INS reference origin, candidate-transform
applicability, runtime MTi configuration, reference timestamp semantics,
reference-to-estimator synchronization, or any evaluation protocol choice.

Permanent evidence:

`manifests/m2dgr_rtk_reference_geometry_timing_semantics_evidence_v1.json`

Content SHA256:

`84dd60b2b886f01e2377df777b629c360d982bab0737aaa55fa342f59791d201`

File SHA256:

`1cf9bbade44db2d1c35e49ff89984cb7e9a34fdfe99978f9c0213e306135c42b`

## HandsFree author transform-direction cross-check

The frozen M2DGR author calibration source contains:

`Handsfree IMU`

with an extrinsic labeled:

`[to LIDAR]`

and translation:

`[-0.27255, 0.00053, -0.17954]`.

The frozen author `my_params_lidar.yaml` explicitly labels the estimator
extrinsic as:

`lidar -> IMU`

with translation:

`[0.27255, -0.00053, 0.17954]`.

The inverse of that author configuration is exactly equal to the published
HandsFree `[to LIDAR]` matrix.

Maximum absolute matrix residual:

`0.0`

This is exact **author cross-file consistency for the HandsFree IMU block
only**.

It supports interpretation of the transform-direction convention for that
cross-checked block.

It does not:

- independently verify the HandsFree physical extrinsic;
- establish that every calibration block uses an independently cross-checked
  convention;
- establish applicability of the Xsens IMU candidate transform to released
  RTK/INS GT;
- establish applicability of the GNSS candidate transform to released RTK/INS
  GT;
- establish applicability of the Leica candidate transform to released Leica
  GT.

Generalization of this exact cross-file result to Xsens/GNSS/Leica remains
unsupported.

## Xsens/GNSS author candidate geometry

The frozen author calibration source contains the following candidate
translations to LiDAR:

Xsens IMU:

`[0.15905, 0.00067, -0.16824]`

UBLOX,Xsens GNSS:

`[-0.09825, 0.00582, 0.72673]`

Their algebraic difference, expressed as the GNSS candidate origin relative to
the Xsens candidate origin under these author matrices, is:

`[-0.2573, 0.00515, 0.89497]`

Candidate origin separation:

`0.9312363359534465 m`

This is geometry derived only from author-published candidate transforms.

It is **not** promoted to a verified MTi runtime GNSS lever arm.

## MTi-680G manufacturer semantics

The hash-bound manufacturer documentation states that the MTi-680G supports a
GNSS lever-arm configuration.

The documentation defines the lever arm as the GPS antenna position with
respect to the MT device origin of measurement, and states that the algorithm
can use this information to correct position and velocity.

The manufacturer documentation also describes an optional position/velocity
smoother.

Neither the actual M2DGR runtime GNSS lever-arm configuration nor the M2DGR
smoother configuration has been recovered.

Therefore the manufacturer documentation describes device capabilities and
semantics, not the actual M2DGR runtime configuration.

## MTi timestamp semantics

Manufacturer low-level documentation distinguishes timestamp outputs including:

- `XDI_UtcTime`;
- `XDI_SampleTimeFine`;
- `XDI_SampleTimeCoarse`.

`XDI_SampleTimeFine` is expressed in 10 kHz clock ticks.

`SampleTimeCoarse` and `SampleTimeFine` can be combined into a larger
sample-time coordinate.

These are distinct concepts from the explicit UTC-time output.

The available M2DGR evidence does not identify which device timestamp,
host/system timestamp, export conversion, or other time source generated the
released RTK/INS GT timestamp column.

Consequently:

- RTK/INS GT timestamp physical-event semantics remain unverified;
- RTK/INS GT timestamp timebase/export semantics remain unverified;
- numeric Unix-like values are not promoted to synchronization proof.

## Released-dataset limitation

The frozen M2DGR README lists Ublox M8T topics and the HandsFree IMU topic in
the released ROS bags, but does not list a fused Xsens navigation topic.

No runtime Xsens configuration or GT-generation/export path was identified in
the frozen source metadata inspected for this checkpoint.

Therefore the released ROS bags cannot directly recover the Xsens GT output
field selection or runtime MTi configuration from an identified released
Xsens navigation stream.

## Source provenance

Frozen author revision:

`5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5`

Author calibration SHA256:

`e515207fcf53668953a21a2e4d990643007a3a12ad54b91c456a8ee8a8100a90`

Author LIO configuration SHA256:

`95429a4cf76f1b712b2038d8c993530529070fcacd4195c51c750e396bf84bf9`

MTi-600-series manufacturer datasheet snapshot SHA256:

`27f483571786d449592104437790f63bc6ee8f201fb419e6c20503126127b4d3`

Xsens low-level documentation snapshot SHA256:

`f0a00a2e20e53feb2d07544015a006efb47bc14e356a06149f02aad9e481f568`

The manufacturer-document snapshots are not claimed to be dataset runtime
configuration or GT-export provenance.

## Scientific conclusion

Positive evidence:

- HandsFree `[to LIDAR]` author transform-direction convention is exactly
  cross-file consistent with the inverse of the author's explicitly labeled
  `lidar -> IMU` configuration: TRUE.

Explicit limitations:

- this support scope is HandsFree IMU block only;
- independent physical calibration from this cross-file result: FALSE;
- all calibration blocks cross-file direction verified: FALSE;
- exact released RTK/INS physical origin verified: FALSE;
- RTK/INS candidate transform applicability verified: FALSE;
- runtime Xsens GNSS lever arm verified: FALSE;
- runtime Xsens smoother configuration verified: FALSE;
- reference timestamp physical-event semantics verified: FALSE;
- reference timestamp timebase/export semantics verified: FALSE;
- reference-to-estimator temporal association verified: FALSE;
- reference interpolation authorized: FALSE;
- nearest-neighbor association authorized: FALSE;
- association tolerance selected: FALSE;
- evaluation interval created: FALSE;
- alignment mode selected: FALSE;
- estimator scoring authorized: FALSE;
- dataset calibration verified: FALSE;
- synchronization verified: FALSE;
- evaluation ready: FALSE.

No ATE/RPE scoring is authorized.

## Frozen-evidence handling

This checkpoint is additive.

The following remain byte-identical for their original scopes:

- `configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json`
- `manifests/m2dgr_reference_physical_semantics_evidence_v1.json`
- `manifests/m2dgr_reference_temporal_association_evidence_v1.json`
- `manifests/m2dgr_calibration_evidence_v1.json`
- `manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`
- `manifests/m2dgr_split_freeze_evidence_v1.json`
