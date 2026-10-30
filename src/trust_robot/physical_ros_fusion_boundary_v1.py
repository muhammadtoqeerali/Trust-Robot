"""R135-A29-1: fail-closed offline ROS sensor-fusion admission boundary.

This module intentionally creates no physical estimator factors.
It does not load ROS, connect to hardware, or access M2DGR.

Successful validation is a diagnostic/schema result, NOT permission
to estimate physical pose or use physical measurements.
"""

from __future__ import annotations

import math

SCHEMA = "TRUST_ROBOT_R135_A29_1_FUSION_BOUNDARY_V1"

ALLOWED_STREAMS = frozenset({
    "imu",
    "left_image",
    "right_image",
    "left_camera_info",
    "right_camera_info",
    "lidar",
    "clock_correlation",
})

ALLOWED_FIELDS = frozenset({
    "stream",
    "sequence",
    "header_stamp_ns",
    "recorder_stamp_ns",
    "frame_id",
    "payload_bytes",
    "source_kind",
})

class FusionBoundaryError(ValueError):
    """Malformed or unsupported input at the scientific boundary."""


def require(ok, message):
    if not ok:
        raise FusionBoundaryError(message)


def validate_descriptor(item):
    """Validate a metadata-only descriptor, never a ROS payload.

    Raw observations, data arrays, factor definitions and unknown
    fields are deliberately rejected.
    """
    require(type(item) is dict, "Descriptor must be a dict")

    require(set(item) == ALLOWED_FIELDS,
            "Unexpected or missing descriptor fields")

    require(item["stream"] in ALLOWED_STREAMS,
            "Unrecognized stream")

    require(item["source_kind"] in ("SYNTHETIC", "PHYSICAL"),
            "Invalid source kind")

    for key in (
        "sequence",
        "header_stamp_ns",
        "recorder_stamp_ns",
        "payload_bytes",
    ):
        value = item[key]
        require(type(value) is int and value >= 0,
                "Invalid nonnegative integer: " + key)

    require(
        type(item["frame_id"]) is str
        and 0 < len(item["frame_id"]) <= 256
        and all(ord(c) >= 32 for c in item["frame_id"]),
        "Invalid frame identifier",
    )

    # Descriptor completeness is NOT physical qualification.
    return {
        "schema": SCHEMA,
        "stream": item["stream"],
        "source_kind": item["source_kind"],
        "descriptor_valid": True,
        "physical_timing_verified": False,
        "physical_extrinsics_verified": False,
        "physical_intrinsics_verified": False,
        "independent_ground_truth_verified": False,
        "estimator_factor_created": False,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def review_batch(items):
    """Produce only inventory counts and permanent closed-gate denials."""
    require(type(items) is list and len(items) <= 10000,
            "Invalid bounded descriptor batch")

    counts = {k: 0 for k in sorted(ALLOWED_STREAMS)}
    previous = {}

    for item in items:
        decision = validate_descriptor(item)

        stream = decision["stream"]
        source = decision["source_kind"]
        stamp = item["header_stamp_ns"]
        sequence = item["sequence"]

        identity = (source, stream)

        if identity in previous:
            last_seq, last_stamp = previous[identity]
            require(sequence > last_seq,
                    "Nonincreasing sequence")
            require(stamp > last_stamp,
                    "Nonincreasing header stamp")

        previous[identity] = (sequence, stamp)
        counts[stream] += 1

    return {
        "schema": SCHEMA,
        "status": "METADATA_ONLY_NO_FACTOR_ADMISSION",
        "descriptor_count": len(items),
        "stream_counts": counts,
        "synthetic_descriptor_test_only":
            all(x["source_kind"] == "SYNTHETIC" for x in items),
        "estimator_invoked": False,
        "physical_pose_estimated": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
        "physical_time_accuracy": "UNVERIFIED",
        "physical_calibration_accuracy": "UNVERIFIED",
        "independent_ground_truth": "UNVERIFIED",
    }


def admit_real_factors(*args, **kwargs):
    """No current physical evidence can authorize this operation."""
    raise FusionBoundaryError(
        "Real sensor factors are scientifically denied"
    )


def score_physical_localization(*args, **kwargs):
    """No independent reference is available for scoring."""
    raise FusionBoundaryError(
        "Independent physical ground truth is unverified"
    )
