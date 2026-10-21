# TRUST-ROBOT R51–R55F evidence checkpoint

This is a provenance-preserving preparation checkpoint for the
authentic M2DGR room_02 TRAIN research track.

Base Git commit:
58e23861811e51c5d00f00f5d22e5cb561c4b43a

Frozen split:
22 TRAIN / 7 validation_calibration / 7 confirmation_test.

## Preserved work

R51: Authentic previously frozen timestamp evidence and record/header
timing diagnostics. These do not establish physical synchronization.

R52: Counterfactual clock-shift sensitivity diagnostics.
No clock offset was selected.

R53: Physical evidence admission boundary, NULL evidence receipts,
and unchanged source-qualification requirements.

R54: Official author GT candidate inventory and unsent source request.
No author contact is claimed.

R55: Controlled HTTPS acquisition attempts received HTTP 302 redirects.
The original attempt did not acquire official GT bytes.

R55F: Manual browser download fallback, adversarial controls and
independent verification. At the time of checkpoint preparation, the
official reference file had not been staged or authenticated.

The later targeted stage-check returned NO_NEW_SOURCE_YET and created
no new result artifact.

## Scientific boundary

The eleven R43 physical qualification gates remain CLOSED.

No verified common clock, physical capture time, complete camera/IMU/
LiDAR extrinsics, mocap reference-frame mapping, independently
qualified continuous reference, or metric real 6DoF reference
association has been established.

No real sensor pose factor admission, trained modality-health
probability, supervised health label, or ATE/RPE scoring is allowed.

Raw recording, downloaded ground truth, credentials, and
confirmation_test observations are excluded from this checkpoint.

## Verification

Run:

python3 -B verify_checkpoint.py

This independently verifies the archived file SHA256 manifest and
the original independent-result report hashes.

It does not replace phase-specific scientific independent replay,
which must be checked separately before publishing the checkpoint.

The manifest records excluded non-whitelisted source names.
Those source files remain preserved in the off-Git KIOS directories.

## Next

Verify full evidence completeness, run phase-specific independent
replays, audit Git inclusion policy and documentation, then perform
a guarded KIOS-only commit/push and check remote HEAD.

For the science track, obtain authentic official room_02 GT bytes
through normal authorized manual access, followed by independent
format/frame/time/reference validation.
