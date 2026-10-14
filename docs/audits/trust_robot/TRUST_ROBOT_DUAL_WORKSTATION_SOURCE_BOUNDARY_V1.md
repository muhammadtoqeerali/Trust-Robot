# TRUST-ROBOT dual-workstation source boundary V1

Status: development-validated source-provenance contract.
Not empirical sensor-health qualification.

## Research architecture

Verona is the real-data research workstation.

Its existing M2DGR corpus contains the frozen 22 TRAIN
recordings. The previously frozen SE3 pipeline produced
2,816,957 camera/IMU diagnostic feature records.

Those stored data and feature payloads remain on Verona.
Their historical source and output receipts are immutable
evidence. Finding the files does not constitute fresh
raw-content hashing or physical sensor calibration.

KIOS is the Isaac Sim, simulation-sensor and prospective
physical-robot integration workstation.

The preserved V15 Isaac Sim recording is synthetic.
Its six recorded camera frames must not be reclassified
as physical sensor measurements. Its five unavailable
sparse camera-motion pairs remain unavailable.

Both workstations use the same GitHub repository, but
their working branches and local dataset storage remain
separate until reviewed integration operations.

## Implemented software boundary

The new source-review implementation binds:

- frozen real M2DGR TRAIN ingestion evidence;
- frozen SE3 real camera and IMU diagnostic extraction;
- frozen SE2 health-supervision absence;
- frozen SE4 model-training blockade;
- unresolved physical M2DGR calibration;
- synthetic Isaac Sim V15 source evidence.

Contradictory source identities, input populations,
frozen totals, simulation origins or claimed upstream
authorization are rejected.

This version deliberately reviews the existing checkpoint
only. It does not implement a prospective automatic
promotion mechanism when new evidence becomes available.

## Scientific restrictions

There are no accepted real healthy/degraded/unusable
training labels.

No current physical capture-time or complete cross-modal
calibration evidence is asserted.

Real-data visual factors, health training, probability
calibration, reference scoring, factor conditioning and
robot control remain blocked.

Source review does not open any dataset payload, held-out
partition, confirmation test or reference trajectory.

Synthetic simulation outputs cannot be used as real
independently supervised sensor-health truth.

## Reproducibility

Run the new test suite alongside all previously published
TRUST-ROBOT estimator and geometry regressions.

Verona raw datasets and workstation-local experiment
receipts must not be committed to GitHub.

## Next concrete milestones

1. On Verona, examine admissible independent TRAIN
   baseline, intervention and measurement-relation
   supervision evidence under the frozen SE2 rules.
2. On KIOS, qualify actual sensor interfaces, camera
   intrinsics, capture timing and simulator source roles.
3. Exchange only source-qualified compact provenance
   artifacts as necessary.
4. Advance health training and real sensor fusion only
   when the frozen scientific prerequisites are satisfied.
