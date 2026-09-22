from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable
import json
import math


RELATIVE_POSE_CONVENTION = "prev_body_T_current_body"
RUN_SCHEMA = "TRUST_ROBOT_CLEAN_BACKBONE_RUN_V1"
RUN_SCHEMA_VERSION = 1


class CleanBackboneError(ValueError):
    """Raised when the clean-backbone mathematical contract is violated."""


def _require_text(
    value: str,
    *,
    name: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise CleanBackboneError(
            f"{name} must be a non-empty string"
        )

    return value


def _finite_vector3(
    value,
    *,
    name: str,
) -> tuple[float, float, float]:
    if len(value) != 3:
        raise CleanBackboneError(
            f"{name} must contain exactly 3 values"
        )

    result = tuple(
        float(item)
        for item in value
    )

    if not all(
        math.isfinite(item)
        for item in result
    ):
        raise CleanBackboneError(
            f"{name} must contain finite values"
        )

    return result


def _canonical_unit_quaternion(
    value,
) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise CleanBackboneError(
            "quaternion_wxyz must contain exactly 4 values"
        )

    q = tuple(
        float(item)
        for item in value
    )

    if not all(
        math.isfinite(item)
        for item in q
    ):
        raise CleanBackboneError(
            "quaternion_wxyz must contain finite values"
        )

    norm_squared = sum(
        item * item
        for item in q
    )

    if (
        not math.isfinite(norm_squared)
        or norm_squared <= 0.0
    ):
        raise CleanBackboneError(
            "quaternion_wxyz must represent a non-zero finite rotation"
        )

    norm = math.sqrt(
        norm_squared
    )

    unit = tuple(
        item / norm
        for item in q
    )

    # q and -q represent exactly the same SO(3) rotation. Canonicalizing the
    # sign makes serialization deterministic without changing the rotation.
    for item in unit:
        if item > 0.0:
            break

        if item < 0.0:
            unit = tuple(
                -component
                for component in unit
            )
            break

    return unit


def _quat_mul_raw(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    lw, lx, ly, lz = left
    rw, rx, ry, rz = right

    return (
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    )


def _quat_conjugate(
    value: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    w, x, y, z = value

    return (
        w,
        -x,
        -y,
        -z,
    )


def rotate_vector(
    quaternion_wxyz: tuple[float, float, float, float],
    vector_xyz: tuple[float, float, float],
) -> tuple[float, float, float]:
    q = _canonical_unit_quaternion(
        quaternion_wxyz
    )

    vector = _finite_vector3(
        vector_xyz,
        name="vector_xyz",
    )

    pure = (
        0.0,
        vector[0],
        vector[1],
        vector[2],
    )

    rotated = _quat_mul_raw(
        _quat_mul_raw(
            q,
            pure,
        ),
        _quat_conjugate(
            q
        ),
    )

    return (
        rotated[1],
        rotated[2],
        rotated[3],
    )


@dataclass(
    frozen=True,
)
class PoseSE3:
    """Rigid transform represented as translation plus unit quaternion.

    `a_T_b.compose(b_T_c)` returns `a_T_c`.
    """

    translation_m: tuple[float, float, float]
    quaternion_wxyz: tuple[float, float, float, float]

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "translation_m",
            _finite_vector3(
                self.translation_m,
                name="translation_m",
            ),
        )

        object.__setattr__(
            self,
            "quaternion_wxyz",
            _canonical_unit_quaternion(
                self.quaternion_wxyz
            ),
        )

    @classmethod
    def identity(
        cls,
    ) -> "PoseSE3":
        return cls(
            translation_m=(
                0.0,
                0.0,
                0.0,
            ),
            quaternion_wxyz=(
                1.0,
                0.0,
                0.0,
                0.0,
            ),
        )

    def compose(
        self,
        other: "PoseSE3",
    ) -> "PoseSE3":
        rotated_translation = rotate_vector(
            self.quaternion_wxyz,
            other.translation_m,
        )

        translation = tuple(
            left + right
            for left, right
            in zip(
                self.translation_m,
                rotated_translation,
                strict=True,
            )
        )

        quaternion = _quat_mul_raw(
            self.quaternion_wxyz,
            other.quaternion_wxyz,
        )

        return PoseSE3(
            translation_m=translation,
            quaternion_wxyz=quaternion,
        )

    def inverse(
        self,
    ) -> "PoseSE3":
        inverse_q = _quat_conjugate(
            self.quaternion_wxyz
        )

        inverse_translation = rotate_vector(
            inverse_q,
            tuple(
                -item
                for item in self.translation_m
            ),
        )

        return PoseSE3(
            translation_m=inverse_translation,
            quaternion_wxyz=inverse_q,
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "translation_m":
                list(
                    self.translation_m
                ),

            "quaternion_wxyz":
                list(
                    self.quaternion_wxyz
                ),
        }


@dataclass(
    frozen=True,
)
class CleanBackboneConfig:
    """Fixed mathematical configuration for one clean relative-pose source."""

    world_frame_id: str
    body_frame_id: str
    relative_pose_source_id: str

    initial_timestamp_ns: int
    initial_pose_world_T_body: PoseSE3

    relative_pose_convention: str = RELATIVE_POSE_CONVENTION

    def __post_init__(
        self,
    ) -> None:
        _require_text(
            self.world_frame_id,
            name="world_frame_id",
        )

        _require_text(
            self.body_frame_id,
            name="body_frame_id",
        )

        _require_text(
            self.relative_pose_source_id,
            name="relative_pose_source_id",
        )

        if (
            not isinstance(
                self.initial_timestamp_ns,
                int,
            )
            or isinstance(
                self.initial_timestamp_ns,
                bool,
            )
        ):
            raise CleanBackboneError(
                "initial_timestamp_ns must be an integer"
            )

        if (
            self.relative_pose_convention
            != RELATIVE_POSE_CONVENTION
        ):
            raise CleanBackboneError(
                "unsupported relative-pose convention"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "world_frame_id":
                self.world_frame_id,

            "body_frame_id":
                self.body_frame_id,

            "relative_pose_source_id":
                self.relative_pose_source_id,

            "initial_timestamp_ns":
                self.initial_timestamp_ns,

            "initial_pose_world_T_body":
                self.initial_pose_world_T_body.to_dict(),

            "relative_pose_convention":
                self.relative_pose_convention,
        }


@dataclass(
    frozen=True,
)
class RelativePoseIncrement:
    """One fixed-source body-motion increment.

    The transform is previous-body -> current-body and is expressed in the
    previous body frame. This object contains no reference/ground-truth data.
    """

    timestamp_ns: int
    body_frame_id: str
    source_id: str
    delta_prev_body_T_current_body: PoseSE3

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.timestamp_ns,
                int,
            )
            or isinstance(
                self.timestamp_ns,
                bool,
            )
        ):
            raise CleanBackboneError(
                "timestamp_ns must be an integer"
            )

        _require_text(
            self.body_frame_id,
            name="body_frame_id",
        )

        _require_text(
            self.source_id,
            name="source_id",
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "timestamp_ns":
                self.timestamp_ns,

            "body_frame_id":
                self.body_frame_id,

            "source_id":
                self.source_id,

            "delta_prev_body_T_current_body":
                self.delta_prev_body_T_current_body.to_dict(),
        }


@dataclass(
    frozen=True,
)
class CleanBackboneState:
    sequence_index: int
    timestamp_ns: int
    pose_world_T_body: PoseSE3
    last_source_id: str | None

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "sequence_index":
                self.sequence_index,

            "timestamp_ns":
                self.timestamp_ns,

            "pose_world_T_body":
                self.pose_world_T_body.to_dict(),

            "last_source_id":
                self.last_source_id,
        }


class FixedCleanBackbone:
    """Deterministic 6-DoF pose-chain backend.

    This kernel does not extract relative pose from camera, LiDAR, or IMU data.
    A future fixed clean frontend must provide increments using the exact
    convention declared by `CleanBackboneConfig`.

    It performs no reliability weighting, fault detection, health-state
    inference, reference association, alignment, ATE/RPE, or scoring.
    """

    def __init__(
        self,
        config: CleanBackboneConfig,
    ) -> None:
        self._config = config

        self._state = CleanBackboneState(
            sequence_index=0,
            timestamp_ns=
                config.initial_timestamp_ns,
            pose_world_T_body=
                config.initial_pose_world_T_body,
            last_source_id=None,
        )

    @property
    def config(
        self,
    ) -> CleanBackboneConfig:
        return self._config

    @property
    def state(
        self,
    ) -> CleanBackboneState:
        return self._state

    def apply(
        self,
        increment: RelativePoseIncrement,
    ) -> CleanBackboneState:
        if (
            increment.body_frame_id
            != self._config.body_frame_id
        ):
            raise CleanBackboneError(
                "relative-pose body frame does not match fixed backbone body frame"
            )

        if (
            increment.source_id
            != self._config.relative_pose_source_id
        ):
            raise CleanBackboneError(
                "relative-pose source does not match fixed backbone source"
            )

        if (
            increment.timestamp_ns
            <= self._state.timestamp_ns
        ):
            raise CleanBackboneError(
                "relative-pose timestamps must be strictly increasing"
            )

        next_pose = (
            self._state.pose_world_T_body.compose(
                increment.delta_prev_body_T_current_body
            )
        )

        self._state = CleanBackboneState(
            sequence_index=
                self._state.sequence_index
                + 1,

            timestamp_ns=
                increment.timestamp_ns,

            pose_world_T_body=
                next_pose,

            last_source_id=
                increment.source_id,
        )

        return self._state


def run_clean_backbone(
    config: CleanBackboneConfig,
    increments: Iterable[RelativePoseIncrement],
) -> tuple[CleanBackboneState, ...]:
    backbone = FixedCleanBackbone(
        config
    )

    states = [
        backbone.state
    ]

    for increment in increments:
        states.append(
            backbone.apply(
                increment
            )
        )

    return tuple(
        states
    )


def _canonical_json_bytes(
    payload: dict[str, object],
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def build_clean_backbone_run_payload(
    config: CleanBackboneConfig,
    increments: Iterable[RelativePoseIncrement],
) -> dict[str, object]:
    increment_tuple = tuple(
        increments
    )

    states = run_clean_backbone(
        config,
        increment_tuple,
    )

    payload: dict[str, object] = {
        "schema":
            RUN_SCHEMA,

        "schema_version":
            RUN_SCHEMA_VERSION,

        "status":
            "clean_backbone_kernel_run",

        "config":
            config.to_dict(),

        "increments": [
            increment.to_dict()
            for increment in increment_tuple
        ],

        "states": [
            state.to_dict()
            for state in states
        ],

        "scientific_scope": {
            "raw_camera_frontend_executed":
                False,

            "raw_lidar_frontend_executed":
                False,

            "raw_imu_propagation_executed":
                False,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "health_model_used":
                False,

            "fault_threshold_used":
                False,

            "evaluation_metric_computed":
                False,

            "phase2_exit_evidence_satisfied":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = sha256(
        _canonical_json_bytes(
            payload
        )
    ).hexdigest()

    return payload


def clean_backbone_run_content_sha256(
    payload: dict[str, object],
) -> str:
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        _canonical_json_bytes(
            value
        )
    ).hexdigest()
