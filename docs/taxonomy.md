# Integrity evidence taxonomy

## Principle

External integrity cause codes require direct acquisition,
measurement, or data-path evidence.

Ambiguous signal behavior remains suspect/internal.

Multiple simultaneously qualified hard causes are retained as a set
or bitmask rather than collapsed to one label.

## Cause contract

### FRAME_GAP

Meaning:

A discontinuity in an independently qualified acquisition frame
sequence.

Hard qualification:

`current_counter > previous_counter + 1`

only when the counter has direct acquisition provenance.

Current dataset status:

- KFall raw: qualified
- UniVR original: unavailable
- UniVR oriented: counter exists but provenance unverified; not hard

A frame gap does not imply `FIFO_OVERRUN`.

### FIFO_OVERRUN

Meaning:

Acquisition FIFO/status evidence directly reports overflow/overrun.

Current status:

Unsupported.

No surviving FIFO or overrun status field has been recovered.

Never infer this cause from timing gaps or missing frame counters
alone.

### FRAME_REPEAT

Meaning:

A previously acquired frame is independently demonstrated to have
been repeated by the data path.

Current status:

Not hard-qualified from the available historical datasets.

Identical sensor values alone are insufficient.

Synthetic P0 repeated-frame episodes may be evaluated with known
injection labels but must remain P0 evidence.

### BUFFER_STALL

Meaning:

Independent data-path evidence shows acquisition/output progress has
stalled.

Current status:

Unsupported as a hard historical-data cause.

A repeated sensor vector or repeated UniVR millisecond timestamp is
insufficient.

### ACQ_TIMING_VIOLATION

Meaning:

The acquisition timing interval violates a predeclared operating
envelope derived from a characterized timestamp source.

Current status:

- KFall timestamp: empirically clean 10-ms sequence
- UniVR timestamp: available but quantized/coarse with common
  0/10/20-ms behavior
- final threshold: not frozen

Do not select the threshold from final-test outcomes.

Until the primary UniVR timestamp operating envelope is frozen on
development data, timing evidence must not be promoted to a final
external cause.

### RANGE_CLIP

Meaning:

Persistent measurements lie at or sufficiently near a traceable
configured measurement rail, indicating information loss.

Current status:

Not hard-qualified.

Observed UniVR acceleration approaches ±4000 mg and the historical
model normalizer also uses 4000 mg, but model normalization is not
proof of sensor configuration.

Isolated high-magnitude samples are insufficient.

If authoritative range/configuration evidence is later recovered,
the detector may be promoted under a documented provenance revision.

### CHANNEL_FREEZE_SUSPECT

Meaning:

One or more sensor channels show implausibly persistent unchanged or
near-unchanged values.

Status:

Supported as suspect-only signal evidence.

It is not a hardware-fault diagnosis.

It must never generate an external hard integrity cause without
independent evidence.

## Evidence layers

The implementation distinguishes:

1. raw observation/evidence;
2. suspect indicators;
3. qualified hard causes;
4. synthetic injection ground truth.

These layers must not be conflated.

## P0 reporting rule

A P0 corruption label records what the experiment injected.

A runtime cause records only what the monitor can support from its
available evidence.

Both fields are retained in evaluation outputs.

## Trust-state interaction

The reliability layer uses:

- `INTEGRITY_ALERT(C_t)` when at least one qualified hard cause exists;
- otherwise OOD evaluation may produce `OOD_UNKNOWN`;
- otherwise the state is `VALID`.

Suspect-only indicators do not by themselves populate `C_t`.

They may be retained internally for diagnostics, ablations, and later
persistence studies.
