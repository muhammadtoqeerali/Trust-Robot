"""Noise-sensitive LiDAR residual-distribution diagnostics.

This module is a parallel TRAIN-only development diagnostic layer.

It does NOT alter the historical frozen five-feature Phase-4 LiDAR
diagnostic contract and does NOT alter the frozen registration algorithm.

Required execution architecture
-------------------------------

1. The caller executes the already-frozen LiDAR registration.
2. This module receives:
       previous_xyz
       current_xyz
       the frozen registration result
3. The exact frozen pose is reused.
4. Final nearest-neighbor distances are reconstructed observationally.
5. Reconstructed RMSE must match the frozen RMSE within 1e-12 relative
   and absolute tolerance.
6. Only then are eight deterministic residual-distribution statistics
   emitted.

No registration refit, correspondence rejection, downsampling, clipping,
normalization, thresholding, health labeling, or reference data are used.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree

from .lidar_frontend import (
    transform_xyz,
)


LEGACY_PHASE4_FEATURE_NAMES = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

NOISE_SENSITIVE_FEATURE_NAMES = (
    "final_nearest_neighbor_mean_m",
    "final_nearest_neighbor_std_m",
    "final_nearest_neighbor_median_m",
    "final_nearest_neighbor_mad_m",
    "final_nearest_neighbor_p75_m",
    "final_nearest_neighbor_p90_m",
    "final_nearest_neighbor_p95_m",
    "final_nearest_neighbor_max_m",
)

COMBINED_FEATURE_NAMES = (
    LEGACY_PHASE4_FEATURE_NAMES
    + NOISE_SENSITIVE_FEATURE_NAMES
)

NOISE_SENSITIVE_FEATURE_UNITS = (
    "m",
    "m",
    "m",
    "m",
    "m",
    "m",
    "m",
    "m",
)

RMSE_IDENTITY_REL_TOL = 1.0e-12
RMSE_IDENTITY_ABS_TOL = 1.0e-12


class LidarNoiseSensitiveDiagnosticError(
    ValueError
):
    """Raised when observational diagnostic extraction fails closed."""


@dataclass(
    frozen=True
)
class LidarNoiseSensitiveDiagnostics:
    final_nearest_neighbor_mean_m: float

    final_nearest_neighbor_std_m: float

    final_nearest_neighbor_median_m: float

    final_nearest_neighbor_mad_m: float

    final_nearest_neighbor_p75_m: float

    final_nearest_neighbor_p90_m: float

    final_nearest_neighbor_p95_m: float

    final_nearest_neighbor_max_m: float

    def __post_init__(
        self,
    ) -> None:
        values = self.feature_values()

        if len(
            values
        ) != len(
            NOISE_SENSITIVE_FEATURE_NAMES
        ):
            raise LidarNoiseSensitiveDiagnosticError(
                "noise-sensitive feature count changed"
            )

        for value in values:
            if (
                not math.isfinite(
                    value
                )
                or value < 0.0
            ):
                raise LidarNoiseSensitiveDiagnosticError(
                    "noise-sensitive diagnostic must be finite and non-negative"
                )

        if not (
            self.final_nearest_neighbor_max_m
            >= self.final_nearest_neighbor_p95_m
            >= self.final_nearest_neighbor_p90_m
            >= self.final_nearest_neighbor_p75_m
            >= self.final_nearest_neighbor_median_m
        ):
            raise LidarNoiseSensitiveDiagnosticError(
                "residual order-statistic invariant violated"
            )

    def feature_values(
        self,
    ) -> tuple[float, ...]:
        return (
            float(
                self.final_nearest_neighbor_mean_m
            ),
            float(
                self.final_nearest_neighbor_std_m
            ),
            float(
                self.final_nearest_neighbor_median_m
            ),
            float(
                self.final_nearest_neighbor_mad_m
            ),
            float(
                self.final_nearest_neighbor_p75_m
            ),
            float(
                self.final_nearest_neighbor_p90_m
            ),
            float(
                self.final_nearest_neighbor_p95_m
            ),
            float(
                self.final_nearest_neighbor_max_m
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, float]:
        return dict(
            zip(
                NOISE_SENSITIVE_FEATURE_NAMES,
                self.feature_values(),
                strict=True,
            )
        )


def _xyz_array(
    values: object,
    *,
    field_name: str,
) -> np.ndarray:
    array = np.asarray(
        values
    )

    if (
        array.ndim != 2
        or array.shape[
            1
        ] != 3
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            field_name
            + " must have shape (N,3)"
        )

    if array.shape[
        0
    ] < 2:
        raise LidarNoiseSensitiveDiagnosticError(
            field_name
            + " requires at least two points"
        )

    if not np.issubdtype(
        array.dtype,
        np.floating,
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            field_name
            + " must use floating-point XYZ values"
        )

    result = np.asarray(
        array,
        dtype=np.float64,
    )

    if not np.all(
        np.isfinite(
            result
        )
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            field_name
            + " contains non-finite XYZ values"
        )

    return result


def _frozen_pose_and_rmse(
    registration_result: object,
):
    if not hasattr(
        registration_result,
        "previous_lidar_T_current_lidar",
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "registration result does not expose frozen pose"
        )

    if not hasattr(
        registration_result,
        "diagnostics",
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "registration result does not expose frozen diagnostics"
        )

    diagnostics = (
        registration_result
        .diagnostics
    )

    if not hasattr(
        diagnostics,
        "final_nearest_neighbor_rmse_m",
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "frozen diagnostics do not expose final RMSE"
        )

    try:
        frozen_rmse = float(
            diagnostics
            .final_nearest_neighbor_rmse_m
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise LidarNoiseSensitiveDiagnosticError(
            "frozen RMSE must be numeric"
        ) from exc

    if (
        not math.isfinite(
            frozen_rmse
        )
        or frozen_rmse < 0.0
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "frozen RMSE must be finite and non-negative"
        )

    return (
        registration_result
        .previous_lidar_T_current_lidar,

        frozen_rmse,
    )


def _reconstruct_final_distances(
    previous_xyz: np.ndarray,
    current_xyz: np.ndarray,
    *,
    frozen_pose,
) -> np.ndarray:
    transformed = transform_xyz(
        frozen_pose,
        current_xyz,
    )

    transformed = np.asarray(
        transformed,
        dtype=np.float64,
    )

    if (
        transformed.shape
        != current_xyz.shape
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "frozen pose transformation changed point-cloud shape"
        )

    if not np.all(
        np.isfinite(
            transformed
        )
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "frozen pose produced non-finite transformed XYZ"
        )

    tree = cKDTree(
        previous_xyz
    )

    distances, _ = tree.query(
        transformed,
        k=1,
        workers=1,
    )

    result = np.asarray(
        distances,
        dtype=np.float64,
    )

    if result.shape != (
        current_xyz.shape[
            0
        ],
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "final nearest-neighbor distance vector shape changed"
        )

    if not np.all(
        np.isfinite(
            result
        )
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "final nearest-neighbor distances contain non-finite values"
        )

    if np.any(
        result < 0.0
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "nearest-neighbor distance cannot be negative"
        )

    return result


def _rmse(
    distances: np.ndarray,
) -> float:
    value = math.sqrt(
        float(
            np.mean(
                np.square(
                    distances,
                    dtype=np.float64,
                ),
                dtype=np.float64,
            )
        )
    )

    if (
        not math.isfinite(
            value
        )
        or value < 0.0
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "reconstructed RMSE is invalid"
        )

    return value


def extract_lidar_noise_sensitive_diagnostics(
    previous_xyz: object,
    current_xyz: object,
    registration_result: object,
) -> LidarNoiseSensitiveDiagnostics:
    """Extract eight diagnostics using only the already-frozen final pose."""

    previous = _xyz_array(
        previous_xyz,
        field_name=
            "previous_xyz",
    )

    current = _xyz_array(
        current_xyz,
        field_name=
            "current_xyz",
    )

    frozen_pose, frozen_rmse = (
        _frozen_pose_and_rmse(
            registration_result
        )
    )

    distances = (
        _reconstruct_final_distances(
            previous,
            current,
            frozen_pose=
                frozen_pose,
        )
    )

    reconstructed_rmse = (
        _rmse(
            distances
        )
    )

    if not math.isclose(
        reconstructed_rmse,
        frozen_rmse,
        rel_tol=
            RMSE_IDENTITY_REL_TOL,
        abs_tol=
            RMSE_IDENTITY_ABS_TOL,
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "observational RMSE does not reproduce frozen registration RMSE"
        )

    median = float(
        np.median(
            distances
        )
    )

    result = (
        LidarNoiseSensitiveDiagnostics(
            final_nearest_neighbor_mean_m=
                float(
                    np.mean(
                        distances,
                        dtype=np.float64,
                    )
                ),

            final_nearest_neighbor_std_m=
                float(
                    np.std(
                        distances,
                        dtype=np.float64,
                        ddof=0,
                    )
                ),

            final_nearest_neighbor_median_m=
                median,

            final_nearest_neighbor_mad_m=
                float(
                    np.median(
                        np.abs(
                            distances
                            - median
                        )
                    )
                ),

            final_nearest_neighbor_p75_m=
                float(
                    np.quantile(
                        distances,
                        0.75,
                        method="linear",
                    )
                ),

            final_nearest_neighbor_p90_m=
                float(
                    np.quantile(
                        distances,
                        0.90,
                        method="linear",
                    )
                ),

            final_nearest_neighbor_p95_m=
                float(
                    np.quantile(
                        distances,
                        0.95,
                        method="linear",
                    )
                ),

            final_nearest_neighbor_max_m=
                float(
                    np.max(
                        distances
                    )
                ),
        )
    )

    return result


def combine_legacy_and_noise_sensitive_features(
    legacy_feature_values: Sequence[object],
    extended: LidarNoiseSensitiveDiagnostics,
) -> tuple[float, ...]:
    if isinstance(
        legacy_feature_values,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "legacy feature vector must be a numeric sequence"
        )

    if len(
        legacy_feature_values
    ) != len(
        LEGACY_PHASE4_FEATURE_NAMES
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "legacy Phase-4 feature vector must contain exactly five values"
        )

    legacy = []

    for value in legacy_feature_values:
        if isinstance(
            value,
            bool,
        ):
            raise LidarNoiseSensitiveDiagnosticError(
                "legacy feature must be finite numeric"
            )

        try:
            normalized = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise LidarNoiseSensitiveDiagnosticError(
                "legacy feature must be finite numeric"
            ) from exc

        if not math.isfinite(
            normalized
        ):
            raise LidarNoiseSensitiveDiagnosticError(
                "legacy feature must be finite numeric"
            )

        legacy.append(
            normalized
        )

    if not isinstance(
        extended,
        LidarNoiseSensitiveDiagnostics,
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "extended diagnostics type mismatch"
        )

    result = tuple(
        legacy
    ) + extended.feature_values()

    if len(
        result
    ) != len(
        COMBINED_FEATURE_NAMES
    ):
        raise LidarNoiseSensitiveDiagnosticError(
            "combined feature count changed"
        )

    return result
