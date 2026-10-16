# KIOS L24-L30 Multimodal Evidence Checkpoint

This is a compact hash-pinned engineering evidence archive.

## Validated phases

- L24: freshness and provenance challenge; 11 cases, with sequence-only blind spots.
- L25: common-mode and scripted-USD comparisons; coherent faults can remain unflagged.
- L26: 11 readiness requirements, none independently qualified; four gates denied.
- L27: six-camera/six-LiDAR offline inventory and acquisition contract.
- L28: 272-event offline SHADOW envelope; six negative controls passed.
- L29: separate instrumented candidate, offline adapter and dry-run envelope.
- L30: fresh guarded Isaac Sim acquisition, runtime exit zero.

L30 acquired six camera frames, six 16-return LiDAR scans,
130 IMU rows and 130 scripted USD pose rows.

The fresh metadata envelope contains 272 events. Its SHA256 is
b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444.

## Scope and reproducibility

Archived Python source files are faithful snapshots, not automatically
portable programs. The L29 candidate references KIOS-local paths.
Do not execute it on another workstation unchanged.

The actual L30 terminal launch block was supplied separately in
conversation, not independently verified as an existing local .sh file.
The checkpoint retains the candidate source, runtime verification report,
fresh metadata envelope, and source hashes, but does not claim to
contain a byte-identical executable L30 launch script.

Original raw recordings, Isaac Sim logs, scene binaries and sensor
array payload files remain on KIOS. The scene hash is recorded
without duplicating the scene.

An event payload hash is a recorded provenance assertion, not
independent authentication of physical measurement source.

## Scientific restrictions

There is no qualified independent physical 6DoF ground truth,
measured camera/LiDAR/IMU exposure synchronization, approved factor
uncertainty, validated health probability or sensor-failure rate.

No pose factor or supervised health label is authorized.
The frozen LiDAR frontend is unchanged.

## Verify

Run from repository root:

python3 -B experiments/isaacsim_v16_l24_l30_multimodal_evidence_v1/verify_checkpoint.py

## Next phase

L31: offline audit and falsification of fresh multimodal provenance,
timing fields and replay/source-independence assumptions before any
new GPU capture or estimator admission.
