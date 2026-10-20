# R27–R31: Recorded single-modality motion candidates

Immutable SHA-pinned engineering evidence based on authenticated M2DGR `room_02.bag` (TRAIN only). The original bag is NOT archived.

Run `python3 -B verify_checkpoint.py` to check the archive independently without requiring the original bag or OpenCV.

R27 computed diagnostic LiDAR registration between two authentic scans, using 512 points per scan. R28 challenged 12 subset and initialization configurations. Maximum observed translation spread was 0.057863 m; rotation spread was 2.291 degrees.

R29 evaluated eight distributed adjacent LiDAR pairs (16 recorded scans). R30 evaluated registration in both directions, observing round-trip discrepancies up to 0.107653 m and 2.527491 degrees.

R31 tracked image features between two consecutive, authenticated 640x480 camera JPEGs: 400 forward/backward-consistent tracks and median displacement 0.023073415420015515 pixels.

All results are engineering diagnostics, not qualified localization factors or pose-accuracy evidence. No physical synchronization, full extrinsics, independent reference scoring, health labels, health training, or authorized real pose factors are established.

The original bag, frozen trajectory split, and historical checkpoints remain unchanged.
