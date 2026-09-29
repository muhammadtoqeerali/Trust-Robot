"""Deterministic point-level LiDAR corruption operators.

These operators support TRAIN-only synthetic robustness experiments.

Families
--------
POINT_DROPOUT
    Remove a prospectively fixed fraction of points from one LiDAR event.

XYZ_GAUSSIAN_NOISE
    Add deterministic pseudo-random zero-mean Gaussian XYZ perturbations.

AZIMUTH_SECTOR_OCCLUSION
    Remove all points inside one deterministic azimuth sector.

Scientific boundary
-------------------
The resulting truth records describe synthetic interventions performed by
TRUST-ROBOT.  They are not real physical sensor-health labels.

The clean EventStream is never modified in-place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping
import json
import math

import numpy as np

from .corruption import (
    EventStream,
    SensorModality,
)


class LidarPointCorruptionError(
    ValueError
):
    """Raised when the point-level corruption contract is violated."""


class LidarPointCorruptionFamily(
    str,
    Enum,
):
    POINT_DROPOUT = "POINT_DROPOUT"

    XYZ_GAUSSIAN_NOISE = (
        "XYZ_GAUSSIAN_NOISE"
    )

    AZIMUTH_SECTOR_OCCLUSION = (
        "AZIMUTH_SECTOR_OCCLUSION"
    )


@dataclass(
    frozen=True
)
class LidarPointCorruptionSpec:
    family: LidarPointCorruptionFamily

    target_event_index: int = 1

    remove_fraction: float | None = None

    sigma_m: float | None = None

    sector_width_degrees: float | None = None


@dataclass(
    frozen=True
)
class LidarPointCorruptionResult:
    clean: EventStream

    corrupt: EventStream

    truth: Mapping[
        str,
        Any,
    ]


def _canonical_json_bytes(
    payload: Mapping[
        str,
        Any,
    ],
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )


def _sha256_json(
    payload: Mapping[
        str,
        Any,
    ],
) -> str:
    return sha256(
        _canonical_json_bytes(
            payload
        )
    ).hexdigest()


def _validate_window_key(
    window_key: str,
) -> str:
    if (
        not isinstance(
            window_key,
            str,
        )
        or not window_key
        or len(
            window_key
        ) > 512
    ):
        raise LidarPointCorruptionError(
            "window_key must be a non-empty string <=512 characters"
        )

    return window_key


def _validate_payload(
    payload: np.ndarray,
) -> np.ndarray:
    array = np.asarray(
        payload
    )

    if (
        array.ndim != 2
        or array.shape[
            1
        ] != 3
    ):
        raise LidarPointCorruptionError(
            "LiDAR payload must have shape (N,3)"
        )

    if array.shape[
        0
    ] < 2:
        raise LidarPointCorruptionError(
            "LiDAR payload requires at least two points"
        )

    if not np.issubdtype(
        array.dtype,
        np.floating,
    ):
        raise LidarPointCorruptionError(
            "LiDAR payload must use floating-point XYZ values"
        )

    if not np.all(
        np.isfinite(
            array
        )
    ):
        raise LidarPointCorruptionError(
            "LiDAR payload must contain finite XYZ values"
        )

    return np.asarray(
        array,
        dtype=np.float64,
    )


def _validate_stream(
    stream: EventStream,
    target_event_index: int,
) -> None:
    if stream.modality != SensorModality.LIDAR:
        raise LidarPointCorruptionError(
            "point-level corruption requires LiDAR modality"
        )

    if (
        type(
            target_event_index
        ) is not int
        or target_event_index < 0
        or target_event_index
        >= stream.n_events
    ):
        raise LidarPointCorruptionError(
            "target_event_index outside stream"
        )

    for payload in stream.payloads:
        _validate_payload(
            payload
        )


def _derive_seed(
    *,
    window_key: str,
    family: LidarPointCorruptionFamily,
    target_event_index: int,
) -> int:
    payload = {
        "schema":
            "TRUST_ROBOT_LIDAR_POINT_CORRUPTION_SEED_V1",

        "window_key":
            window_key,

        "family":
            family.value,

        "target_event_index":
            target_event_index,
    }

    digest = sha256(
        _canonical_json_bytes(
            payload
        )
    ).digest()

    return int.from_bytes(
        digest[
            :8
        ],
        byteorder="big",
        signed=False,
    )


def _point_data_sha256(
    points: np.ndarray,
) -> str:
    canonical = np.ascontiguousarray(
        points,
        dtype="<f8",
    )

    return sha256(
        canonical.tobytes(
            order="C"
        )
    ).hexdigest()


def _index_data_sha256(
    indices: np.ndarray,
) -> str:
    canonical = np.ascontiguousarray(
        indices,
        dtype="<i8",
    )

    return sha256(
        canonical.tobytes(
            order="C"
        )
    ).hexdigest()


def _copy_payloads(
    stream: EventStream,
) -> list[
    np.ndarray
]:
    return [
        np.asarray(
            payload,
            dtype=np.float64,
        ).copy()
        for payload
        in stream.payloads
    ]


def _build_corrupt_stream(
    *,
    clean: EventStream,
    payloads: list[np.ndarray],
    truth: Mapping[str, Any],
) -> EventStream:
    metadata = dict(
        clean.metadata
    )

    metadata.update(
        {
            "synthetic_point_level_corruption":
                True,

            "synthetic_point_level_corruption_family":
                truth[
                    "family"
                ],

            "synthetic_truth_is_real_physical_health_truth":
                False,
        }
    )

    origin_indices = (
        None
        if clean.origin_indices
        is None
        else np.asarray(
            clean.origin_indices,
            dtype=np.int64,
        ).copy()
    )

    return EventStream(
        modality=
            clean.modality,

        source_id=
            clean.source_id,

        timestamps_ns=
            np.asarray(
                clean.timestamps_ns,
                dtype=np.int64,
            ).copy(),

        payloads=
            tuple(
                payloads
            ),

        origin_indices=
            origin_indices,

        metadata=
            metadata,
    )


def _base_truth(
    *,
    stream: EventStream,
    spec: LidarPointCorruptionSpec,
    window_key: str,
    seed: int,
    before: np.ndarray,
    after: np.ndarray,
) -> dict[str, Any]:
    truth = {
        "schema":
            "TRUST_ROBOT_LIDAR_POINT_LEVEL_CORRUPTION_TRUTH_V1",

        "schema_version":
            1,

        "family":
            spec.family.value,

        "modality":
            "lidar",

        "source_id":
            stream.source_id,

        "target_event_index":
            spec.target_event_index,

        "window_key":
            window_key,

        "derived_seed":
            seed,

        "before_point_count":
            int(
                before.shape[
                    0
                ]
            ),

        "after_point_count":
            int(
                after.shape[
                    0
                ]
            ),

        "before_xyz_sha256":
            _point_data_sha256(
                before
            ),

        "after_xyz_sha256":
            _point_data_sha256(
                after
            ),

        "timestamps_modified":
            False,

        "origin_indices_modified":
            False,

        "non_target_events_modified":
            False,

        "clean_stream_mutated":
            False,

        "synthetic_truth_is_real_physical_health_truth":
            False,

        "synthetic_truth_is_physical_cause_evidence":
            False,

        "synthetic_truth_is_runtime_causal_evidence":
            False,
    }

    return truth


def _apply_point_dropout(
    *,
    stream: EventStream,
    spec: LidarPointCorruptionSpec,
    window_key: str,
    seed: int,
) -> LidarPointCorruptionResult:
    fraction = spec.remove_fraction

    if (
        fraction is None
        or isinstance(
            fraction,
            bool,
        )
        or not isinstance(
            fraction,
            (
                int,
                float,
            ),
        )
        or not math.isfinite(
            float(
                fraction
            )
        )
        or not (
            0.0
            < float(
                fraction
            )
            < 1.0
        )
    ):
        raise LidarPointCorruptionError(
            "POINT_DROPOUT requires remove_fraction strictly between 0 and 1"
        )

    payloads = _copy_payloads(
        stream
    )

    before = payloads[
        spec.target_event_index
    ].copy()

    point_count = before.shape[
        0
    ]

    remove_count = int(
        round(
            point_count
            * float(
                fraction
            )
        )
    )

    remove_count = max(
        1,
        remove_count,
    )

    remove_count = min(
        point_count - 1,
        remove_count,
    )

    generator = np.random.Generator(
        np.random.PCG64(
            seed
        )
    )

    removed_indices = np.sort(
        generator.choice(
            point_count,
            size=
                remove_count,
            replace=
                False,
        ).astype(
            np.int64
        )
    )

    keep_mask = np.ones(
        point_count,
        dtype=bool,
    )

    keep_mask[
        removed_indices
    ] = False

    after = before[
        keep_mask
    ].copy()

    payloads[
        spec.target_event_index
    ] = after

    truth = _base_truth(
        stream=
            stream,

        spec=
            spec,

        window_key=
            window_key,

        seed=
            seed,

        before=
            before,

        after=
            after,
    )

    truth.update(
        {
            "remove_fraction_requested":
                float(
                    fraction
                ),

            "removed_point_count":
                int(
                    remove_count
                ),

            "remove_fraction_actual":
                float(
                    remove_count
                    / point_count
                ),

            "removed_indices_sha256":
                _index_data_sha256(
                    removed_indices
                ),

            "selection_method":
                "PCG64_without_replacement_from_hash_derived_seed",
        }
    )

    truth[
        "truth_content_sha256"
    ] = _sha256_json(
        truth
    )

    corrupt = _build_corrupt_stream(
        clean=
            stream,

        payloads=
            payloads,

        truth=
            truth,
    )

    return LidarPointCorruptionResult(
        clean=
            stream,

        corrupt=
            corrupt,

        truth=
            truth,
    )


def _apply_xyz_gaussian_noise(
    *,
    stream: EventStream,
    spec: LidarPointCorruptionSpec,
    window_key: str,
    seed: int,
) -> LidarPointCorruptionResult:
    sigma = spec.sigma_m

    if (
        sigma is None
        or isinstance(
            sigma,
            bool,
        )
        or not isinstance(
            sigma,
            (
                int,
                float,
            ),
        )
        or not math.isfinite(
            float(
                sigma
            )
        )
        or float(
            sigma
        ) <= 0.0
    ):
        raise LidarPointCorruptionError(
            "XYZ_GAUSSIAN_NOISE requires sigma_m > 0"
        )

    payloads = _copy_payloads(
        stream
    )

    before = payloads[
        spec.target_event_index
    ].copy()

    generator = np.random.Generator(
        np.random.PCG64(
            seed
        )
    )

    noise = generator.normal(
        loc=
            0.0,

        scale=
            float(
                sigma
            ),

        size=
            before.shape,
    ).astype(
        np.float64
    )

    after = (
        before
        + noise
    )

    payloads[
        spec.target_event_index
    ] = after

    truth = _base_truth(
        stream=
            stream,

        spec=
            spec,

        window_key=
            window_key,

        seed=
            seed,

        before=
            before,

        after=
            after,
    )

    truth.update(
        {
            "sigma_m":
                float(
                    sigma
                ),

            "noise_xyz_sha256":
                _point_data_sha256(
                    noise
                ),

            "noise_mean_xyz_m": [
                float(
                    value
                )
                for value
                in np.mean(
                    noise,
                    axis=0,
                )
            ],

            "noise_std_xyz_m": [
                float(
                    value
                )
                for value
                in np.std(
                    noise,
                    axis=0,
                )
            ],

            "sampling_method":
                "numpy_PCG64_gaussian_from_hash_derived_seed",
        }
    )

    truth[
        "truth_content_sha256"
    ] = _sha256_json(
        truth
    )

    corrupt = _build_corrupt_stream(
        clean=
            stream,

        payloads=
            payloads,

        truth=
            truth,
    )

    return LidarPointCorruptionResult(
        clean=
            stream,

        corrupt=
            corrupt,

        truth=
            truth,
    )


def _deterministic_sector_center_degrees(
    *,
    window_key: str,
    target_event_index: int,
) -> float:
    payload = {
        "schema":
            "TRUST_ROBOT_LIDAR_OCCLUSION_CENTER_V1",

        "window_key":
            window_key,

        "target_event_index":
            target_event_index,
    }

    integer = int.from_bytes(
        sha256(
            _canonical_json_bytes(
                payload
            )
        ).digest()[
            :8
        ],
        byteorder="big",
        signed=False,
    )

    unit = (
        integer
        / float(
            2 ** 64
        )
    )

    return (
        -180.0
        + 360.0
        * unit
    )


def _apply_azimuth_sector_occlusion(
    *,
    stream: EventStream,
    spec: LidarPointCorruptionSpec,
    window_key: str,
    seed: int,
) -> LidarPointCorruptionResult:
    width = spec.sector_width_degrees

    if (
        width is None
        or isinstance(
            width,
            bool,
        )
        or not isinstance(
            width,
            (
                int,
                float,
            ),
        )
        or not math.isfinite(
            float(
                width
            )
        )
        or not (
            0.0
            < float(
                width
            )
            < 360.0
        )
    ):
        raise LidarPointCorruptionError(
            "AZIMUTH_SECTOR_OCCLUSION requires width strictly between 0 and 360 degrees"
        )

    payloads = _copy_payloads(
        stream
    )

    before = payloads[
        spec.target_event_index
    ].copy()

    center_degrees = (
        _deterministic_sector_center_degrees(
            window_key=
                window_key,

            target_event_index=
                spec.target_event_index,
        )
    )

    center_radians = np.deg2rad(
        center_degrees
    )

    half_width_radians = np.deg2rad(
        float(
            width
        )
        / 2.0
    )

    azimuth = np.arctan2(
        before[
            :,
            1
        ],
        before[
            :,
            0
        ],
    )

    wrapped_difference = (
        (
            azimuth
            - center_radians
            + np.pi
        )
        % (
            2.0
            * np.pi
        )
        - np.pi
    )

    removed_mask = (
        np.abs(
            wrapped_difference
        )
        <= half_width_radians
    )

    removed_indices = np.flatnonzero(
        removed_mask
    ).astype(
        np.int64
    )

    if removed_indices.size == 0:
        raise LidarPointCorruptionError(
            "deterministic azimuth sector removed zero points"
        )

    if removed_indices.size >= before.shape[
        0
    ]:
        raise LidarPointCorruptionError(
            "deterministic azimuth sector removed all points"
        )

    after = before[
        ~removed_mask
    ].copy()

    payloads[
        spec.target_event_index
    ] = after

    truth = _base_truth(
        stream=
            stream,

        spec=
            spec,

        window_key=
            window_key,

        seed=
            seed,

        before=
            before,

        after=
            after,
    )

    truth.update(
        {
            "sector_width_degrees":
                float(
                    width
                ),

            "sector_center_degrees":
                float(
                    center_degrees
                ),

            "removed_point_count":
                int(
                    removed_indices.size
                ),

            "removed_fraction_actual":
                float(
                    removed_indices.size
                    / before.shape[
                        0
                    ]
                ),

            "removed_indices_sha256":
                _index_data_sha256(
                    removed_indices
                ),

            "center_selection_method":
                "SHA256_window_key_mapping_to_azimuth",
        }
    )

    truth[
        "truth_content_sha256"
    ] = _sha256_json(
        truth
    )

    corrupt = _build_corrupt_stream(
        clean=
            stream,

        payloads=
            payloads,

        truth=
            truth,
    )

    return LidarPointCorruptionResult(
        clean=
            stream,

        corrupt=
            corrupt,

        truth=
            truth,
    )


def apply_lidar_point_corruption(
    stream: EventStream,
    spec: LidarPointCorruptionSpec,
    *,
    window_key: str,
) -> LidarPointCorruptionResult:
    if not isinstance(
        spec,
        LidarPointCorruptionSpec,
    ):
        raise LidarPointCorruptionError(
            "spec must be LidarPointCorruptionSpec"
        )

    key = _validate_window_key(
        window_key
    )

    _validate_stream(
        stream,
        spec.target_event_index,
    )

    seed = _derive_seed(
        window_key=
            key,

        family=
            spec.family,

        target_event_index=
            spec.target_event_index,
    )

    if spec.family == (
        LidarPointCorruptionFamily.POINT_DROPOUT
    ):
        return _apply_point_dropout(
            stream=
                stream,

            spec=
                spec,

            window_key=
                key,

            seed=
                seed,
        )

    if spec.family == (
        LidarPointCorruptionFamily.XYZ_GAUSSIAN_NOISE
    ):
        return _apply_xyz_gaussian_noise(
            stream=
                stream,

            spec=
                spec,

            window_key=
                key,

            seed=
                seed,
        )

    if spec.family == (
        LidarPointCorruptionFamily.AZIMUTH_SECTOR_OCCLUSION
    ):
        return _apply_azimuth_sector_occlusion(
            stream=
                stream,

            spec=
                spec,

            window_key=
                key,

            seed=
                seed,
        )

    raise LidarPointCorruptionError(
        "unsupported point-level corruption family"
    )
