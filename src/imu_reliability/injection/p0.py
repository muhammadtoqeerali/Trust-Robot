from __future__ import annotations

from hashlib import sha256
from typing import Callable

import numpy as np

from .types import (
    P0CorruptionKind,
    P0InjectionSpec,
    P0Pair,
    P0Stream,
    P0Truth,
)


def _injection_instance_id(
    clean: P0Stream,
    spec: P0InjectionSpec,
) -> str:
    """
    Deterministic ID for this specification applied to this clean
    stream.
    """

    payload = (
        clean.fingerprint()
        + ":"
        + spec.spec_id
    ).encode("utf-8")

    return (
        "P0I_"
        + sha256(
            payload
        ).hexdigest()[:24]
    )


def _validate_bounds(
    stream: P0Stream,
    spec: P0InjectionSpec,
) -> int:

    end = (
        spec.start_index
        + spec.length
    )

    if end > stream.n_samples:
        raise ValueError(
            "Injection exceeds stream bounds: "
            f"start={spec.start_index}, "
            f"length={spec.length}, "
            f"n={stream.n_samples}"
        )

    return end


def _validate_channels(
    stream: P0Stream,
    spec: P0InjectionSpec,
) -> None:

    for channel in spec.channels:

        if channel >= stream.n_channels:
            raise ValueError(
                f"Channel {channel} outside "
                f"0..{stream.n_channels - 1}"
            )


def _stream_from_arrays(
    source: P0Stream,
    *,
    values,
    timestamps=None,
    counters=None,
    origin_indices=None,
) -> P0Stream:

    return P0Stream(
        values=values,
        timestamps=(
            source.timestamps
            if timestamps is None
            else timestamps
        ),
        counters=(
            source.counters
            if counters is None
            else counters
        ),
        origin_indices=(
            source.origin_indices
            if origin_indices is None
            else origin_indices
        ),
        source_id=source.source_id,
    )


def inject_frame_gap(
    clean: P0Stream,
    spec: P0InjectionSpec,
) -> P0Pair:

    end = _validate_bounds(
        clean,
        spec,
    )

    if spec.start_index == 0:
        raise ValueError(
            "FRAME_GAP start_index must be >= 1 "
            "so a pre-gap boundary exists"
        )

    if end >= clean.n_samples:
        raise ValueError(
            "FRAME_GAP must leave at least one post-gap sample "
            "so the discontinuity has an observable boundary"
        )

    keep = np.ones(
        clean.n_samples,
        dtype=bool,
    )

    keep[
        spec.start_index:end
    ] = False

    corrupt = P0Stream(
        values=clean.values[keep],
        timestamps=(
            None
            if clean.timestamps is None
            else clean.timestamps[keep]
        ),
        counters=(
            None
            if clean.counters is None
            else clean.counters[keep]
        ),
        origin_indices=(
            clean.origin_indices[keep]
        ),
        source_id=clean.source_id,
    )

    details = {
        "removed_samples":
            spec.length,
    }

    if clean.counters is not None:

        before = int(
            clean.counters[
                spec.start_index - 1
            ]
        )

        after = (
            int(
                clean.counters[end]
            )
            if end < clean.n_samples
            else None
        )

        details.update(
            {
                "counter_before_gap":
                    before,
                "counter_after_gap":
                    after,
            }
        )

    truth = P0Truth(
        spec=spec,
        injection_id=_injection_instance_id(
            clean,
            spec,
        ),
        clean_n_samples=
            clean.n_samples,
        corrupt_n_samples=
            corrupt.n_samples,
        affected_clean_start=
            spec.start_index,
        affected_clean_end_exclusive=
            end,
        corrupt_anchor_index=
            min(
                spec.start_index,
                corrupt.n_samples - 1,
            ),
        details=details,
    )

    return P0Pair(
        clean=clean,
        corrupt=corrupt,
        truths=(truth,),
    )


def inject_frame_repeat(
    clean: P0Stream,
    spec: P0InjectionSpec,
) -> P0Pair:

    end = _validate_bounds(
        clean,
        spec,
    )

    if spec.start_index == 0:
        raise ValueError(
            "FRAME_REPEAT start_index must be >= 1"
        )

    values = clean.values.copy()

    repeated_value = clean.values[
        spec.start_index - 1
    ].copy()

    values[
        spec.start_index:end
    ] = repeated_value

    if np.array_equal(
        values[
            spec.start_index:end
        ],
        clean.values[
            spec.start_index:end
        ],
    ):
        raise ValueError(
            "FRAME_REPEAT injection produced no sensor-value change"
        )

    corrupt = _stream_from_arrays(
        clean,
        values=values,
    )

    truth = P0Truth(
        spec=spec,
        injection_id=_injection_instance_id(
            clean,
            spec,
        ),
        clean_n_samples=
            clean.n_samples,
        corrupt_n_samples=
            corrupt.n_samples,
        affected_clean_start=
            spec.start_index,
        affected_clean_end_exclusive=
            end,
        corrupt_anchor_index=
            spec.start_index,
        details={
            "repeated_from_clean_index":
                spec.start_index - 1,
            "metadata_progress_preserved":
                True,
        },
    )

    return P0Pair(
        clean=clean,
        corrupt=corrupt,
        truths=(truth,),
    )


def inject_channel_freeze(
    clean: P0Stream,
    spec: P0InjectionSpec,
) -> P0Pair:

    end = _validate_bounds(
        clean,
        spec,
    )

    _validate_channels(
        clean,
        spec,
    )

    if not spec.channels:
        raise ValueError(
            "CHANNEL_FREEZE requires channels"
        )

    if spec.start_index == 0:
        raise ValueError(
            "CHANNEL_FREEZE start_index must be >= 1"
        )

    values = clean.values.copy()

    for channel in spec.channels:

        freeze_value = clean.values[
            spec.start_index - 1,
            channel,
        ]

        values[
            spec.start_index:end,
            channel,
        ] = freeze_value

    selected = list(
        spec.channels
    )

    if np.array_equal(
        values[
            spec.start_index:end,
            :
        ][
            :,
            selected
        ],
        clean.values[
            spec.start_index:end,
            :
        ][
            :,
            selected
        ],
    ):
        raise ValueError(
            "CHANNEL_FREEZE injection produced no selected-channel change"
        )

    corrupt = _stream_from_arrays(
        clean,
        values=values,
    )

    truth = P0Truth(
        spec=spec,
        injection_id=_injection_instance_id(
            clean,
            spec,
        ),
        clean_n_samples=
            clean.n_samples,
        corrupt_n_samples=
            corrupt.n_samples,
        affected_clean_start=
            spec.start_index,
        affected_clean_end_exclusive=
            end,
        corrupt_anchor_index=
            spec.start_index,
        details={
            "channels":
                list(
                    spec.channels
                ),
            "metadata_progress_preserved":
                True,
        },
    )

    return P0Pair(
        clean=clean,
        corrupt=corrupt,
        truths=(truth,),
    )


def inject_timing_perturbation(
    clean: P0Stream,
    spec: P0InjectionSpec,
) -> P0Pair:

    if clean.timestamps is None:
        raise ValueError(
            "TIMING_PERTURBATION requires timestamps"
        )

    if spec.length != 1:
        raise ValueError(
            "TIMING_PERTURBATION currently requires length=1"
        )

    if (
        spec.start_index <= 0
        or spec.start_index >= clean.n_samples
    ):
        raise ValueError(
            "TIMING_PERTURBATION start_index must identify "
            "an internal boundary"
        )

    if "offset" not in spec.parameters:
        raise ValueError(
            "TIMING_PERTURBATION requires parameters['offset']"
        )

    offset = float(
        spec.parameters[
            "offset"
        ]
    )

    if offset == 0.0:
        raise ValueError(
            "TIMING_PERTURBATION offset must be non-zero"
        )

    timestamps = clean.timestamps.copy()

    # Step change: produce exactly one perturbed inter-sample boundary,
    # then preserve all subsequent inter-sample intervals.
    timestamps[
        spec.start_index:
    ] += offset

    corrupt = _stream_from_arrays(
        clean,
        values=clean.values,
        timestamps=timestamps,
    )

    truth = P0Truth(
        spec=spec,
        injection_id=_injection_instance_id(
            clean,
            spec,
        ),
        clean_n_samples=
            clean.n_samples,
        corrupt_n_samples=
            corrupt.n_samples,
        affected_clean_start=
            spec.start_index,
        affected_clean_end_exclusive=
            spec.start_index + 1,
        corrupt_anchor_index=
            spec.start_index,
        details={
            "timestamp_offset":
                offset,
            "mode":
                "step",
        },
    )

    return P0Pair(
        clean=clean,
        corrupt=corrupt,
        truths=(truth,),
    )


def inject_range_clip(
    clean: P0Stream,
    spec: P0InjectionSpec,
) -> P0Pair:

    end = _validate_bounds(
        clean,
        spec,
    )

    _validate_channels(
        clean,
        spec,
    )

    if not spec.channels:
        raise ValueError(
            "RANGE_CLIP requires channels"
        )

    if (
        "low" not in spec.parameters
        or "high" not in spec.parameters
    ):
        raise ValueError(
            "RANGE_CLIP requires parameters['low'] "
            "and parameters['high']"
        )

    low = float(
        spec.parameters[
            "low"
        ]
    )

    high = float(
        spec.parameters[
            "high"
        ]
    )

    if high < low:
        raise ValueError(
            "RANGE_CLIP high must be >= low"
        )

    values = clean.values.copy()

    for channel in spec.channels:

        values[
            spec.start_index:end,
            channel,
        ] = np.clip(
            values[
                spec.start_index:end,
                channel,
            ],
            low,
            high,
        )

    selected = list(
        spec.channels
    )

    if np.array_equal(
        values[
            spec.start_index:end,
            :
        ][
            :,
            selected
        ],
        clean.values[
            spec.start_index:end,
            :
        ][
            :,
            selected
        ],
    ):
        raise ValueError(
            "RANGE_CLIP injection produced no selected-channel change"
        )

    corrupt = _stream_from_arrays(
        clean,
        values=values,
    )

    truth = P0Truth(
        spec=spec,
        injection_id=_injection_instance_id(
            clean,
            spec,
        ),
        clean_n_samples=
            clean.n_samples,
        corrupt_n_samples=
            corrupt.n_samples,
        affected_clean_start=
            spec.start_index,
        affected_clean_end_exclusive=
            end,
        corrupt_anchor_index=
            spec.start_index,
        details={
            "low": low,
            "high": high,
            "channels":
                list(
                    spec.channels
                ),
            "physical_rail_claim":
                False,
        },
    )

    return P0Pair(
        clean=clean,
        corrupt=corrupt,
        truths=(truth,),
    )


_INJECTORS: dict[
    P0CorruptionKind,
    Callable[
        [P0Stream, P0InjectionSpec],
        P0Pair,
    ],
] = {
    P0CorruptionKind.FRAME_GAP:
        inject_frame_gap,
    P0CorruptionKind.FRAME_REPEAT:
        inject_frame_repeat,
    P0CorruptionKind.CHANNEL_FREEZE:
        inject_channel_freeze,
    P0CorruptionKind.TIMING_PERTURBATION:
        inject_timing_perturbation,
    P0CorruptionKind.RANGE_CLIP:
        inject_range_clip,
}


def apply_p0_injection(
    clean: P0Stream,
    spec: P0InjectionSpec,
) -> P0Pair:

    try:
        injector = _INJECTORS[
            spec.kind
        ]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported P0 corruption: {spec.kind}"
        ) from exc

    return injector(
        clean,
        spec,
    )
