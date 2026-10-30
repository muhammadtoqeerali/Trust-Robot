"""A31-4: simulation-only trust selection of toy innovations.

Combines the synthetic 15D innovation diagnostic with validated
software replay observability. Selection is not physical sensor
health, a factor weight, an estimator update or admission.
"""

from __future__ import annotations

from fractions import Fraction

from trust_robot.synthetic_15d_innovation_v1 import (
    innovation,
)

from trust_robot.replay_observability_v1 import (
    review_software_observability,
)

SCHEMA = "TRUST_ROBOT_R135_A31_4_SYNTHETIC_TRUST_GATE_V1"


class SyntheticTrustGateError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise SyntheticTrustGateError(message)


def screen_toy_candidate(
    state,
    descriptor,
    scenario,
    *,
    nis_limit_num=4,
    nis_limit_den=1,
):
    """Screen a toy candidate against declared NIS and delivery."""

    require(
        type(nis_limit_num) is int
        and 0 <= nis_limit_num <= 1000000
        and type(nis_limit_den) is int
        and 1 <= nis_limit_den <= 1000000,
        "Invalid predeclared NIS limit",
    )

    diagnostic = innovation(state, descriptor)

    delivery = review_software_observability(scenario)

    stream = diagnostic["stream"]

    label = delivery["stream_labels"][stream][
        "software_label"
    ]

    within_nis = (
        Fraction.from_float(
            diagnostic["normalized_innovation_squared"]
        )
        <= Fraction(nis_limit_num, nis_limit_den)
    )

    if label != "SOFTWARE_DELIVERY_WITHIN_DECLARED_THRESHOLD":
        decision = "WITHHELD_SIMULATED_DELIVERY"

    elif not within_nis:
        decision = "WITHHELD_TOY_INNOVATION"

    else:
        decision = "ELIGIBLE_TOY_DIAGNOSTIC_ONLY"

    return {
        "schema": SCHEMA,
        "status": "SIMULATION_ONLY_NO_ESTIMATOR_FACTOR",
        "toy_stream": stream,
        "toy_factor_kind": diagnostic["factor_kind"],
        "software_delivery_label": label,
        "toy_nis": diagnostic[
            "normalized_innovation_squared"
        ],
        "declared_nis_limit": [
            nis_limit_num,
            nis_limit_den,
        ],
        "toy_decision": decision,
        "toy_selection_only":
            decision == "ELIGIBLE_TOY_DIAGNOSTIC_ONLY",
        "physical_sensor_health_probability": None,
        "factor_weight": None,
        "physical_measurement_qualified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def apply_real_trust_policy(*args, **kwargs):
    raise SyntheticTrustGateError(
        "Simulation-only trust selection cannot control "
        "physical estimator factors"
    )
