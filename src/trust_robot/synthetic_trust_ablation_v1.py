"""R135-A31-6: four-way toy trust-screening ablation.

Compares:
1. Unscreened synthetic updates.
2. Toy innovation NIS-only screening.
3. Simulated software-delivery-only screening.
4. Combined toy NIS + software-delivery screening.

All state updates remain synthetic numerical operations.
Neither software delivery nor toy NIS can certify real
sensor health, physical association, or factor admission.
"""

from __future__ import annotations

from fractions import Fraction

from trust_robot.synthetic_15d_kalman_v1 import (
    propose_toy_kalman_update,
)

from trust_robot.replay_observability_v1 import (
    review_software_observability,
)

SCHEMA = "TRUST_ROBOT_R135_A31_6_SYNTHETIC_ABLATION_V1"

VARIANTS = {
    "unscreened_toy": (False, False),
    "toy_nis_only": (True, False),
    "software_delivery_only": (False, True),
    "combined_toy_screening": (True, True),
}


class SyntheticAblationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SyntheticAblationError(message)


def run_toy_ablation(
    state,
    covariance,
    descriptors,
    scenario,
    *,
    nis_limit_num=4,
    nis_limit_den=1,
):
    """Run independent toy trajectories under four fixed policies."""

    require(
        type(nis_limit_num) is int
        and type(nis_limit_den) is int
        and 0 <= nis_limit_num <= 1000000
        and 1 <= nis_limit_den <= 1000000,
        "Invalid predeclared toy NIS threshold",
    )

    require(
        type(descriptors) is list
        and 1 <= len(descriptors) <= 16,
        "Invalid bounded toy descriptor list",
    )

    delivery = review_software_observability(scenario)

    first = descriptors[0]

    require(
        type(first) is dict
        and first.get("source_kind") == "SYNTHETIC_ONLY",
        "Only synthetic candidate descriptors are allowed",
    )

    stream = first.get("stream")
    domain = first.get("clock_domain")

    previous_sequence = None
    previous_stamp = None

    for descriptor in descriptors:
        require(
            type(descriptor) is dict
            and descriptor.get("source_kind") == "SYNTHETIC_ONLY"
            and descriptor.get("stream") == stream
            and descriptor.get("clock_domain") == domain,
            "Mixed or non-synthetic toy candidate stream",
        )

        sequence = descriptor.get("sequence")
        stamp = descriptor.get("event_stamp_ns")

        require(
            type(sequence) is int
            and type(stamp) is int
            and sequence >= 0
            and stamp >= 0,
            "Invalid toy event sequence or time",
        )

        require(
            previous_sequence is None
            or sequence > previous_sequence,
            "Toy event sequences are not strictly ordered",
        )

        require(
            previous_stamp is None
            or stamp >= previous_stamp,
            "Toy event times are not ordered",
        )

        previous_sequence = sequence
        previous_stamp = stamp

    label = delivery["stream_labels"][stream][
        "software_label"
    ]

    delivery_available = (
        label ==
        "SOFTWARE_DELIVERY_WITHIN_DECLARED_THRESHOLD"
    )

    threshold = Fraction(
        nis_limit_num, nis_limit_den
    )

    variants = {}

    for name, (use_nis, use_delivery) in VARIANTS.items():
        current_state = list(state)
        current_covariance = [
            list(row) for row in covariance
        ]

        accepted = 0
        decisions = []

        for descriptor in descriptors:
            proposal = propose_toy_kalman_update(
                current_state,
                current_covariance,
                descriptor,
            )

            nis = proposal["toy_full_innovation_nis"]

            nis_allowed = (
                Fraction.from_float(nis) <= threshold
            )

            if use_delivery and not delivery_available:
                decision = "WITHHELD_SOFTWARE_DELIVERY"
                selected = False

            elif use_nis and not nis_allowed:
                decision = "WITHHELD_TOY_NIS"
                selected = False

            else:
                decision = "ACCEPTED_SYNTHETIC_UPDATE_ONLY"
                selected = True

            if selected:
                current_state = proposal[
                    "posterior_state_15"
                ]
                current_covariance = proposal[
                    "posterior_covariance_15x15"
                ]
                accepted += 1

            decisions.append({
                "sequence": descriptor["sequence"],
                "toy_full_nis": nis,
                "software_delivery_label": label,
                "toy_decision": decision,
                "synthetic_update_applied": selected,
            })

        variants[name] = {
            "toy_candidates": len(descriptors),
            "accepted_synthetic_updates": accepted,
            "withheld_toy_updates":
                len(descriptors) - accepted,
            "decisions": decisions,
            "final_toy_state_15": current_state,
            "final_covariance_trace": sum(
                current_covariance[i][i]
                for i in range(15)
            ),
            "physical_state_updated": False,
            "real_factor_count": 0,
            "real_factor_admission": "DENIED",
        }

    return {
        "schema": SCHEMA,
        "status": "FOUR_WAY_SYNTHETIC_ABLATION_ONLY",
        "toy_candidate_count": len(descriptors),
        "toy_stream": stream,
        "software_delivery_label": label,
        "predeclared_nis_limit": [
            nis_limit_num, nis_limit_den,
        ],
        "variants": variants,
        "physical_sensor_health_measured": False,
        "physical_clock_mapping_verified": False,
        "physical_factor_weights_computed": False,
        "real_robot_state_updated": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def apply_real_ablation_policy(*args, **kwargs):
    raise SyntheticAblationError(
        "Synthetic ablation cannot authorize physical factors"
    )
