from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json
import re


SCHEMA = "TRUST_ROBOT_M2DGR_SYNCHRONIZATION_EVIDENCE_V1"
SCHEMA_VERSION = 1

EXPECTED_SOURCE_ARTIFACT_KEYS = {
    "connection_inventory",
    "gnss_clock",
    "clock_domain_fingerprint",
    "within_trajectory_clock_drift",
    "vector_gyro_clean_cohort",
    "phase3_timing_index",
    "phase3_manifest",
}

EXPECTED_STREAM_IDS = (
    "/camera/color/image_raw/compressed",
    "/camera/imu",
    "/handsfree/imu",
    "/velodyne_points",
)

CONSERVATIVE_CLOCK_DOMAINS = {
    "/handsfree/imu":
        "m2dgr_handsfree_header_clock_unverified",
    "/camera/imu":
        "m2dgr_camera_imu_header_clock_unverified",
    "/velodyne_points":
        "m2dgr_velodyne_header_clock_unverified",
    "/camera/color/image_raw/compressed":
        "m2dgr_camera_image_header_clock_unverified",
}

EXPECTED_BLOCKERS = {
    "camera_image_to_imu_physical_capture_timing_not_independently_verified",
    "lidar_to_imu_physical_capture_timing_not_independently_verified",
    "reference_to_estimator_temporal_association_not_independently_verified",
    "common_physical_clock_not_independently_verified",
    "no_validation_calibration_split_for_data_selected_sync_tolerance",
    "calibration_not_independently_verified",
}

EXPECTED_POLICY = {
    "characterization_only": True,
    "raw_data_modified": False,
    "phase3_manifest_modified": False,
    "automatic_sample_exclusion_rule_created": False,
    "alignment_based_exclusion_rule_created": False,
    "fixed_offset_estimated": False,
    "fixed_offset_applied": False,
    "synchronization_tolerance_frozen": False,
    "clock_domain_verified": False,
    "physical_capture_synchronization_verified": False,
    "synchronization_verified": False,
    "evaluation_ready": False,
}

HEX64 = re.compile(
    r"^[0-9a-f]{64}$"
)


class M2DGRSynchronizationEvidenceError(ValueError):
    """Raised when Phase-3B synchronization evidence violates its contract."""


def _require_mapping(
    value: object,
    label: str,
) -> dict:
    if not isinstance(
        value,
        dict,
    ):
        raise M2DGRSynchronizationEvidenceError(
            f"{label} must be a mapping"
        )
    return value


def _require_exact_keys(
    payload: dict,
    expected: set[str],
    label: str,
) -> None:
    actual = set(
        payload
    )

    if actual != expected:
        raise M2DGRSynchronizationEvidenceError(
            f"{label} keys mismatch: "
            f"missing={sorted(expected - actual)!r}, "
            f"extra={sorted(actual - expected)!r}"
        )


def _require_sha256(
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
        raise M2DGRSynchronizationEvidenceError(
            f"{label} must be a lowercase SHA256 digest"
        )

    return value


def _require_relative_path(
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
        raise M2DGRSynchronizationEvidenceError(
            f"{label} must be a non-empty relative path"
        )

    return value


def _require_number(
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
        raise M2DGRSynchronizationEvidenceError(
            f"{label} must be numeric"
        )

    number = float(
        value
    )

    if not (
        number
        == number
        and abs(
            number
        )
        != float(
            "inf"
        )
    ):
        raise M2DGRSynchronizationEvidenceError(
            f"{label} must be finite"
        )

    return number


def _validate_summary(
    value: object,
    label: str,
    *,
    bounded_correlation: bool = False,
    nonnegative: bool = False,
) -> None:
    payload = _require_mapping(
        value,
        label,
    )

    _require_exact_keys(
        payload,
        {
            "min",
            "median",
            "max",
        },
        label,
    )

    minimum = _require_number(
        payload[
            "min"
        ],
        f"{label}.min",
    )

    median = _require_number(
        payload[
            "median"
        ],
        f"{label}.median",
    )

    maximum = _require_number(
        payload[
            "max"
        ],
        f"{label}.max",
    )

    if not (
        minimum
        <= median
        <= maximum
    ):
        raise M2DGRSynchronizationEvidenceError(
            f"{label} must satisfy min <= median <= max"
        )

    if bounded_correlation and (
        minimum < -1.0
        or maximum > 1.0
    ):
        raise M2DGRSynchronizationEvidenceError(
            f"{label} correlation values must lie in [-1, 1]"
        )

    if nonnegative and minimum < 0.0:
        raise M2DGRSynchronizationEvidenceError(
            f"{label} must be non-negative"
        )


def synchronization_evidence_content_sha256(
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


def validate_m2dgr_synchronization_evidence(
    payload: dict,
) -> None:
    payload = _require_mapping(
        payload,
        "synchronization evidence",
    )

    _require_exact_keys(
        payload,
        {
            "schema",
            "schema_version",
            "dataset_id",
            "source_artifacts",
            "observations",
            "manifest_semantics",
            "remaining_blockers",
            "policy",
            "content_sha256",
        },
        "synchronization evidence",
    )

    if payload[
        "schema"
    ] != SCHEMA:
        raise M2DGRSynchronizationEvidenceError(
            "unexpected synchronization-evidence schema"
        )

    if payload[
        "schema_version"
    ] != SCHEMA_VERSION:
        raise M2DGRSynchronizationEvidenceError(
            "unexpected synchronization-evidence schema version"
        )

    if payload[
        "dataset_id"
    ] != "M2DGR":
        raise M2DGRSynchronizationEvidenceError(
            "synchronization evidence must describe M2DGR"
        )

    stored_digest = _require_sha256(
        payload[
            "content_sha256"
        ],
        "content_sha256",
    )

    expected_digest = (
        synchronization_evidence_content_sha256(
            payload
        )
    )

    if stored_digest != expected_digest:
        raise M2DGRSynchronizationEvidenceError(
            "synchronization-evidence content digest mismatch"
        )

    source_artifacts = _require_mapping(
        payload[
            "source_artifacts"
        ],
        "source_artifacts",
    )

    if set(
        source_artifacts
    ) != EXPECTED_SOURCE_ARTIFACT_KEYS:
        raise M2DGRSynchronizationEvidenceError(
            "unexpected synchronization-evidence source-artifact set"
        )

    for key, artifact in source_artifacts.items():
        artifact = _require_mapping(
            artifact,
            f"source_artifacts.{key}",
        )

        _require_exact_keys(
            artifact,
            {
                "relative_path",
                "file_sha256",
                "size_bytes",
            },
            f"source_artifacts.{key}",
        )

        _require_relative_path(
            artifact[
                "relative_path"
            ],
            f"source_artifacts.{key}.relative_path",
        )

        _require_sha256(
            artifact[
                "file_sha256"
            ],
            f"source_artifacts.{key}.file_sha256",
        )

        if (
            not isinstance(
                artifact[
                    "size_bytes"
                ],
                int,
            )
            or artifact[
                "size_bytes"
            ] <= 0
        ):
            raise M2DGRSynchronizationEvidenceError(
                f"source_artifacts.{key}.size_bytes "
                "must be a positive integer"
            )

    observations = _require_mapping(
        payload[
            "observations"
        ],
        "observations",
    )

    _require_exact_keys(
        observations,
        {
            "connection_inventory",
            "gnss_receiver_clock",
            "bag_record_clock",
            "sensor_header_epoch",
            "imu_content_association",
        },
        "observations",
    )

    inventory = _require_mapping(
        observations[
            "connection_inventory"
        ],
        "connection_inventory",
    )

    expected_inventory = {
        "trajectory_count": 36,
        "gnss_clock_topics_present_trajectory_count": 18,
        "velodyne_packets_present_trajectory_count": 0,
        "rosout_present_trajectory_count": 0,
        "diagnostics_present_trajectory_count": 0,
        "clock_topic_present_trajectory_count": 0,
    }

    for key, expected in expected_inventory.items():
        if inventory.get(
            key
        ) != expected:
            raise M2DGRSynchronizationEvidenceError(
                f"unexpected connection inventory: "
                f"{key}={inventory.get(key)!r}"
            )

    gnss = _require_mapping(
        observations[
            "gnss_receiver_clock"
        ],
        "gnss_receiver_clock",
    )

    if gnss.get(
        "trajectory_count"
    ) != 18:
        raise M2DGRSynchronizationEvidenceError(
            "expected 18 GNSS-bearing trajectories"
        )

    if gnss.get(
        "all_fix_headers_exact_receiver_utc"
    ) is not True:
        raise M2DGRSynchronizationEvidenceError(
            "GNSS fix headers are not recorded as exact receiver UTC"
        )

    for key in (
        "receiver_clock_reset_count",
        "unresolved_pvt_utc_count",
        "reverse_receiver_utc_count",
    ):
        if gnss.get(
            key
        ) != 0:
            raise M2DGRSynchronizationEvidenceError(
                f"unexpected GNSS clock anomaly: {key}"
            )

    bag_clock = _require_mapping(
        observations[
            "bag_record_clock"
        ],
        "bag_record_clock",
    )

    if bag_clock.get(
        "stable_fixed_offset_to_gnss_receiver_utc"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "bag record time must not be represented as "
            "a stable fixed-offset GNSS clock"
        )

    if bag_clock.get(
        "transport_latency_separated_from_clock_offset"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "transport latency must remain inseparable from clock offset"
        )

    header_epoch = _require_mapping(
        observations[
            "sensor_header_epoch"
        ],
        "sensor_header_epoch",
    )

    if header_epoch.get(
        "host_system_epoch_behavior_observed"
    ) is not True:
        raise M2DGRSynchronizationEvidenceError(
            "expected host/system-epoch behavior observation"
        )

    if header_epoch.get(
        "native_gnss_device_utc_behavior_supported"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "sensor headers must not be represented as native GNSS UTC"
        )

    if header_epoch.get(
        "verified_common_physical_clock"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "common physical clock is not independently verified"
        )

    imu = _require_mapping(
        observations[
            "imu_content_association"
        ],
        "imu_content_association",
    )

    if imu.get(
        "clean_trajectory_count"
    ) != 28:
        raise M2DGRSynchronizationEvidenceError(
            "expected 28 clean IMU-association trajectories"
        )

    if imu.get(
        "rotation_estimated_from_timing_data"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "IMU rotation must not be estimated from timing data"
        )

    if imu.get(
        "author_calibration_independently_verified"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "author calibration must remain independently unverified"
        )

    _validate_summary(
        imu.get(
            "best_lag_ms"
        ),
        "imu_content_association.best_lag_ms",
    )

    _validate_summary(
        imu.get(
            "window_median_lag_ms"
        ),
        "imu_content_association.window_median_lag_ms",
    )

    _validate_summary(
        imu.get(
            "window_lag_range_ms"
        ),
        "imu_content_association.window_lag_range_ms",
        nonnegative=True,
    )

    _validate_summary(
        imu.get(
            "zero_lag_vector_correlation"
        ),
        "imu_content_association.zero_lag_vector_correlation",
        bounded_correlation=True,
    )

    _validate_summary(
        imu.get(
            "best_minus_zero_vector_correlation"
        ),
        "imu_content_association.best_minus_zero_vector_correlation",
        nonnegative=True,
    )

    if imu.get(
        "near_zero_temporal_association_observed"
    ) is not True:
        raise M2DGRSynchronizationEvidenceError(
            "expected near-zero IMU temporal-association observation"
        )

    if imu.get(
        "nonzero_fixed_offset_supported"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "nonzero IMU fixed offset must remain unsupported"
        )

    semantics = _require_mapping(
        payload[
            "manifest_semantics"
        ],
        "manifest_semantics",
    )

    _require_sha256(
        semantics.get(
            "phase3_source_manifest_content_sha256"
        ),
        "phase3_source_manifest_content_sha256",
    )

    _require_sha256(
        semantics.get(
            "phase3_timing_index_content_sha256"
        ),
        "phase3_timing_index_content_sha256",
    )

    if semantics.get(
        "current_shared_sensor_clock_label_is_physical_clock_proof"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "shared sensor_clock label must not be physical-clock proof"
        )

    domains = _require_mapping(
        semantics.get(
            "recommended_conservative_clock_domains"
        ),
        "recommended_conservative_clock_domains",
    )

    if domains != CONSERVATIVE_CLOCK_DOMAINS:
        raise M2DGRSynchronizationEvidenceError(
            "unexpected conservative clock-domain mapping"
        )

    if len(
        set(
            domains.values()
        )
    ) != len(
        domains
    ):
        raise M2DGRSynchronizationEvidenceError(
            "conservative clock-domain labels must remain distinct"
        )

    if semantics.get(
        "clock_domain_equality_may_be_used_as_sync_proof"
    ) is not False:
        raise M2DGRSynchronizationEvidenceError(
            "clock-domain equality must not be synchronization proof"
        )

    blockers = payload[
        "remaining_blockers"
    ]

    if (
        not isinstance(
            blockers,
            list,
        )
        or len(
            blockers
        ) != len(
            set(
                blockers
            )
        )
        or set(
            blockers
        ) != EXPECTED_BLOCKERS
    ):
        raise M2DGRSynchronizationEvidenceError(
            "remaining synchronization blocker set mismatch"
        )

    policy = _require_mapping(
        payload[
            "policy"
        ],
        "policy",
    )

    _require_exact_keys(
        policy,
        set(
            EXPECTED_POLICY
        ),
        "policy",
    )

    for key, expected in EXPECTED_POLICY.items():
        if policy[
            key
        ] != expected:
            raise M2DGRSynchronizationEvidenceError(
                f"unsafe synchronization policy: "
                f"{key}={policy[key]!r}"
            )


def load_m2dgr_synchronization_evidence(
    path: str | Path,
) -> dict:
    source = Path(
        path
    )

    payload = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    validate_m2dgr_synchronization_evidence(
        payload
    )

    return payload


def verify_synchronization_evidence_sources(
    dataset_root: str | Path,
    payload: dict,
) -> None:
    validate_m2dgr_synchronization_evidence(
        payload
    )

    root = Path(
        dataset_root
    )

    for key, artifact in payload[
        "source_artifacts"
    ].items():
        path = (
            root
            / artifact[
                "relative_path"
            ]
        )

        if not path.is_file():
            raise FileNotFoundError(
                path
            )

        if (
            path.stat().st_size
            != artifact[
                "size_bytes"
            ]
        ):
            raise M2DGRSynchronizationEvidenceError(
                f"{key}: source artifact size mismatch"
            )

        digest = sha256(
            path.read_bytes()
        ).hexdigest()

        if digest != artifact[
            "file_sha256"
        ]:
            raise M2DGRSynchronizationEvidenceError(
                f"{key}: source artifact SHA256 mismatch"
            )
