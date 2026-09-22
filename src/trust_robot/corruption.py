from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
import json

import numpy as np


CORRUPTION_SCHEMA = "TRUST_ROBOT_PAIRED_CORRUPTION_V1"


class CorruptionError(ValueError):
    """Raised when a corruption contract is invalid or inadmissible."""


class SensorModality(str, Enum):
    IMU = "imu"
    CAMERA = "camera"
    LIDAR = "lidar"
    DEPTH = "depth"
    GNSS = "gnss"
    WHEEL_ODOMETRY = "wheel_odometry"
    PROPRIOCEPTION = "proprioception"
    OTHER = "other"


class CorruptionFamily(str, Enum):
    EVENT_GAP = "EVENT_GAP"
    EVENT_REPEAT = "EVENT_REPEAT"
    TIMESTAMP_STEP_SHIFT = "TIMESTAMP_STEP_SHIFT"


class ScenarioContext(str, Enum):
    UNATTRIBUTED = "unattributed"
    FAULT = "fault"
    ENVIRONMENTAL_DEGRADATION = "environmental_degradation"
    ATTACK = "attack"


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


def _readonly_array(
    value,
    *,
    dtype=None,
) -> np.ndarray:
    array = np.asarray(
        value,
        dtype=dtype,
    )

    if array.dtype.hasobject:
        raise CorruptionError(
            "object-dtype arrays are not permitted in deterministic streams"
        )

    copied = np.ascontiguousarray(
        array
    ).copy()

    copied.setflags(
        write=False
    )

    return copied


def _json_mapping(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    mapping = {
        str(key):
            item
        for key, item
        in dict(
            value
            or {}
        ).items()
    }

    _canonical_json(
        mapping
    )

    return MappingProxyType(
        mapping
    )


@dataclass(
    frozen=True,
)
class EventStream:
    """Immutable multimodal sequence of timestamped numerical payloads.

    Each event payload may have a different shape. This supports, for example:

    - IMU vectors;
    - image arrays;
    - LiDAR point clouds with varying point count;
    - other numerical event payloads.

    The class itself does not claim that timestamps are physically
    synchronized. They are simply the event labels supplied by an adapter.
    """

    modality: SensorModality
    source_id: str
    timestamps_ns: np.ndarray
    payloads: tuple[np.ndarray, ...]
    origin_indices: np.ndarray | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "modality",
            SensorModality(
                self.modality
            ),
        )

        source_id = str(
            self.source_id
        ).strip()

        if not source_id:
            raise CorruptionError(
                "source_id cannot be empty"
            )

        object.__setattr__(
            self,
            "source_id",
            source_id,
        )

        timestamps = _readonly_array(
            self.timestamps_ns,
            dtype=np.int64,
        )

        if timestamps.ndim != 1:
            raise CorruptionError(
                "timestamps_ns must have shape (n_events,)"
            )

        n_events = int(
            timestamps.shape[0]
        )

        if n_events < 1:
            raise CorruptionError(
                "EventStream must contain at least one event"
            )

        payloads = tuple(
            _readonly_array(
                payload
            )
            for payload
            in self.payloads
        )

        if len(
            payloads
        ) != n_events:
            raise CorruptionError(
                "payload count must equal timestamp count"
            )

        if self.origin_indices is None:
            origin = np.arange(
                n_events,
                dtype=np.int64,
            )
            origin.setflags(
                write=False
            )
        else:
            origin = _readonly_array(
                self.origin_indices,
                dtype=np.int64,
            )

            if origin.shape != (
                n_events,
            ):
                raise CorruptionError(
                    "origin_indices must have shape (n_events,)"
                )

            if np.any(
                origin < 0
            ):
                raise CorruptionError(
                    "origin_indices cannot contain negative values"
                )

        object.__setattr__(
            self,
            "timestamps_ns",
            timestamps,
        )

        object.__setattr__(
            self,
            "payloads",
            payloads,
        )

        object.__setattr__(
            self,
            "origin_indices",
            origin,
        )

        object.__setattr__(
            self,
            "metadata",
            _json_mapping(
                self.metadata
            ),
        )

    @property
    def n_events(
        self,
    ) -> int:
        return int(
            self.timestamps_ns.shape[0]
        )

    def timestamps_strictly_increasing(
        self,
    ) -> bool:
        if self.n_events < 2:
            return True

        return bool(
            np.all(
                np.diff(
                    self.timestamps_ns
                )
                > 0
            )
        )

    def fingerprint(
        self,
    ) -> str:
        digest = sha256()

        digest.update(
            CORRUPTION_SCHEMA.encode(
                "utf-8"
            )
        )

        digest.update(
            self.modality.value.encode(
                "utf-8"
            )
        )

        digest.update(
            self.source_id.encode(
                "utf-8"
            )
        )

        digest.update(
            _canonical_json(
                dict(
                    self.metadata
                )
            ).encode(
                "utf-8"
            )
        )

        for name, array in (
            (
                "timestamps_ns",
                self.timestamps_ns,
            ),
            (
                "origin_indices",
                self.origin_indices,
            ),
        ):
            digest.update(
                name.encode(
                    "utf-8"
                )
            )

            digest.update(
                array.dtype.str.encode(
                    "ascii"
                )
            )

            digest.update(
                _canonical_json(
                    list(
                        array.shape
                    )
                ).encode(
                    "utf-8"
                )
            )

            digest.update(
                array.tobytes(
                    order="C"
                )
            )

        for index, payload in enumerate(
            self.payloads
        ):
            digest.update(
                f"payload:{index}".encode(
                    "ascii"
                )
            )

            digest.update(
                payload.dtype.str.encode(
                    "ascii"
                )
            )

            digest.update(
                _canonical_json(
                    list(
                        payload.shape
                    )
                ).encode(
                    "utf-8"
                )
            )

            digest.update(
                payload.tobytes(
                    order="C"
                )
            )

        return digest.hexdigest()


@dataclass(
    frozen=True,
)
class CorruptionSpec:
    family: CorruptionFamily
    modality: SensorModality
    start_index: int
    length: int

    scenario_context: ScenarioContext = (
        ScenarioContext.UNATTRIBUTED
    )

    severity_id: str | None = None
    seed: int | None = None
    threat_model_id: str | None = None

    parameters: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "family",
            CorruptionFamily(
                self.family
            ),
        )

        object.__setattr__(
            self,
            "modality",
            SensorModality(
                self.modality
            ),
        )

        object.__setattr__(
            self,
            "scenario_context",
            ScenarioContext(
                self.scenario_context
            ),
        )

        if (
            isinstance(
                self.start_index,
                bool,
            )
            or not isinstance(
                self.start_index,
                int,
            )
            or self.start_index < 0
        ):
            raise CorruptionError(
                "start_index must be an integer >= 0"
            )

        if (
            isinstance(
                self.length,
                bool,
            )
            or not isinstance(
                self.length,
                int,
            )
            or self.length < 1
        ):
            raise CorruptionError(
                "length must be an integer >= 1"
            )

        if self.seed is not None:
            if (
                isinstance(
                    self.seed,
                    bool,
                )
                or not isinstance(
                    self.seed,
                    int,
                )
            ):
                raise CorruptionError(
                    "seed must be an integer or None"
                )

        severity = (
            None
            if self.severity_id is None
            else str(
                self.severity_id
            ).strip()
        )

        if severity == "":
            raise CorruptionError(
                "severity_id cannot be blank"
            )

        object.__setattr__(
            self,
            "severity_id",
            severity,
        )

        threat_model = (
            None
            if self.threat_model_id is None
            else str(
                self.threat_model_id
            ).strip()
        )

        if threat_model == "":
            raise CorruptionError(
                "threat_model_id cannot be blank"
            )

        if (
            self.scenario_context
            is ScenarioContext.ATTACK
            and threat_model is None
        ):
            raise CorruptionError(
                "attack scenario_context requires an explicit threat_model_id"
            )

        if (
            self.scenario_context
            is not ScenarioContext.ATTACK
            and threat_model is not None
        ):
            raise CorruptionError(
                "threat_model_id is only valid for attack scenario_context"
            )

        object.__setattr__(
            self,
            "threat_model_id",
            threat_model,
        )

        object.__setattr__(
            self,
            "parameters",
            _json_mapping(
                self.parameters
            ),
        )

    def canonical_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "family":
                self.family.value,

            "modality":
                self.modality.value,

            "start_index":
                self.start_index,

            "length":
                self.length,

            "scenario_context":
                self.scenario_context.value,

            "severity_id":
                self.severity_id,

            "seed":
                self.seed,

            "threat_model_id":
                self.threat_model_id,

            "parameters":
                dict(
                    self.parameters
                ),
        }

    @property
    def spec_id(
        self,
    ) -> str:
        payload = _canonical_json(
            self.canonical_dict()
        ).encode(
            "utf-8"
        )

        return (
            "TRC_SPEC_"
            + sha256(
                payload
            ).hexdigest()[
                :24
            ]
        )


@dataclass(
    frozen=True,
)
class CorruptionTruth:
    spec: CorruptionSpec
    injection_id: str

    clean_event_count: int
    corrupt_event_count: int

    affected_clean_start: int
    affected_clean_end_exclusive: int

    corrupt_anchor_index: int

    details: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        injection_id = str(
            self.injection_id
        ).strip()

        if not injection_id:
            raise CorruptionError(
                "injection_id cannot be empty"
            )

        object.__setattr__(
            self,
            "injection_id",
            injection_id,
        )

        object.__setattr__(
            self,
            "details",
            _json_mapping(
                self.details
            ),
        )

    def manifest_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "injection_id":
                self.injection_id,

            "spec_id":
                self.spec.spec_id,

            "spec":
                self.spec.canonical_dict(),

            "clean_event_count":
                self.clean_event_count,

            "corrupt_event_count":
                self.corrupt_event_count,

            "affected_clean_start":
                self.affected_clean_start,

            "affected_clean_end_exclusive":
                self.affected_clean_end_exclusive,

            "corrupt_anchor_index":
                self.corrupt_anchor_index,

            "details":
                dict(
                    self.details
                ),

            "synthetic_truth_is_physical_cause_evidence":
                False,

            "synthetic_truth_is_runtime_causal_evidence":
                False,
        }


@dataclass(
    frozen=True,
)
class PairedCorruption:
    clean: EventStream
    corrupt: EventStream
    truths: tuple[CorruptionTruth, ...]

    def __post_init__(
        self,
    ) -> None:
        truths = tuple(
            self.truths
        )

        if not truths:
            raise CorruptionError(
                "PairedCorruption requires at least one truth record"
            )

        if (
            self.clean.modality
            is not self.corrupt.modality
        ):
            raise CorruptionError(
                "clean and corrupt modality must match"
            )

        if (
            self.clean.source_id
            != self.corrupt.source_id
        ):
            raise CorruptionError(
                "clean and corrupt source_id must match"
            )

        object.__setattr__(
            self,
            "truths",
            truths,
        )


def _validate_clean_stream(
    clean: EventStream,
) -> None:
    if not clean.timestamps_strictly_increasing():
        raise CorruptionError(
            "clean EventStream timestamps must be strictly increasing"
        )


def _validate_modality(
    clean: EventStream,
    spec: CorruptionSpec,
) -> None:
    if clean.modality is not spec.modality:
        raise CorruptionError(
            "corruption specification modality does not match clean stream"
        )


def _validate_empty_parameters(
    spec: CorruptionSpec,
) -> None:
    if dict(
        spec.parameters
    ):
        raise CorruptionError(
            f"{spec.family.value} does not accept parameters"
        )


def _validate_bounds(
    clean: EventStream,
    spec: CorruptionSpec,
) -> int:
    end = (
        spec.start_index
        + spec.length
    )

    if end > clean.n_events:
        raise CorruptionError(
            "corruption range exceeds clean stream bounds"
        )

    return end


def _instance_id(
    clean: EventStream,
    spec: CorruptionSpec,
) -> str:
    raw = (
        CORRUPTION_SCHEMA
        + ":"
        + clean.fingerprint()
        + ":"
        + spec.spec_id
    ).encode(
        "utf-8"
    )

    return (
        "TRC_INJ_"
        + sha256(
            raw
        ).hexdigest()[
            :24
        ]
    )


def _stream_from_components(
    source: EventStream,
    *,
    timestamps_ns,
    payloads,
    origin_indices,
) -> EventStream:
    return EventStream(
        modality=
            source.modality,

        source_id=
            source.source_id,

        timestamps_ns=
            timestamps_ns,

        payloads=
            tuple(
                payloads
            ),

        origin_indices=
            origin_indices,

        metadata=
            dict(
                source.metadata
            ),
    )


def inject_event_gap(
    clean: EventStream,
    spec: CorruptionSpec,
) -> PairedCorruption:
    _validate_clean_stream(
        clean
    )

    _validate_modality(
        clean,
        spec,
    )

    if spec.family is not CorruptionFamily.EVENT_GAP:
        raise CorruptionError(
            "inject_event_gap requires EVENT_GAP spec"
        )

    _validate_empty_parameters(
        spec
    )

    end = _validate_bounds(
        clean,
        spec,
    )

    if spec.start_index == 0:
        raise CorruptionError(
            "EVENT_GAP must leave a pre-gap event"
        )

    if end >= clean.n_events:
        raise CorruptionError(
            "EVENT_GAP must leave a post-gap event"
        )

    keep = np.ones(
        clean.n_events,
        dtype=bool,
    )

    keep[
        spec.start_index:
        end
    ] = False

    timestamps = clean.timestamps_ns[
        keep
    ]

    origins = clean.origin_indices[
        keep
    ]

    payloads = tuple(
        payload
        for payload, keep_value
        in zip(
            clean.payloads,
            keep,
            strict=True,
        )
        if bool(
            keep_value
        )
    )

    corrupt = _stream_from_components(
        clean,
        timestamps_ns=
            timestamps,

        payloads=
            payloads,

        origin_indices=
            origins,
    )

    truth = CorruptionTruth(
        spec=
            spec,

        injection_id=
            _instance_id(
                clean,
                spec,
            ),

        clean_event_count=
            clean.n_events,

        corrupt_event_count=
            corrupt.n_events,

        affected_clean_start=
            spec.start_index,

        affected_clean_end_exclusive=
            end,

        corrupt_anchor_index=
            spec.start_index,

        details={
            "removed_event_count":
                spec.length,

            "clean_origin_indices_removed":
                [
                    int(
                        value
                    )
                    for value
                    in clean.origin_indices[
                        spec.start_index:
                        end
                    ]
                ],
        },
    )

    return PairedCorruption(
        clean=
            clean,

        corrupt=
            corrupt,

        truths=(
            truth,
        ),
    )


def inject_event_repeat(
    clean: EventStream,
    spec: CorruptionSpec,
) -> PairedCorruption:
    _validate_clean_stream(
        clean
    )

    _validate_modality(
        clean,
        spec,
    )

    if spec.family is not CorruptionFamily.EVENT_REPEAT:
        raise CorruptionError(
            "inject_event_repeat requires EVENT_REPEAT spec"
        )

    _validate_empty_parameters(
        spec
    )

    end = _validate_bounds(
        clean,
        spec,
    )

    if spec.start_index == 0:
        raise CorruptionError(
            "EVENT_REPEAT start_index must be >= 1"
        )

    repeated_payload = clean.payloads[
        spec.start_index
        - 1
    ]

    payloads = [
        payload.copy()
        for payload
        in clean.payloads
    ]

    changed = False

    for index in range(
        spec.start_index,
        end,
    ):
        if not np.array_equal(
            clean.payloads[
                index
            ],
            repeated_payload,
        ):
            changed = True

        payloads[
            index
        ] = repeated_payload.copy()

    if not changed:
        raise CorruptionError(
            "EVENT_REPEAT produced no payload change"
        )

    corrupt = _stream_from_components(
        clean,
        timestamps_ns=
            clean.timestamps_ns,

        payloads=
            payloads,

        origin_indices=
            clean.origin_indices,
    )

    truth = CorruptionTruth(
        spec=
            spec,

        injection_id=
            _instance_id(
                clean,
                spec,
            ),

        clean_event_count=
            clean.n_events,

        corrupt_event_count=
            corrupt.n_events,

        affected_clean_start=
            spec.start_index,

        affected_clean_end_exclusive=
            end,

        corrupt_anchor_index=
            spec.start_index,

        details={
            "payload_repeated_from_clean_index":
                spec.start_index
                - 1,

            "timestamps_preserved":
                True,

            "clean_origin_indices_preserved":
                True,
        },
    )

    return PairedCorruption(
        clean=
            clean,

        corrupt=
            corrupt,

        truths=(
            truth,
        ),
    )


def inject_timestamp_step_shift(
    clean: EventStream,
    spec: CorruptionSpec,
) -> PairedCorruption:
    _validate_clean_stream(
        clean
    )

    _validate_modality(
        clean,
        spec,
    )

    if (
        spec.family
        is not CorruptionFamily.TIMESTAMP_STEP_SHIFT
    ):
        raise CorruptionError(
            "inject_timestamp_step_shift requires TIMESTAMP_STEP_SHIFT spec"
        )

    if spec.length != 1:
        raise CorruptionError(
            "TIMESTAMP_STEP_SHIFT requires length=1"
        )

    if (
        spec.start_index <= 0
        or spec.start_index >= clean.n_events
    ):
        raise CorruptionError(
            "TIMESTAMP_STEP_SHIFT requires an internal event boundary"
        )

    parameters = dict(
        spec.parameters
    )

    if set(
        parameters
    ) != {
        "offset_ns"
    }:
        raise CorruptionError(
            "TIMESTAMP_STEP_SHIFT requires only parameters['offset_ns']"
        )

    offset = parameters[
        "offset_ns"
    ]

    if (
        isinstance(
            offset,
            bool,
        )
        or not isinstance(
            offset,
            int,
        )
    ):
        raise CorruptionError(
            "TIMESTAMP_STEP_SHIFT offset_ns must be an integer"
        )

    if offset == 0:
        raise CorruptionError(
            "TIMESTAMP_STEP_SHIFT offset_ns must be non-zero"
        )

    suffix = clean.timestamps_ns[
        spec.start_index:
    ]

    info = np.iinfo(
        np.int64
    )

    if offset > 0:
        if int(
            np.max(
                suffix
            )
        ) > (
            int(
                info.max
            )
            - offset
        ):
            raise CorruptionError(
                "TIMESTAMP_STEP_SHIFT would overflow int64"
            )

    else:
        if int(
            np.min(
                suffix
            )
        ) < (
            int(
                info.min
            )
            - offset
        ):
            raise CorruptionError(
                "TIMESTAMP_STEP_SHIFT would underflow int64"
            )

    timestamps = clean.timestamps_ns.copy()

    timestamps[
        spec.start_index:
    ] += offset

    corrupt = _stream_from_components(
        clean,
        timestamps_ns=
            timestamps,

        payloads=
            clean.payloads,

        origin_indices=
            clean.origin_indices,
    )

    truth = CorruptionTruth(
        spec=
            spec,

        injection_id=
            _instance_id(
                clean,
                spec,
            ),

        clean_event_count=
            clean.n_events,

        corrupt_event_count=
            corrupt.n_events,

        affected_clean_start=
            spec.start_index,

        affected_clean_end_exclusive=
            spec.start_index
            + 1,

        corrupt_anchor_index=
            spec.start_index,

        details={
            "timestamp_offset_ns":
                offset,

            "mode":
                "step_shift_all_later_event_labels",

            "payloads_preserved":
                True,

            "clean_origin_indices_preserved":
                True,

            "physical_timestamp_semantics_claimed":
                False,
        },
    )

    return PairedCorruption(
        clean=
            clean,

        corrupt=
            corrupt,

        truths=(
            truth,
        ),
    )


def apply_corruption(
    clean: EventStream,
    spec: CorruptionSpec,
) -> PairedCorruption:
    if spec.family is CorruptionFamily.EVENT_GAP:
        return inject_event_gap(
            clean,
            spec,
        )

    if spec.family is CorruptionFamily.EVENT_REPEAT:
        return inject_event_repeat(
            clean,
            spec,
        )

    if (
        spec.family
        is CorruptionFamily.TIMESTAMP_STEP_SHIFT
    ):
        return inject_timestamp_step_shift(
            clean,
            spec,
        )

    raise CorruptionError(
        f"unsupported corruption family: {spec.family.value}"
    )


def build_pair_manifest(
    pair: PairedCorruption,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema":
            CORRUPTION_SCHEMA,

        "clean": {
            "modality":
                pair.clean.modality.value,

            "source_id":
                pair.clean.source_id,

            "event_count":
                pair.clean.n_events,

            "fingerprint_sha256":
                pair.clean.fingerprint(),
        },

        "corrupt": {
            "modality":
                pair.corrupt.modality.value,

            "source_id":
                pair.corrupt.source_id,

            "event_count":
                pair.corrupt.n_events,

            "fingerprint_sha256":
                pair.corrupt.fingerprint(),
        },

        "truths": [
            truth.manifest_dict()
            for truth
            in pair.truths
        ],

        "scientific_scope": {
            "paired_clean_corrupt":
                True,

            "clean_input_mutated":
                False,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "severity_selected_by_engine":
                False,

            "attack_budget_selected_by_engine":
                False,

            "synthetic_truth_is_physical_cause_evidence":
                False,

            "synthetic_truth_is_runtime_causal_evidence":
                False,

            "estimator_scoring_performed":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,
        },
    }

    canonical = _canonical_json(
        payload
    ).encode(
        "utf-8"
    )

    payload[
        "manifest_content_sha256"
    ] = sha256(
        canonical
    ).hexdigest()

    return payload


def manifest_json(
    pair: PairedCorruption,
) -> str:
    return (
        json.dumps(
            build_pair_manifest(
                pair
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def write_immutable_manifest(
    path,
    pair: PairedCorruption,
) -> Path:
    path = Path(
        path
    )

    content = manifest_json(
        pair
    )

    if path.exists():
        existing = path.read_text(
            encoding="utf-8"
        )

        if existing != content:
            raise FileExistsError(
                "immutable corruption manifest already exists with different content: "
                f"{path}"
            )

        return path

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix
        + ".tmp"
    )

    if temporary.exists():
        raise FileExistsError(
            f"temporary corruption manifest already exists: {temporary}"
        )

    temporary.write_text(
        content,
        encoding="utf-8",
    )

    temporary.replace(
        path
    )

    return path
