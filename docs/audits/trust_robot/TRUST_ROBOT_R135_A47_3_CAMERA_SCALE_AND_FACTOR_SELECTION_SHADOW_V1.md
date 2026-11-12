# TRUST-ROBOT | R135-A47-3 | Synthetic camera-scale sensitivity and factor-availability shadow

**Authority:** offline manufactured data only. Source modules do not admit actual sensor factors, assign physical sensor health, alter operational factor weights, change runtime factor selection, or command a robot.

## A47-1: Scoped mathematical residual-scale perturbations

Reuses the existing experimental separated camera/LiDAR 15D estimator and its original fixed development camera residual scales of 0.03 m and 0.04 rad. Multiplies both by 0.5x, 1.0x and 2.0x only inside scoped software patches, restored even on estimator exceptions. Two synthetic LiDAR conditions and camera-disabled controls give ten solver cases. The numerical results differ from the 1x baseline by the following final-position distances:

| Manufactured condition | 0.5x vs 1x | 2.0x vs 1x |
|---|---:|---:|
| Clean | 0.001687138792 m | 0.000467774050 m |
| LiDAR frame-4 absent | 0.002877252143 m | 0.000870522670 m |

These are *differences between synthetic trajectories*, **not physical localization error, calibrated uncertainty, validated reliability, or superiority of one scale**. The camera-disabled negative control is invariant to changes in camera residual scale. A47-1 passed 251 selected tests; its private receipt SHA-256 is `aa44edfc9b281802c6531dd8dba038ca1d98535fee7ca4be27a1129cf15116cc`.

## A47-2R: Frozen synthetic factor-availability shadow

Reuses the previously published `factor_ownership_availability_bridge_v1` model over all 32 five-node scan-presence masks. In the clean fixture 7 of 7 possible manufactured LiDAR pair factors are available and zero endpoint windows held. Missing manufactured frame 4 leaves 3 of 7 factors; 4 factors lack an endpoint scan, with synthetic shadow holds at windows 2 and 3. Ten A47-1 numerical controls are annotated without any solver reexecution or health-conditioned factor deletion. A47-2R corrected the private test runner's import search path only and passed 270 selected tests; its private receipt SHA-256 is `4b8d25bd62fa76525bfe1cdc2086853cde24f2659b0b41396b05e03721c188b6`.

## Publication and frozen evidence boundaries

Publication copies both tested source modules **without source modifications**; only the two test files receive installed-package import adjustments. The original 15D estimator and Phase-8 factor-conditioning contract stay untouched. A KIOS-only guarded publication requires exact seven-path allowlisting, 270 passing selected regressions using the installed imports, staged byte and mode verification, a non-forced push, independent remote-HEAD agreement and a private SHA-256 publication receipt. Publication should not be declared successful merely because this audit exists.

Real factor admission **DENIED**; physical health **ABSTAIN**; physical fault source **UNRESOLVED**; runtime sensor-health weighting and selection **DENIED**; robot control **DENIED**. No new Nova or UNIVER contact, recorded data opening, M2DGR access or physical timing/extrinsics/6DoF ground-truth validation in this checkpoint. The M2DGR split remains 22 TRAIN / 7 validation_calibration / 7 SEALED confirmation_test with 11 physical science gates CLOSED and 13 evidence requests OPEN.

**Next:** predeclared numerical sensitivity/conditioning stress and physical evidence qualification design; no operational factor tuning or robot actuation without a separate scientifically reviewed authorization.
