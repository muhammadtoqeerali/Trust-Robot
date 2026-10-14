# TRUST-ROBOT — Isaac Sim V16 capture recovery checkpoint

Status: **partial camera recovery; LiDAR remains unqualified**.

## GitHub predecessor

Repository: `muhammadtoqeerali/Trust-Robot`

Branch: `kios-isaacsim-v15-integration`

Predecessor:
`e0d23dae57787df8c9b7727d9db1db3bf27b99f9`

## Historical V15

The preserved October 12 V15 synthetic recording passed
offline validation:

- Six 120 x 160 RGBA images
- Six generic RTX LiDAR point clouds
- Ninety IMU readings
- Ninety USD pose samples

The original scene and source remain unchanged.

This evidence is not independent physical ground truth.

## V16.6 — manual Replicator acquisition

The V15 original scene was used as a control.

Explicit `rep.orchestrator.step()` with four RTX
subframes at each of six observation steps recovered
five camera frames.

Camera recovery steps: 41, 51, 61, 71 and 81.

The first observation, step 31, remained empty.

The direct RGB annotator and Camera wrapper both
returned the same five valid-sized images.

No LiDAR clouds were accepted.

This establishes a partial camera recovery mechanism
under the tested runtime, not six-frame qualification.

## V16.7 — invalid-point dropping workaround

The existing LiDAR prim attribute
`omni:sensor:Core:skipDroppingInvalidPoints`
was set from false to true.

The attribute change succeeded.

All six sampled LiDAR payloads remained empty,
and zero geometrically valid samples were recorded.

The workaround was not effective in this environment.

## V16.8 — event-driven LiDAR writer

A Replicator writer was attached to the same
LiDAR point-cloud annotator.

Five writer callback events were recorded.

All five LiDAR payloads had shape `[0]`.

The callback dictionaries contained timing-related
keys including `reference_time` and `swhFrameNumber`.

Their actual timing values were **not** recorded
in this experiment. Do not infer their validity
from the presence of the keys.

No valid point clouds were produced.

The event-driven writer itself executed, so
a missing callback is not a sufficient explanation.

The experiment does not establish the exact
upstream failure.

## Additional diagnostics

The runtime emitted repeated LiDAR warnings:

`Reference time is 0/0, cannot get simulation time on this frame`

An OptiX cache warning referenced a read-only file
under `/var/tmp/OptixCache_kios/`.

Neither message has yet been proven to cause the
empty LiDAR data in these experiments.

The simulator returning process exit code zero
is not evidence of valid sensor capture.

## Reproducible offline verification

Run:

`PYTHONPATH=src python -B scripts/trust_robot/verify_isaacsim_v16_capture_v1.py WORKSPACE REPO NEW_REPORT_JSON`

The auditor checks frozen hashes for:

- The original V15 scene
- V16.6, V16.7 and V16.8 local candidate scripts
- Their three local diagnostic JSON reports

The report contains compact derived findings and hashes,
not raw sensor recordings.

## Next phase

Investigate the LiDAR simulation-time reference and
the actual SDG `reference_time`/frame-number values.

Examine the LiDAR prim and RTX/OmniGraph timing path
without changing its scan configuration.

Retain the known camera recovery and the original
V15 scene as the control.

Only after generating validated point clouds and
six camera frames should the V16 enriched scene
be requalified.

## Shared KIOS safeguards

Do not modify the shared Isaac Sim installation,
GPU drivers, host namespaces or other users' data.

Every simulator run must use a new project-local
sandbox, read-only shared filesystem, private
network, verified device access, two GPU checks
15 seconds apart and a bounded timeout.

Do not contact physical robots.

Do not equate synthetic sensor readings with
empirical modality-health training labels.

No V16 localization performance or independent
ground-truth trajectory is claimed.
