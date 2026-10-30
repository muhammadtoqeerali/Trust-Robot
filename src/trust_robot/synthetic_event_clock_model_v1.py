"""A30-5: exact anchored synthetic event-clock model.

No physical clock calibration or ROS-header inference.
Large epoch stamps are handled with rational arithmetic,
not floating-point timestamp conversion.
"""

from __future__ import annotations

from fractions import Fraction

SCHEMA = "TRUST_ROBOT_R135_A30_5_SYNTHETIC_CLOCK_V1"

EVENT_FIELDS = frozenset({
    "domain", "event_kind", "stamp_ns",
    "error_bound_ns", "status",
})

MAP_FIELDS = frozenset({
    "source_domain", "target_domain",
    "source_anchor_ns", "target_anchor_ns",
    "scale_num", "scale_den",
    "mapping_error_ns", "drift_bound_ppb", "status",
})

EVENT_KINDS = frozenset({
    "CAMERA_EXPOSURE",
    "IMU_SAMPLE",
    "LIDAR_FIRING",
    "REFERENCE_POSE",
    "SYNTHETIC_MARKER",
})


class ClockModelError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ClockModelError(message)


def unsigned(value):
    return type(value) is int and value >= 0


def text_token(value):
    return (
        type(value) is str
        and 0 < len(value) <= 128
        and all(33 <= ord(ch) <= 126 for ch in value)
    )


def check_event(event):
    require(
        type(event) is dict and set(event) == EVENT_FIELDS,
        "Unexpected event fields",
    )

    require(
        text_token(event["domain"])
        and event["event_kind"] in EVENT_KINDS,
        "Invalid synthetic event identity",
    )

    require(
        unsigned(event["stamp_ns"])
        and unsigned(event["error_bound_ns"]),
        "Invalid integer nanosecond event",
    )

    require(
        event["status"] == "SYNTHETIC_UNQUALIFIED",
        "Physical event qualification unsupported",
    )

    return True


def check_mapping(mapping):
    require(
        type(mapping) is dict and set(mapping) == MAP_FIELDS,
        "Unexpected clock-mapping fields",
    )

    require(
        text_token(mapping["source_domain"])
        and text_token(mapping["target_domain"])
        and mapping["source_domain"] != mapping["target_domain"],
        "Invalid clock-domain relationship",
    )

    for key in (
        "source_anchor_ns", "target_anchor_ns",
        "mapping_error_ns", "drift_bound_ppb",
    ):
        require(
            unsigned(mapping[key]),
            "Invalid mapping integer: " + key,
        )

    require(
        type(mapping["scale_num"]) is int
        and type(mapping["scale_den"]) is int
        and 1 <= mapping["scale_num"] <= 1000000000
        and 1 <= mapping["scale_den"] <= 1000000000,
        "Invalid positive rational scale",
    )

    require(
        mapping["drift_bound_ppb"] <= 1000000,
        "Unsupported drift bound",
    )

    require(
        mapping["status"] == "SYNTHETIC_MODEL_ONLY",
        "Unverified clock mapping cannot claim qualification",
    )

    return True


def ceiling_fraction(x):
    require(isinstance(x, Fraction) and x >= 0,
            "Invalid bound")
    return -(-x.numerator // x.denominator)


def map_synthetic_event(event, mapping):
    check_event(event)
    check_mapping(mapping)

    require(
        event["domain"] == mapping["source_domain"],
        "Source event clock does not match mapping",
    )

    delta = event["stamp_ns"] - mapping["source_anchor_ns"]
    scale = Fraction(
        mapping["scale_num"], mapping["scale_den"]
    )

    estimate = (
        Fraction(mapping["target_anchor_ns"], 1)
        + scale * delta
    )

    require(
        estimate >= 0,
        "Mapped timestamp would be negative",
    )

    # Conservative bounds:
    # scaled source bound + anchor mapping bound
    # + drift proportional to distance from anchor.
    bound = (
        scale * event["error_bound_ns"]
        + mapping["mapping_error_ns"]
        + Fraction(
            abs(delta) * mapping["drift_bound_ppb"],
            1000000000,
        )
    )

    floor = estimate.numerator // estimate.denominator
    remainder = estimate - floor

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_CLOCK_MAPPING_ONLY",
        "source_domain": event["domain"],
        "target_domain": mapping["target_domain"],
        "event_kind": event["event_kind"],
        "mapped_stamp_floor_ns": floor,
        "mapped_fraction_numerator": remainder.numerator,
        "mapped_fraction_denominator": remainder.denominator,
        "error_bound_ceiling_ns": ceiling_fraction(bound),
        "physical_event_semantics_verified": False,
        "clock_mapping_independently_verified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def synthetic_event_gap(first, second):
    check_event(first)
    check_event(second)

    require(
        first["domain"] == second["domain"],
        "Cannot subtract events from unmatched clock domains",
    )

    difference = second["stamp_ns"] - first["stamp_ns"]
    error = (
        first["error_bound_ns"] + second["error_bound_ns"]
    )

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_EVENT_DIFFERENCE_ONLY",
        "nominal_gap_ns": difference,
        "minimum_gap_ns": difference - error,
        "maximum_gap_ns": difference + error,
        "physical_event_correspondence_verified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def estimate_physical_time_offset(*args, **kwargs):
    raise ClockModelError(
        "Synthetic clock models cannot estimate or qualify "
        "physical sensor time offsets"
    )
