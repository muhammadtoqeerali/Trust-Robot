# R52 — Clock provenance and hypothetical timestamp sensitivity (TRAIN room_02)

**All shifted timestamps are manufactured counterfactual coordinates; no offset or tolerance is estimated.** Exactly 48 authentic timestamp receipts from frozen R33/R34 reports; the raw bag and confirmation_test were not opened.

## Predeclared header-shift scenarios

The camera header stamps alone are shifted by −20, −5, −1, 0, +1, +5 and +20 ms. For each shift, we recompute the *nearest of only 16 sampled IMU header stamps* per stream; this sparsity creates arbitrary nearest-neighbor selection, not a physical synchronization measurement.

| Stream | Shift (ms) | Sparse nearest median (ms) | Sparse nearest max (ms) |
|---|---:|---:|---:|
| `/camera/imu` | -20 | 893.752198 | 2675.799112 |
| `/camera/imu` | -5 | 908.752198 | 2690.799112 |
| `/camera/imu` | -1 | 912.752198 | 2694.799112 |
| `/camera/imu` | 0 | 913.530946 | 2695.799112 |
| `/camera/imu` | 1 | 913.530946 | 2696.799112 |
| `/camera/imu` | 5 | 913.530946 | 2700.799112 |
| `/camera/imu` | 20 | 913.530946 | 2715.799112 |
| `/handsfree/imu` | -20 | 881.050825 | 2623.317938 |
| `/handsfree/imu` | -5 | 881.050825 | 2638.317938 |
| `/handsfree/imu` | -1 | 881.050825 | 2642.317938 |
| `/handsfree/imu` | 0 | 881.050825 | 2643.317938 |
| `/handsfree/imu` | 1 | 881.050825 | 2644.317938 |
| `/handsfree/imu` | 5 | 881.028890 | 2648.317938 |
| `/handsfree/imu` | 20 | 881.028890 | 2663.317938 |

## Header-vs-record residual thought experiment

Shifting a given stream header by ±1 ms changes the algebraic `bag_record_stamp − header_stamp`. This is a **coordinate-sensitivity demonstration**, not recorder-latency estimation. The camera IMU has nine negative values at the unshifted baseline.

| Stream | Header shift (ms) | Negative of 16 | Median record−header (ms) |
|---|---:|---:|---:|
| `/camera/color/image_raw/compressed` | -1 | 0 | 81.464823 |
| `/camera/color/image_raw/compressed` | 0 | 0 | 80.464823 |
| `/camera/color/image_raw/compressed` | 1 | 0 | 79.464823 |
| `/camera/imu` | -1 | 8 | -0.073699 |
| `/camera/imu` | 0 | 9 | -1.073698 |
| `/camera/imu` | 1 | 10 | -2.073698 |
| `/handsfree/imu` | -1 | 0 | 2.214427 |
| `/handsfree/imu` | 0 | 0 | 1.214427 |
| `/handsfree/imu` | 1 | 8 | 0.214426 |

## Scientific boundary

No physical event timestamps, hardware clock domain/oscillator relations, cross-stream clock offset/drift, mocap tracked-body origin, or mocap reference association tolerances are verified. R43 source receipts remain unfilled and mocap quality records 90 invalid rotations. Application default `td=0` must not be promoted into a clock result.

No offset, drift, temporal association tolerance, real pose factor, health label or ATE/RPE result is authorized. Confirmation-test trajectories stay sealed.

## Next R53

Specify independently auditable capture-event, clock-domain and mocap export source receipts before future physical synchronization or factor admission.
