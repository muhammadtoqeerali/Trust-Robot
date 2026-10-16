# KIOS L31-L35 Provenance and Witness Checkpoint

This is a compact, hash-pinned engineering research archive.

## Completed research

L31 verified 272 fresh metadata events and 14 L30 source files,
rejected 16 adverse mutations and compared historical fingerprints.

L32 independently verified 28 original/new source files.
Camera payloads matched 0/6; LiDAR 6/6, IMU 130/130 and
scripted USD pose 130/130. The files had distinct inodes.
These matches do not prove replay or independent acquisition.

L33 generated the prospective source/timing/calibration/reference
acquisition contract and an evidence-gap assessment.
Twenty mutation challenges were rejected; four scientific
admission gates remained denied.

L34 implemented separate userspace challenge issuer, frozen-data
file witness and independent receipt verifier. Sixteen source
files were rehashed and sixteen receipt challenges rejected.
Its challenge was issued after historical L30 capture.

L35 implemented a software-order rehearsal: a challenge was
issued before generating twelve transcript records derived from
archived L30 camera/LiDAR metadata. A separate witness sealed
the record chain, and a verifier rejected twenty-five mutations.
No new physical or simulated sensor measurements were acquired.

## Trust boundaries

Historical source snapshots may reference KIOS-local directories.
They are archived byte-identically; do not assume portability.
The source programs should not be blindly rerun on another host.

The L34/L35 nonce and receipt artifacts are historical
verification evidence, not credentials, secret signing keys,
trusted hardware attestations or proof of sensor capture origin.

File hashes verify content equality against pinned bytes, not
whether an independent sensor performed a new measurement.
Host monotonic-clock ordering is a software diagnostic only.

## Scientific gates

No qualified physical exposure synchronization, independent
source authenticity, verified extrinsics, independently measured
six-DoF reference, calibrated sensor-health labels, scientific
ATE/RPE accuracy or authorized localization pose factors.

No raw NPY/NPZ camera/LiDAR arrays, scene copies or Isaac Sim
runtime logs are committed in this checkpoint.

## Verification

From repository root:

python3 -B experiments/isaacsim_v16_l31_l35_provenance_witness_v1/verify_checkpoint.py

## Next step

L36: design and offline-falsify an acquisition-time integration
boundary, including immutable challenge delivery, capture-session
identity, source-writer separation, independent witnessing and
explicit failure behavior, before another guarded GPU acquisition.
