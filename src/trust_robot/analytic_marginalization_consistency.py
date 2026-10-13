"""Manufactured nonlinear Schur and Gaussian consistency study.

The actual TRUST-ROBOT 15D Schur marginalizer is used.

Two deterministic three-node problems are compared:
  * affine relative-state measurements (exact Schur control);
  * locally nonlinear rotation/translation/velocity measurements.

The eliminated 15D state is reoptimized in the nonlinear profile
objective. Differences from a fixed-first-estimate Schur prior are
reported as approximation error, not physical localization error.

A separate known-noise linear Gaussian experiment tests NEES/NIS
calculations and deliberately mismatched assumed noise.

Neither experiment establishes physical sensor covariance calibration,
held-out localization performance, health labels, or observability.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.stats import chi2

from trust_robot.analytic_schur_marginalization import (
    finite_difference_linearization,
    marginalize_one,
    synthetic_initial_anchor,
)
from trust_robot.analytic_factor_support import (
    analyze_factor_support,
    make_linear_factor,
)

SCHEMA = "TRUST_ROBOT_ANALYTIC_MARGINALIZATION_CONSISTENCY_DEV_V1"
DIM = 15
SIGMA = np.array(
    [0.06]*3 + [0.035]*3 + [0.10]*3
    + [0.025]*3 + [0.025]*3,
    dtype=float,
)
NEAR_SCALE = 0.01
FAR_SCALE = 0.18
NONLINEAR_SEEDS = (11, 29, 47, 83)
GAUSSIAN_TRIALS = 512


def truth(k):
    """Declared synthetic states; not externally measured truth."""
    x = np.zeros(DIM)
    x[:3] = [0.4*k, 0.1*k*k, 0.09*np.sin(k)]
    x[3:6] = [0.13*k, -0.04*k, 0.09*k*k]
    x[6:9] = [0.2+0.04*k, -0.13+0.03*k, 0.1*k]
    x[9:12] = [0.01, -0.005, 0.02]
    x[12:15] = [-0.03, 0.02, 0.005]
    return x


def relative(a, b, model):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    if a.shape != (DIM,) or b.shape != (DIM,):
        raise ValueError("Invalid 15D state")

    if model == "affine":
        return b-a

    if model != "se3":
        raise ValueError("Unknown relative-motion model")

    Ri = Rotation.from_rotvec(a[3:6])
    Rj = Rotation.from_rotvec(b[3:6])

    return np.concatenate((
        Ri.inv().apply(b[:3]-a[:3]),
        (Ri.inv()*Rj).as_rotvec(),
        Ri.inv().apply(b[6:9]-a[6:9]),
        b[9:12]-a[9:12],
        b[12:15]-a[12:15],
    ))


def nonlinear_case(model, seed, *, directions=6):
    """Compare actual Schur prior with reoptimized nonlinear profile."""
    if model not in ("affine", "se3"):
        raise ValueError("Invalid model")
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or seed < 0
        or directions < 1
        or directions > 30
    ):
        raise ValueError("Invalid experiment configuration")

    rng = np.random.default_rng(seed)
    reference_truth = {k: truth(k) for k in range(3)}

    observations = {
        (i, j): (
            relative(reference_truth[i], reference_truth[j], model)
            + rng.normal(size=DIM)*SIGMA
        )
        for i, j in ((0, 1), (0, 2), (1, 2))
    }

    anchor = synthetic_initial_anchor(
        reference_truth[0], sigma=0.2
    )

    def edge(states, i, j):
        return (
            relative(states[i], states[j], model)
            - observations[i, j]
        ) / SIGMA

    def incident(states):
        return np.concatenate((
            anchor.residual(states),
            edge(states, 0, 1),
            edge(states, 0, 2),
        ))

    def full_residual(z):
        states = {
            k: z[k*DIM:(k+1)*DIM]
            for k in range(3)
        }
        return np.concatenate((
            incident(states),
            edge(states, 1, 2),
        ))

    x_initial = np.concatenate([
        reference_truth[k] for k in range(3)
    ])

    solution = least_squares(
        full_residual,
        x_initial,
        loss="linear",
        max_nfev=100,
        ftol=1e-11,
        xtol=1e-11,
        gtol=1e-11,
    )

    if not (
        solution.success
        and np.isfinite(solution.x).all()
        and np.isfinite(solution.cost)
    ):
        raise ValueError("Full nonlinear synthetic solve failed")

    reference = {
        k: solution.x[k*DIM:(k+1)*DIM].copy()
        for k in range(3)
    }

    prior, elimination = marginalize_one(
        (0, 1, 2),
        reference,
        incident,
        0,
    )

    zref = np.r_[reference[1], reference[2]]

    def retained(z):
        return {
            1: z[:DIM],
            2: z[DIM:],
        }

    def fixed_cost(z):
        states = retained(z)
        rp = prior.residual(states)
        rc = edge(states, 1, 2)
        return 0.5*float(rp@rp + rc@rc)

    def profile_cost(z):
        fixed = retained(z)

        def residual_of_eliminated(x0):
            states = {0: x0, **fixed}
            return incident(states)

        fit = least_squares(
            residual_of_eliminated,
            reference[0],
            loss="linear",
            max_nfev=100,
            ftol=1e-11,
            xtol=1e-11,
            gtol=1e-11,
        )

        if not fit.success or not np.isfinite(fit.cost):
            raise ValueError("Nonlinear profile optimization failed")

        current = edge(fixed, 1, 2)
        return float(fit.cost + 0.5*(current@current))

    _, Jcurrent = finite_difference_linearization(
        lambda z: edge(retained(z), 1, 2),
        zref,
    )

    support = analyze_factor_support(
        2*DIM,
        [
            make_linear_factor(
                "schur_historical_prior",
                ("historical_anchor_and_edges",),
                prior.square_root_information,
            ),
            make_linear_factor(
                "unconsumed_current_edge",
                ("current_edge_1_2",),
                Jcurrent,
            ),
        ],
        relative_rank_tolerance=1e-12,
        maximum_condition=1e14,
    )

    if support["status"] != "NUMERICALLY_SUPPORTED":
        raise ValueError("Manufactured Schur support incomplete")

    baseline_fixed = fixed_cost(zref)
    baseline_profile = profile_cost(zref)

    near_errors = []
    far_errors = []

    for _ in range(directions):
        d = rng.normal(size=2*DIM)
        norm = np.linalg.norm(d)
        if norm <= 0:
            raise ValueError("Invalid deterministic perturbation")
        d /= norm

        for scale, destination in (
            (NEAR_SCALE, near_errors),
            (FAR_SCALE, far_errors),
        ):
            candidate = zref + scale*d

            exact_change = (
                profile_cost(candidate) - baseline_profile
            )
            fixed_change = (
                fixed_cost(candidate) - baseline_fixed
            )

            destination.append(
                abs(float(exact_change-fixed_change))
            )

    return {
        "model": model,
        "seed": int(seed),
        "directions": int(directions),
        "full_batch_optimization_success": True,
        "schur_elimination_completed": True,
        "schur_retained_nodes": list(prior.node_ids),
        "schur_retained_rank": (
            elimination["retained_prior_rank"]
        ),
        "local_support_rank": support["numerical_rank"],
        "local_support_dimension": 2*DIM,
        "near_perturbation_norm": NEAR_SCALE,
        "far_perturbation_norm": FAR_SCALE,
        "near_mean_absolute_profile_cost_error": float(
            np.mean(near_errors)
        ),
        "far_mean_absolute_profile_cost_error": float(
            np.mean(far_errors)
        ),
        "near_max_absolute_profile_cost_error": float(
            max(near_errors)
        ),
        "far_max_absolute_profile_cost_error": float(
            max(far_errors)
        ),
        "physical_observability_verified": False,
        "real_sensor_measurements": False,
    }


def gaussian_consistency(trials=GAUSSIAN_TRIALS):
    """NEES/NIS sanity under fully declared synthetic linear Gaussian noise.

    True and assumed noise standard deviations are 1 for the matched
    experiment. The deliberately mismatched case has true standard
    deviation 2 but retains the originally assumed information matrix.

    These are not real-sensor calibration or uncertainty claims.
    """
    if (
        isinstance(trials, bool)
        or not isinstance(trials, int)
        or trials < 100
        or trials > 10000
    ):
        raise ValueError("Invalid Monte Carlo trial count")

    design_rng = np.random.default_rng(77)
    raw = design_rng.normal(size=(45, DIM))
    Q, _ = np.linalg.qr(raw, mode="reduced")
    A = Q @ np.diag(np.linspace(0.8, 2.0, DIM))

    H = A.T @ A
    covariance = np.linalg.inv(H)

    if np.linalg.eigvalsh(covariance)[0] <= 0:
        raise ValueError("Invalid manufactured covariance")

    # Identical standardized noise draws make the mismatch
    # comparison controlled and paired, not independent cohorts.
    draws = np.stack([
        np.random.default_rng(4000+i).normal(size=45)
        for i in range(trials)
    ])

    def evaluate(true_noise_std):
        noise = draws*true_noise_std
        estimated_error = np.linalg.solve(
            H, A.T @ noise.T
        ).T

        residual = noise - estimated_error @ A.T

        nees = np.einsum(
            "bi,ij,bj->b",
            estimated_error, H, estimated_error,
        )
        nis = np.sum(residual**2, axis=1)

        # Here NIS names the minimized whitened residual
        # chi-square statistic, with m-n degrees of freedom.
        # It is not a sequential innovation-filter NIS.
        return {
            "true_noise_std": float(true_noise_std),
            "assumed_noise_std": 1.0,
            "mean_nees": float(np.mean(nees)),
            "mean_residual_chi_square": float(np.mean(nis)),
            "nees_95pct_coverage": float(np.mean(
                nees <= chi2.ppf(0.95, DIM)
            )),
            "residual_95pct_coverage": float(np.mean(
                nis <= chi2.ppf(0.95, 45-DIM)
            )),
        }

    matched = evaluate(1.0)
    mismatched = evaluate(2.0)

    return {
        "trials": trials,
        "state_dimension": DIM,
        "measurement_dimension": 45,
        "residual_degrees_of_freedom": 45-DIM,
        "known_manufactured_truth": True,
        "noise_assumption_matched": matched,
        "noise_assumption_mismatched": mismatched,
        "paired_standardized_noise_draws": True,
        "empirical_sensor_covariance_calibrated": False,
        "held_out_robot_data_used": False,
    }


def execute():
    affine = [
        nonlinear_case("affine", seed)
        for seed in NONLINEAR_SEEDS
    ]
    nonlinear = [
        nonlinear_case("se3", seed)
        for seed in NONLINEAR_SEEDS
    ]

    def summarize(rows):
        return {
            "cases": rows,
            "mean_near_error": float(np.mean([
                r["near_mean_absolute_profile_cost_error"]
                for r in rows
            ])),
            "mean_far_error": float(np.mean([
                r["far_mean_absolute_profile_cost_error"]
                for r in rows
            ])),
        }

    a = summarize(affine)
    n = summarize(nonlinear)
    g = gaussian_consistency()

    # Numerical sanity bounds apply only to this manufactured study.
    if not (
        a["mean_far_error"] < 1e-5
        and n["mean_far_error"] > 4*n["mean_near_error"]
        and 12 < g["noise_assumption_matched"]["mean_nees"] < 18
        and 0.90 < g["noise_assumption_matched"][
            "nees_95pct_coverage"
        ] < 1.0
        and g["noise_assumption_mismatched"]["mean_nees"]
        > 3*g["noise_assumption_matched"]["mean_nees"]
        and g["noise_assumption_mismatched"][
            "nees_95pct_coverage"
        ] < g["noise_assumption_matched"][
            "nees_95pct_coverage"
        ]
    ):
        raise ValueError("Manufactured consistency checks failed")

    return {
        "schema": SCHEMA,
        "status": "MANUFACTURED_MATH_STUDY_PASSED",
        "affine_control": a,
        "se3_nonlinear_profile": n,
        "linear_gaussian_consistency": g,
        "fixed_first_estimate_approximation_quantified": True,
        "nonlinear_profile_reoptimizes_eliminated_state": True,
        "physical_timing_verified": False,
        "physical_observability_verified": False,
        "real_sensor_noise_calibrated": False,
        "estimator_posterior_coverage_validated": False,
        "health_training_data_created": False,
        "physical_robot_used": False,
    }


def canonical(value):
    return (
        json.dumps(
            value, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ) + "\n"
    ).encode("utf-8")
