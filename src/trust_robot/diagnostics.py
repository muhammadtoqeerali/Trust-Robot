from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Iterable, Mapping
import json
import math

from .lidar_frontend import (
    LidarRegistrationDiagnostics,
)


DIAGNOSTIC_FEATURE_SCHEMA = (
    "TRUST_ROBOT_PHASE4_DIAGNOSTIC_FEATURE_RECORD_V1"
)

DIAGNOSTIC_MANIFEST_SCHEMA = (
    "TRUST_ROBOT_PHASE4_DIAGNOSTIC_FEATURE_MANIFEST_V1"
)

LIDAR_REGISTRATION_EXTRACTOR_ID = (
    "trust_robot_phase4_lidar_registration_diagnostics_v1"
)

FROZEN_LIDAR_FRONTEND_SHA256 = (
    "c1aac98d3081d338036a7ae9fd4ffd5c8f345f217ca8dbfa6426b0ac4e65cf7a"
)

LIDAR_REGISTRATION_FEATURE_ORDER = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
)

LIDAR_REGISTRATION_FEATURE_UNITS = (
    "count",
    "count",
    "count",
    "count",
    "m",
)

EXPECTED_CONVERGENCE_RULE = (
    "exact_nearest_neighbor_assignment_unchanged"
)


class DiagnosticFeatureError(ValueError):
    """Raised when diagnostic feature extraction violates its contract."""


def _canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _nonempty_text(
    value,
    *,
    name,
) -> str:
    result = str(
        value
    ).strip()

    if not result:
        raise DiagnosticFeatureError(
            f"{name} cannot be empty"
        )

    return result


def _immutable_scalar_mapping(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    copied = {}

    for key, item in dict(
        value
        or {}
    ).items():
        key_text = _nonempty_text(
            key,
            name="metadata key",
        )

        if not isinstance(
            item,
            (
                str,
                int,
                float,
                bool,
                type(
                    None
                ),
            ),
        ):
            raise DiagnosticFeatureError(
                "diagnostic metadata values must be JSON scalar values"
            )

        if (
            isinstance(
                item,
                float,
            )
            and not math.isfinite(
                item
            )
        ):
            raise DiagnosticFeatureError(
                "diagnostic metadata float must be finite"
            )

        copied[
            key_text
        ] = item

    _canonical_json(
        copied
    )

    return MappingProxyType(
        copied
    )


@dataclass(
    frozen=True,
)
class DiagnosticFeature:
    name: str
    value: int | float
    unit: str
    source_field: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "name",
            _nonempty_text(
                self.name,
                name="feature name",
            ),
        )

        object.__setattr__(
            self,
            "unit",
            _nonempty_text(
                self.unit,
                name="feature unit",
            ),
        )

        object.__setattr__(
            self,
            "source_field",
            _nonempty_text(
                self.source_field,
                name="feature source_field",
            ),
        )

        if isinstance(
            self.value,
            bool,
        ):
            raise DiagnosticFeatureError(
                "boolean is not a numeric diagnostic feature value"
            )

        if not isinstance(
            self.value,
            (
                int,
                float,
            ),
        ):
            raise DiagnosticFeatureError(
                "diagnostic feature value must be int or float"
            )

        if (
            isinstance(
                self.value,
                float,
            )
            and not math.isfinite(
                self.value
            )
        ):
            raise DiagnosticFeatureError(
                "diagnostic feature value must be finite"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "name":
                self.name,

            "value":
                self.value,

            "unit":
                self.unit,

            "source_field":
                self.source_field,
        }


@dataclass(
    frozen=True,
)
class DiagnosticFeatureRecord:
    modality: str
    source_id: str
    extractor_id: str
    features: tuple[DiagnosticFeature, ...]
    metadata: Mapping[str, Any]

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "modality",
            _nonempty_text(
                self.modality,
                name="modality",
            ),
        )

        object.__setattr__(
            self,
            "source_id",
            _nonempty_text(
                self.source_id,
                name="source_id",
            ),
        )

        object.__setattr__(
            self,
            "extractor_id",
            _nonempty_text(
                self.extractor_id,
                name="extractor_id",
            ),
        )

        features = tuple(
            self.features
        )

        if not features:
            raise DiagnosticFeatureError(
                "diagnostic feature record cannot be empty"
            )

        names = tuple(
            feature.name
            for feature
            in features
        )

        if len(
            names
        ) != len(
            set(
                names
            )
        ):
            raise DiagnosticFeatureError(
                "diagnostic feature names must be unique"
            )

        object.__setattr__(
            self,
            "features",
            features,
        )

        object.__setattr__(
            self,
            "metadata",
            _immutable_scalar_mapping(
                self.metadata
            ),
        )

    @property
    def feature_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            feature.name
            for feature
            in self.features
        )

    @property
    def numeric_values(
        self,
    ) -> tuple[float, ...]:
        return tuple(
            float(
                feature.value
            )
            for feature
            in self.features
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema":
                DIAGNOSTIC_FEATURE_SCHEMA,

            "modality":
                self.modality,

            "source_id":
                self.source_id,

            "extractor_id":
                self.extractor_id,

            "features": [
                feature.to_dict()
                for feature
                in self.features
            ],

            "metadata":
                dict(
                    self.metadata
                ),

            "provenance": {
                "source_contract":
                    (
                        "trust_robot.lidar_frontend."
                        "LidarRegistrationDiagnostics"
                    ),

                "frozen_lidar_frontend_sha256":
                    FROZEN_LIDAR_FRONTEND_SHA256,

                "transformation":
                    "identity_direct_field_extraction",
            },

            "scientific_scope": {
                "normalization_applied":
                    False,

                "window_aggregation_applied":
                    False,

                "threshold_applied":
                    False,

                "health_label_emitted":
                    False,

                "fault_label_emitted":
                    False,

                "reliability_score_emitted":
                    False,

                "accuracy_score_emitted":
                    False,

                "reference_data_used":
                    False,

                "confirmation_test_data_used":
                    False,

                "ate_computed":
                    False,

                "rpe_computed":
                    False,
            },
        }

    @property
    def fingerprint_sha256(
        self,
    ) -> str:
        return sha256(
            _canonical_json(
                self.to_dict()
            ).encode(
                "utf-8"
            )
        ).hexdigest()


def _require_exact_nonnegative_int(
    value,
    *,
    name,
    positive,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise DiagnosticFeatureError(
            f"{name} must be an exact integer"
        )

    minimum = (
        1
        if positive
        else 0
    )

    if value < minimum:
        comparator = (
            "positive"
            if positive
            else "nonnegative"
        )

        raise DiagnosticFeatureError(
            f"{name} must be {comparator}"
        )

    return value


def extract_lidar_registration_diagnostics(
    diagnostics: LidarRegistrationDiagnostics,
) -> DiagnosticFeatureRecord:
    """Extract threshold-free numeric features from frozen registration output.

    The extraction is deliberately identity-like: no normalization, temporal
    aggregation, thresholding, health inference, fault inference, or scoring
    is performed.
    """

    if not isinstance(
        diagnostics,
        LidarRegistrationDiagnostics,
    ):
        raise DiagnosticFeatureError(
            "expected LidarRegistrationDiagnostics"
        )

    source_point_count = _require_exact_nonnegative_int(
        diagnostics.source_point_count,
        name="source_point_count",
        positive=True,
    )

    target_point_count = _require_exact_nonnegative_int(
        diagnostics.target_point_count,
        name="target_point_count",
        positive=True,
    )

    fixed_point_iterations = _require_exact_nonnegative_int(
        diagnostics.fixed_point_iterations,
        name="fixed_point_iterations",
        positive=True,
    )

    final_correspondence_count = _require_exact_nonnegative_int(
        diagnostics.final_correspondence_count,
        name="final_correspondence_count",
        positive=True,
    )

    if (
        final_correspondence_count
        != source_point_count
    ):
        raise DiagnosticFeatureError(
            "frozen no-rejection registration requires one final "
            "correspondence per source point"
        )

    rmse = diagnostics.final_nearest_neighbor_rmse_m

    if (
        isinstance(
            rmse,
            bool,
        )
        or not isinstance(
            rmse,
            (
                int,
                float,
            ),
        )
    ):
        raise DiagnosticFeatureError(
            "final_nearest_neighbor_rmse_m must be numeric"
        )

    rmse = float(
        rmse
    )

    if (
        not math.isfinite(
            rmse
        )
        or rmse < 0.0
    ):
        raise DiagnosticFeatureError(
            "final_nearest_neighbor_rmse_m must be finite and nonnegative"
        )

    if (
        diagnostics.convergence_rule
        != EXPECTED_CONVERGENCE_RULE
    ):
        raise DiagnosticFeatureError(
            "unexpected frozen registration convergence rule"
        )

    if diagnostics.correspondence_rejection_used is not False:
        raise DiagnosticFeatureError(
            "frozen registration diagnostic unexpectedly reports "
            "correspondence rejection"
        )

    if diagnostics.voxel_downsampling_used is not False:
        raise DiagnosticFeatureError(
            "frozen registration diagnostic unexpectedly reports "
            "voxel downsampling"
        )

    features = (
        DiagnosticFeature(
            name=
                "source_point_count",

            value=
                source_point_count,

            unit=
                "count",

            source_field=
                "source_point_count",
        ),

        DiagnosticFeature(
            name=
                "target_point_count",

            value=
                target_point_count,

            unit=
                "count",

            source_field=
                "target_point_count",
        ),

        DiagnosticFeature(
            name=
                "fixed_point_iterations",

            value=
                fixed_point_iterations,

            unit=
                "count",

            source_field=
                "fixed_point_iterations",
        ),

        DiagnosticFeature(
            name=
                "final_correspondence_count",

            value=
                final_correspondence_count,

            unit=
                "count",

            source_field=
                "final_correspondence_count",
        ),

        DiagnosticFeature(
            name=
                "final_nearest_neighbor_rmse_m",

            value=
                rmse,

            unit=
                "m",

            source_field=
                "final_nearest_neighbor_rmse_m",
        ),
    )

    record = DiagnosticFeatureRecord(
        modality=
            "lidar",

        source_id=
            "phase2_lidar_registration",

        extractor_id=
            LIDAR_REGISTRATION_EXTRACTOR_ID,

        features=
            features,

        metadata={
            "convergence_rule":
                diagnostics.convergence_rule,

            "correspondence_rejection_used":
                diagnostics.correspondence_rejection_used,

            "voxel_downsampling_used":
                diagnostics.voxel_downsampling_used,
        },
    )

    if (
        record.feature_names
        != LIDAR_REGISTRATION_FEATURE_ORDER
    ):
        raise DiagnosticFeatureError(
            "LiDAR diagnostic feature order changed unexpectedly"
        )

    if (
        tuple(
            feature.unit
            for feature
            in record.features
        )
        != LIDAR_REGISTRATION_FEATURE_UNITS
    ):
        raise DiagnosticFeatureError(
            "LiDAR diagnostic feature units changed unexpectedly"
        )

    return record


def build_diagnostic_feature_manifest(
    records: Iterable[DiagnosticFeatureRecord],
) -> dict[str, object]:
    record_tuple = tuple(
        records
    )

    if not record_tuple:
        raise DiagnosticFeatureError(
            "diagnostic manifest requires at least one record"
        )

    payload: dict[str, object] = {
        "schema":
            DIAGNOSTIC_MANIFEST_SCHEMA,

        "record_count":
            len(
                record_tuple
            ),

        "record_fingerprints_sha256": [
            record.fingerprint_sha256
            for record
            in record_tuple
        ],

        "records": [
            record.to_dict()
            for record
            in record_tuple
        ],

        "scientific_scope": {
            "diagnostic_feature_extraction_only":
                True,

            "threshold_applied":
                False,

            "health_label_emitted":
                False,

            "fault_label_emitted":
                False,

            "reliability_score_emitted":
                False,

            "accuracy_score_emitted":
                False,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "estimator_scoring_performed":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = sha256(
        _canonical_json(
            payload
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return payload
