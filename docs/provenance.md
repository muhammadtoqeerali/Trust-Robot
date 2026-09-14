# Acquisition and integrity provenance

## Scope

This document freezes the evidence boundary used by the reliability
wrapper.

A runtime external integrity cause may be emitted only when the
corresponding evidence has direct and defensible provenance.

Synthetic corruption ground truth is kept separate from runtime
causal attribution.

## Protected task-model input

The protected DATE2025 reconstruction consumes 400 ms windows at
100 Hz.

Stored windows contain nine channels:

- AccX, AccY, AccZ
- GyrX, GyrY, GyrZ
- EulerX, EulerY, EulerZ

The protected CNN consumes only accelerometer and gyroscope channels
after its historical normalizer.

Integrity checks must operate from acquisition/raw-stream evidence
before destructive filtering/windowing whenever such evidence is
required.

## Processed-window limitation

Historical `segments.npy` artifacts retain sensor values and labels
but do not retain timestamp, frame-counter, FIFO/status, or other
acquisition metadata sidecars.

Therefore processed windows alone are not sufficient evidence for
causes such as frame loss, FIFO overrun, or buffer stall.

## KFall acquisition evidence

Original KFall CSV files contain:

- `TimeStamp(s)`
- `FrameCounter`
- accelerometer
- gyroscope
- Euler channels

Full-dataset audit:

- 5,075 files
- 3,990,025 within-file counter transitions
- every observed counter transition was +1
- every observed timestamp transition was 0.01 s
- no counter gaps observed
- no duplicate counters observed
- no backwards counters observed
- no non-positive timestamp transitions observed

The oriented KFall representation preserves the counter and timestamp
fields while rotating/scaling sensor channels.

### Qualification

For KFall raw streams, `FrameCounter` is accepted as direct sequence
evidence.

A discontinuity `counter_t > counter_(t-1) + 1` may therefore support
`FRAME_GAP`.

This does not identify FIFO overrun or any specific lower-level cause.

## UniVR acquisition evidence

The original UniVR archive contains a raw-like `time[ms]` field and
sensor values in mg and mdps.

The original files do not expose the `FrameCounter` field present in
the later model-compatible `UniVrFall_oriented` CSV representation.

No surviving source lineage was found that establishes how the
original UniVR files were converted into that oriented representation.

### UniVR oriented FrameCounter

The oriented counter increments by one throughout the audited files,
but its acquisition provenance is unverified.

It must therefore not be used as hard acquisition-boundary evidence
in the primary UniVR study.

It may be retained for indexing/alignment only.

### UniVR timestamp behavior

Observed original-file time deltas are dominated by:

- 10 ms
- 0 ms
- 20 ms

Duplicate millisecond timestamps are common.

Therefore:

- a zero timestamp delta is not evidence of buffer stall;
- a 20-ms delta is not automatically a dropped frame;
- timing thresholds must be selected using development data;
- native large discontinuities must not be assigned a physical cause
  without additional evidence.

`ACQ_TIMING_VIOLATION` remains an evidence candidate rather than a
fully qualified primary-dataset cause at this stage.

## Sensor units and range evidence

Original UniVR columns explicitly encode acceleration in mg and
gyroscope in mdps.

Observed acceleration reaches approximately ±3997 mg on every axis.

The historical model normalizer divides acceleration by 4000.

This numerical agreement is not sufficient proof that ±4000 mg is the
configured acquisition rail.

The historical normalizer is task-model preprocessing, not sensor
configuration evidence.

The local source/documentation audit did not recover authoritative
device configuration establishing the active accelerometer or
gyroscope full-scale ranges.

Therefore hard `RANGE_CLIP` attribution is not yet qualified.

## KFall orientation conversion

The preserved orientation conversion:

- converts KFall acceleration from g to mg;
- converts KFall gyroscope from degrees/s to mdps;
- applies an axis reflection/rotation;
- sets Euler channels to zero.

Metadata fields are otherwise retained by the dataframe conversion.

## P0 versus runtime evidence

P0 synthetic injections provide known experimental ground truth.

Example:

- an experiment may inject a missing-frame episode;
- the injection label can be `FRAME_GAP`;
- a detector can be evaluated against that known corruption.

This does not automatically prove that the same observable pattern
identifies a particular physical mechanism in deployment.

All P0 results must be reported separately from P1-P3 evidence.

## Provenance tiers

- P0: offline synthetic corruption
- P1: firmware-injected corruption
- P2: hardware-in-the-loop or interface corruption
- P3: physical/configuration/status evidence

Claims must remain stratified by tier.

## Reliability lineage V2 freeze

The protected historical combined 400-ms dataset is frozen with
dataset identity, protected-signal lineage, and raw-metadata provenance
recorded separately.

The trial population contains:

- UniVRFall: 1,100 trials
- KFall: 5,075 trials
- OnField: 18 trials

The historical train/validation/test window counts remain
510,479 / 89,868 / 366,507.

Historical training-only OnField augmentation remains separate at
220,472 windows.

### UniVRFall

The historical back tree is authoritative for protected-model signal
experiments.

Relative to the later current processed generation:

- 713 trials have an exact full protected-six-channel transform;
- 289 have an exact historical-prefix protected-six-channel transform;
- 98 are current-processed-version divergent.

Current processed arrays must not silently replace the historical
protected-model arrays.

### OnField

All 18 historical trials have an exact protected-six-channel transform
relative to the current processed representation.

Subjects 999 and 1000 remain historical-training augmentation only.

Raw OnField trial mapping remains unverified.

### KFall

Multiple processed generations exist.

- 3,301 trials are shape/label aligned under the recovered fixed-sign
  transform;
- 1,573 are length-divergent while retaining overlapping label
  alignment;
- 201 are current-processed-version divergent.

Across the 3,301 aligned trials, the recovered transform has aggregate
native-unit MAE approximately 0.238064 and maximum absolute residual
approximately 1.105019.

Those residuals describe preprocessing lineage and are not integrity
detector thresholds.

### Metadata boundary

Raw filename pairing exists for all 1,100 UniVR trials and all 5,075
KFall trials.

Filename pairing does not itself qualify metadata as acquisition
evidence.

The previously frozen integrity evidence contract remains controlling:

- KFall raw FrameCounter is qualified sequence evidence;
- UniVR oriented FrameCounter is not hard-qualified;
- FIFO-overrun evidence remains unavailable;
- physical measurement rails remain unverified;
- synthetic corruption truth remains distinct from runtime causal
  attribution.

The machine-readable frozen record is
`data/provenance/reliability_lineage_v2.json`.
