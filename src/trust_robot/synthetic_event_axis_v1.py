"""A31-9: synthetic trajectory event/propagation time contract.

Requires each event timestamp to equal the initial
synthetic anchor plus the cumulative propagation
intervals. Integer nanoseconds are compared exactly.

No ROS recorder timestamp, physical exposure event,
clock offset or real synchronization is qualified.
"""

from __future__ import annotations

from trust_robot.synthetic_15d_innovation_v1 import innovation
from trust_robot.synthetic_truth_consistency_v1 import check_truth
from trust_robot.synthetic_15d_trajectory_v1 import STEP_FIELDS

SCHEMA = "TRUST_ROBOT_R135_A31_9_EVENT_AXIS_V1"


class SyntheticAxisError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SyntheticAxisError(message)


def check_synthetic_event_axis(steps, *, anchor_ns):
    require(
        type(anchor_ns) is int
        and 0 <= anchor_ns <= 10**19,
        "Invalid synthetic anchor timestamp",
    )

    require(
        type(steps) is list
        and 1 <= len(steps) <= 32,
        "Invalid bounded synthetic schedule",
    )

    clock_domain = None
    current_ns = anchor_ns
    previous_ns = anchor_ns
    trace = []

    for index, step in enumerate(steps):
        require(
            type(step) is dict
            and set(step) == STEP_FIELDS,
            "Unexpected synthetic step fields",
        )

        require(
            type(step["index"]) is int
            and step["index"] == index,
            "Synthetic step index mismatch",
        )

        require(
            type(step["software_available"]) is bool,
            "Invalid synthetic availability flag",
        )

        dt_ns = step["dt_ns"]

        require(
            type(dt_ns) is int
            and 1 <= dt_ns <= 10**10,
            "Invalid propagation interval",
        )

        candidate = step["candidate"]

        require(
            type(candidate) is dict
            and candidate.get("source_kind")
            == "SYNTHETIC_ONLY"
            and candidate.get("factor_kind")
            == "toy_position_xyz",
            "Real or unsupported candidate rejected",
        )

        require(
            type(candidate.get("sequence")) is int
            and candidate["sequence"] == index,
            "Candidate sequence mismatch",
        )

        domain = candidate.get("clock_domain")

        require(
            type(domain) is str
            and 0 < len(domain) <= 128,
            "Invalid synthetic clock domain",
        )

        require(
            clock_domain is None or domain == clock_domain,
            "Mixed synthetic clock domains",
        )

        clock_domain = domain

        # Delegate full descriptor and truth validation
        # to the existing fail-closed toy modules.
        innovation([0.0] * 15, candidate)
        check_truth(step["synthetic_truth"])

        stamp = candidate.get("event_stamp_ns")

        require(
            type(stamp) is int
            and stamp >= 0,
            "Invalid integer nanosecond event",
        )

        current_ns += dt_ns

        require(
            stamp == current_ns,
            "Event timestamp and propagation interval disagree",
        )

        require(
            stamp > previous_ns,
            "Synthetic events are not strictly increasing",
        )

        trace.append({
            "index": index,
            "declared_propagation_dt_ns": dt_ns,
            "synthetic_event_stamp_ns": stamp,
            "observed_event_delta_ns": stamp - previous_ns,
            "axis_discrepancy_ns": 0,
            "software_available":
                step["software_available"],
        })

        previous_ns = stamp

    return {
        "schema": SCHEMA,
        "status": "EXACT_SYNTHETIC_TIME_AXIS_ONLY",
        "anchor_ns": anchor_ns,
        "clock_domain": clock_domain,
        "step_count": len(steps),
        "final_event_stamp_ns": current_ns,
        "time_axis_consistent": True,
        "synthetic_trace": trace,
        "recorder_time_used_as_physical_event": False,
        "physical_event_semantics_verified": False,
        "physical_clock_mapping_verified": False,
        "physical_sync_accuracy_verified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def qualify_real_event_axis(*args, **kwargs):
    raise SyntheticAxisError(
        "Synthetic event-axis consistency does not "
        "qualify physical sensor clocks"
    )
