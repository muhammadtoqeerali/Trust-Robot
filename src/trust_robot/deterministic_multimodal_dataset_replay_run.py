"""Persistent artifact layer for TRUST-ROBOT SE1 deterministic replay.

The artifact layer records aggregate replay evidence without writing raw
per-message observations or treating availability/timestamps as health or
physical synchronization evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Optional
import json

from .deterministic_multimodal_dataset_replay import (
    FROZEN_SPLIT_SHA256,
    SCHEMA as REPLAY_SCHEMA,
    STREAM_ORDER,
    ReplayEnvelope,
    TrainReplaySource,
)
from .software_evidence_completion import (
    TRAIN_TRAJECTORIES,
)


CANDIDATE_SCHEMA = (
    "TRUST_ROBOT_SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY_CANDIDATE_V1"
)

TRAJECTORY_SCHEMA = (
    "TRUST_ROBOT_SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY_TRAJECTORY_V1"
)

RUN_SCHEMA = (
    "TRUST_ROBOT_SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY_RUN_V1"
)

RUN_ID = (
    "trust_robot_se1_m2dgr_deterministic_multimodal_dataset_replay_v1"
)


class DeterministicReplayRunError(ValueError):
    """Raised when persistent SE1 replay evidence violates its contract."""


def canonical_json_bytes(
    payload: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_sha256(
    payload: Mapping[str, Any],
) -> str:
    unhashed = dict(
        payload
    )

    unhashed.pop(
        "content_sha256",
        None,
    )

    return sha256(
        canonical_json_bytes(
            unhashed
        )
    ).hexdigest()


def file_sha256(
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


def _update_payload_sequence_digest(
    digest: Any,
    payload: bytes,
) -> None:
    digest.update(
        len(
            payload
        ).to_bytes(
            8,
            byteorder="big",
            signed=False,
        )
    )

    digest.update(
        payload
    )


@dataclass
class StreamReplayAggregateBuilder:
    """Aggregate one declared stream without retaining individual messages."""

    trajectory_id: str
    source_stream_id: str
    modality: str
    message_type: Optional[str] = None
    message_count: int = 0
    total_serialized_payload_bytes: int = 0
    header_stamp_present_count: int = 0
    first_observed_bag_record_time_ns: Optional[int] = None
    last_observed_bag_record_time_ns: Optional[int] = None
    first_observed_header_stamp_ns: Optional[int] = None
    last_observed_header_stamp_ns: Optional[int] = None
    _metadata_digest: Any = field(
        default_factory=sha256,
        repr=False,
    )
    _payload_sequence_digest: Any = field(
        default_factory=sha256,
        repr=False,
    )

    def add(
        self,
        envelope: ReplayEnvelope,
    ) -> None:
        if envelope.trajectory_id != self.trajectory_id:
            raise DeterministicReplayRunError(
                "stream aggregate trajectory identity changed"
            )

        if envelope.split_role != "train":
            raise DeterministicReplayRunError(
                "stream aggregate accepts TRAIN replay only"
            )

        if envelope.source_stream_id != self.source_stream_id:
            raise DeterministicReplayRunError(
                "stream aggregate source stream identity changed"
            )

        if envelope.modality != self.modality:
            raise DeterministicReplayRunError(
                "stream aggregate modality changed"
            )

        if envelope.stream_message_index != self.message_count:
            raise DeterministicReplayRunError(
                "stream message indices must be contiguous from zero"
            )

        if self.message_type is None:
            self.message_type = (
                envelope.message_type
            )

        elif self.message_type != envelope.message_type:
            raise DeterministicReplayRunError(
                "message type changed inside one replay stream"
            )

        metadata = (
            envelope.metadata_payload()
        )

        self._metadata_digest.update(
            canonical_json_bytes(
                metadata
            )
        )
        self._metadata_digest.update(
            b"\n"
        )

        _update_payload_sequence_digest(
            self._payload_sequence_digest,
            envelope.serialized_payload,
        )

        self.message_count += 1
        self.total_serialized_payload_bytes += (
            envelope.serialized_payload_bytes
        )

        if self.first_observed_bag_record_time_ns is None:
            self.first_observed_bag_record_time_ns = (
                envelope.bag_record_time_ns
            )

        self.last_observed_bag_record_time_ns = (
            envelope.bag_record_time_ns
        )

        if envelope.header_stamp_ns is not None:
            self.header_stamp_present_count += 1

            if self.first_observed_header_stamp_ns is None:
                self.first_observed_header_stamp_ns = (
                    envelope.header_stamp_ns
                )

            self.last_observed_header_stamp_ns = (
                envelope.header_stamp_ns
            )

    def payload(
        self,
    ) -> dict[str, Any]:
        return {
            "trajectory_id":
                self.trajectory_id,

            "split_role":
                "train",

            "source_stream_id":
                self.source_stream_id,

            "modality":
                self.modality,

            "manifest_declared_present":
                True,

            "message_type":
                self.message_type,

            "message_count":
                self.message_count,

            "total_serialized_payload_bytes":
                self.total_serialized_payload_bytes,

            "header_stamp_present_count":
                self.header_stamp_present_count,

            "first_observed_bag_record_time_ns":
                self.first_observed_bag_record_time_ns,

            "last_observed_bag_record_time_ns":
                self.last_observed_bag_record_time_ns,

            "first_observed_header_stamp_ns":
                self.first_observed_header_stamp_ns,

            "last_observed_header_stamp_ns":
                self.last_observed_header_stamp_ns,

            "aggregate_replay_metadata_sha256":
                self._metadata_digest.hexdigest(),

            "aggregate_serialized_payload_sequence_sha256":
                self._payload_sequence_digest.hexdigest(),

            "timestamp_boundary": {
                "bag_record_time_is_transport_provenance":
                    True,

                "bag_record_time_is_physical_capture_time_proof":
                    False,

                "header_stamp_preserved_when_structurally_present":
                    True,

                "header_stamp_is_shared_physical_clock_proof":
                    False,

                "fixed_offset_selected":
                    False,

                "interpolation_performed":
                    False,
            },

            "health_boundary": {
                "availability_is_health_label":
                    False,

                "health_label_assigned":
                    False,

                "health_probability_emitted":
                    False,
            },
        }


class TrajectoryReplayAggregateBuilder:
    """Aggregate one trajectory in unchanged selected reader-emission order."""

    def __init__(
        self,
        source: TrainReplaySource,
    ) -> None:
        if not isinstance(
            source,
            TrainReplaySource,
        ):
            raise DeterministicReplayRunError(
                "source must be a validated TrainReplaySource"
            )

        if source.split_role != "train":
            raise DeterministicReplayRunError(
                "trajectory aggregate accepts TRAIN source only"
            )

        self.source = source
        self.message_count = 0
        self.total_serialized_payload_bytes = 0
        self.header_stamp_present_count = 0
        self.first_observed_bag_record_time_ns: Optional[int] = None
        self.last_observed_bag_record_time_ns: Optional[int] = None
        self.first_observed_header_stamp_ns: Optional[int] = None
        self.last_observed_header_stamp_ns: Optional[int] = None

        self._metadata_digest = sha256()
        self._payload_sequence_digest = sha256()

        self._streams = {
            stream.stream_id:
                StreamReplayAggregateBuilder(
                    trajectory_id=source.trajectory_id,
                    source_stream_id=stream.stream_id,
                    modality=stream.modality,
                )
            for stream in source.streams
        }

    def add(
        self,
        envelope: ReplayEnvelope,
    ) -> None:
        if envelope.trajectory_id != self.source.trajectory_id:
            raise DeterministicReplayRunError(
                "trajectory identity changed during replay"
            )

        if envelope.split_role != "train":
            raise DeterministicReplayRunError(
                "trajectory replay envelope is not TRAIN"
            )

        if envelope.source_bag_relative_path != self.source.bag_relative_path:
            raise DeterministicReplayRunError(
                "bag relative-path provenance changed during replay"
            )

        if envelope.source_bag_sha256 != self.source.bag_sha256:
            raise DeterministicReplayRunError(
                "bag SHA-256 provenance changed during replay"
            )

        if envelope.record_index != self.message_count:
            raise DeterministicReplayRunError(
                "trajectory replay record indices must be contiguous "
                "from zero in reader emission order"
            )

        if envelope.source_stream_id not in self._streams:
            raise DeterministicReplayRunError(
                "trajectory replay emitted an undeclared stream"
            )

        metadata = (
            envelope.metadata_payload()
        )

        self._metadata_digest.update(
            canonical_json_bytes(
                metadata
            )
        )
        self._metadata_digest.update(
            b"\n"
        )

        _update_payload_sequence_digest(
            self._payload_sequence_digest,
            envelope.serialized_payload,
        )

        self._streams[
            envelope.source_stream_id
        ].add(
            envelope
        )

        self.message_count += 1
        self.total_serialized_payload_bytes += (
            envelope.serialized_payload_bytes
        )

        if self.first_observed_bag_record_time_ns is None:
            self.first_observed_bag_record_time_ns = (
                envelope.bag_record_time_ns
            )

        self.last_observed_bag_record_time_ns = (
            envelope.bag_record_time_ns
        )

        if envelope.header_stamp_ns is not None:
            self.header_stamp_present_count += 1

            if self.first_observed_header_stamp_ns is None:
                self.first_observed_header_stamp_ns = (
                    envelope.header_stamp_ns
                )

            self.last_observed_header_stamp_ns = (
                envelope.header_stamp_ns
            )

    def payload(
        self,
        *,
        bag_file_size_bytes: int,
    ) -> dict[str, Any]:
        if (
            type(
                bag_file_size_bytes
            ) is not int
            or bag_file_size_bytes <= 0
        ):
            raise DeterministicReplayRunError(
                "bag file size must be a positive exact integer"
            )

        stream_payloads = [
            self._streams[
                stream.stream_id
            ].payload()
            for stream in self.source.streams
        ]

        payload: dict[str, Any] = {
            "schema":
                TRAJECTORY_SCHEMA,

            "replay_schema":
                REPLAY_SCHEMA,

            "run_id":
                RUN_ID,

            "stage_id":
                "SE1",

            "dataset_id":
                "M2DGR",

            "trajectory_id":
                self.source.trajectory_id,

            "split_role":
                "train",

            "bag_relative_path":
                self.source.bag_relative_path,

            "bag_manifest_sha256":
                self.source.bag_sha256,

            "bag_file_size_bytes":
                bag_file_size_bytes,

            "availability":
                self.source.availability_payload(),

            "declared_stream_count":
                len(
                    self.source.streams
                ),

            "streams":
                stream_payloads,

            "message_count":
                self.message_count,

            "total_serialized_payload_bytes":
                self.total_serialized_payload_bytes,

            "header_stamp_present_count":
                self.header_stamp_present_count,

            "first_observed_bag_record_time_ns":
                self.first_observed_bag_record_time_ns,

            "last_observed_bag_record_time_ns":
                self.last_observed_bag_record_time_ns,

            "first_observed_header_stamp_ns":
                self.first_observed_header_stamp_ns,

            "last_observed_header_stamp_ns":
                self.last_observed_header_stamp_ns,

            "aggregate_reader_order_metadata_sha256":
                self._metadata_digest.hexdigest(),

            "aggregate_reader_order_serialized_payload_sequence_sha256":
                self._payload_sequence_digest.hexdigest(),

            "ordering_contract": {
                "record_index_basis":
                    "selected_reader_emission_order",

                "reader_emission_order_preserved":
                    True,

                "timestamp_sort_performed":
                    False,

                "cross_stream_synchronization_performed":
                    False,
            },

            "artifact_contract": {
                "raw_per_message_payload_written":
                    False,

                "per_message_metadata_artifact_written":
                    False,

                "stream_aggregate_evidence_written":
                    True,

                "trajectory_reader_order_digest_written":
                    True,
            },

            "scientific_boundary": {
                "train_only":
                    True,

                "validation_bag_opened":
                    False,

                "confirmation_bag_opened":
                    False,

                "reference_data_read":
                    False,

                "availability_is_health_label":
                    False,

                "missing_measurement_is_zero_feature_vector":
                    False,

                "fabricated_streams":
                    False,

                "physical_measurement_time_selected":
                    False,

                "shared_clock_domain_verified":
                    False,

                "fixed_offset_selected":
                    False,

                "interpolation_performed":
                    False,

                "feature_extraction_performed":
                    False,

                "health_label_assigned":
                    False,

                "health_probability_emitted":
                    False,

                "model_training_performed":
                    False,

                "reference_association_performed":
                    False,

                "ate_rpe_computed":
                    False,

                "final_score_computed":
                    False,
            },
        }

        payload[
            "content_sha256"
        ] = content_sha256(
            payload
        )

        return payload


def build_candidate_contract(
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema":
            CANDIDATE_SCHEMA,

        "run_id":
            RUN_ID,

        "stage_id":
            "SE1",

        "dataset_id":
            "M2DGR",

        "split_scope":
            "train",

        "frozen_split_file_sha256":
            FROZEN_SPLIT_SHA256,

        "trajectory_order":
            list(
                TRAIN_TRAJECTORIES
            ),

        "trajectory_count":
            len(
                TRAIN_TRAJECTORIES
            ),

        "supported_replay_stream_order":
            list(
                STREAM_ORDER
            ),

        "reader": {
            "package":
                "rosbags",

            "interface":
                "rosbags.highlevel.AnyReader",
        },

        "execution_contract": {
            "trajectory_processing":
                "sequential_frozen_train_order",

            "message_processing":
                "selected_reader_emission_order",

            "timestamp_sort":
                False,

            "cross_stream_synchronization":
                False,

            "interpolation":
                False,

            "missing_stream_fabrication":
                False,

            "failure_policy":
                "fail_closed",
        },

        "output_contract": {
            "candidate_contract":
                True,

            "per_trajectory_aggregate_json":
                True,

            "run_manifest":
                True,

            "success_marker":
                True,

            "per_message_raw_payload_written":
                False,

            "per_message_metadata_artifact_written":
                False,

            "aggregate_metadata_digest":
                True,

            "aggregate_serialized_payload_sequence_digest":
                True,
        },

        "scientific_boundary": {
            "validation_access":
                False,

            "confirmation_access":
                False,

            "reference_data_read":
                False,

            "feature_selection":
                False,

            "feature_extraction":
                False,

            "health_supervision":
                False,

            "health_label_assignment":
                False,

            "health_probability_inference":
                False,

            "model_training":
                False,

            "threshold_selection":
                False,

            "probability_calibration":
                False,

            "physical_capture_synchronization_inference":
                False,

            "reference_association":
                False,

            "ate_rpe":
                False,

            "final_scoring":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def build_trajectory_record(
    *,
    trajectory_payload: Mapping[str, Any],
    trajectory_file_sha256: str,
) -> dict[str, Any]:
    trajectory_id = trajectory_payload.get(
        "trajectory_id"
    )

    if trajectory_id not in TRAIN_TRAJECTORIES:
        raise DeterministicReplayRunError(
            "trajectory record is outside frozen TRAIN"
        )

    expected_content_sha256 = content_sha256(
        trajectory_payload
    )

    if trajectory_payload.get(
        "content_sha256"
    ) != expected_content_sha256:
        raise DeterministicReplayRunError(
            "trajectory payload content SHA-256 is invalid"
        )

    if (
        type(
            trajectory_file_sha256
        ) is not str
        or len(
            trajectory_file_sha256
        ) != 64
    ):
        raise DeterministicReplayRunError(
            "trajectory file SHA-256 is malformed"
        )

    return {
        "trajectory_id":
            trajectory_id,

        "trajectory_file_sha256":
            trajectory_file_sha256,

        "trajectory_content_sha256":
            expected_content_sha256,

        "declared_stream_count":
            trajectory_payload[
                "declared_stream_count"
            ],

        "message_count":
            trajectory_payload[
                "message_count"
            ],

        "total_serialized_payload_bytes":
            trajectory_payload[
                "total_serialized_payload_bytes"
            ],

        "aggregate_reader_order_metadata_sha256":
            trajectory_payload[
                "aggregate_reader_order_metadata_sha256"
            ],

        "aggregate_reader_order_serialized_payload_sequence_sha256":
            trajectory_payload[
                "aggregate_reader_order_serialized_payload_sequence_sha256"
            ],
    }


def build_run_manifest(
    *,
    dataset_root: str,
    candidate_contract_content_sha256: str,
    trajectory_records: list[Mapping[str, Any]],
) -> dict[str, Any]:
    actual_order = tuple(
        record.get(
            "trajectory_id"
        )
        for record in trajectory_records
    )

    if actual_order != TRAIN_TRAJECTORIES:
        raise DeterministicReplayRunError(
            "trajectory records must follow the exact frozen TRAIN order"
        )

    aggregate = sha256()

    total_messages = 0
    total_bytes = 0

    for record in trajectory_records:
        aggregate.update(
            canonical_json_bytes(
                record
            )
        )
        aggregate.update(
            b"\n"
        )

        total_messages += int(
            record[
                "message_count"
            ]
        )

        total_bytes += int(
            record[
                "total_serialized_payload_bytes"
            ]
        )

    payload: dict[str, Any] = {
        "schema":
            RUN_SCHEMA,

        "run_id":
            RUN_ID,

        "stage_id":
            "SE1",

        "dataset_id":
            "M2DGR",

        "split_scope":
            "train",

        "frozen_split_file_sha256":
            FROZEN_SPLIT_SHA256,

        "candidate_contract_content_sha256":
            candidate_contract_content_sha256,

        "dataset_root":
            dataset_root,

        "trajectory_count":
            len(
                trajectory_records
            ),

        "trajectory_order":
            list(
                TRAIN_TRAJECTORIES
            ),

        "trajectory_records":
            list(
                trajectory_records
            ),

        "aggregate_trajectory_record_sha256":
            aggregate.hexdigest(),

        "total_selected_replay_messages":
            total_messages,

        "total_selected_serialized_payload_bytes":
            total_bytes,

        "scientific_boundary": {
            "train_only":
                True,

            "validation_bags_opened":
                False,

            "confirmation_bags_opened":
                False,

            "reference_data_read":
                False,

            "stream_synchronization_performed":
                False,

            "timestamp_sort_performed":
                False,

            "interpolation_performed":
                False,

            "feature_extraction_performed":
                False,

            "health_labels_assigned":
                False,

            "health_probability_inference_performed":
                False,

            "model_training_performed":
                False,

            "ate_rpe_computed":
                False,

            "final_score_computed":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def build_success_payload(
    *,
    run_manifest_file_sha256: str,
    run_manifest_content_sha256: str,
    total_selected_replay_messages: int,
    total_selected_serialized_payload_bytes: int,
) -> dict[str, Any]:
    return {
        "run_id":
            RUN_ID,

        "stage_id":
            "SE1",

        "status":
            "success",

        "run_manifest_file_sha256":
            run_manifest_file_sha256,

        "run_manifest_content_sha256":
            run_manifest_content_sha256,

        "train_trajectory_count":
            len(
                TRAIN_TRAJECTORIES
            ),

        "total_selected_replay_messages":
            total_selected_replay_messages,

        "total_selected_serialized_payload_bytes":
            total_selected_serialized_payload_bytes,

        "validation_bags_opened":
            False,

        "confirmation_bags_opened":
            False,

        "reference_data_read":
            False,

        "health_labels_assigned":
            False,

        "model_training_performed":
            False,

        "ate_rpe_computed":
            False,

        "final_score_computed":
            False,
    }
