from pathlib import Path

import numpy as np

from imu_reliability.injection import (
    P0CorruptionKind,
    P0InjectionSpec,
    P0Stream,
    apply_p0_injection,
    p0_truth_to_evidence,
    write_immutable_manifest,
)
from imu_reliability.integrity import (
    IntegrityCause,
    assess_evidence,
    observe_frame_counter,
)


values = np.arange(
    72,
    dtype=np.float64,
).reshape(12, 6)

timestamps = (
    np.arange(
        1,
        13,
        dtype=np.float64,
    )
    * 0.01
)

counters = np.arange(
    1,
    13,
    dtype=np.int64,
)

clean = P0Stream(
    values=values,
    timestamps=timestamps,
    counters=counters,
    source_id="P0_SYNTHETIC_SANITY_STREAM",
)

spec = P0InjectionSpec(
    kind=P0CorruptionKind.FRAME_GAP,
    start_index=5,
    length=2,
    severity="moderate",
)

pair = apply_p0_injection(
    clean,
    spec,
)

truth_evidence = p0_truth_to_evidence(
    pair.truths[0]
)

truth_assessment = assess_evidence(
    [truth_evidence]
)

previous_counter = int(
    pair.corrupt.counters[4]
)

current_counter = int(
    pair.corrupt.counters[5]
)

runtime_evidence = observe_frame_counter(
    previous_counter,
    current_counter,
    provenance_qualified=True,
    source="synthetic_qualified_counter",
)

runtime_assessment = assess_evidence(
    [runtime_evidence]
)

manifest_path = Path(
    "experiments/01_integrity_p0/"
    "p0_synthetic_sanity_manifest.json"
)

write_immutable_manifest(
    manifest_path,
    pair,
)

# Idempotence check.
write_immutable_manifest(
    manifest_path,
    pair,
)

print(
    "spec_id =",
    spec.spec_id,
)

print(
    "injection_id =",
    pair.truths[0].injection_id,
)

print(
    "clean_fingerprint =",
    pair.clean.fingerprint(),
)

print(
    "corrupt_fingerprint =",
    pair.corrupt.fingerprint(),
)

print(
    "clean_n =",
    pair.clean.n_samples,
)

print(
    "corrupt_n =",
    pair.corrupt.n_samples,
)

print(
    "boundary_counters =",
    previous_counter,
    current_counter,
)

print(
    "P0_TRUTH_CAUSE_MASK =",
    int(
        truth_assessment.cause_mask
    ),
)

print(
    "RUNTIME_CAUSE_MASK =",
    int(
        runtime_assessment.cause_mask
    ),
)

print(
    "EXPECTED_RUNTIME_FRAME_GAP =",
    int(
        IntegrityCause.FRAME_GAP
    ),
)

print(
    "TRUTH_RUNTIME_SEPARATION_PASS =",
    (
        truth_assessment.cause_mask
        == IntegrityCause.NONE
        and runtime_assessment.cause_mask
        == IntegrityCause.FRAME_GAP
    ),
)

print(
    "MANIFEST =",
    manifest_path,
)
