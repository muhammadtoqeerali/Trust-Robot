# TRUST-ROBOT Phase-14 Supervisory / Physical-Integration Contract V1

Status: guarded supervisory / physical-integration software architecture
implemented locally. Robot action semantics, fallback/safety operating points,
physical platform evidence, physical execution, and closed-loop claims remain
deferred.

## Authoritative supervisory architecture

The learned health model is not the robot controller.

Safety response is a separate rule-based supervisory layer.

The authoritative candidate supervisor inputs are:

- calibrated modality-health probabilities;
- estimator covariance/status;
- tracking availability;
- residual consistency;
- solver validity;
- frozen validation-selected thresholds.

These input identities do not establish runtime availability.

## Planned policy comparisons

The project names:

- nominal continuation;
- always-stop;
- health-triggered policy;
- oracle-health policy.

These are comparison identities, not robot command definitions and not a
selected operational policy.

Oracle health is a planned comparison construct, not an available runtime
signal.

## Robot-action boundary

No controller API, command type, transport/topic, nominal continuation
command, stop command, speed-reduction command, hold-position command,
emergency action, fallback action mapping, supervisor state machine, or
supervisor update rate is selected.

The authoritative project currently defines no safe-stop semantics, emergency
semantics, stopping-distance metric, control-command semantics, or cmd_vel
contract.

## Physical platform

The local quadruped is the eventual primary physical platform.

The provisional local dataset identity is KIOS_QUADRUPED and local readiness
is not_collected.

Actual robot identity, compute hardware, sensor suite, calibration,
synchronization, reference instrumentation, controller semantics, and
proprioceptive signals remain unverified/unfrozen.

## Physical partition

Development/calibration physical trajectories must remain separate from final
held-out physical testing.

Held-out physical data may not select models, learned parameters, calibration
temperatures, fault/attack operating points, health thresholds,
suppression/recovery thresholds, fallback thresholds, or safety operating
points.

## Fallback boundary

Phase 9 did not define an operational fallback policy.

No fallback or safety threshold is selected.

Fallback/safety thresholds must be frozen prospectively before physical
testing, using an admissible validation process rather than final held-out
physical tests or confirmation.

## Historical reuse

Phase-5 live-executor safety is acquisition/filesystem execution safety, not
Phase-14 closed-loop robot supervision.

Historical IMU runtime/embedded safety semantics, OOD thresholds, or robot
action semantics are not adopted.

## RQ4

Phase 13 did not establish onboard resource constraints or answer the resource
component of RQ4.

Phase 14 owns the guarded closed-loop safety component architecturally, but no
guarded physical test has been executed and no closed-loop safety answer or
full RQ4 answer is available.

## Execution

Robot integration execution is unauthorized.

Physical testing is unauthorized.

Closed-loop safety measurement is unauthorized.

Closed-loop safety claims are unauthorized.

Validation remains unopened.

Confirmation remains closed.

No ATE/RPE or final scoring is authorized.

## Artifact hashes

- config: `d5bfc1cd75a2a2dfcc41954856b10163ca9c6f8f66f44b454c88a037269907e3`
- module: `e0a89e0e69bb8c58d7e754569a341010543b7dc6e674129995f2df7c8f7eb9c1`
- tests: `cbcf423ff43140b4b68cab1826b5b359e92b4a61c0561d428749091802fa48c1`
- Phase-13 freeze: `18e8ae494281a3d20567aa7e7404909ccccc832c7426cf0b0ba5ff683f9ffac8`
- Phase-9 freeze: `9c84e85ed6789e01e6eb8d6d25cf40bcdec8b436af879cf54aa3e1b1df80122d`
- frontier report: `34e307d58a03a612c95caece4cb9b5f7ce1670b333e8c66aba3543256e626942`
- frontier JSON: `ee4e7be9b62fe4a2126f1f7758b837ff031928ec00d9867efc8b800109a96627`
- supervisory basis report: `3c139828a42d4607136c77f04d1df60adf0a422544f98e7d51493f9e7c8c89d1`
- supervisory basis JSON: `88d1378dffa70ce512ae7d84b59f3e15e11cef11a270b94ff1a931415bb60899`
