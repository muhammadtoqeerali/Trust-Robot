"""Deterministic TRAIN-only multimodal dataset replay for TRUST-ROBOT SE1.

This module defines the transport/provenance contract for treating recorded
M2DGR camera, IMU, and LiDAR messages as virtual sensor observations.

It deliberately does not:
- synchronize streams,
- infer common physical capture time,
- invent unavailable streams,
- interpolate measurements,
- assign health labels,
- extract/select diagnostic features,
- train a model,
- open validation or confirmation data,
- read reference trajectories,
- perform association, ATE/RPE, or final scoring.

Replay order is the order supplied by the underlying bag reader. The replay
layer never re-sorts records by bag time or header time.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional
import json

from .software_evidence_completion import (
    TRAIN_TRAJECTORIES,
)


SCHEMA = "TRUST_ROBOT_SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY_V1"

FROZEN_SPLIT_SHA256 = (
    "017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f"
)

CAMERA_STREAM_ID = "/camera/color/image_raw/compressed"
D435I_IMU_STREAM_ID = "/camera/imu"
HANDSFREE_IMU_STREAM_ID = "/handsfree/imu"
LIDAR_STREAM_ID = "/velodyne_points"

STREAM_MODALITY = {
    CAMERA_STREAM_ID: "camera",
    D435I_IMU_STREAM_ID: "imu",
    HANDSFREE_IMU_STREAM_ID: "imu",
    LIDAR_STREAM_ID: "lidar",
}

STREAM_ORDER = (
    CAMERA_STREAM_ID,
    D435I_IMU_STREAM_ID,
    HANDSFREE_IMU_STREAM_ID,
    LIDAR_STREAM_ID,
)

REDUCED_AVAILABILITY_TRAJECTORIES = frozenset(
    {
        "street_010",
        "street_09",
    }
)


class DeterministicReplayError(ValueError):
    """Raised when SE1 replay would violate the frozen replay contract."""


def expected_stream_ids(
    trajectory_id: str,
) -> tuple[str, ...]:
    """Return the frozen TRAIN stream-availability contract."""

    if trajectory_id not in TRAIN_TRAJECTORIES:
        raise DeterministicReplayError(
            "trajectory is not in the frozen TRAIN partition"
        )

    if trajectory_id in REDUCED_AVAILABILITY_TRAJECTORIES:
        return (
            HANDSFREE_IMU_STREAM_ID,
            LIDAR_STREAM_ID,
        )

    return STREAM_ORDER


@dataclass(frozen=True)
class ReplayStream:
    """One estimator-input stream declared by the frozen trajectory manifest."""

    stream_id: str
    modality: str
    frame_id: str
    clock_domain: str
    timestamp_unit: str
    estimator_input: bool
    reference_only: bool


@dataclass(frozen=True)
class TrainReplaySource:
    """Validated TRAIN bag and stream provenance for one trajectory."""

    trajectory_id: str
    split_role: str
    bag_relative_path: str
    bag_sha256: str
    streams: tuple[ReplayStream, ...]

    def stream_by_id(
        self,
    ) -> dict[str, ReplayStream]:
        return {
            stream.stream_id: stream
            for stream in self.streams
        }

    def availability_payload(
        self,
    ) -> list[dict[str, Any]]:
        """Expose manifest availability without converting absence to health."""

        declared = self.stream_by_id()

        return [
            {
                "stream_id": stream_id,
                "modality": STREAM_MODALITY[
                    stream_id
                ],
                "present_in_frozen_manifest":
                    stream_id in declared,
            }
            for stream_id in STREAM_ORDER
        ]

    def contract_payload(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                SCHEMA,

            "stage_id":
                "SE1",

            "trajectory_id":
                self.trajectory_id,

            "split_role":
                self.split_role,

            "bag_relative_path":
                self.bag_relative_path,

            "bag_sha256":
                self.bag_sha256,

            "availability":
                self.availability_payload(),

            "ordering_contract": {
                "preserve_underlying_reader_emission_order":
                    True,

                "resort_by_bag_record_time":
                    False,

                "resort_by_header_time":
                    False,

                "cross_stream_synchronization_performed":
                    False,
            },

            "scientific_boundary": {
                "availability_is_health_label":
                    False,

                "missing_stream_is_zero_feature_vector":
                    False,

                "fabricated_streams_allowed":
                    False,

                "physical_capture_time_inferred":
                    False,

                "shared_clock_domain_inferred":
                    False,

                "fixed_time_offset_selected":
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

                "validation_data_read":
                    False,

                "confirmation_data_read":
                    False,

                "reference_data_read":
                    False,

                "reference_association_performed":
                    False,

                "ate_rpe_computed":
                    False,

                "final_score_computed":
                    False,
            },
        }


def _require_exact_text(
    value: Any,
    label: str,
) -> str:
    if type(value) is not str or not value:
        raise DeterministicReplayError(
            f"{label} must be non-empty exact text"
        )

    return value


def _require_sha256(
    value: Any,
    label: str,
) -> str:
    text = _require_exact_text(
        value,
        label,
    )

    if len(text) != 64:
        raise DeterministicReplayError(
            f"{label} must be a SHA-256 hex digest"
        )

    if any(
        character not in "0123456789abcdef"
        for character in text
    ):
        raise DeterministicReplayError(
            f"{label} must be lowercase SHA-256 hex"
        )

    return text


def build_train_replay_source(
    record: Mapping[str, Any],
) -> TrainReplaySource:
    """Validate one frozen manifest record for SE1 TRAIN replay."""

    if not isinstance(record, Mapping):
        raise DeterministicReplayError(
            "trajectory manifest record must be a mapping"
        )

    trajectory_id = _require_exact_text(
        record.get(
            "trajectory_id"
        ),
        "trajectory_id",
    )

    if trajectory_id not in TRAIN_TRAJECTORIES:
        raise DeterministicReplayError(
            "SE1 may open TRAIN trajectories only"
        )

    if record.get("split") != "train":
        raise DeterministicReplayError(
            "SE1 manifest record must have split=train"
        )

    if record.get("base_trajectory_id") != trajectory_id:
        raise DeterministicReplayError(
            "base trajectory identity differs from trajectory identity"
        )

    if record.get("derivative_kind") != "clean":
        raise DeterministicReplayError(
            "SE1 base replay requires the clean recorded trajectory record"
        )

    expected_bag_path = (
        f"raw/rosbags/{trajectory_id}.bag"
    )

    artifacts = record.get(
        "calibration_artifacts"
    )

    if not isinstance(artifacts, list):
        raise DeterministicReplayError(
            "calibration_artifacts must be a list"
        )

    bag_artifacts = [
        artifact
        for artifact in artifacts
        if isinstance(
            artifact,
            Mapping,
        )
        and artifact.get(
            "source_path"
        ) == expected_bag_path
    ]

    if len(bag_artifacts) != 1:
        raise DeterministicReplayError(
            "exactly one frozen raw-bag integrity artifact is required"
        )

    bag_artifact = bag_artifacts[0]

    if bag_artifact.get(
        "verification_status"
    ) != "verified":
        raise DeterministicReplayError(
            "raw-bag integrity artifact must be verified"
        )

    bag_sha256 = _require_sha256(
        bag_artifact.get(
            "sha256"
        ),
        "raw bag sha256",
    )

    raw_streams = record.get(
        "streams"
    )

    if not isinstance(
        raw_streams,
        list,
    ):
        raise DeterministicReplayError(
            "streams must be a list"
        )

    streams = []
    seen = set()

    for raw in raw_streams:
        if not isinstance(
            raw,
            Mapping,
        ):
            raise DeterministicReplayError(
                "stream entry must be a mapping"
            )

        stream_id = _require_exact_text(
            raw.get(
                "stream_id"
            ),
            "stream_id",
        )

        if stream_id not in STREAM_MODALITY:
            raise DeterministicReplayError(
                "SE1 manifest contains an unsupported or reference stream"
            )

        if stream_id in seen:
            raise DeterministicReplayError(
                "duplicate stream identity in trajectory manifest"
            )

        seen.add(
            stream_id
        )

        modality = _require_exact_text(
            raw.get(
                "modality"
            ),
            "modality",
        )

        if modality != STREAM_MODALITY[
            stream_id
        ]:
            raise DeterministicReplayError(
                "stream modality differs from frozen stream identity"
            )

        if raw.get(
            "estimator_input"
        ) is not True:
            raise DeterministicReplayError(
                "SE1 replay accepts estimator-input streams only"
            )

        if raw.get(
            "reference_only"
        ) is not False:
            raise DeterministicReplayError(
                "SE1 replay may not read reference-only streams"
            )

        timestamp_unit = _require_exact_text(
            raw.get(
                "timestamp_unit"
            ),
            "timestamp_unit",
        )

        if timestamp_unit != "nanoseconds":
            raise DeterministicReplayError(
                "SE1 frozen M2DGR stream timestamp unit changed"
            )

        streams.append(
            ReplayStream(
                stream_id=stream_id,
                modality=modality,
                frame_id=_require_exact_text(
                    raw.get(
                        "frame_id"
                    ),
                    "frame_id",
                ),
                clock_domain=_require_exact_text(
                    raw.get(
                        "clock_domain"
                    ),
                    "clock_domain",
                ),
                timestamp_unit=timestamp_unit,
                estimator_input=True,
                reference_only=False,
            )
        )

    actual_ids = tuple(
        stream.stream_id
        for stream in streams
    )

    expected_ids = expected_stream_ids(
        trajectory_id
    )

    if set(actual_ids) != set(
        expected_ids
    ):
        raise DeterministicReplayError(
            "manifest stream availability differs from frozen TRAIN evidence"
        )

    ordered_streams = tuple(
        next(
            stream
            for stream in streams
            if stream.stream_id == stream_id
        )
        for stream_id in expected_ids
    )

    return TrainReplaySource(
        trajectory_id=trajectory_id,
        split_role="train",
        bag_relative_path=expected_bag_path,
        bag_sha256=bag_sha256,
        streams=ordered_streams,
    )


@dataclass(frozen=True)
class ReplayEnvelope:
    """One virtual-sensor record in unchanged reader emission order."""

    schema: str
    trajectory_id: str
    split_role: str
    source_bag_relative_path: str
    source_bag_sha256: str
    record_index: int
    stream_message_index: int
    source_stream_id: str
    modality: str
    message_type: str
    serialized_payload: bytes
    serialized_payload_bytes: int
    serialized_payload_sha256: str
    bag_record_time_ns: int
    header_stamp_ns: Optional[int]

    def metadata_payload(
        self,
    ) -> dict[str, Any]:
        """Return deterministic provenance without duplicating raw payload."""

        return {
            "schema":
                self.schema,

            "trajectory_id":
                self.trajectory_id,

            "split_role":
                self.split_role,

            "source_bag_relative_path":
                self.source_bag_relative_path,

            "source_bag_sha256":
                self.source_bag_sha256,

            "record_index":
                self.record_index,

            "stream_message_index":
                self.stream_message_index,

            "source_stream_id":
                self.source_stream_id,

            "modality":
                self.modality,

            "message_type":
                self.message_type,

            "serialized_payload_bytes":
                self.serialized_payload_bytes,

            "serialized_payload_sha256":
                self.serialized_payload_sha256,

            "bag_record_time_ns":
                self.bag_record_time_ns,

            "header_stamp_ns":
                self.header_stamp_ns,

            "timestamp_semantics": {
                "bag_record_time_is_transport_provenance":
                    True,

                "bag_record_time_is_proof_of_capture_time":
                    False,

                "header_stamp_is_directly_recorded_when_present":
                    True,

                "header_stamp_is_proof_of_shared_physical_clock":
                    False,
            },
        }


class ReplayEnvelopeBuilder:
    """Assign deterministic replay and per-stream indices in reader order."""

    def __init__(
        self,
        source: TrainReplaySource,
    ) -> None:
        if not isinstance(
            source,
            TrainReplaySource,
        ):
            raise DeterministicReplayError(
                "source must be a validated TrainReplaySource"
            )

        self._source = source
        self._record_index = 0
        self._stream_indices = {
            stream.stream_id: 0
            for stream in source.streams
        }
        self._streams = source.stream_by_id()

    @property
    def next_record_index(
        self,
    ) -> int:
        return self._record_index

    def add(
        self,
        *,
        source_stream_id: str,
        message_type: str,
        serialized_payload: bytes,
        bag_record_time_ns: int,
        header_stamp_ns: Optional[int],
    ) -> ReplayEnvelope:
        """Emit one envelope exactly at the reader's current record position."""

        if source_stream_id not in self._streams:
            raise DeterministicReplayError(
                "reader emitted an undeclared stream"
            )

        message_type = _require_exact_text(
            message_type,
            "message_type",
        )

        if not isinstance(
            serialized_payload,
            bytes,
        ):
            raise DeterministicReplayError(
                "serialized payload must be immutable bytes"
            )

        if type(
            bag_record_time_ns
        ) is not int:
            raise DeterministicReplayError(
                "bag record time must be an exact integer"
            )

        if bag_record_time_ns < 0:
            raise DeterministicReplayError(
                "bag record time must be non-negative"
            )

        if header_stamp_ns is not None:
            if type(
                header_stamp_ns
            ) is not int:
                raise DeterministicReplayError(
                    "header timestamp must be an exact integer or None"
                )

            if header_stamp_ns < 0:
                raise DeterministicReplayError(
                    "header timestamp must be non-negative"
                )

        stream = self._streams[
            source_stream_id
        ]

        stream_message_index = self._stream_indices[
            source_stream_id
        ]

        payload_sha256 = sha256(
            serialized_payload
        ).hexdigest()

        envelope = ReplayEnvelope(
            schema=SCHEMA,
            trajectory_id=self._source.trajectory_id,
            split_role=self._source.split_role,
            source_bag_relative_path=self._source.bag_relative_path,
            source_bag_sha256=self._source.bag_sha256,
            record_index=self._record_index,
            stream_message_index=stream_message_index,
            source_stream_id=source_stream_id,
            modality=stream.modality,
            message_type=message_type,
            serialized_payload=serialized_payload,
            serialized_payload_bytes=len(
                serialized_payload
            ),
            serialized_payload_sha256=payload_sha256,
            bag_record_time_ns=bag_record_time_ns,
            header_stamp_ns=header_stamp_ns,
        )

        self._record_index += 1

        self._stream_indices[
            source_stream_id
        ] += 1

        return envelope

def load_train_replay_source_from_manifest_file(
    manifest_path: Path,
    trajectory_id: str,
    *,
    expected_file_sha256: str = FROZEN_SPLIT_SHA256,
) -> TrainReplaySource:
    """Load exactly one frozen TRAIN replay source from a split manifest.

    The manifest file digest is checked before JSON interpretation. This guard
    prevents SE1 from silently switching to another split definition.
    """

    if not isinstance(
        manifest_path,
        Path,
    ):
        manifest_path = Path(
            manifest_path
        )

    raw = manifest_path.read_bytes()

    actual_sha256 = sha256(
        raw
    ).hexdigest()

    if actual_sha256 != expected_file_sha256:
        raise DeterministicReplayError(
            "split manifest file SHA-256 differs from the frozen SE1 value"
        )

    payload = json.loads(
        raw
    )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise DeterministicReplayError(
            "split manifest root must be a mapping"
        )

    if payload.get(
        "dataset_id"
    ) != "M2DGR":
        raise DeterministicReplayError(
            "SE1 replay manifest dataset_id must be M2DGR"
        )

    records = payload.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise DeterministicReplayError(
            "split manifest records must be a list"
        )

    matches = [
        record
        for record in records
        if isinstance(
            record,
            Mapping,
        )
        and record.get(
            "trajectory_id"
        ) == trajectory_id
    ]

    if len(matches) != 1:
        raise DeterministicReplayError(
            "trajectory must resolve to exactly one frozen manifest record"
        )

    return build_train_replay_source(
        matches[0]
    )


def resolve_train_bag_path(
    dataset_root: Path,
    source: TrainReplaySource,
) -> Path:
    """Resolve the already-validated raw TRAIN bag path."""

    if not isinstance(
        dataset_root,
        Path,
    ):
        dataset_root = Path(
            dataset_root
        )

    dataset_root = dataset_root.resolve()

    bag_path = (
        dataset_root
        / source.bag_relative_path
    ).resolve()

    try:
        bag_path.relative_to(
            dataset_root
        )
    except ValueError as exc:
        raise DeterministicReplayError(
            "resolved bag path escapes the dataset root"
        ) from exc

    if not bag_path.is_file():
        raise DeterministicReplayError(
            "validated TRAIN bag path does not exist"
        )

    return bag_path


def iter_anyreader_replay(
    source: TrainReplaySource,
    bag_path: Path,
    *,
    reader_class: Any = None,
) -> Iterator[ReplayEnvelope]:
    """Replay declared virtual-sensor records in AnyReader emission order.

    Only frozen estimator-input camera/IMU/LiDAR streams are selected.
    No sorting, synchronization, interpolation, association, or scoring occurs.

    ``record_index`` in each envelope is the selected replay reader-emission
    index, not an asserted absolute index among every record in the ROS bag.
    """

    if not isinstance(
        source,
        TrainReplaySource,
    ):
        raise DeterministicReplayError(
            "source must be a validated TrainReplaySource"
        )

    if not isinstance(
        bag_path,
        Path,
    ):
        bag_path = Path(
            bag_path
        )

    if not bag_path.is_file():
        raise DeterministicReplayError(
            "TRAIN replay bag does not exist"
        )

    if bag_path.name != (
        f"{source.trajectory_id}.bag"
    ):
        raise DeterministicReplayError(
            "bag filename differs from frozen trajectory identity"
        )

    if reader_class is None:
        from rosbags.highlevel import (
            AnyReader,
        )

        reader_class = AnyReader

    from .camera_imu_train_ingestion import (
        header_stamp_ns_from_message,
    )

    expected_streams = set(
        source.stream_by_id()
    )

    builder = ReplayEnvelopeBuilder(
        source
    )

    with reader_class(
        [bag_path]
    ) as reader:
        supported_connections = [
            connection
            for connection in reader.connections
            if connection.topic in STREAM_MODALITY
        ]

        supported_topics = {
            connection.topic
            for connection in supported_connections
        }

        if supported_topics != expected_streams:
            raise DeterministicReplayError(
                "bag replay-stream availability differs from the frozen "
                "trajectory manifest"
            )

        selected = [
            connection
            for connection in reader.connections
            if connection.topic in expected_streams
        ]

        selected_topics = {
            connection.topic
            for connection in selected
        }

        if selected_topics != expected_streams:
            raise DeterministicReplayError(
                "not every frozen replay stream has a readable bag connection"
            )

        for connection, timestamp, rawdata in reader.messages(
            connections=selected
        ):
            if connection.topic not in expected_streams:
                raise DeterministicReplayError(
                    "reader emitted a stream outside the frozen replay source"
                )

            raw_bytes = bytes(
                rawdata
            )

            message = reader.deserialize(
                rawdata,
                connection.msgtype,
            )

            header_stamp_ns = (
                header_stamp_ns_from_message(
                    message
                )
            )

            yield builder.add(
                source_stream_id=connection.topic,
                message_type=connection.msgtype,
                serialized_payload=raw_bytes,
                bag_record_time_ns=int(
                    timestamp
                ),
                header_stamp_ns=header_stamp_ns,
            )
