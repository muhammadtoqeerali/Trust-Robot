from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json
import re


SCHEMA = "TRUST_ROBOT_M2DGR_LIDAR_IMU_SYNCHRONIZATION_EVIDENCE_V1"
SCHEMA_VERSION = 1

STAGING_SCHEMA = (
    "trust_robot.m2dgr_phase3d_lidar_imu_synchronization_evidence"
)
STAGING_VERSION = 1

LIDAR_SYNC_STREAM_IDS = (
    "/velodyne_points",
)

EXPECTED_SOURCE_KEYS = {
    "lidar_point_time_mechanism",
    "lidar_imu_zero_lag_pilot",
    "lidar_imu_lag_pilot",
    "lidar_imu_zero_lag_full_cohort",
}

EXPECTED_PILOT_IDS = (
    "gate_01",
    "hall_01",
    "room_01",
)

EXPECTED_BLOCKERS = {
    "released_bags_do_not_retain_raw_velodyne_packets",
    "exact_m2dgr_velodyne_driver_revision_not_identified",
    "exact_m2dgr_velodyne_runtime_configuration_not_identified",
    "pointcloud_header_physical_reference_event_not_independently_verified",
    "header_plus_point_time_not_independently_verified_as_physical_firing_time",
    "whole_scan_registration_effective_time_confounds_lag_interpretation",
    "handsfree_to_lidar_calibration_not_independently_verified",
    "unique_lidar_to_imu_fixed_offset_not_identified",
    "no_validation_calibration_split_for_data_selected_sync_tolerance",
}

EXPECTED_STAGING_POLICY = {
    "fixed_offset_estimated": False,
    "fixed_offset_applied": False,
    "synchronization_tolerance_frozen": False,
    "lidar_to_imu_physical_capture_sync_verified": False,
    "synchronization_verified": False,
    "evaluation_ready": False,
}

EXPECTED_POLICY = {
    "characterization_only": True,
    "raw_data_modified": False,
    "phase3c_manifest_modified": False,
    "successor_stream_metadata_modified": False,
    "successor_clock_domains_modified": False,
    "successor_non_lidar_synchronization_modified": False,
    "automatic_sample_exclusion_rule_created": False,
    "alignment_based_exclusion_rule_created": False,
    "fixed_offset_estimated": False,
    "fixed_offset_applied": False,
    "synchronization_tolerance_frozen": False,
    "physical_capture_synchronization_verified": False,
    "synchronization_verified": False,
    "evaluation_ready": False,
}

HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


class M2DGRLiDARIMUSynchronizationEvidenceError(
    ValueError
):
    pass


def _mapping(
    value: object,
    label: str,
) -> dict:
    if not isinstance(
        value,
        dict,
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} must be a mapping"
        )

    return value


def _exact_keys(
    payload: dict,
    expected: set[str],
    label: str,
) -> None:
    actual = set(
        payload
    )

    if actual != expected:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} keys mismatch: "
            f"missing={sorted(expected - actual)!r}, "
            f"extra={sorted(actual - expected)!r}"
        )


def _sha(
    value: object,
    label: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not HEX64.fullmatch(
            value
        )
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} must be a lowercase SHA256 digest"
        )

    return value


def _relative_path(
    value: object,
    label: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
        or Path(
            value
        ).is_absolute()
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} must be a non-empty relative path"
        )

    return value


def _number(
    value: object,
    label: str,
) -> float:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (
                int,
                float,
            ),
        )
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} must be numeric"
        )

    number = float(
        value
    )

    if not (
        number == number
        and abs(
            number
        ) != float(
            "inf"
        )
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} must be finite"
        )

    return number


def _content_sha256(
    payload: Mapping[str, object],
) -> str:
    unhashed = deepcopy(
        dict(
            payload
        )
    )

    unhashed.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
    ).encode(
        "utf-8"
    )

    return sha256(
        raw
    ).hexdigest()


def _file_sha256(
    path: Path,
) -> str:
    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                block
            )

    return digest.hexdigest()


def phase3d_lidar_imu_staging_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload
    )


def lidar_imu_evidence_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(
        payload
    )


def _validate_summary(
    value: object,
    label: str,
    *,
    correlation: bool = False,
    nonnegative: bool = False,
) -> None:
    payload = _mapping(
        value,
        label,
    )

    _exact_keys(
        payload,
        {
            "count",
            "min",
            "median",
            "max",
        },
        label,
    )

    count = payload[
        "count"
    ]

    if (
        not isinstance(
            count,
            int,
        )
        or count <= 0
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label}.count must be positive"
        )

    values = [
        _number(
            payload[
                key
            ],
            f"{label}.{key}",
        )
        for key in (
            "min",
            "median",
            "max",
        )
    ]

    if values != sorted(
        values
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} values must be ordered"
        )

    if (
        correlation
        and (
            values[
                0
            ] < -1.0
            or values[
                -1
            ] > 1.0
        )
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} must lie in [-1, 1]"
        )

    if (
        nonnegative
        and values[
            0
        ] < 0.0
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            f"{label} must be non-negative"
        )


def _validate_core_observations(
    mechanism: object,
    zero_lag: object,
    lag: object,
    interpretation: object,
    blockers: object,
) -> None:
    mechanism = _mapping(
        mechanism,
        "mechanism_evidence",
    )

    expected_mechanism = {
        "sensor_model":
            "Velodyne VLP-32C",

        "released_pointcloud_topic":
            "/velodyne_points",

        "released_raw_velodyne_packets_present":
            False,

        "released_payload_strongly_matches_vlp32c_timing_table":
            True,

        "released_payload_strongly_consistent_with_last_packet_referenced_relative_point_time":
            True,

        "last_packet_reference_independently_verified":
            False,

        "header_plus_point_time_independently_verified_as_physical_firing_time":
            False,

        "exact_m2dgr_velodyne_driver_revision_identified":
            False,

        "exact_m2dgr_velodyne_runtime_configuration_identified":
            False,
    }

    if mechanism != expected_mechanism:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected LiDAR mechanism evidence"
        )

    zero_lag = _mapping(
        zero_lag,
        "zero_lag_full_cohort",
    )

    exact_zero_values = {
        "trajectory_count":
            36,

        "candidate_pair_count":
            10764,

        "admitted_pair_count":
            10758,

        "unsupported_pair_count":
            6,

        "unsupported_leading_pair_count":
            6,

        "unsupported_trailing_pair_count":
            0,

        "unsupported_internal_pair_count":
            0,

        "failed_pair_count":
            0,

        "all_primary_vector_correlations_positive":
            True,

        "all_raw_icp_vector_correlations_negative":
            True,

        "quality_threshold_for_pair_admission":
            None,

        "metric_based_pair_exclusion":
            False,

        "imu_extrapolation_used":
            False,

        "point_time_used":
            False,

        "deskewing_used":
            False,
    }

    for key, expected in (
        exact_zero_values.items()
    ):
        if zero_lag.get(
            key
        ) != expected:
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                f"unexpected full-cohort value for {key}"
            )

    unsupported = _mapping(
        zero_lag.get(
            "unsupported_trajectories"
        ),
        "unsupported_trajectories",
    )

    if (
        sum(
            len(
                value
            )
            for value
            in unsupported.values()
        )
        != 6
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected unsupported-pair inventory"
        )

    for key in (
        "vector_correlation",
        "rotation_angle_correlation",
        "z_component_correlation",
        "raw_icp_vector_correlation",
    ):
        _validate_summary(
            zero_lag.get(
                key
            ),
            key,
            correlation=True,
        )

    for key in (
        "median_rotation_error_deg",
        "p95_rotation_error_deg",
    ):
        _validate_summary(
            zero_lag.get(
                key
            ),
            key,
            nonnegative=True,
        )

    lag = _mapping(
        lag,
        "lag_characterization",
    )

    if tuple(
        lag.get(
            "trajectory_ids",
            (),
        )
    ) != EXPECTED_PILOT_IDS:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected LiDAR/IMU lag-pilot trajectory set"
        )

    if lag.get(
        "lag_grid_ms"
    ) != {
        "min":
            -101,

        "max":
            101,

        "step":
            1,
    }:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected LiDAR/IMU lag grid"
        )

    expected_lag_flags = {
        "grid_expanded_after_results":
            False,

        "same_pair_support_every_lag":
            True,

        "frontend_changed":
            False,

        "deskewing_used":
            False,

        "exact_common_primary_best_lag_exists":
            False,

        "common_nonzero_fixed_offset_supported":
            False,

        "objectives_identify_unique_common_offset":
            False,

        "scan_expansion_scientifically_justified":
            False,

        "whole_scan_registration_confounds_clock_offset_interpretation":
            True,
    }

    for key, expected in (
        expected_lag_flags.items()
    ):
        if lag.get(
            key
        ) != expected:
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                f"unexpected lag characterization for {key}"
            )

    per_trajectory = _mapping(
        lag.get(
            "per_trajectory"
        ),
        "lag_characterization.per_trajectory",
    )

    if set(
        per_trajectory
    ) != set(
        EXPECTED_PILOT_IDS
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "lag-pilot trajectory inventory mismatch"
        )

    for trajectory_id, row in (
        per_trajectory.items()
    ):
        row = _mapping(
            row,
            f"lag result {trajectory_id}",
        )

        for key in (
            "best_vector_lags_ms",
            "best_angle_lags_ms",
            "minimum_error_lags_ms",
        ):
            values = row.get(
                key
            )

            if (
                not isinstance(
                    values,
                    list,
                )
                or not values
                or any(
                    not isinstance(
                        item,
                        int,
                    )
                    for item
                    in values
                )
            ):
                raise M2DGRLiDARIMUSynchronizationEvidenceError(
                    f"{trajectory_id}/{key} must be a non-empty integer list"
                )

        if _number(
            row.get(
                "best_minus_zero_vector_correlation"
            ),
            f"{trajectory_id}/vector gain",
        ) < 0.0:
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                "vector-correlation gain must be non-negative"
            )

        if _number(
            row.get(
                "zero_minus_best_median_error_deg"
            ),
            f"{trajectory_id}/error gain",
        ) < 0.0:
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                "rotation-error improvement must be non-negative"
            )

    interpretation = _mapping(
        interpretation,
        "interpretation",
    )

    expected_interpretation = {
        "zero_header_lag_rotational_content_consistency_generalizes_across_full_cohort":
            True,

        "primary_lidar_body_rotation_convention_supported_over_raw_icp_convention":
            True,

        "full_cohort_results_create_timing_validity_threshold":
            False,

        "lower_correlation_trajectories_are_automatically_invalid":
            False,

        "lag_pilot_identifies_unique_sensor_clock_offset":
            False,

        "common_nonzero_lidar_imu_fixed_offset_supported":
            False,

        "released_data_independently_verify_lidar_point_physical_capture_time":
            False,

        "released_data_independently_verify_lidar_to_imu_physical_capture_synchronization":
            False,
    }

    if interpretation != expected_interpretation:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected Phase-3D interpretation"
        )

    if (
        not isinstance(
            blockers,
            list,
        )
        or set(
            blockers
        )
        != EXPECTED_BLOCKERS
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected Phase-3D blocker set"
        )


def validate_phase3d_lidar_imu_staging_evidence(
    payload: dict,
) -> None:
    payload = _mapping(
        payload,
        "Phase-3D staging evidence",
    )

    _exact_keys(
        payload,
        {
            "schema",
            "version",
            "dataset_id",
            "source_artifacts",
            "mechanism_evidence",
            "zero_lag_full_cohort",
            "lag_characterization",
            "interpretation",
            "remaining_blockers",
            "policy",
            "content_sha256",
        },
        "Phase-3D staging evidence",
    )

    if (
        payload[
            "schema"
        ] != STAGING_SCHEMA
        or payload[
            "version"
        ] != STAGING_VERSION
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected Phase-3D staging schema/version"
        )

    if payload[
        "dataset_id"
    ] != "M2DGR":
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "Phase-3D evidence must describe M2DGR"
        )

    if (
        _sha(
            payload[
                "content_sha256"
            ],
            "content_sha256",
        )
        != phase3d_lidar_imu_staging_content_sha256(
            payload
        )
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "Phase-3D staging content digest mismatch"
        )

    sources = _mapping(
        payload[
            "source_artifacts"
        ],
        "source_artifacts",
    )

    if set(
        sources
    ) != EXPECTED_SOURCE_KEYS:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected Phase-3D source-artifact set"
        )

    for key, row in (
        sources.items()
    ):
        row = _mapping(
            row,
            f"source_artifacts.{key}",
        )

        _exact_keys(
            row,
            {
                "relative_path",
                "content_sha256",
                "file_sha256",
                "size_bytes",
            },
            f"source_artifacts.{key}",
        )

        _relative_path(
            row[
                "relative_path"
            ],
            f"source_artifacts.{key}.relative_path",
        )

        _sha(
            row[
                "content_sha256"
            ],
            f"source_artifacts.{key}.content_sha256",
        )

        _sha(
            row[
                "file_sha256"
            ],
            f"source_artifacts.{key}.file_sha256",
        )

        if (
            not isinstance(
                row[
                    "size_bytes"
                ],
                int,
            )
            or row[
                "size_bytes"
            ] <= 0
        ):
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                f"source_artifacts.{key}.size_bytes must be positive"
            )

    _validate_core_observations(
        payload[
            "mechanism_evidence"
        ],
        payload[
            "zero_lag_full_cohort"
        ],
        payload[
            "lag_characterization"
        ],
        payload[
            "interpretation"
        ],
        payload[
            "remaining_blockers"
        ],
    )

    if payload[
        "policy"
    ] != EXPECTED_STAGING_POLICY:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected Phase-3D staging policy"
        )


def verify_phase3d_lidar_imu_staging_sources(
    dataset_root: str | Path,
    staging_evidence: dict,
) -> None:
    validate_phase3d_lidar_imu_staging_evidence(
        staging_evidence
    )

    dataset_root = Path(
        dataset_root
    )

    for key, source in (
        staging_evidence[
            "source_artifacts"
        ].items()
    ):
        path = (
            dataset_root
            / source[
                "relative_path"
            ]
        )

        if not path.is_file():
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                f"missing Phase-3D source artifact {key!r}: {path}"
            )

        if (
            _file_sha256(
                path
            )
            != source[
                "file_sha256"
            ]
        ):
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                f"Phase-3D source file hash mismatch for {key!r}"
            )

        try:
            source_payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception as exc:
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                f"could not parse Phase-3D source artifact {key!r}"
            ) from exc

        if (
            _content_sha256(
                source_payload
            )
            != source[
                "content_sha256"
            ]
        ):
            raise M2DGRLiDARIMUSynchronizationEvidenceError(
                f"Phase-3D source content hash mismatch for {key!r}"
            )


def build_m2dgr_lidar_imu_synchronization_evidence(
    phase3c_manifest: dict,
    staging_evidence: dict,
    *,
    staging_relative_path: str,
    staging_file_sha256: str,
    staging_size_bytes: int,
) -> dict:
    validate_phase3d_lidar_imu_staging_evidence(
        staging_evidence
    )

    if phase3c_manifest.get(
        "dataset_id"
    ) != "M2DGR":
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "Phase-3D evidence requires an M2DGR manifest"
        )

    source_manifest_sha = _sha(
        phase3c_manifest.get(
            "manifest_content_sha256"
        ),
        "Phase-3C manifest content SHA256",
    )

    _relative_path(
        staging_relative_path,
        "staging_relative_path",
    )

    _sha(
        staging_file_sha256,
        "staging_file_sha256",
    )

    if (
        not isinstance(
            staging_size_bytes,
            int,
        )
        or staging_size_bytes <= 0
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "staging_size_bytes must be positive"
        )

    payload = {
        "schema":
            SCHEMA,

        "schema_version":
            SCHEMA_VERSION,

        "dataset_id":
            "M2DGR",

        "staging_source": {
            "relative_path":
                staging_relative_path,

            "file_sha256":
                staging_file_sha256,

            "content_sha256":
                staging_evidence[
                    "content_sha256"
                ],

            "size_bytes":
                staging_size_bytes,
        },

        "observations": {
            "mechanism_evidence":
                deepcopy(
                    staging_evidence[
                        "mechanism_evidence"
                    ]
                ),

            "zero_lag_full_cohort":
                deepcopy(
                    staging_evidence[
                        "zero_lag_full_cohort"
                    ]
                ),

            "lag_characterization":
                deepcopy(
                    staging_evidence[
                        "lag_characterization"
                    ]
                ),

            "interpretation":
                deepcopy(
                    staging_evidence[
                        "interpretation"
                    ]
                ),
        },

        "manifest_semantics": {
            "phase3c_source_manifest_content_sha256":
                source_manifest_sha,

            "lidar_sync_stream_ids":
                list(
                    LIDAR_SYNC_STREAM_IDS
                ),

            "phase3c_clock_domains_preserved":
                True,

            "only_lidar_sync_method_updates_allowed":
                True,
        },

        "remaining_blockers":
            list(
                staging_evidence[
                    "remaining_blockers"
                ]
            ),

        "policy":
            dict(
                EXPECTED_POLICY
            ),
    }

    payload[
        "content_sha256"
    ] = lidar_imu_evidence_content_sha256(
        payload
    )

    validate_m2dgr_lidar_imu_synchronization_evidence(
        payload
    )

    return payload


def validate_m2dgr_lidar_imu_synchronization_evidence(
    payload: dict,
) -> None:
    payload = _mapping(
        payload,
        "LiDAR/IMU synchronization evidence",
    )

    _exact_keys(
        payload,
        {
            "schema",
            "schema_version",
            "dataset_id",
            "staging_source",
            "observations",
            "manifest_semantics",
            "remaining_blockers",
            "policy",
            "content_sha256",
        },
        "LiDAR/IMU synchronization evidence",
    )

    if (
        payload[
            "schema"
        ] != SCHEMA
        or payload[
            "schema_version"
        ] != SCHEMA_VERSION
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected LiDAR/IMU evidence schema/version"
        )

    if payload[
        "dataset_id"
    ] != "M2DGR":
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "LiDAR/IMU evidence must describe M2DGR"
        )

    if (
        _sha(
            payload[
                "content_sha256"
            ],
            "content_sha256",
        )
        != lidar_imu_evidence_content_sha256(
            payload
        )
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "LiDAR/IMU evidence content digest mismatch"
        )

    source = _mapping(
        payload[
            "staging_source"
        ],
        "staging_source",
    )

    _exact_keys(
        source,
        {
            "relative_path",
            "file_sha256",
            "content_sha256",
            "size_bytes",
        },
        "staging_source",
    )

    _relative_path(
        source[
            "relative_path"
        ],
        "staging_source.relative_path",
    )

    _sha(
        source[
            "file_sha256"
        ],
        "staging_source.file_sha256",
    )

    _sha(
        source[
            "content_sha256"
        ],
        "staging_source.content_sha256",
    )

    if (
        not isinstance(
            source[
                "size_bytes"
            ],
            int,
        )
        or source[
            "size_bytes"
        ] <= 0
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "staging source size must be positive"
        )

    observations = _mapping(
        payload[
            "observations"
        ],
        "observations",
    )

    _exact_keys(
        observations,
        {
            "mechanism_evidence",
            "zero_lag_full_cohort",
            "lag_characterization",
            "interpretation",
        },
        "observations",
    )

    _validate_core_observations(
        observations[
            "mechanism_evidence"
        ],
        observations[
            "zero_lag_full_cohort"
        ],
        observations[
            "lag_characterization"
        ],
        observations[
            "interpretation"
        ],
        payload[
            "remaining_blockers"
        ],
    )

    semantics = _mapping(
        payload[
            "manifest_semantics"
        ],
        "manifest_semantics",
    )

    _exact_keys(
        semantics,
        {
            "phase3c_source_manifest_content_sha256",
            "lidar_sync_stream_ids",
            "phase3c_clock_domains_preserved",
            "only_lidar_sync_method_updates_allowed",
        },
        "manifest_semantics",
    )

    _sha(
        semantics[
            "phase3c_source_manifest_content_sha256"
        ],
        "phase3c_source_manifest_content_sha256",
    )

    if tuple(
        semantics[
            "lidar_sync_stream_ids"
        ]
    ) != LIDAR_SYNC_STREAM_IDS:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected Phase-3D LiDAR stream set"
        )

    if (
        semantics[
            "phase3c_clock_domains_preserved"
        ] is not True
        or semantics[
            "only_lidar_sync_method_updates_allowed"
        ] is not True
    ):
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected Phase-3D manifest semantics"
        )

    if payload[
        "policy"
    ] != EXPECTED_POLICY:
        raise M2DGRLiDARIMUSynchronizationEvidenceError(
            "unexpected permanent Phase-3D policy"
        )


def load_phase3d_lidar_imu_staging_evidence(
    path: str | Path,
) -> dict:
    path = Path(
        path
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    validate_phase3d_lidar_imu_staging_evidence(
        payload
    )

    return payload
