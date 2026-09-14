# Protected baseline v1

## Status

`DATE2025_CNN_400MS_RECONSTRUCTED_V1` is the frozen protected
task-model baseline for the IMU reliability study.

It is a historical reconstruction, not a claim that the original
DATE 2025 STM32 firmware or generated network binary was recovered.

## Recovered checkpoint

- Window: 400 ms at 100 Hz = 40 samples.
- Stored input: 40 x 9.
- Effective CNN input: accelerometer + gyroscope = 6 channels.
- CNN: 32-channel Conv1D blocks, kernel 4, pool 2.
- Flatten dimension: 224.
- Hidden FC representation: 256.
- Trainable parameters: 63,173.
- Classes: Activity / Falling.
- SHA-256:
  `ee7c0079bfb8555bff45c3077cc24eaa4373c57729045d92a831a1d7a3ea9bb1`.

## Training-lineage evidence

The surviving split and augmentation reproduce the checkpoint optimizer
history exactly:

- pre-augmentation train windows: 510,479
- falling train windows: 3,014
- two falling time-warp copies: 6,028
- OnField subjects 999 + 1000: 220,472
- augmented train windows: 736,979
- batch size: 64
- batches per epoch: ceil(736979 / 64) = 11,516
- completed epochs inferred from epoch index 60: 61
- 11,516 x 61 = 702,476
- recovered checkpoint global_step: 702,476

The training dataset/split lineage is therefore treated as strongly
supported reconstructed provenance.

## One-forward invariant

The protected CNN is not retrained or duplicated by the reliability
wrapper.

The reconstruction exposes the post-PReLU 256-dimensional penultimate
representation during the same task forward. Verification produced:

- maximum logit difference: 0.0
- identical task predictions: yes

OOD methods must reuse these logits/features rather than execute another
full task-model forward.

## Decision semantics

Two historical semantics are kept distinct.

`Predictor` classifier metrics use `argmax(logits)`.

The historical streaming `Simulator.get_output` uses a confidence bias
of 0.9. Its binary behavior is:

`Falling iff P(Falling) > 0.9`, otherwise `Activity`.

The comparison is strict `>`.

The optional threshold filter and smoothing routines are not active in
the recovered simulator path.

The event-level simulator subsequently requires its preserved event
criterion; that behavior is reported separately from window-level
classification.

## Claim boundary

The following were not recovered:

- exact STM32 application firmware
- exact generated STM32 network representation
- original 400-ms ONNX artifact
- historical source commit proving byte-identical deployment

Any later MCU implementation must therefore be labelled a reconstruction
unless stronger deployment artifacts are recovered independently.

## Evaluation discipline

The historical baseline test set has already been inspected during
baseline recovery. No integrity, OOD, persistence or fusion parameter
may be selected using final reliability-test outcomes.

Development/calibration decisions must be frozen before the final
reliability evaluation.
