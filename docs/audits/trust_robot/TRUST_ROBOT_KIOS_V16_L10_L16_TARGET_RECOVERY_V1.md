# KIOS L10-L16 Target Recovery and Long-Baseline ICP Audit

Date: 2026-10-15
Previous checkpoint: c8d13cc7f6fe5a5faaa4c828cb4c5c2bc68cad9c

## Completed

L10: At step 101, only two raw GMO elements were recorded,
both valid. Analytic geometry predicted 16 ray intersections.
Therefore the VALID filter did not cause the missing returns.

The saved sensor_world_xyz metadata was found to correspond to the
previous USD step, approximately 0.004 m behind the current step.
This metadata is not a verified measurement-exposure pose.

L11: Raw returns declined progressively near the end of the
trajectory. Step 92 also contained zero raw returns.

L12: Observed azimuth convention had a sign inversion.
The two remaining step-101 returns corresponded by elevation to
configured index positions 0 and 15. These are not independently
verified physical emitter identities.

L13: A separate 16-beam candidate moved the front calibration
cube by +0.30 m in X, preserving the scripted trajectory.

L14: The new synthetic capture passed guarded Isaac Sim execution:
6 camera frames, 6 LiDAR frames, 130 IMU records, and 130 USD poses.
All six LiDAR scans contained 16 valid points, totaling 96.
Step 101 improved from 2 to 16 returns.
The step-92 zero-count event remained.

The controlled intervention supports a distance-dependent return
effect, not proof of the underlying RTX rendering mechanism.

L15: All five consecutive registrations were diagnostic-available.
The restored 91-to-101 translation magnitude was 0.041927 m
versus approximately 0.040 m of scripted displacement.
Forward-reverse closures were near numerical zero.
The final pair passed 24 deterministic perturbation trials.

L16: All 15 direct scan-pair registrations completed.
Two- and three-hop closures were small.

Four- and five-hop pairs showed rotational discrepancies
up to approximately 4.219 degrees and translation discrepancies
up to approximately 0.03823 m.

The composed 51-to-101 translation magnitude was approximately
0.200119 m against scripted 0.200 m.

Agreement of translation magnitudes is not independent six-DoF
pose accuracy or scientific ground-truth validation.

## Preservation and scientific restrictions

Exact compact source snapshots, scene and reports are stored in:
experiments/isaacsim_v16_l10_l16_target_recovery_v1/

Raw recordings and runtime logs stay on KIOS.

The existing M2DGR split restrictions, SE4 health-label gate and
estimator-factor qualification restrictions remain unchanged.

No calibrated cross-sensor synchronization, independently qualified
ground truth, physical sensor validation, ATE/RPE, health training
authorization or scientifically admitted pose factors exist.

## Next phase

L17: Investigate why longer-baseline ICP registrations disagree
with compositions of shorter-range registrations.

Test correspondence and initialization ambiguity offline.
Preserve the frozen Phase-2 frontend.

Working method: one implementation phase at a time. User executes
the complete code and provides the output. Review validation before
proceeding. Commit to GitHub only after substantial milestones.
