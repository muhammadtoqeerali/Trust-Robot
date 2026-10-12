# KIOS V15 synthetic LiDAR registration qualification

Status: **bounded offline pairwise qualification executed**.

## Implemented

The preserved V15 six-frame LiDAR sequence was processed in two
conditions: original clean and frame-3 every-other-point sparsified.

Five consecutive scan pairs per condition were attempted using
the existing, unchanged Phase-2 exact-nearest-neighbor registration
and frozen Phase-4 five-feature diagnostic extractor.

Total pair attempts: **10**.

Pairs producing valid frozen diagnostics:
**10**.

Pairs explicitly unavailable (no fabricated features):
**0**.

Each registration has a bounded execution time and each
condition is recomputed for byte-level determinism.

## Temporal and geometry qualification

Recorded camera/LiDAR simulation read-step time ordering and
USD-pose simulation-step order were checked for monotonicity.

Equal values at a common simulation read step do not establish
physical synchronization, capture timestamps, exposure timing,
LiDAR point firing time or a shared clock.

LiDAR XYZ coordinate-frame provenance is unverified.

USD-composed robot and LiDAR transforms are not independent
ground truth or independently validated sensor extrinsics.

Per-cloud spatial rank is a structural diagnostic only, not
an estimator observability or geometric-accuracy guarantee.

The 16-emitter generic simulated LiDAR does not establish
equivalence to an M2DGR VLP-32C, a physical Hesai device,
or a properly deskewed mobile 3D sensor.

## Scientific limits

Registration nearest-neighbor RMSE is a fitting diagnostic,
not absolute or relative trajectory error.

No ground truth association, ATE/RPE, 6-DoF localization
evaluation, calibrated health model, health label or safety
policy evaluation is claimed.

Empirical SE4 training remains blocked by its existing
supervision and acquisition-source requirements.

No frozen TRUST-ROBOT protocol was edited.

## Provenance

Parent commit: `b9b5d00247d52d2f6aceb7cc2f91e80bebaae1c2`

New module SHA-256: `d477121d3fdc6ca8673b212961f6ed93a744c5c28cd4028375572382230b91c3`

Tests SHA-256: `59b50bcb634d0961bd2650485e544a63fae196467d0215226819b9dc0062b589`

Local run manifest SHA-256:
`907fa1126910673bd2d403f0c2dc7f0f77d1f549c67d0a10df1c8ff81db4d08f`

Local paired-record SHA-256:
`cec3f7931774fdf7a3ab8a32115c8b707ab1b6cb2ff5f9b8bc8b159080eb4c37`

The detailed pair records are retained locally, not uploaded
to the source repository.

## Reproduction

    PYTHONPATH=src python -B src/trust_robot/isaacsim_v15_registration_qualification.py RECORDING_DIR PRIOR_BRIDGE_DIR experiments/isaacsim_v15/compact_evidence_v15.json NEW_OUTPUT_DIR

    PYTHONPATH=src python -B tests/trust_robot/test_isaacsim_v15_registration_qualification.py -v

This work runs offline and does not contact physical sensors,
ROS, networked robots, or Isaac Sim.
