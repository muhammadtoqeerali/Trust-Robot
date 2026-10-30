"""R135-A29-4: deterministic, bounded offline replay of metadata envelopes.

Only ordered ROS recorder-metadata envelopes are accepted. Software ticks
are NOT physical time. No payload decoding, pose estimation, frame inference,
clock calibration, or factor admission is implemented here.
"""

from __future__ import annotations

from collections import deque
import hashlib
import json

from trust_robot.physical_ros_bag_envelope_v1 import (
    TOPICS, EnvelopeValidationError, review_envelopes,
)

SCHEMA = "TRUST_ROBOT_R135_A29_4_OFFLINE_REPLAY_V1"
STREAMS = frozenset(v[0] for v in TOPICS.values())


def require(ok, message):
    if not ok:
        raise EnvelopeValidationError(message)


def _digest_event(h, fields):
    h.update(json.dumps(
        fields,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii"))
    h.update(b"\n")


def simulate_replay(
    rows,
    *,
    queue_capacity=32,
    ingress_per_tick=8,
    delivery_per_tick=8,
    suppressed_streams=(),
):
    """Run a deterministic tick-driven FIFO metadata simulation.

    A software tick ingests up to ingress_per_tick source records in
    their original order, then emits up to delivery_per_tick records.

    A full queue causes explicit drop-tail overflow.

    Suppression is a synthetic software scenario even when envelopes
    originate from a physical recording. It is not a measured fault.
    """
    review_envelopes(rows)

    for name, value in (
        ("queue_capacity", queue_capacity),
        ("ingress_per_tick", ingress_per_tick),
        ("delivery_per_tick", delivery_per_tick),
    ):
        require(
            type(value) is int and 1 <= value <= 512,
            "Invalid scheduler parameter: " + name,
        )

    require(
        type(suppressed_streams) in (
            tuple, list, frozenset, set,
        ),
        "Invalid suppressed-stream container",
    )

    require(
        all(type(x) is str for x in suppressed_streams),
        "Suppression entries must be strings",
    )

    require(
        len(suppressed_streams) == len(set(suppressed_streams)),
        "Duplicate stream suppression",
    )

    suppressed = frozenset(suppressed_streams)

    require(
        suppressed <= STREAMS,
        "Unknown suppressed stream",
    )

    queue = deque()

    seen = {name: 0 for name in sorted(STREAMS)}
    deliberate = dict.fromkeys(seen, 0)
    overflow = dict.fromkeys(seen, 0)
    delivered = dict.fromkeys(seen, 0)

    emitted_ordinals = []
    event_hash = hashlib.sha256()

    cursor = 0
    ticks = 0
    peak = 0

    while cursor < len(rows) or queue:
        ticks += 1

        require(
            ticks <= len(rows) + queue_capacity,
            "Unexpected replay tick count",
        )

        for _ in range(ingress_per_tick):
            if cursor >= len(rows):
                break

            ordinal = cursor
            row = rows[cursor]
            cursor += 1

            stream = row["stream"]
            seen[stream] += 1

            _digest_event(event_hash, (
                "source",
                ordinal,
                stream,
                row["sequence"],
                row["recorder_stamp_ns"],
                row["serialized_bytes"],
            ))

            if stream in suppressed:
                deliberate[stream] += 1

                _digest_event(
                    event_hash,
                    ("synthetic_suppression", ordinal),
                )

            elif len(queue) >= queue_capacity:
                overflow[stream] += 1

                _digest_event(
                    event_hash,
                    ("queue_overflow", ordinal),
                )

            else:
                queue.append((ordinal, stream))

                _digest_event(
                    event_hash,
                    ("enqueue", ordinal),
                )

            peak = max(peak, len(queue))

        for _ in range(delivery_per_tick):
            if not queue:
                break

            ordinal, stream = queue.popleft()

            delivered[stream] += 1
            emitted_ordinals.append(ordinal)

            _digest_event(
                event_hash,
                ("emit", ordinal),
            )

        require(
            len(queue) <= queue_capacity,
            "Queue capacity violated",
        )

    require(len(queue) == 0, "Queue not drained")

    require(
        emitted_ordinals == sorted(emitted_ordinals),
        "FIFO output did not preserve source order",
    )

    require(
        all(
            seen[s] == (
                deliberate[s] + overflow[s] + delivered[s]
            )
            for s in seen
        ),
        "Envelope accounting mismatch",
    )

    require(
        sum(seen.values()) == len(rows),
        "Incomplete source accounting",
    )

    return {
        "schema": SCHEMA,
        "status": "OFFLINE_RECORDER_ORDER_SIMULATION_ONLY",
        "input_count": len(rows),
        "tick_count": ticks,
        "queue_capacity": queue_capacity,
        "ingress_per_tick": ingress_per_tick,
        "delivery_per_tick": delivery_per_tick,
        "peak_queued_envelopes": peak,
        "suppressed_streams": sorted(suppressed),
        "source_counts": seen,
        "synthetic_suppressed_counts": deliberate,
        "queue_overflow_counts": overflow,
        "delivered_counts": delivered,
        "delivered_input_ordinals": emitted_ordinals,
        "event_trace_sha256": event_hash.hexdigest(),
        "equal_recorder_stamp_source_order_preserved": True,
        "time_axis":
            "ORDINAL_SOFTWARE_TICKS_NOT_PHYSICAL_SECONDS",
        "header_timestamp_inferred": False,
        "frame_id_inferred": False,
        "payload_decoded": False,
        "real_factor_count": 0,
        "estimator_invoked": False,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def scenario_matrix(rows):
    """Fixed descriptive cases, not physical recovery or health scores."""
    specs = (
        ("lossless_reference", 64, 8, 8, ()),
        (
            "synthetic_lidar_suppression",
            64, 8, 8, ("lidar",),
        ),
        (
            "synthetic_stereo_image_suppression",
            64, 8, 8, ("left_image", "right_image"),
        ),
        (
            "synthetic_imu_suppression",
            64, 8, 8, ("imu",),
        ),
        (
            "synthetic_queue_pressure",
            8, 8, 2, (),
        ),
    )

    results = {}

    for label, cap, incoming, outgoing, suppressed in specs:
        item = simulate_replay(
            rows,
            queue_capacity=cap,
            ingress_per_tick=incoming,
            delivery_per_tick=outgoing,
            suppressed_streams=suppressed,
        )

        # Retain aggregate counts/digest, not individual source
        # ordinals, in the scenario evidence report.
        item.pop("delivered_input_ordinals")

        results[label] = item

    reference = results["lossless_reference"]

    require(
        sum(reference["queue_overflow_counts"].values()) == 0
        and sum(
            reference["synthetic_suppressed_counts"].values()
        ) == 0
        and sum(
            reference["delivered_counts"].values()
        ) == len(rows),
        "Lossless reference is not lossless",
    )

    for item in results.values():
        require(
            item["real_factor_count"] == 0
            and item["real_factor_admission"] == "DENIED"
            and item["m2dgr_gates"] == "11_CLOSED",
            "Admission boundary changed",
        )

    return {
        "schema": SCHEMA,
        "status": "DESCRIPTIVE_SIMULATED_REPLAY_MATRIX_ONLY",
        "scenario_count": len(results),
        "scenarios": results,
        "physical_health_recovery_measured": False,
        "physical_clock_accuracy": "UNVERIFIED",
        "independent_trajectory_reference": "UNVERIFIED",
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def to_estimator_factors(*args, **kwargs):
    """Real sensor factors remain prohibited."""
    raise EnvelopeValidationError(
        "Unqualified envelopes cannot produce real factors"
    )
