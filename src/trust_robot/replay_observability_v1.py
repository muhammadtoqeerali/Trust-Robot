"""A31-2: deterministic software observability of metadata replay.

Labels describe simulated queue delivery, not physical sensor health.
No health probability, factor weight or physical admission is produced.
"""

from __future__ import annotations

from trust_robot.physical_ros_bag_envelope_v1 import TOPICS

SCHEMA = "TRUST_ROBOT_R135_A31_2_REPLAY_OBSERVABILITY_V1"

STREAMS = frozenset(row[0] for row in TOPICS.values())


class ReplayObservabilityError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ReplayObservabilityError(message)


def review_software_observability(
    scenario,
    *,
    minimum_delivered_num=1,
    minimum_delivered_den=2,
):
    require(
        type(scenario) is dict
        and scenario.get("schema")
        == "TRUST_ROBOT_R135_A29_4_OFFLINE_REPLAY_V1"
        and scenario.get("status")
        == "OFFLINE_RECORDER_ORDER_SIMULATION_ONLY",
        "Unexpected replay scenario",
    )

    require(
        type(minimum_delivered_num) is int
        and type(minimum_delivered_den) is int
        and 0 <= minimum_delivered_num
        <= minimum_delivered_den <= 1000
        and minimum_delivered_den > 0,
        "Invalid explicit delivery threshold",
    )

    require(
        scenario.get("real_factor_admission") == "DENIED"
        and scenario.get("m2dgr_gates") == "11_CLOSED"
        and type(scenario.get("real_factor_count")) is int
        and scenario["real_factor_count"] == 0
        and scenario.get("estimator_invoked") is False
        and scenario.get("payload_decoded") is False
        and scenario.get("header_timestamp_inferred") is False
        and scenario.get("frame_id_inferred") is False
        and scenario.get("time_axis")
        == "ORDINAL_SOFTWARE_TICKS_NOT_PHYSICAL_SECONDS",
        "Replay scientific boundary violated",
    )

    tables = []

    for name in (
        "source_counts",
        "synthetic_suppressed_counts",
        "queue_overflow_counts",
        "delivered_counts",
    ):
        value = scenario.get(name)

        require(
            type(value) is dict
            and set(value) == STREAMS
            and all(
                type(n) is int and 0 <= n <= 10000
                for n in value.values()
            ),
            "Invalid per-stream accounting: " + name,
        )

        tables.append(value)

    source, suppressed, overflow, delivered = tables

    total = scenario.get("input_count")

    require(
        type(total) is int
        and 0 < total <= 10000
        and sum(source.values()) == total
        and all(
            source[s] ==
            suppressed[s] + overflow[s] + delivered[s]
            for s in STREAMS
        ),
        "Stream conservation failed",
    )

    require(
        type(scenario.get("queue_capacity")) is int
        and type(scenario.get("peak_queued_envelopes")) is int
        and 1 <= scenario["queue_capacity"] <= 512
        and 0 <= scenario["peak_queued_envelopes"]
        <= scenario["queue_capacity"],
        "Queue bound violation",
    )

    suppression_list = scenario.get("suppressed_streams")

    require(
        type(suppression_list) is list
        and all(type(s) is str for s in suppression_list)
        and suppression_list == sorted(set(suppression_list))
        and set(suppression_list) <= STREAMS
        and all(
            suppressed[s] == 0
            for s in STREAMS - set(suppression_list)
        ),
        "Unexpected synthetic suppression accounting",
    )

    results = {}

    for stream in sorted(STREAMS):
        n = source[stream]

        if n == 0:
            label = "NO_SOURCE_ENVELOPES"
        elif suppressed[stream] > 0:
            label = "INTENTIONALLY_SUPPRESSED_IN_SOFTWARE"
        elif overflow[stream] > 0:
            label = "SOFTWARE_QUEUE_OVERFLOW"
        elif (
            delivered[stream] * minimum_delivered_den
            < n * minimum_delivered_num
        ):
            label = "BELOW_DECLARED_SOFTWARE_DELIVERY_THRESHOLD"
        else:
            label = "SOFTWARE_DELIVERY_WITHIN_DECLARED_THRESHOLD"

        results[stream] = {
            "software_label": label,
            "source": n,
            "synthetic_suppressed": suppressed[stream],
            "queue_overflow": overflow[stream],
            "delivered": delivered[stream],
        }

    return {
        "schema": SCHEMA,
        "status": "SIMULATED_SOFTWARE_DELIVERY_DIAGNOSTIC_ONLY",
        "input_count": total,
        "declared_minimum_delivery_fraction": [
            minimum_delivered_num,
            minimum_delivered_den,
        ],
        "stream_labels": results,
        "physical_sensor_health_measured": False,
        "physical_health_probabilities_generated": False,
        "factor_weights_computed": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def generate_physical_health_weights(*args, **kwargs):
    raise ReplayObservabilityError(
        "Simulation counts cannot authorize physical "
        "health inference or estimator factor weights"
    )
