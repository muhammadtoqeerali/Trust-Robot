# Reliability operating-point freeze

## Integrity calibration protocol V1

The integrity detector calibration search space and selection rules are
frozen before reading calibration detector outcomes.

The machine-readable protocol is:

`configs/integrity/integrity_calibration_protocol_v1.json`

The controlling calibration population is the already frozen P0
calibration specification receipt:

`data/manifests/p0_calibration_spec_receipt_v1.json`

## Evidence boundary

The calibration protocol does not relax the frozen integrity evidence
taxonomy.

### FRAME_GAP

KFall raw `FrameCounter` is qualified direct sequence evidence.

A positive counter discontinuity greater than one may therefore enter
the external hard-cause set as `FRAME_GAP`.

UniVRFall does not have an independently qualified raw frame counter for
this purpose. Its later derived/oriented counter cannot create a hard
`FRAME_GAP` cause.

No detector threshold is tuned for FRAME_GAP.

### CHANNEL_FREEZE_SUSPECT

Channel freeze remains suspect-only.

It never enters the hard cause set and does not independently force the
three-state wrapper into `INTEGRITY_ALERT`.

Calibration searches only exact digital equality with persistence
values:

`2, 3, 4, 5, 8, 10, 15, 20` consecutive deltas.

The same selected persistence value is used for KFall and UniVRFall.

### ACQ_TIMING_VIOLATION

Timing-envelope selection in historical P0 V1 is diagnostic and
observation-only.

Dataset-specific timing envelopes may be selected during calibration,
but the selected envelope does not itself qualify a hard
`ACQ_TIMING_VIOLATION`.

In particular, historical P0 timing evaluation must not set timestamp
provenance qualification in a way that promotes the observation to
`HARD_QUALIFIED`.

Hard timing attribution requires a later documented provenance revision
or stronger P1-P3 acquisition-boundary evidence in addition to a frozen
operating envelope.

### FRAME_REPEAT and BUFFER_STALL

No hard historical P0 cause is enabled.

Sensor-value repetition alone is not independent evidence of a repeated
acquisition frame or stalled data path.

### RANGE_CLIP

No hard historical P0 cause is enabled.

The P0 clipping levels are development-derived synthetic quantile clamps
and are not verified configured physical sensor rails.

## Calibration selection

Clean-stream constraints are feasibility constraints and are evaluated
before corruption-detection performance is optimized.

For `CHANNEL_FREEZE_SUSPECT`, every dataset-specific clean constraint
must hold. Among feasible candidates, selection maximizes
equal-dataset-weighted macro event recall over low, medium, and high P0
freeze episodes. Ties are resolved first by lower confirmation latency
and then by greater persistence.

Timing envelopes are selected separately by dataset. All clean timing
constraints must hold first. Among feasible candidates, selection
maximizes macro event recall over low, medium, and high P0 timing
episodes. Ties prefer the wider envelope.

If no candidate satisfies the predeclared clean constraints, the
constraints are not relaxed after outcome review.

## Leakage boundary

During integrity calibration:

- final-test data are unavailable;
- final-test corruptions must not be generated;
- the frozen P0 corruption policy cannot change;
- frozen calibration specifications cannot change;
- task-model outcomes are not used;
- OOD outcomes are not used.

After calibration, selected detector operating points are written and
frozen before final-test P0 specifications are generated.
