# M2DGR Phase 3E — Reference Temporal Association Evidence

## Status

Phase 3E is complete as a conservative characterization checkpoint.

Reference-to-estimator temporal association remains **unverified**. No fixed
reference offset, association tolerance, interpolation policy, evaluation
interval, or automatic exclusion rule is authorized.

Permanent evidence:

- `manifests/m2dgr_reference_temporal_association_evidence_v1.json`
- content SHA256: `505c1b63fc7e74907ce915472b243230a2cc86017248edaca255b5be5bc079fd`

The Phase-3D trajectory manifest remains authoritative and is unchanged.

## Timestamp-coordinate inventory

All 36 released reference files occupy a broadly comparable numeric epoch with
the estimator sensor-header coordinates, and all 36 have numeric interval
overlap with HandsFree IMU and LiDAR headers.

That overlap is structural characterization only. It is not synchronization
proof and the numeric intersection is not an evaluation interval.

RTK/INS and mocap references contain the complete HandsFree/LiDAR header spans
for all 16 and 9 trajectories respectively. Leica contains those complete
sensor spans on 9/11 trajectories. `lift_01` and `lift_02` are partial, while
`lift_03` begins about 1339.6 s before the HandsFree run.

## Rotation-supported references

A frame-invariant native-interval observable compared reference quaternion-step
angular-speed magnitude against HandsFree gyroscope magnitude without using an
extrinsic rotation, interpolation, timestamp tolerance, motion threshold, or
lag search.

RTK/INS, 16 trajectories:

- correlation min/median/max:
  `0.700585994 / 0.970229178 / 0.990359633`

Mocap, 9 trajectories:

- correlation min/median/max:
  `0.091928138 / 0.174282151 / 0.611117285`

The RTK/INS cohort shows strong nominal-coordinate rotational content
consistency. Mocap is weak and heterogeneous as a family. Neither result
establishes physical synchronization. A mocap lag scan is not justified from
these data.

## Translation diagnostics

A frozen Phase-3D LiDAR ICP frontend was reused without tuning. Translation
norms are descriptive only: undeskewed whole-scan effective time and the
unverified reference-to-LiDAR lever arm remain material confounds.

Reference-step / LiDAR-midpoint correlations:

- `gate_01`: `0.178972065`
- `hall_01`: `0.707523123`
- `room_01`: `0.866145937`

When temporal support was instead defined by each native LiDAR interval:

- `gate_01`: `0.369118202`
- `hall_01`: not computable for any of 299 pairs without interpolation
- `room_01`: `0.038627360`

The result is therefore not robust to a scientifically reasonable change in
temporal support. Translation content does not justify lag fitting or a timing
tolerance.

## RTK/INS and GNSS receiver UTC

Phase 3B independently established that `/ublox/fix` headers exactly reproduce
GNSS receiver UTC on all GNSS-bearing trajectories.

For all 16 RTK/INS reference trajectories:

- numeric reference/GNSS coordinate range overlap: `16/16`
- complete `/ublox/fix` range contained by the reference range: `16/16`
- every receiver-UTC fix timestamp exactly present as an RTK/INS reference
  timestamp: `0/16`
- exact match fraction min/median/max: `0 / 0 / 0`

This supports broad numeric epoch compatibility, but does not establish the
physical measurement-time event represented by each RTK/INS pose. Different
native sampling alone can account for the absence of exact sample identity.
It does not prove estimator/reference synchronization.

## Scientific conclusion

The released M2DGR reference timestamp coordinates are numerically compatible
with estimator sensor-header epochs, but the evidence does not identify a
single scientifically defensible reference-to-estimator timing policy.

RTK/INS has strong nominal-time rotational content agreement, but exact
receiver-UTC pose timestamp semantics remain unresolved. Mocap rotational
content agreement is weak and heterogeneous. Leica cannot support the
LiDAR-native translation construction without interpolation. Translation
results are not stable across temporal-support definitions.

Therefore:

- reference interpolation remains unauthorized;
- nearest-neighbor pose association remains unauthorized;
- no fixed reference offset is estimated or applied;
- no association tolerance is frozen;
- no evaluation interval is created;
- no lag scan is justified from the Phase-3E evidence;
- synchronization remains unverified;
- `evaluation_ready` remains false.

## Manifest handling

No Phase-3E successor trajectory manifest is created.

The current manifest schema has no explicit reference-to-estimator temporal
association field. Updating sensor synchronization methods would conflate
sensor-to-sensor synchronization with reference timing, while adding an ad-hoc
reference field would violate the schema.

The authoritative trajectory manifest therefore remains:

`manifests/m2dgr_trajectory_manifest_v1_phase3d_lidar_imu_sync_evidence.json`
