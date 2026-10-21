# TRUST-ROBOT KIOS R51–R55F evidence checkpoint preparation

Base commit:
58e23861811e51c5d00f00f5d22e5cb561c4b43a

Branch:
kios-isaacsim-v15-integration

Archive:
experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/

R51–R55F completed successfully as bounded diagnostic,
source-evidence and manual-access fallback phases.

Official room_02 ground truth was NOT ACQUIRED.

R55's two HTTPS attempts returned HTTP 302.
R55F's independent offline check confirmed that no user-downloaded
file existed at the approved staging path.

The later targeted staging check also reported NO_NEW_SOURCE_YET.

No source bytes have been authenticated against the historical
expected GT digest.

The original 22/7/7 split is unchanged.
All eleven physical-evidence qualification gates remain closed.

No real pose factors, health training, or ATE/RPE scoring are
authorized. No original raw bag or confirmation-test trajectory
was accessed in these phases.

This archive is a prepared checkpoint. A standalone file-hash
verification and six SHA-pinned original independent reports are
included. Full phase-specific replay and the final inclusion audit
remain required before Git publication.

This document does not assert that the archive is already committed
or pushed. Publishing must be performed on KIOS after independent
validation of the complete staged Git diff.

## R57/R57A independent replay, repair and publication boundary

R57 independently matched 39 R56 archived files to their preserved off-Git
sources and the standalone SHA verifier passed. Two disposable adversarial
changes were rejected. Its first R51 synthetic test failed in the launcher
(`IndexError: list index out of range`) because sys.argv[1] was omitted; no
underlying R51 science failure was inferred. The original failed launcher,
replay source and traceback log were preserved. R57A patched argument
forwarding in a COPY of that launcher and separately ran R51, R52, R53, R54,
R55 and R55F synthetic/negative test scripts; all six exited zero. Pinned
replay sources, failure and logs are recorded in the R57/R57A checkpoint.

The R58 package may be published only if KIOS checks exact Git staging,
SHA-pinned R56 and R57/R57A archives, three commit-scoped documents, normal
Git history and exact remote SHA. Before those terminal checks complete,
publication is not established. GT is NOT_ACQUIRED, all eleven R43 gates
CLOSED, raw sensor recording and confirmation_test excluded, and pose-factor,
health and ATE/RPE claims DENIED. Author contact packet remains UNSENT.

## R58 partial builder failure and R58A targeted correction

The original R58 builder aborted with `R58_BUILD_DENIED:ORIGINAL_FAILURE`.
It incorrectly required `R57_PHASE_TEST_FAILED:r51` inside the saved R57
child-process test log, although that message came from the parent R57
orchestrator. The authentic child traceback shows `test_r51.py` and
`sys.argv[1]` raising `IndexError: list index out of range`. R58A checks
that authentic traceback instead and safely reuses each of the twelve
already copied source files only if its full content is unchanged.
The original R58 builder/verifier bytes are preserved off-Git as SHA-bound
R58A repair evidence; the earlier R57 failure and R57A correction remain
unchanged. No old phase or raw sensor data was reprocessed, no scientific
gate opened, and no premature Git commit/push was performed.

Original R58 builder SHA256: `d3fde8be9919c5ecdae5be9297955d532bddd4caf3e4f3dd9b30c4f4ca6f9482`.
Original R58 verifier SHA256: `427c06762d1a29f00e63b1b241a13f82320c97394f3b4a143b0867b6633441c7`.
