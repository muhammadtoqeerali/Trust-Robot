"""TRUST-ROBOT SE4 software-only end-to-end qualification.

This qualification intentionally combines two different software lanes.

Lane A uses one real frozen M2DGR TRAIN trajectory to demonstrate:

* frozen split loading;
* deterministic SE1 replay;
* real camera feature extraction;
* real D435i IMU feature extraction;
* real HandsFree IMU feature extraction;
* LiDAR replay/provenance observation;
* SE2 and SE4 fail-closed training boundaries.

Lane B uses synthetic documentation-only network values and injected component
functions to demonstrate:

* V2 runtime binding;
* authorization-record hashing;
* hash-bound execution authorization;
* file-driven runner validation;
* explicit dispatch gates;
* composite orchestration;
* UDP receipt;
* three HTTP receipts;
* final composite session receipt.

Lane B performs no socket operations, HTTP requests or physical sensor contact.

This qualification is a software integration demonstration. It is not health
supervision, physical evidence, model training, validation-set access,
confirmation-set access or trajectory scoring.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping
import json
import os

from rosbags.highlevel import AnyReader

from .deterministic_multimodal_dataset_replay import (
    iter_anyreader_replay,
    load_train_replay_source_from_manifest_file,
    resolve_train_bag_path,
)

from .health_supervision_resolution import (
    SE2HealthSupervisionProtocolError,
    assert_health_model_training_authorized,
    build_se2_health_supervision_protocol_manifest,
    validate_se2_health_supervision_protocol_manifest,
)

from .se3_multimodal_feature_contract import (
    LIDAR_FEATURE_NAMES,
    extract_camera_features,
    extract_imu_features,
)

from .se4_composite_live_session_orchestrator import (
    build_execution_authorization_candidate,
    execute_composite_live_session,
)

from .se4_health_model_training_resolution import (
    SE4HealthModelTrainingResolutionError,
    assert_se5_entry_authorized,
    assert_training_execution_authorized,
    build_se4_health_model_training_resolution,
    validate_se4_health_model_training_resolution,
)

from .se4_real_train_execution_runner import (
    NETWORK_IO_ACKNOWLEDGEMENT,
    execute_real_session_from_files,
    validate_real_execution_inputs_from_files,
)

from .se4_real_train_runtime_input_binding_v2 import (
    build_runtime_binding_candidate_v2,
)


RESOLUTION_SCHEMA = (
    "TRUST_ROBOT_SE4_SOFTWARE_ONLY_END_TO_END_QUALIFICATION_RESOLUTION_V1"
)

QUALIFICATION_SCHEMA = (
    "TRUST_ROBOT_SE4_SOFTWARE_ONLY_END_TO_END_QUALIFICATION_V1"
)

RESOLUTION_ID = (
    "trust_robot_se4_software_only_end_to_end_qualification_resolution_v1"
)

REPRESENTATIVE_TRAJECTORY = (
    "room_02"
)

EXPECTED_SPLIT_MANIFEST_SHA256 = (
    "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f"
)

CAMERA_FEATURE_NAMES = (
    "gray_mean_intensity_8bit",
    "gray_std_intensity_8bit",
    "gray_mean_abs_neighbor_difference_8bit",
)

IMU_FEATURE_NAMES = (
    "angular_speed_norm_rad_s",
    "linear_acceleration_norm_m_s2",
)


class SE4SoftwareOnlyE2EQualificationError(
    ValueError
):
    """Raised when the qualification contract is violated."""


def canonical_json_bytes(
    payload: object,
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


def content_sha256(
    payload: Mapping[str, object],
    *,
    digest_field: str = "content_sha256",
) -> str:
    body = dict(
        payload
    )

    body.pop(
        digest_field,
        None,
    )

    return sha256(
        canonical_json_bytes(
            body
        )
    ).hexdigest()


def file_sha256(
    path: str | Path,
) -> str:
    digest = sha256()

    with Path(
        path
    ).open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def _normalized(
    value: object,
) -> object:
    if isinstance(
        value,
        bytes,
    ):
        return {
            "byte_count":
                len(
                    value
                ),

            "sha256":
                sha256(
                    value
                ).hexdigest(),
        }

    if is_dataclass(
        value
    ):
        return _normalized(
            asdict(
                value
            )
        )

    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(
                key
            ):
                _normalized(
                    child
                )
            for key, child
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            _normalized(
                child
            )
            for child
            in value
        ]

    if isinstance(
        value,
        Path,
    ):
        return str(
            value
        )

    return value


def _mapping_value(
    payload: Mapping[str, object],
    candidates: tuple[str, ...],
) -> object | None:
    for name in candidates:
        if name in payload:
            return payload[
                name
            ]

    return None


def _manifest_train_record(
    manifest_path: Path,
    trajectory_id: str,
) -> Mapping[str, object]:
    payload = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    records = [
        record
        for record
        in payload[
            "records"
        ]
        if record.get(
            "trajectory_id"
        ) == trajectory_id
    ]

    if len(
        records
    ) != 1:
        raise SE4SoftwareOnlyE2EQualificationError(
            "representative trajectory must occur exactly once in frozen manifest"
        )

    record = records[
        0
    ]

    if record.get(
        "split"
    ) != "train":
        raise SE4SoftwareOnlyE2EQualificationError(
            "representative trajectory must be frozen TRAIN"
        )

    return record


def _topic_to_stream_id(
    manifest_record: Mapping[str, object],
) -> dict[str, str]:
    """Map ROS topic to frozen stream identity.

    In the frozen M2DGR manifest the stream_id itself is the ROS topic.
    There is intentionally no separately invented topic field.
    """

    raw_streams = manifest_record.get(
        "streams"
    )

    if not isinstance(
        raw_streams,
        list,
    ):
        raise SE4SoftwareOnlyE2EQualificationError(
            "frozen manifest streams must be a list"
        )

    mapping: dict[str, str] = {}

    for raw_stream in raw_streams:
        if not isinstance(
            raw_stream,
            Mapping,
        ):
            raise SE4SoftwareOnlyE2EQualificationError(
                "frozen manifest stream entry must be a mapping"
            )

        stream_id = raw_stream.get(
            "stream_id"
        )

        if not isinstance(
            stream_id,
            str,
        ) or not stream_id:
            raise SE4SoftwareOnlyE2EQualificationError(
                "frozen manifest stream_id must be non-empty text"
            )

        if raw_stream.get(
            "estimator_input"
        ) is not True:
            continue

        if raw_stream.get(
            "reference_only"
        ) is not False:
            continue

        if stream_id in mapping:
            raise SE4SoftwareOnlyE2EQualificationError(
                "duplicate frozen manifest stream_id"
            )

        mapping[
            stream_id
        ] = stream_id

    if not mapping:
        raise SE4SoftwareOnlyE2EQualificationError(
            "could not derive estimator-input ROS topics from frozen manifest"
        )

    return mapping


def _stream_id_from_envelope(
    envelope: object,
) -> str:
    """Read the frozen SE1 source stream identity from a replay envelope."""

    for attribute in (
        "source_stream_id",
        "stream_id",
    ):
        if hasattr(
            envelope,
            attribute,
        ):
            value = getattr(
                envelope,
                attribute,
            )

            if isinstance(
                value,
                str,
            ) and value:
                return value

    normalized = _normalized(
        envelope
    )

    if isinstance(
        normalized,
        Mapping,
    ):
        for key in (
            "source_stream_id",
            "stream_id",
        ):
            value = normalized.get(
                key
            )

            if isinstance(
                value,
                str,
            ) and value:
                return value

    raise SE4SoftwareOnlyE2EQualificationError(
        "replay envelope does not expose frozen source_stream_id"
    )


def _bounded_replay_pass(
    *,
    source: object,
    bag_path: Path,
    required_stream_ids: set[str],
    max_messages: int,
) -> dict[str, object]:
    if max_messages <= 0:
        raise SE4SoftwareOnlyE2EQualificationError(
            "max_messages must be positive"
        )

    seen: set[str] = set()

    aggregate = sha256()

    message_count = 0

    normalized_samples: dict[
        str,
        object,
    ] = {}

    for envelope in iter_anyreader_replay(
        source,
        bag_path,
        reader_class=AnyReader,
    ):
        message_count += 1

        normalized = _normalized(
            envelope
        )

        aggregate.update(
            canonical_json_bytes(
                normalized
            )
        )

        aggregate.update(
            b"\n"
        )

        stream_id = _stream_id_from_envelope(
            envelope
        )

        if stream_id not in normalized_samples:
            normalized_samples[
                stream_id
            ] = normalized

        seen.add(
            stream_id
        )

        if required_stream_ids.issubset(
            seen
        ):
            break

        if message_count >= max_messages:
            break

    if not required_stream_ids.issubset(
        seen
    ):
        missing = sorted(
            required_stream_ids
            - seen
        )

        raise SE4SoftwareOnlyE2EQualificationError(
            "bounded real replay did not observe required streams: "
            + ",".join(
                missing
            )
        )

    return {
        "message_count":
            message_count,

        "observed_stream_ids":
            sorted(
                seen
            ),

        "reader_order_digest_sha256":
            aggregate.hexdigest(),

        "first_envelope_by_stream":
            normalized_samples,
    }


def _vector_xyz(
    value: object,
) -> tuple[
    float,
    float,
    float,
]:
    return (
        float(
            getattr(
                value,
                "x"
            )
        ),
        float(
            getattr(
                value,
                "y"
            )
        ),
        float(
            getattr(
                value,
                "z"
            )
        ),
    )


def _extract_real_feature_samples(
    *,
    bag_path: Path,
    topic_to_stream: Mapping[str, str],
) -> dict[str, object]:
    wanted_streams = set(
        topic_to_stream.values()
    )

    samples: dict[
        str,
        object,
    ] = {}

    with AnyReader(
        [
            bag_path,
        ]
    ) as reader:
        for connection, timestamp, rawdata in reader.messages():
            stream_id = topic_to_stream.get(
                connection.topic
            )

            if stream_id is None:
                continue

            if stream_id in samples:
                continue

            if stream_id == "/camera/color/image_raw/compressed":
                message = reader.deserialize(
                    rawdata,
                    connection.msgtype,
                )

                payload = bytes(
                    message.data
                )

                values = extract_camera_features(
                    payload
                )

                samples[
                    stream_id
                ] = {
                    "topic":
                        connection.topic,

                    "message_type":
                        connection.msgtype,

                    "bag_timestamp_ns":
                        int(
                            timestamp
                        ),

                    "serialized_payload_bytes":
                        len(
                            rawdata
                        ),

                    "compressed_image_payload_bytes":
                        len(
                            payload
                        ),

                    "compressed_image_payload_sha256":
                        sha256(
                            payload
                        ).hexdigest(),

                    "feature_names":
                        list(
                            CAMERA_FEATURE_NAMES
                        ),

                    "feature_values":
                        [
                            float(
                                value
                            )
                            for value
                            in values
                        ],
                }

            elif stream_id in {
                "/camera/imu",
                "/handsfree/imu",
            }:
                message = reader.deserialize(
                    rawdata,
                    connection.msgtype,
                )

                angular = _vector_xyz(
                    message.angular_velocity
                )

                linear = _vector_xyz(
                    message.linear_acceleration
                )

                values = extract_imu_features(
                    angular,
                    linear,
                )

                samples[
                    stream_id
                ] = {
                    "topic":
                        connection.topic,

                    "message_type":
                        connection.msgtype,

                    "bag_timestamp_ns":
                        int(
                            timestamp
                        ),

                    "serialized_payload_bytes":
                        len(
                            rawdata
                        ),

                    "angular_velocity_xyz":
                        list(
                            angular
                        ),

                    "linear_acceleration_xyz":
                        list(
                            linear
                        ),

                    "feature_names":
                        list(
                            IMU_FEATURE_NAMES
                        ),

                    "feature_values":
                        [
                            float(
                                value
                            )
                            for value
                            in values
                        ],
                }

            elif stream_id == "/velodyne_points":
                raw = bytes(
                    rawdata
                )

                samples[
                    stream_id
                ] = {
                    "topic":
                        connection.topic,

                    "message_type":
                        connection.msgtype,

                    "bag_timestamp_ns":
                        int(
                            timestamp
                        ),

                    "serialized_payload_bytes":
                        len(
                            raw
                        ),

                    "serialized_payload_sha256":
                        sha256(
                            raw
                        ).hexdigest(),

                    "SE3_lidar_feature_contract_names":
                        list(
                            LIDAR_FEATURE_NAMES
                        ),

                    "lidar_feature_recomputation_performed":
                        False,

                    "lidar_feature_recomputation_nonclaim":
                        (
                            "The SE3 LiDAR five-feature contract comes from the "
                            "already frozen validated Phase4 registration "
                            "pipeline; this bounded demonstration observes real "
                            "LiDAR replay provenance without rerunning that "
                            "full registration pipeline."
                        ),
                }

            if wanted_streams.issubset(
                samples
            ):
                break

    missing = sorted(
        wanted_streams
        - set(
            samples
        )
    )

    if missing:
        raise SE4SoftwareOnlyE2EQualificationError(
            "real feature demonstration did not obtain samples for: "
            + ",".join(
                missing
            )
        )

    return {
        "stream_samples":
            samples,

        "stream_count":
            len(
                samples
            ),

        "camera_feature_extraction_performed":
            (
                "/camera/color/image_raw/compressed"
                in samples
            ),

        "IMU_feature_extraction_performed":
            (
                "/camera/imu"
                in samples
                and "/handsfree/imu"
                in samples
            ),

        "LiDAR_real_replay_observed":
            (
                "/velodyne_points"
                in samples
            ),

        "LiDAR_full_feature_recomputation_performed":
            False,
    }


def run_real_data_lane(
    *,
    dataset_root: str | Path,
    split_manifest: str | Path,
    trajectory_id: str = REPRESENTATIVE_TRAJECTORY,
    max_replay_messages: int = 20000,
) -> dict[str, object]:
    root = Path(
        dataset_root
    )

    manifest = Path(
        split_manifest
    )

    if not root.is_absolute():
        raise SE4SoftwareOnlyE2EQualificationError(
            "dataset_root must be absolute"
        )

    if not root.is_dir():
        raise SE4SoftwareOnlyE2EQualificationError(
            "dataset_root does not exist"
        )

    if not manifest.is_file():
        raise SE4SoftwareOnlyE2EQualificationError(
            "split_manifest does not exist"
        )

    if file_sha256(
        manifest
    ) != EXPECTED_SPLIT_MANIFEST_SHA256:
        raise SE4SoftwareOnlyE2EQualificationError(
            "split manifest differs from frozen contract"
        )

    record = _manifest_train_record(
        manifest,
        trajectory_id,
    )

    topic_to_stream = _topic_to_stream_id(
        record
    )

    required_stream_ids = set(
        topic_to_stream.values()
    )

    source = load_train_replay_source_from_manifest_file(
        manifest,
        trajectory_id,
        expected_file_sha256=
            EXPECTED_SPLIT_MANIFEST_SHA256,
    )

    bag_path = resolve_train_bag_path(
        root,
        source,
    )

    if not bag_path.is_file():
        raise SE4SoftwareOnlyE2EQualificationError(
            "resolved TRAIN bag does not exist"
        )

    first = _bounded_replay_pass(
        source=
            source,

        bag_path=
            bag_path,

        required_stream_ids=
            required_stream_ids,

        max_messages=
            max_replay_messages,
    )

    second = _bounded_replay_pass(
        source=
            source,

        bag_path=
            bag_path,

        required_stream_ids=
            required_stream_ids,

        max_messages=
            max_replay_messages,
    )

    if (
        first[
            "message_count"
        ]
        != second[
            "message_count"
        ]
        or first[
            "reader_order_digest_sha256"
        ]
        != second[
            "reader_order_digest_sha256"
        ]
    ):
        raise SE4SoftwareOnlyE2EQualificationError(
            "bounded SE1 replay was not deterministic"
        )

    features = _extract_real_feature_samples(
        bag_path=
            bag_path,

        topic_to_stream=
            topic_to_stream,
    )

    se2 = (
        build_se2_health_supervision_protocol_manifest()
    )

    validate_se2_health_supervision_protocol_manifest(
        se2
    )

    se2_training_blocked = False

    try:
        assert_health_model_training_authorized(
            se2
        )
    except SE2HealthSupervisionProtocolError:
        se2_training_blocked = True

    if not se2_training_blocked:
        raise SE4SoftwareOnlyE2EQualificationError(
            "SE2 unexpectedly authorized health-model training"
        )

    se4 = (
        build_se4_health_model_training_resolution()
    )

    validate_se4_health_model_training_resolution(
        se4
    )

    se4_training_blocked = False
    se5_blocked = False

    try:
        assert_training_execution_authorized(
            se4
        )
    except SE4HealthModelTrainingResolutionError:
        se4_training_blocked = True

    try:
        assert_se5_entry_authorized(
            se4
        )
    except SE4HealthModelTrainingResolutionError:
        se5_blocked = True

    if not (
        se4_training_blocked
        and se5_blocked
    ):
        raise SE4SoftwareOnlyE2EQualificationError(
            "SE4/SE5 fail-closed boundary unexpectedly opened"
        )

    return {
        "lane":
            "real_M2DGR_TRAIN_software",

        "trajectory_id":
            trajectory_id,

        "representative_only":
            True,

        "representative_selection_reason":
            (
                "room_02 is the smallest available frozen TRAIN bag; selection "
                "is for bounded software demonstration only and is not a "
                "statistical or scientific representativeness claim."
            ),

        "dataset_root":
            str(
                root
            ),

        "split_manifest":
            str(
                manifest
            ),

        "split_manifest_sha256":
            EXPECTED_SPLIT_MANIFEST_SHA256,

        "bag_path":
            str(
                bag_path
            ),

        "bag_file_size_bytes":
            bag_path.stat().st_size,

        "required_stream_ids":
            sorted(
                required_stream_ids
            ),

        "bounded_replay_first_pass":
            first,

        "bounded_replay_second_pass": {
            "message_count":
                second[
                    "message_count"
                ],

            "reader_order_digest_sha256":
                second[
                    "reader_order_digest_sha256"
                ],
        },

        "bounded_replay_deterministic":
            True,

        "real_feature_demonstration":
            features,

        "SE2_health_model_training_blocked":
            True,

        "SE4_training_execution_blocked":
            True,

        "SE5_entry_blocked":
            True,

        "health_label_generated":
            False,

        "reference_trajectory_accessed":
            False,

        "ATE_RPE_computed":
            False,

        "validation_accessed":
            False,

        "confirmation_accessed":
            False,
    }


def _synthetic_udp_capture(
    call_order: list[str],
) -> Callable[..., Mapping[str, object]]:
    def run(
        candidate: object,
    ) -> Mapping[str, object]:
        call_order.append(
            "UDP"
        )

        session = (
            Path(
                candidate.absolute_output_root
            )
            / candidate.acquisition_session_id
        )

        session.mkdir(
            parents=False,
            exist_ok=False,
        )

        measurement = (
            session
            / "measurement_payloads.bin"
        )

        position = (
            session
            / "position_payloads.bin"
        )

        measurement_payload = (
            b"SYNTHETIC_SOFTWARE_ONLY_MEASUREMENT_DATAGRAM"
        )

        position_payload = (
            b"SYNTHETIC_SOFTWARE_ONLY_POSITION_DATAGRAM"
        )

        measurement.write_bytes(
            measurement_payload
        )

        position.write_bytes(
            position_payload
        )

        receipt = {
            "schema":
                "TRUST_ROBOT_SYNTHETIC_SOFTWARE_ONLY_UDP_RECEIPT_V1",

            "acquisition_session_id":
                candidate.acquisition_session_id,

            "measurement_datagram_count":
                1,

            "position_datagram_count":
                1,

            "measurement_payload_sha256":
                sha256(
                    measurement_payload
                ).hexdigest(),

            "position_payload_sha256":
                sha256(
                    position_payload
                ).hexdigest(),

            "real_network_IO_executed":
                False,

            "real_sensor_contact":
                False,

            "health_label_generated":
                False,
        }

        receipt_path = (
            session
            / "capture_receipt.json"
        )

        receipt_path.write_text(
            json.dumps(
                receipt,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return {
            "session_directory":
                str(
                    session
                ),

            "capture_receipt":
                receipt,

            "capture_receipt_publication": {
                "final_path":
                    str(
                        receipt_path
                    ),

                "final_sha256":
                    file_sha256(
                        receipt_path
                    ),
            },
        }

    return run


def _synthetic_http_read(
    call_order: list[str],
) -> Callable[..., Mapping[str, object]]:
    def run(
        **kwargs: object,
    ) -> Mapping[str, object]:
        evidence_kind = str(
            kwargs[
                "evidence_kind"
            ]
        )

        call_order.append(
            "HTTP:"
            + evidence_kind
        )

        session = Path(
            kwargs[
                "session_directory"
            ]
        )

        body_names = {
            "identity":
                "info.json",

            "status":
                "status.json",

            "diagnostic":
                "diagnostic.json",
        }

        header_names = {
            "identity":
                "info.headers",

            "status":
                "status.headers",

            "diagnostic":
                "diagnostic.headers",
        }

        body_payload = {
            "synthetic":
                True,

            "evidence_kind":
                evidence_kind,

            "software_only":
                True,

            "real_sensor_contact":
                False,
        }

        body = (
            session
            / body_names[
                evidence_kind
            ]
        )

        headers = (
            session
            / header_names[
                evidence_kind
            ]
        )

        body.write_text(
            json.dumps(
                body_payload,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        headers.write_text(
            "HTTP/1.1 200 SYNTHETIC\r\n"
            "X-Trust-Robot-Software-Only: true\r\n"
            "\r\n",
            encoding="utf-8",
        )

        return {
            "schema":
                "TRUST_ROBOT_SYNTHETIC_SOFTWARE_ONLY_HTTP_RECEIPT_V1",

            "evidence_kind":
                evidence_kind,

            "body_path":
                str(
                    body
                ),

            "body_sha256":
                file_sha256(
                    body
                ),

            "headers_path":
                str(
                    headers
                ),

            "headers_sha256":
                file_sha256(
                    headers
                ),

            "real_network_IO_executed":
                False,

            "real_sensor_contact":
                False,

            "health_label_generated":
                False,

            "interval_binding_established":
                False,
        }

    return run


def run_synthetic_live_lane(
    *,
    working_root: str | Path,
) -> dict[str, object]:
    root = Path(
        working_root
    )

    root.mkdir(
        parents=True,
        exist_ok=False,
    )

    capture_root = (
        root
        / "capture"
    )

    capture_root.mkdir()

    binding = build_runtime_binding_candidate_v2(
        acquisition_session_id=
            "SOFTWARE_ONLY_E2E_SYNTHETIC_SESSION",

        split=
            "TRAIN",

        bind_ipv4=
            "192.0.2.10",

        measurement_udp_port=
            25000,

        position_udp_port=
            25001,

        sensor_ipv4=
            "192.0.2.20",

        capture_duration_seconds=
            1,

        absolute_output_root=
            str(
                capture_root
            ),

        http_port=
            8080,

        http_connect_timeout_seconds=
            1,

        http_total_timeout_seconds=
            2,

        vlp32c_destination_ipv4=
            "192.0.2.10",

        vlp32c_measurement_destination_udp_port=
            25000,

        vlp32c_position_destination_udp_port=
            25001,

        vlp32c_destination_configuration_verified=
            True,

        declared_before_execution=
            True,
    )

    authorization_record = (
        root
        / "SYNTHETIC_AUTHORIZATION_RECORD.txt"
    )

    authorization_record.write_text(
        "TRUST-ROBOT SOFTWARE-ONLY TEST RECORD\n"
        "This file authorizes no physical sensor access.\n"
        "It exists only to exercise hash-binding software.\n",
        encoding="utf-8",
    )

    authorization_record_sha = file_sha256(
        authorization_record
    )

    authorization = build_execution_authorization_candidate(
        authorization_id=
            "SOFTWARE_ONLY_E2E_SYNTHETIC_AUTHORIZATION",

        binding_sha256=
            binding[
                "binding_sha256"
            ],

        authorization_record_sha256=
            authorization_record_sha,

        authorized_for_real_sensor_execution=
            True,

        declared_before_execution=
            True,
    )

    binding_path = (
        root
        / "synthetic_binding.json"
    )

    authorization_path = (
        root
        / "synthetic_execution_authorization.json"
    )

    binding_path.write_text(
        json.dumps(
            binding,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    authorization_path.write_text(
        json.dumps(
            authorization,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    validation = validate_real_execution_inputs_from_files(
        runtime_binding_file=
            binding_path,

        execution_authorization_file=
            authorization_path,

        authorization_record_file=
            authorization_record,
    )

    call_order: list[str] = []

    def injected_orchestrator(
        *,
        runtime_binding: Mapping[str, object],
        execution_authorization: Mapping[str, object],
    ) -> Mapping[str, object]:
        return execute_composite_live_session(
            runtime_binding=
                runtime_binding,

            execution_authorization=
                execution_authorization,

            udp_capture_fn=
                _synthetic_udp_capture(
                    call_order
                ),

            http_read_fn=
                _synthetic_http_read(
                    call_order
                ),
        )

    execution = execute_real_session_from_files(
        runtime_binding_file=
            binding_path,

        execution_authorization_file=
            authorization_path,

        authorization_record_file=
            authorization_record,

        execute_real=
            True,

        network_io_acknowledgement=
            NETWORK_IO_ACKNOWLEDGEMENT,

        orchestrator_fn=
            injected_orchestrator,
    )

    expected_order = [
        "UDP",
        "HTTP:identity",
        "HTTP:status",
        "HTTP:diagnostic",
    ]

    if call_order != expected_order:
        raise SE4SoftwareOnlyE2EQualificationError(
            "synthetic live software execution order differs from contract"
        )

    composite = execution[
        "execution_result"
    ][
        "composite_session_receipt"
    ]

    return {
        "lane":
            "synthetic_live_software",

        "documentation_only_network_values":
            True,

        "runtime_binding_file":
            str(
                binding_path
            ),

        "runtime_binding_file_sha256":
            file_sha256(
                binding_path
            ),

        "execution_authorization_file":
            str(
                authorization_path
            ),

        "execution_authorization_file_sha256":
            file_sha256(
                authorization_path
            ),

        "synthetic_authorization_record_file":
            str(
                authorization_record
            ),

        "synthetic_authorization_record_sha256":
            authorization_record_sha,

        "authorization_record_is_grounded_real_authorization":
            False,

        "file_validation_receipt":
            validation[
                "input_validation"
            ],

        "dispatch_gate_exercised":
            True,

        "dispatch_uses_injected_orchestrator":
            True,

        "dispatch_is_real_sensor_execution":
            False,

        "execution_order":
            call_order,

        "composite_session_directory":
            execution[
                "execution_result"
            ][
                "session_directory"
            ],

        "composite_session_receipt":
            composite,

        "composite_session_receipt_publication":
            execution[
                "execution_result"
            ][
                "composite_session_receipt_publication"
            ],

        "real_network_IO_executed":
            False,

        "real_sensor_contact":
            False,

        "real_runtime_binding_created":
            False,

        "grounded_execution_authorization_created":
            False,

        "health_supervision_source_accepted":
            False,

        "health_label_generated":
            False,

        "interval_binding_established":
            False,
    }


def build_qualification_resolution(
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            RESOLUTION_SCHEMA,

        "schema_version":
            1,

        "resolution_id":
            RESOLUTION_ID,

        "qualification_scope": {
            "software_only":
                True,

            "representative_real_data_lane":
                True,

            "synthetic_live_software_lane":
                True,

            "real_network_IO_allowed":
                False,

            "real_sensor_contact_allowed":
                False,

            "representative_TRAIN_trajectory":
                REPRESENTATIVE_TRAJECTORY,

            "representative_selection_is_scientific_sampling_claim":
                False,
        },

        "lane_A_contract": {
            "uses_frozen_M2DGR_TRAIN":
                True,

            "uses_SE1_deterministic_replay":
                True,

            "replay_is_run_twice_for_bounded_digest_comparison":
                True,

            "real_camera_feature_extraction":
                True,

            "real_D435i_IMU_feature_extraction":
                True,

            "real_HandsFree_IMU_feature_extraction":
                True,

            "real_LiDAR_replay_observation":
                True,

            "reruns_full_SE3_LiDAR_registration_pipeline":
                False,

            "invokes_SE2_training_guard":
                True,

            "invokes_SE4_training_guard":
                True,

            "invokes_SE5_entry_guard":
                True,
        },

        "lane_B_contract": {
            "uses_synthetic_documentation_only_network_values":
                True,

            "uses_synthetic_authorization_record":
                True,

            "authorization_record_is_real_grounded_authorization":
                False,

            "uses_V2_binding_builder":
                True,

            "uses_hash_bound_authorization_builder":
                True,

            "uses_file_input_validator":
                True,

            "uses_file_driven_dispatch_gate":
                True,

            "uses_injected_composite_orchestrator":
                True,

            "uses_synthetic_UDP_component":
                True,

            "uses_synthetic_HTTP_component":
                True,

            "real_network_IO":
                False,

            "real_sensor_contact":
                False,
        },

        "scientific_boundary": {
            "real_runtime_binding_count":
                0,

            "real_execution_authorization_count":
                0,

            "grounded_authorization_record_count":
                0,

            "accepted_baseline_nominality_source_count":
                0,

            "accepted_health_supervision_source_count":
                0,

            "real_health_label_count":
                0,

            "interval_binding_established":
                False,

            "physical_measurement_time_established":
                False,

            "SE4_complete":
                False,

            "SE4_training_authorized":
                False,

            "SE5_may_proceed":
                False,

            "validation_open":
                False,

            "confirmation_open":
                False,

            "ATE_RPE_computed":
                False,
        },

        "qualification_interpretation": {
            "demonstrates_current_software_stack_integration":
                True,

            "proves_real_sensor_system":
                False,

            "proves_health_model":
                False,

            "proves_health_labels":
                False,

            "replaces_future_hardware_validation":
                False,

            "replaces_future_scientific_validation":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def validate_qualification_resolution(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    expected = build_qualification_resolution()

    if dict(
        payload
    ) != expected:
        raise SE4SoftwareOnlyE2EQualificationError(
            "qualification resolution differs from canonical contract"
        )

    return payload


def run_software_only_end_to_end_qualification(
    *,
    dataset_root: str | Path,
    split_manifest: str | Path,
    output_root: str | Path,
    trajectory_id: str = REPRESENTATIVE_TRAJECTORY,
    max_replay_messages: int = 20000,
) -> dict[str, object]:
    output = Path(
        output_root
    )

    if output.exists():
        raise SE4SoftwareOnlyE2EQualificationError(
            "qualification output root already exists"
        )

    staging = output.with_name(
        "."
        + output.name
        + ".partial"
    )

    if staging.exists():
        raise SE4SoftwareOnlyE2EQualificationError(
            "qualification partial output already exists"
        )

    staging.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:
        real_lane = run_real_data_lane(
            dataset_root=
                dataset_root,

            split_manifest=
                split_manifest,

            trajectory_id=
                trajectory_id,

            max_replay_messages=
                max_replay_messages,
        )

        synthetic_lane = run_synthetic_live_lane(
            working_root=
                staging
                / "synthetic_live_lane",
        )

        receipt: dict[str, object] = {
            "schema":
                QUALIFICATION_SCHEMA,

            "schema_version":
                1,

            "qualification_id":
                "TRUST_ROBOT_SE4_SOFTWARE_ONLY_END_TO_END_QUALIFICATION_V1",

            "software_only":
                True,

            "real_data_lane":
                real_lane,

            "synthetic_live_lane":
                synthetic_lane,

            "final_assertions": {
                "real_network_IO_executed":
                    False,

                "real_sensor_contact":
                    False,

                "real_runtime_binding_count":
                    0,

                "real_execution_authorization_count":
                    0,

                "grounded_authorization_record_count":
                    0,

                "accepted_baseline_nominality_source_count":
                    0,

                "accepted_health_supervision_source_count":
                    0,

                "real_health_label_count":
                    0,

                "interval_binding_established":
                    False,

                "physical_measurement_time_established":
                    False,

                "SE4_complete":
                    False,

                "SE4_training_authorized":
                    False,

                "SE5_may_proceed":
                    False,

                "validation_open":
                    False,

                "confirmation_open":
                    False,

                "ATE_RPE_computed":
                    False,
            },

            "outcome":
                (
                    "CURRENT_IMPLEMENTABLE_SOFTWARE_STACK_OPERATES_END_TO_END_"
                    "WITHOUT_FABRICATING_PHYSICAL_OR_HEALTH_EVIDENCE"
                ),
        }

        receipt[
            "content_sha256"
        ] = content_sha256(
            receipt
        )

        receipt_path = (
            staging
            / "software_only_e2e_qualification_receipt.json"
        )

        receipt_path.write_text(
            json.dumps(
                receipt,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            staging,
            output,
        )

        final_receipt = (
            output
            / receipt_path.name
        )

        return {
            "output_root":
                str(
                    output
                ),

            "receipt_path":
                str(
                    final_receipt
                ),

            "receipt_file_sha256":
                file_sha256(
                    final_receipt
                ),

            "receipt_content_sha256":
                receipt[
                    "content_sha256"
                ],

            "receipt":
                receipt,
        }

    except Exception:
        raise
