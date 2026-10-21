# TRUST-ROBOT R76–R78 physical evidence intake and runtime denial checkpoint

This is software-only development and audit evidence, NOT physical qualification.
All source files are SHA-pinned and independently reviewed. The archived modules
run with the existing `src/trust_robot` recorded M2DGR admission/factor gates.
The original R43 (11 unfilled gates), R53 (5 unfilled timing receipts),
R70–R74 scientific results, and R75 GitHub checkpoint remain unchanged.
The room_02 GT was recovered in R64–R69; old R43 raw-source receipt status
is historical, not a claim the recovered GT is missing today.

R76 provides strict source-candidate formatting, 12 negative controls, and an
UNSENT author request. R77 binds format-only candidates to both existing
fail-closed recorded-factor entry points (8 tests + 19 + 11 regressions).
R78 refuses execution even for 11 apparently complete author-like candidate
submissions (9 further tests). A format-valid input is NOT verified physics.

Standalone verification from the project checkout:
`python3 experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1`

Recorded-factor regression execution (no raw inputs):
`A=experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1; PYTHONPATH="$A/evidence/r78/dev:$A/evidence/r77/dev:$A/evidence/r76/dev:src" python3 -B "$A/evidence/r78/dev/test_r78.py" . "$A/evidence/r76/dev" "$A/evidence/r76/result" "$A/evidence/r77/dev" "$A/evidence/r77/result"`

Original Verona source reports remain private off Git; no original GT, raw
ROS bags, confirmation_test material, source receipts from real sensors, or
physical credentials are archived. The author request is only a draft and
has not been sent. Eleven scientific gates remain CLOSED. No calibration,
real pose factors, health training, ATE/RPE or cross-sensor alignment authorized.
