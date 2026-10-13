"""Development-only typed factor provenance and recorded-source gate.

Recorded M2DGR data cannot enter the 15D estimator through this API.

Synthetic camera-style relative-pose packets are distinct from
LiDAR registration outputs. They are not extracted from images.

No synchronization, physical extrinsic, health or calibrated
factor covariance is selected by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from trust_robot.clean_backbone import PoseSE3
from trust_robot.m2dgr_sensor_admission import (
    CAMERA,
    BODY_IMU,
    LIDAR,
    SensorAdmissionError,
    require_real_factor_execution,
)

SCHEMA = "TRUST_ROBOT_MULTIMODAL_FACTOR_INTERFACE_DEV_V1"

ANALYTIC_ORIGIN = "ANALYTIC_FIXTURE"
ANALYTIC_FRAME = "synthetic_body"

CAMERA_SOURCE = "analytic_camera_relative_motion_v1"
LIDAR_SOURCE = "analytic_lidar_registration_v1"

SUPPORTED_RECORDED_SOURCES = frozenset((
    CAMERA, BODY_IMU, LIDAR,
))


class MultimodalFactorError(ValueError):
    """Invalid source identity or unsupported factor provenance."""


@dataclass(frozen=True)
class SyntheticPoseFactor:
    modality: str
    edge: tuple[int, int]
    measurement_id: str
    source_id: str
    frame_id: str
    measurement: PoseSE3
    origin: str = ANALYTIC_ORIGIN

    def __post_init__(self):
        if self.origin != ANALYTIC_ORIGIN:
            raise MultimodalFactorError(
                "Recorded or physical pose factors not authorized"
            )

        expected = {
            "camera": CAMERA_SOURCE,
            "lidar": LIDAR_SOURCE,
        }

        if (
            self.modality not in expected
            or self.source_id != expected[self.modality]
            or self.frame_id != ANALYTIC_FRAME
        ):
            raise MultimodalFactorError(
                "Synthetic modality/frame/source mismatch"
            )

        edge = self.edge

        if (
            type(edge) is not tuple
            or len(edge) != 2
            or any(type(v) is not int for v in edge)
            or edge[0] < 0
            or edge[1] <= edge[0]
        ):
            raise MultimodalFactorError(
                "Invalid relative-pose edge identity"
            )

        if (
            type(self.measurement_id) is not str
            or not self.measurement_id.strip()
            or not isinstance(self.measurement, PoseSE3)
        ):
            raise MultimodalFactorError(
                "Invalid synthetic relative-pose measurement"
            )


def describe_recorded_claim(
    snapshot,
    trajectory_id,
    stream_id,
    header_stamp_ns,
):
    """Inspect an existing recorded stream without admitting a factor.

    One timestamp does not prove inter-stream synchronization.
    Transport timestamps cannot substitute for capture timestamps.
    """
    if trajectory_id not in snapshot["by_id"]:
        raise MultimodalFactorError("Unknown trajectory")

    trajectory = snapshot["by_id"][trajectory_id]

    if trajectory["split"] != "train":
        raise MultimodalFactorError(
            "Held-out source cannot enter development factor interface"
        )

    streams = {
        s["stream_id"]: s
        for s in trajectory["streams"]
    }

    if (
        stream_id not in SUPPORTED_RECORDED_SOURCES
        or stream_id not in streams
    ):
        raise MultimodalFactorError(
            "Unavailable or unsupported recorded source"
        )

    if (
        type(header_stamp_ns) is not int
        or header_stamp_ns < 0
    ):
        raise MultimodalFactorError(
            "Invalid sensor-header timestamp"
        )

    if snapshot["scientific_gates"][
        "real_sensor_factor_execution_authorized"
    ] is not False:
        raise MultimodalFactorError(
            "Unexpected scientific authorization state"
        )

    return {
        "schema": SCHEMA,
        "trajectory_id": trajectory_id,
        "split": "train",
        "stream_id": stream_id,
        "frame_id": streams[stream_id]["frame_id"],
        "observed_header_stamp_ns": header_stamp_ns,
        "header_timestamp_is_sync_proof": False,
        "physical_extrinsic_verified": False,
        "relative_pose_available": False,
        "factor_execution_authorized": False,
        "status": "RECORDED_PROVENANCE_ONLY",
    }


def require_recorded_factor_execution(snapshot, trajectory_id):
    """Do not provide a user-controlled override for frozen gates."""
    try:
        require_real_factor_execution(snapshot, trajectory_id)
    except SensorAdmissionError as exc:
        raise MultimodalFactorError(
            "Recorded factor execution remains blocked"
        ) from exc

    raise MultimodalFactorError(
        "Unexpected real-factor authorization"
    )


def assemble_synthetic_pose_slot(
    lidar_factors: Mapping,
    camera_packets,
    node_frames,
):
    """Build the existing relative-pose solver slot without duplicates.

    Existing 15D estimator code has a single pose-factor dictionary
    historically named 'lidar'. This development-only adapter
    substitutes camera-style measurements on specified edges.

    It does NOT support simultaneous independent camera and LiDAR
    factors on the same edge or distinct camera noise weighting.
    It MUST NOT be used to admit real camera/M2DGR measurements.
    """
    frames = tuple(node_frames)

    if (
        len(frames) < 3
        or type(frames[0]) is not int
        or frames[0] != 0
        or any(type(k) is not int for k in frames)
        or any(b <= a for a, b in zip(frames, frames[1:]))
    ):
        raise MultimodalFactorError(
            "Invalid analytic state chronology"
        )

    merged = {}
    ledger = []
    ids = set()

    for edge, measurement in sorted(lidar_factors.items()):
        if (
            type(edge) is not tuple
            or len(edge) != 2
            or any(type(k) is not int for k in edge)
            or not (0 <= edge[0] < edge[1] < len(frames))
            or not isinstance(measurement, PoseSE3)
        ):
            raise MultimodalFactorError(
                "Invalid synthetic LiDAR registration factor"
            )

        merged[edge] = measurement

    removed_lidar = []

    for packet in camera_packets:
        if not isinstance(packet, SyntheticPoseFactor):
            raise MultimodalFactorError(
                "Unexpected camera factor representation"
            )

        if packet.modality != "camera":
            raise MultimodalFactorError(
                "Only manufactured camera factors may be substituted"
            )

        i, j = packet.edge

        if not (0 <= i < j < len(frames) and j-i <= 2):
            raise MultimodalFactorError(
                "Camera factor outside local estimator horizon"
            )

        if packet.measurement_id in ids:
            raise MultimodalFactorError(
                "Duplicate manufactured camera measurement ID"
            )

        if any(
            row["edge"] == [i, j] and row["modality"] == "camera"
            for row in ledger
        ):
            raise MultimodalFactorError(
                "Duplicate manufactured camera graph edge"
            )

        ids.add(packet.measurement_id)

        if packet.edge in merged:
            removed_lidar.append(packet.edge)

        merged[packet.edge] = packet.measurement

        ledger.append({
            "modality": "camera",
            "edge": [i, j],
            "measurement_id": packet.measurement_id,
            "origin": ANALYTIC_ORIGIN,
            "source_id": packet.source_id,
        })

    cam_edges = {tuple(row["edge"]) for row in ledger}

    for edge in sorted(merged):
        if edge in cam_edges:
            continue

        ledger.append({
            "modality": "lidar",
            "edge": list(edge),
            "measurement_id": (
                f"analytic_lidar_edge:{edge[0]}:{edge[1]}"
            ),
            "origin": ANALYTIC_ORIGIN,
            "source_id": LIDAR_SOURCE,
        })

    assert len(ledger) == len(merged)

    return merged, {
        "schema": SCHEMA,
        "synthetic_camera_factor_count": len(cam_edges),
        "synthetic_lidar_factor_count": (
            len(merged) - len(cam_edges)
        ),
        "total_relative_pose_factor_count": len(merged),
        "replaced_lidar_edges": [
            list(edge) for edge in sorted(removed_lidar)
        ],
        "factor_ledger": sorted(
            ledger,
            key=lambda row: tuple(row["edge"]),
        ),
        "same_edge_measurements_double_counted": False,
        "legacy_backend_pose_slot_is_named_lidar": True,
        "backend_can_independently_weight_camera": False,
        "real_visual_frontend_used": False,
        "real_sensor_factor_execution_authorized": False,
    }
