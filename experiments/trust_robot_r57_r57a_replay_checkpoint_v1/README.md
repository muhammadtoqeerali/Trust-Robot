# TRUST-ROBOT R57/R57A independent replay and launcher-repair provenance

R56 archived 39 byte-identified R51–R55F code/results artifacts. In R57,
39 archived/source byte comparisons and the standalone verifier passed, and
2 disposable tamper controls were correctly rejected. R57 then stopped when
the **test runner**, not the R51 science code, omitted an expected sys.argv
argument. The original R57 source, launcher, and failing R51 log are retained.

R57A used a separately copied launcher with only argument forwarding patched.
All six archived synthetic/negative test programs exited successfully in
isolated temporary execution copies. Their logs, source SHA receipts, and the
R57A result JSON are preserved. These are engineering replays, **not** newly
validated physical timing, GT association, health calibration or real 6-DoF.

Original R57 and R57A outputs remain unmodified off Git on KIOS. The
`checkpoint_manifest_v1.json` binds all archived copies and three project
documentation files. `verify_checkpoint.py` independently checks byte hashes,
R56 linkage, all six test-log receipts, failure/repair identity, and closed
scientific gates. It checks documents from the specific checkpoint Git commit
once committed, so later documentation edits cannot invalidate its history.

Official room_02 GT remains NOT_ACQUIRED, all 11 R43 scientific admission
gates remain CLOSED. Frozen 22/7/7 split, raw bag and confirmation_test are
untouched. No raw dataset, GT payload or authentication material is archived.

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
