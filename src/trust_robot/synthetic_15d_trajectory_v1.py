"""Toy constant-velocity 15D prediction and dropout/recovery.

All candidate observations, truth, time intervals and delivery
masks are deliberately synthetic.

Counterfactual variants can inspect hypothetical undelivered
toy candidates. Such policies are not physically realizable
sensor processing policies.
"""

from fractions import Fraction
import math

from trust_robot.synthetic_15d_innovation_v1 import (
    innovation,
    vector,
)

from trust_robot.synthetic_15d_kalman_v1 import (
    cholesky,
    matrix,
    transpose,
    multiply,
    add,
    propose_toy_kalman_update,
)

from trust_robot.synthetic_truth_consistency_v1 import (
    check_truth,
    review_toy_consistency,
    summarize_toy_consistency,
)

SCHEMA = "TRUST_ROBOT_R135_A31_7_TOY_TRAJECTORY_V1"

MODES = {
    "counterfactual_all_candidates": (False, False),
    "toy_nis_counterfactual": (True, False),
    "scheduled_delivery_only": (False, True),
    "combined_toy_screening": (True, True),
}

STEP_FIELDS = {
    "index",
    "dt_ns",
    "candidate",
    "software_available",
    "synthetic_truth",
}


class ToyTrajectoryError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ToyTrajectoryError(message)


def predict_toy_15d(
    state,
    covariance,
    *,
    dt_ns,
    acceleration_noise=0.01,
):
    """Synthetic constant-velocity prediction.

    State positions: 0-2
    State velocities: 3-5
    Remaining nine toy coordinates: constant.

    Process noise follows an explicitly synthetic
    discrete acceleration model.
    """

    x = vector(state, 15)
    p = matrix(covariance, 15)
    cholesky(p)

    require(
        type(dt_ns) is int
        and 1 <= dt_ns <= 10**10,
        "Invalid synthetic propagation time",
    )

    require(
        type(acceleration_noise) in (int, float)
        and math.isfinite(acceleration_noise)
        and 0 <= acceleration_noise <= 1e5,
        "Invalid synthetic process variance",
    )

    dt = float(Fraction(dt_ns, 10**9))

    f = [
        [
            1.0 if i == j else 0.0
            for j in range(15)
        ]
        for i in range(15)
    ]

    q = [
        [0.0] * 15
        for _ in range(15)
    ]

    for axis in range(3):
        f[axis][axis + 3] = dt

        q[axis][axis] += (
            acceleration_noise * dt ** 4 / 4
        )

        q[axis][axis + 3] += (
            acceleration_noise * dt ** 3 / 2
        )

        q[axis + 3][axis] += (
            acceleration_noise * dt ** 3 / 2
        )

        q[axis + 3][axis + 3] += (
            acceleration_noise * dt ** 2
        )

    next_x = [
        sum(
            f[i][j] * x[j]
            for j in range(15)
        )
        for i in range(15)
    ]

    next_p = add(
        multiply(
            multiply(f, p),
            transpose(f),
        ),
        q,
    )

    next_p = [
        [
            (next_p[i][j] + next_p[j][i]) / 2
            for j in range(15)
        ]
        for i in range(15)
    ]

    cholesky(next_p)

    require(
        all(math.isfinite(v) for v in next_x),
        "Nonfinite predicted state",
    )

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_PREDICTION_ONLY",
        "predicted_state_15": next_x,
        "predicted_covariance_15x15": next_p,
        "physical_dynamics_verified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def run_toy_trajectory(
    state,
    covariance,
    steps,
    *,
    nis_limit_num=9,
    nis_limit_den=1,
    acceleration_noise=0.01,
):
    """Evaluate four independent synthetic trajectory policies."""

    x0 = vector(state, 15)
    p0 = matrix(covariance, 15)
    cholesky(p0)

    require(
        type(steps) is list
        and 1 <= len(steps) <= 32,
        "Invalid number of synthetic steps",
    )

    require(
        type(nis_limit_num) is int
        and type(nis_limit_den) is int
        and 0 <= nis_limit_num <= 1000000
        and 1 <= nis_limit_den <= 1000000,
        "Invalid declared NIS threshold",
    )

    clock = None
    last_stamp = None

    # Validate the complete schedule, including candidates
    # not available to the delivery-aware policies.

    for i, step in enumerate(steps):
        require(
            type(step) is dict
            and set(step) == STEP_FIELDS
            and type(step["index"]) is int
            and step["index"] == i
            and type(step["software_available"]) is bool,
            "Invalid synthetic schedule step",
        )

        require(
            type(step["dt_ns"]) is int
            and 1 <= step["dt_ns"] <= 10**10,
            "Invalid step time",
        )

        check_truth(step["synthetic_truth"])

        descriptor = step["candidate"]

        require(
            type(descriptor) is dict
            and descriptor.get("source_kind")
            == "SYNTHETIC_ONLY"
            and type(descriptor.get("sequence")) is int
            and descriptor["sequence"] == i,
            "Unqualified or out-of-order toy candidate",
        )

        innovation(x0, descriptor)

        require(
            descriptor["factor_kind"] == "toy_position_xyz",
            "Only declared toy position observations supported",
        )

        require(
            clock is None
            or descriptor["clock_domain"] == clock,
            "Mixed synthetic clock domains",
        )

        clock = descriptor["clock_domain"]

        require(
            last_stamp is None
            or descriptor["event_stamp_ns"] > last_stamp,
            "Non-increasing synthetic timestamps",
        )

        last_stamp = descriptor["event_stamp_ns"]

    variants = {}

    threshold = Fraction(
        nis_limit_num,
        nis_limit_den,
    )

    for name, (use_nis, use_delivery) in MODES.items():
        x = x0[:]
        p = [row[:] for row in p0]

        history = []
        consistency = []
        accepted = 0

        for step in steps:
            prediction = predict_toy_15d(
                x,
                p,
                dt_ns=step["dt_ns"],
                acceleration_noise=acceleration_noise,
            )

            x = prediction["predicted_state_15"]
            p = prediction["predicted_covariance_15x15"]

            proposal = None

            if use_delivery and not step["software_available"]:
                decision = "WITHHELD_SYNTHETIC_DELIVERY"

            else:
                proposal = propose_toy_kalman_update(
                    x,
                    p,
                    step["candidate"],
                )

                nis = proposal["toy_full_innovation_nis"]

                require(
                    math.isfinite(nis) and nis >= 0,
                    "Invalid toy NIS",
                )

                if (
                    use_nis
                    and Fraction.from_float(nis) > threshold
                ):
                    decision = "WITHHELD_TOY_NIS"

                else:
                    decision = "APPLIED_SYNTHETIC_UPDATE"

                    x = proposal["posterior_state_15"]
                    p = proposal["posterior_covariance_15x15"]

                    accepted += 1

            review = review_toy_consistency(
                x,
                p,
                step["synthetic_truth"],
            )

            consistency.append(review)

            history.append({
                "index": step["index"],
                "software_available":
                    step["software_available"],
                "decision": decision,
                "toy_full_nis":
                    None if proposal is None
                    else proposal["toy_full_innovation_nis"],
                "toy_nees_15d": review["toy_nees_15d"],
                "toy_position_squared_error":
                    review["toy_position_squared_error"],
                "physical_measurement_used": False,
            })

        variants[name] = {
            "accepted_toy_updates": accepted,
            "withheld_toy_updates":
                len(steps) - accepted,
            "toy_trajectory_trace": history,
            "toy_consistency":
                summarize_toy_consistency(consistency),
            "final_toy_state_15": x,
            "final_toy_covariance_trace": sum(
                p[i][i] for i in range(15)
            ),
            "physical_state_estimated": False,
            "real_factor_count": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "COUNTERFACTUAL_TOY_TRAJECTORIES_ONLY",
        "step_count": len(steps),
        "synthetic_availability_mask": [
            step["software_available"]
            for step in steps
        ],
        "declared_nis_limit": [
            nis_limit_num,
            nis_limit_den,
        ],
        "variants": variants,
        "counterfactual_undelivered_candidates_not_physical":
            True,
        "statistical_calibration_established": False,
        "physical_ground_truth_verified": False,
        "physical_sensor_health_measured": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def apply_real_trajectory(*args, **kwargs):
    raise ToyTrajectoryError(
        "Toy trajectories cannot execute physical localization"
    )
