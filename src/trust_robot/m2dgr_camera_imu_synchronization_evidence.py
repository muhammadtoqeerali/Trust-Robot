from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json
import re


SCHEMA = "TRUST_ROBOT_M2DGR_CAMERA_IMU_SYNCHRONIZATION_EVIDENCE_V1"
SCHEMA_VERSION = 1

STAGING_SCHEMA = (
    "trust_robot.m2dgr_phase3c_camera_imu_synchronization_evidence"
)
STAGING_VERSION = 1

CAMERA_IMU_STREAM_IDS = (
    "/camera/color/image_raw/compressed",
    "/camera/imu",
)

EXPECTED_SOURCE_KEYS = {
    "accel_affine_fingerprint_pilot",
    "camera_connection_inventory",
    "united_imu_fingerprint_pilot",
    "visual_gyro_lag_pilot",
    "visual_gyro_zero_lag_clean_cohort",
    "visual_gyro_zero_lag_pilot",
}

EXPECTED_PILOT_IDS = (
    "gate_01",
    "hall_01",
    "room_01",
)

EXPECTED_BEST_LAGS_MS = {
    "gate_01": [23],
    "hall_01": [-67],
    "room_01": [-3],
}

EXPECTED_BOUNDARY_FLAGS = {
    "gate_01": False,
    "hall_01": True,
    "room_01": False,
}

EXPECTED_DARK_IDS = {
    "room_dark_04",
    "room_dark_05",
    "room_dark_06",
}

EXPECTED_BLOCKERS = {
    "rgb_image_header_physical_capture_event_not_independently_verified",
    "released_bags_do_not_retain_realsense_frame_metadata",
    "exact_realsense_driver_revision_and_runtime_configuration_not_identified",
    "camera_calibration_not_independently_verified",
    "visual_content_association_is_heterogeneous_across_trajectories",
    "unique_camera_to_imu_fixed_offset_not_identified",
    "no_validation_calibration_split_for_data_selected_sync_tolerance",
}

EXPECTED_STAGING_POLICY = {
    "camera_image_to_imu_physical_capture_sync_verified": False,
    "unique_fixed_camera_imu_offset_supported": False,
    "fixed_offset_estimated": False,
    "synchronization_tolerance_frozen": False,
    "lag_grid_is_synchronization_tolerance": False,
    "visual_frontend_success_is_validity_mask": False,
    "visual_frontend_failure_is_evaluation_exclusion": False,
    "camera_calibration_independently_verified": False,
    "realsense_driver_revision_identified": False,
    "image_header_physical_capture_event_independently_verified": False,
    "synchronization_verified": False,
    "evaluation_ready": False,
}

EXPECTED_POLICY = {
    "characterization_only": True,
    "raw_data_modified": False,
    "phase3b_manifest_modified": False,
    "successor_stream_metadata_modified": False,
    "successor_clock_domains_modified": False,
    "successor_non_camera_synchronization_modified": False,
    "automatic_sample_exclusion_rule_created": False,
    "alignment_based_exclusion_rule_created": False,
    "fixed_offset_estimated": False,
    "fixed_offset_applied": False,
    "synchronization_tolerance_frozen": False,
    "physical_capture_synchronization_verified": False,
    "synchronization_verified": False,
    "evaluation_ready": False,
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")


class M2DGRCameraIMUSynchronizationEvidenceError(ValueError):
    pass


def _mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} must be a mapping"
        )
    return value


def _exact_keys(
    payload: dict,
    expected: set[str],
    label: str,
) -> None:
    actual = set(payload)

    if actual != expected:
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} keys mismatch: "
            f"missing={sorted(expected - actual)!r}, "
            f"extra={sorted(actual - expected)!r}"
        )


def _sha(
    value: object,
    label: str,
) -> str:
    if (
        not isinstance(value, str)
        or not HEX64.fullmatch(value)
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} must be a lowercase SHA256 digest"
        )

    return value


def _relative_path(
    value: object,
    label: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or Path(value).is_absolute()
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} must be a non-empty relative path"
        )

    return value


def _number(
    value: object,
    label: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (
                int,
                float,
            ),
        )
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} must be numeric"
        )

    number = float(value)

    if not (
        number == number
        and abs(number) != float("inf")
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} must be finite"
        )

    return number


def _content_sha256(
    payload: Mapping[str, object],
) -> str:
    unhashed = deepcopy(
        dict(payload)
    )

    unhashed.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256(raw).hexdigest()


def phase3c_staging_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(payload)


def camera_imu_evidence_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return _content_sha256(payload)


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
            "p25",
            "median",
            "p75",
            "max",
        },
        label,
    )

    if (
        not isinstance(
            payload["count"],
            int,
        )
        or payload["count"] <= 0
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label}.count must be positive"
        )

    values = [
        _number(
            payload[key],
            f"{label}.{key}",
        )
        for key in (
            "min",
            "p25",
            "median",
            "p75",
            "max",
        )
    ]

    if values != sorted(values):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} quantiles must be ordered"
        )

    if (
        correlation
        and (
            values[0] < -1.0
            or values[-1] > 1.0
        )
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} must lie in [-1, 1]"
        )

    if (
        nonnegative
        and values[0] < 0.0
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"{label} must be non-negative"
        )


def validate_phase3c_camera_imu_staging_evidence(
    payload: dict,
) -> None:
    payload = _mapping(
        payload,
        "Phase-3C staging evidence",
    )

    _exact_keys(
        payload,
        {
            "schema",
            "version",
            "dataset_id",
            "source_artifacts",
            "released_topic_evidence",
            "united_imu_characterization",
            "zero_lag_visual_gyro_clean_cohort",
            "lag_pilot",
            "remaining_blockers",
            "conclusion",
            "policy",
            "content_sha256",
        },
        "Phase-3C staging evidence",
    )

    if (
        payload["schema"] != STAGING_SCHEMA
        or payload["version"] != STAGING_VERSION
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected Phase-3C staging schema/version"
        )

    if payload["dataset_id"] != "M2DGR":
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "Phase-3C evidence must describe M2DGR"
        )

    stored = _sha(
        payload["content_sha256"],
        "content_sha256",
    )

    if (
        stored
        != phase3c_staging_content_sha256(
            payload
        )
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "Phase-3C staging content digest mismatch"
        )

    sources = _mapping(
        payload["source_artifacts"],
        "source_artifacts",
    )

    if set(sources) != EXPECTED_SOURCE_KEYS:
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected Phase-3C source-artifact set"
        )

    for key, row in sources.items():
        row = _mapping(
            row,
            f"source_artifacts.{key}",
        )

        _exact_keys(
            row,
            {
                "relative_path",
                "file_sha256",
                "content_sha256",
            },
            f"source_artifacts.{key}",
        )

        _relative_path(
            row["relative_path"],
            f"source_artifacts.{key}.relative_path",
        )

        _sha(
            row["file_sha256"],
            f"source_artifacts.{key}.file_sha256",
        )

        _sha(
            row["content_sha256"],
            f"source_artifacts.{key}.content_sha256",
        )

    topics = payload[
        "released_topic_evidence"
    ]

    expected_topics = {
        "trajectory_count": 36,
        "camera_metadata_topics_present": False,
        "raw_camera_gyro_topics_present": False,
        "raw_camera_accel_topics_present": False,
        "camera_info_topics_present": False,
        "united_camera_imu_topic_present": True,
        "compressed_d435i_color_topic_present": True,
        "exact_driver_configuration_recoverable_from_bag_topics": False,
    }

    if topics != expected_topics:
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected released camera-topic evidence"
        )

    united = _mapping(
        payload[
            "united_imu_characterization"
        ],
        "united_imu_characterization",
    )

    if tuple(
        united[
            "pilot_trajectory_ids"
        ]
    ) != EXPECTED_PILOT_IDS:
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected united-IMU pilot trajectory set"
        )

    repeats = _mapping(
        united[
            "exact_consecutive_acceleration_repeat_count"
        ],
        "exact_consecutive_acceleration_repeat_count",
    )

    if (
        set(repeats)
        != set(EXPECTED_PILOT_IDS)
        or any(
            value != 0
            for value in repeats.values()
        )
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "copy-style acceleration hold unexpectedly observed"
        )

    if (
        united[
            "copy_style_sample_hold_supported"
        ] is not False
        or united[
            "linear_interpolation_or_other_processing_resolved"
        ] is not False
        or united[
            "affine_pilot_used_to_reject_linear_interpolation"
        ] is not False
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected united-IMU interpretation"
        )

    cohort = _mapping(
        payload[
            "zero_lag_visual_gyro_clean_cohort"
        ],
        "zero_lag_visual_gyro_clean_cohort",
    )

    if (
        cohort[
            "trajectory_count"
        ] != 28
        or cohort[
            "successful_trajectory_count"
        ] != 28
        or cohort[
            "failed_trajectory_count"
        ] != 0
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "expected 28/28 clean-cohort processing success"
        )

    if (
        cohort[
            "method_changed_after_pilot"
        ] is not False
        or cohort[
            "lag_search_performed"
        ] is not False
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "clean cohort must use the frozen zero-lag method"
        )

    _validate_summary(
        cohort[
            "visual_success_fraction"
        ],
        "visual_success_fraction",
        nonnegative=True,
    )

    _validate_summary(
        cohort[
            "usable_visual_imu_pair_count"
        ],
        "usable_visual_imu_pair_count",
        nonnegative=True,
    )

    _validate_summary(
        cohort[
            "vector_correlation"
        ],
        "vector_correlation",
        correlation=True,
    )

    _validate_summary(
        cohort[
            "rotation_angle_correlation"
        ],
        "rotation_angle_correlation",
        correlation=True,
    )

    _validate_summary(
        cohort[
            "median_rotation_error_deg"
        ],
        "median_rotation_error_deg",
        nonnegative=True,
    )

    dark = _mapping(
        cohort[
            "dark_room_frontend_success_counterexample"
        ],
        "dark_room_frontend_success_counterexample",
    )

    if set(dark) != EXPECTED_DARK_IDS:
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected dark-room counterexample set"
        )

    lag = _mapping(
        payload["lag_pilot"],
        "lag_pilot",
    )

    if tuple(
        lag[
            "trajectory_ids"
        ]
    ) != EXPECTED_PILOT_IDS:
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected lag-pilot trajectory set"
        )

    if (
        lag[
            "visual_method_changed_after_zero_lag_pilot"
        ] is not False
        or lag[
            "common_support_across_all_lags"
        ] is not True
        or lag[
            "lag_specific_sample_admission"
        ] is not False
        or lag[
            "lag_step_ms"
        ] != 1
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected lag-pilot method"
        )

    if (
        lag[
            "best_vector_correlation_lags_ms"
        ]
        != EXPECTED_BEST_LAGS_MS
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected lag-pilot best-lag observations"
        )

    if (
        lag[
            "primary_best_lag_hits_scan_boundary"
        ]
        != EXPECTED_BOUNDARY_FLAGS
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected lag-pilot boundary observations"
        )

    gains = _mapping(
        lag[
            "best_minus_zero_vector_correlation"
        ],
        "best_minus_zero_vector_correlation",
    )

    if set(gains) != set(
        EXPECTED_PILOT_IDS
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "lag gain trajectory set mismatch"
        )

    for key, value in gains.items():
        if _number(
            value,
            f"lag gain {key}",
        ) < 0.0:
            raise M2DGRCameraIMUSynchronizationEvidenceError(
                "lag gain must be non-negative"
            )

    if (
        lag[
            "common_nonzero_fixed_offset_supported"
        ] is not False
        or lag[
            "scan_expansion_scientifically_justified"
        ] is not False
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected lag-pilot conclusion"
        )

    if (
        set(
            payload[
                "remaining_blockers"
            ]
        )
        != EXPECTED_BLOCKERS
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected Phase-3C blocker set"
        )

    conclusion = _mapping(
        payload["conclusion"],
        "conclusion",
    )

    expected_conclusion = {
        "camera_and_d435i_imu_show_zero_lag_physical_content_consistency_on_many_trajectories":
            True,
        "consistency_is_uniform_across_clean_cohort":
            False,
        "released_data_identify_unique_camera_to_imu_fixed_offset":
            False,
        "released_data_independently_verify_rgb_physical_capture_synchronization":
            False,
    }

    for key, expected in (
        expected_conclusion.items()
    ):
        if conclusion.get(
            key
        ) is not expected:
            raise M2DGRCameraIMUSynchronizationEvidenceError(
                f"unexpected conclusion for {key}"
            )

    if (
        payload["policy"]
        != EXPECTED_STAGING_POLICY
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected Phase-3C staging policy"
        )


def build_m2dgr_camera_imu_synchronization_evidence(
    phase3b_manifest: dict,
    staging_evidence: dict,
    *,
    staging_relative_path: str,
    staging_file_sha256: str,
    staging_size_bytes: int,
) -> dict:
    validate_phase3c_camera_imu_staging_evidence(
        staging_evidence
    )

    if (
        phase3b_manifest.get(
            "dataset_id"
        )
        != "M2DGR"
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "Phase-3C evidence requires an M2DGR manifest"
        )

    source_manifest_sha = _sha(
        phase3b_manifest.get(
            "manifest_content_sha256"
        ),
        "Phase-3B manifest content SHA256",
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
        raise M2DGRCameraIMUSynchronizationEvidenceError(
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
            "released_topic_evidence":
                deepcopy(
                    staging_evidence[
                        "released_topic_evidence"
                    ]
                ),

            "united_imu_characterization":
                deepcopy(
                    staging_evidence[
                        "united_imu_characterization"
                    ]
                ),

            "zero_lag_visual_gyro_clean_cohort":
                deepcopy(
                    staging_evidence[
                        "zero_lag_visual_gyro_clean_cohort"
                    ]
                ),

            "lag_pilot":
                deepcopy(
                    staging_evidence[
                        "lag_pilot"
                    ]
                ),

            "conclusion":
                deepcopy(
                    staging_evidence[
                        "conclusion"
                    ]
                ),
        },

        "manifest_semantics": {
            "phase3b_source_manifest_content_sha256":
                source_manifest_sha,

            "camera_imu_sync_stream_ids":
                list(
                    CAMERA_IMU_STREAM_IDS
                ),

            "phase3b_clock_domains_preserved":
                True,

            "only_camera_imu_sync_method_updates_allowed":
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
    ] = (
        camera_imu_evidence_content_sha256(
            payload
        )
    )

    validate_m2dgr_camera_imu_synchronization_evidence(
        payload
    )

    return payload


def validate_m2dgr_camera_imu_synchronization_evidence(
    payload: dict,
) -> None:
    payload = _mapping(
        payload,
        "camera/IMU synchronization evidence",
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
        "camera/IMU synchronization evidence",
    )

    if (
        payload["schema"] != SCHEMA
        or payload[
            "schema_version"
        ] != SCHEMA_VERSION
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected camera/IMU evidence schema/version"
        )

    if payload[
        "dataset_id"
    ] != "M2DGR":
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "camera/IMU evidence must describe M2DGR"
        )

    if (
        _sha(
            payload[
                "content_sha256"
            ],
            "content_sha256",
        )
        != camera_imu_evidence_content_sha256(
            payload
        )
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "camera/IMU evidence content digest mismatch"
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
        raise M2DGRCameraIMUSynchronizationEvidenceError(
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
            "released_topic_evidence",
            "united_imu_characterization",
            "zero_lag_visual_gyro_clean_cohort",
            "lag_pilot",
            "conclusion",
        },
        "observations",
    )

    synthetic_staging = {
        "schema":
            STAGING_SCHEMA,

        "version":
            STAGING_VERSION,

        "dataset_id":
            "M2DGR",

        "source_artifacts": {
            key: {
                "relative_path":
                    f"audit/{key}.json",
                "file_sha256":
                    "1" * 64,
                "content_sha256":
                    "2" * 64,
            }
            for key in sorted(
                EXPECTED_SOURCE_KEYS
            )
        },

        **deepcopy(
            observations
        ),

        "remaining_blockers":
            list(
                payload[
                    "remaining_blockers"
                ]
            ),

        "policy":
            dict(
                EXPECTED_STAGING_POLICY
            ),
    }

    synthetic_staging[
        "content_sha256"
    ] = phase3c_staging_content_sha256(
        synthetic_staging
    )

    validate_phase3c_camera_imu_staging_evidence(
        synthetic_staging
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
            "phase3b_source_manifest_content_sha256",
            "camera_imu_sync_stream_ids",
            "phase3b_clock_domains_preserved",
            "only_camera_imu_sync_method_updates_allowed",
        },
        "manifest_semantics",
    )

    _sha(
        semantics[
            "phase3b_source_manifest_content_sha256"
        ],
        "phase3b_source_manifest_content_sha256",
    )

    if tuple(
        semantics[
            "camera_imu_sync_stream_ids"
        ]
    ) != CAMERA_IMU_STREAM_IDS:
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected Phase-3C camera/IMU stream set"
        )

    if (
        semantics[
            "phase3b_clock_domains_preserved"
        ] is not True
        or semantics[
            "only_camera_imu_sync_method_updates_allowed"
        ] is not True
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected Phase-3C manifest semantics"
        )

    if (
        payload[
            "policy"
        ]
        != EXPECTED_POLICY
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "unexpected permanent Phase-3C policy"
        )


def verify_phase3c_camera_imu_staging_sources(
    dataset_root: str | Path,
    staging_evidence: dict,
) -> None:
    validate_phase3c_camera_imu_staging_evidence(
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
            raise M2DGRCameraIMUSynchronizationEvidenceError(
                f"missing Phase-3C source artifact "
                f"{key!r}: {path}"
            )

        if (
            _file_sha256(
                path
            )
            != source[
                "file_sha256"
            ]
        ):
            raise M2DGRCameraIMUSynchronizationEvidenceError(
                f"Phase-3C source artifact file hash "
                f"mismatch for {key!r}"
            )

        try:
            source_payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception as exc:
            raise M2DGRCameraIMUSynchronizationEvidenceError(
                f"could not parse Phase-3C source artifact "
                f"{key!r}: {path}"
            ) from exc

        calculated_content_sha = (
            _content_sha256(
                source_payload
            )
        )

        embedded_content_sha = (
            source_payload.get(
                "content_sha256"
            )
        )

        if (
            embedded_content_sha
            is not None
            and embedded_content_sha
            != calculated_content_sha
        ):
            raise M2DGRCameraIMUSynchronizationEvidenceError(
                f"Phase-3C source artifact embedded digest "
                f"mismatch for {key!r}"
            )

        if (
            calculated_content_sha
            != source[
                "content_sha256"
            ]
        ):
            raise M2DGRCameraIMUSynchronizationEvidenceError(
                f"Phase-3C source artifact content hash "
                f"mismatch for {key!r}"
            )



def load_phase3c_camera_imu_staging_evidence(
    path: str | Path,
) -> dict:
    payload = json.loads(
        Path(path).read_text(
            encoding="utf-8"
        )
    )

    validate_phase3c_camera_imu_staging_evidence(
        payload
    )

    return payload


def load_m2dgr_camera_imu_synchronization_evidence(
    path: str | Path,
) -> dict:
    payload = json.loads(
        Path(path).read_text(
            encoding="utf-8"
        )
    )

    validate_m2dgr_camera_imu_synchronization_evidence(
        payload
    )

    return payload


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
            digest.update(block)

    return digest.hexdigest()


def verify_camera_imu_synchronization_evidence_source(
    dataset_root: str | Path,
    evidence: dict,
) -> None:
    validate_m2dgr_camera_imu_synchronization_evidence(
        evidence
    )

    dataset_root = Path(
        dataset_root
    )

    source = evidence[
        "staging_source"
    ]

    path = (
        dataset_root
        / source[
            "relative_path"
        ]
    )

    if not path.is_file():
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            f"missing Phase-3C staging source: {path}"
        )

    if (
        path.stat().st_size
        != source[
            "size_bytes"
        ]
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "Phase-3C staging source size mismatch"
        )

    if (
        _file_sha256(path)
        != source[
            "file_sha256"
        ]
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "Phase-3C staging source file hash mismatch"
        )

    staging = (
        load_phase3c_camera_imu_staging_evidence(
            path
        )
    )

    if (
        staging[
            "content_sha256"
        ]
        != source[
            "content_sha256"
        ]
    ):
        raise M2DGRCameraIMUSynchronizationEvidenceError(
            "Phase-3C staging source content hash mismatch"
        )
