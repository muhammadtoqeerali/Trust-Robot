"""A31-1: deterministic synthetic-only clock-aware event association.

Pairing is conservative, greedy, order-preserving and NOT globally optimal.
It does not infer or certify physical clock relationships, frame transforms,
measurement alignment or estimator factors.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json

from trust_robot.synthetic_event_clock_model_v1 import (
    ClockModelError,
    check_event,
    check_mapping,
    map_synthetic_event,
)

SCHEMA = "TRUST_ROBOT_R135_A31_1_SYNTHETIC_ASSOCIATION_V1"


class SyntheticAssociationError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise SyntheticAssociationError(message)


def _ceil(value):
    return -(-value.numerator // value.denominator)


def _checked_events(items):
    require(
        type(items) is list and 0 < len(items) <= 10000,
        "Invalid bounded synthetic event list",
    )

    domain = None
    previous = None

    for item in items:
        try:
            check_event(item)
        except (ClockModelError, KeyError, TypeError) as exc:
            raise SyntheticAssociationError(
                "Invalid synthetic event"
            ) from exc

        if domain is None:
            domain = item["domain"]

        require(
            item["domain"] == domain,
            "Mixed clock domains",
        )

        value = item["stamp_ns"]

        require(
            previous is None or value >= previous,
            "Input stamps not monotone",
        )

        previous = value

    return domain


def associate_synthetic_events(
    left,
    right,
    *,
    tolerance_ns,
    right_to_left_mapping=None,
):
    """Conservative head-first one-to-one pairing without time fitting.

    |t_left-t_right| plus both declared uncertainty bounds
    must not exceed the predeclared integer tolerance.

    This is not a globally optimal pairing algorithm.
    """
    require(
        type(tolerance_ns) is int
        and 0 <= tolerance_ns <= 10**12,
        "Invalid predeclared association tolerance",
    )

    left_domain = _checked_events(left)
    right_domain = _checked_events(right)

    mapping_used = right_to_left_mapping is not None

    if mapping_used:
        try:
            check_mapping(right_to_left_mapping)
        except (ClockModelError, KeyError, TypeError) as exc:
            raise SyntheticAssociationError(
                "Invalid synthetic clock map"
            ) from exc

        require(
            right_to_left_mapping["source_domain"] == right_domain
            and right_to_left_mapping["target_domain"] == left_domain,
            "Incorrect clock map direction",
        )
    else:
        require(
            left_domain == right_domain,
            "Different clocks without explicit synthetic mapping",
        )

    lhs = [
        (Fraction(e["stamp_ns"]), e["error_bound_ns"])
        for e in left
    ]

    rhs = []

    for event in right:
        if mapping_used:
            try:
                mapped = map_synthetic_event(
                    event, right_to_left_mapping
                )
            except (ClockModelError, KeyError, TypeError) as exc:
                raise SyntheticAssociationError(
                    "Synthetic clock conversion failed"
                ) from exc

            stamp = (
                Fraction(mapped["mapped_stamp_floor_ns"])
                + Fraction(
                    mapped["mapped_fraction_numerator"],
                    mapped["mapped_fraction_denominator"],
                )
            )

            bound = mapped["error_bound_ceiling_ns"]
        else:
            stamp = Fraction(event["stamp_ns"])
            bound = event["error_bound_ns"]

        rhs.append((stamp, bound))

    require(
        all(
            rhs[i][0] <= rhs[i + 1][0]
            for i in range(len(rhs) - 1)
        ),
        "Mapped events not ordered",
    )

    i = 0
    j = 0
    matches = []

    while i < len(lhs) and j < len(rhs):
        left_stamp, left_error = lhs[i]
        right_stamp, right_error = rhs[j]

        gap = right_stamp - left_stamp
        bound = abs(gap) + left_error + right_error

        if bound <= tolerance_ns:
            matches.append({
                "left_index": i,
                "right_index": j,
                "right_minus_left_ns_numerator": gap.numerator,
                "right_minus_left_ns_denominator": gap.denominator,
                "worst_case_gap_ceiling_ns": _ceil(bound),
            })

            i += 1
            j += 1

        elif left_stamp <= right_stamp:
            i += 1
        else:
            j += 1

    require(
        len(matches) <= min(len(left), len(right)),
        "Pair accounting violated",
    )

    canonical = json.dumps(
        matches,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_CONSERVATIVE_ASSOCIATION_ONLY",
        "algorithm": "GREEDY_HEAD_FIRST_NOT_GLOBAL_OPTIMUM",
        "predeclared_tolerance_ns": tolerance_ns,
        "clock_mapping_used": mapping_used,
        "left_input_count": len(left),
        "right_input_count": len(right),
        "matched_count": len(matches),
        "unmatched_left_count": len(left) - len(matches),
        "unmatched_right_count": len(right) - len(matches),
        "matches": matches,
        "matches_sha256":
            hashlib.sha256(canonical).hexdigest(),
        "physical_event_correspondence_verified": False,
        "physical_sync_verified": False,
        "estimator_invoked": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def associate_real_sensor_events(*args, **kwargs):
    raise SyntheticAssociationError(
        "No physical event association or factor admission permitted"
    )
