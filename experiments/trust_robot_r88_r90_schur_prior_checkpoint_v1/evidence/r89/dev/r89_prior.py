"""R89 frozen Schur prior: exact recentering versus nonlinear relinearization.

Tests local Gaussian information-form invariance after changing the
retained state coordinate origin. Uses real existing analytic 15D
residual mathematics only on synthetic fixture inputs.

Changing coordinates does NOT relinearize eliminated nonlinear factors.
"""

from __future__ import annotations

import hashlib
import json
import math

import numpy as np

import r84_gap_frontend as gap
import r85_fusion as fusion
import r86_rolling as rolling
import r88_schur as schur

from trust_robot.analytic_preintegrated_fusion import (
    whitened_inertial_residual,
)

SCHEMA = (
    'TRUST_ROBOT_R89_SYNTHETIC_FROZEN_PRIOR_RELINEARIZATION_AUDIT_V1'
)

N = 15
EPS = 1e-6


class PriorConsistencyError(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise PriorConsistencyError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ) + '\n'
    ).encode('utf-8')


def vector(x, name):
    x = np.asarray(x, dtype=np.float64)

    need(
        x.shape == (N,)
        and np.isfinite(x).all(),
        'VECTOR:' + name
    )

    return x


def authorize_prior_operation(operation):
    need(
        operation == 'EXACT_COORDINATE_RECENTER',
        'FROZEN_PRIOR_NONLINEAR_RELINEARIZATION_DENIED'
    )


def recenter(H, g, c, displacement, operation='EXACT_COORDINATE_RECENTER'):
    """For x = displacement + u, transform q(x) to q_new(u).

    q(x) = 0.5*x.T@H@x - g.T@x + c
    The prior's original Jacobians remain frozen.
    """
    authorize_prior_operation(operation)

    H = schur.require_spd(H)
    g = vector(g, 'information_vector')
    d = vector(displacement, 'origin_displacement')

    need(
        H.shape == (N, N)
        and math.isfinite(float(c)),
        'PRIOR_SHAPE'
    )

    new_g = g - H @ d
    new_c = float(
        c
        + 0.5*d @ H @ d
        - g @ d
    )

    need(
        np.isfinite(new_g).all()
        and math.isfinite(new_c),
        'RECENTER_OUTPUT'
    )

    return H.copy(), new_g, new_c


def quadratic(H, g, c, x):
    x = vector(x, 'query')

    return float(
        0.5*x @ H @ x
        - g @ x
        + c
    )


def construct_condensed_prior(groups, segment_id):
    """Rebuild the exact R88 local Gaussian prior from its factors."""

    need(len(groups) >= 1, 'EMPTY_SEGMENT')

    factors = schur.synthetic_factors(
        groups, segment_id
    )

    _, J, y, _ = factors[0]

    H = schur.require_spd(
        J.T @ J
        + schur.RIDGE**2*np.eye(N)
    )

    g = J.T @ y
    c = 0.5*float(y @ y)

    for Ai, Aj, y, _ in factors[1:]:
        H, g, c = schur.schur(
            H, g, c, Ai, Aj, y
        )

    need(
        len(factors) == len(groups),
        'FACTOR_COUNT'
    )

    return H, g, c


def audit_segment(groups, segment_id):
    H, g, c = construct_condensed_prior(
        groups, segment_id
    )

    # Upstream R88 checked the same prior against a
    # separately assembled full-batch system.
    upstream = schur.solve_segment(
        groups, segment_id
    )

    optimum = np.linalg.solve(H, g)

    optimal_cost = quadratic(
        H, g, c, optimum
    )

    need(
        abs(
            optimal_cost
            - upstream['full_batch_optimum_cost']
        ) < 1e-5,
        'R88_FULL_BATCH_COST_LINEAGE'
    )

    covariance = np.linalg.solve(
        H, np.eye(N)
    )

    need(
        np.isfinite(covariance).all(),
        'PRIOR_COVARIANCE'
    )

    maximum_cost_error = 0.0
    maximum_optimum_error = 0.0
    maximum_covariance_error = 0.0

    for i in range(3):
        displacement = (
            optimum
            + 2e-4*np.sin(
                np.arange(N, dtype=float)
                + segment_id
                + i + 1
            )
        )

        Hr, gr, cr = recenter(
            H, g, c, displacement
        )

        # Exact transformation of the minimizer:
        # x* becomes u* = x* - displacement.
        shifted_optimum = np.linalg.solve(
            Hr, gr
        )

        expected = optimum - displacement

        opt_error = float(
            np.linalg.norm(
                shifted_optimum - expected
            )
        )

        maximum_optimum_error = max(
            maximum_optimum_error,
            opt_error
        )

        cov_r = np.linalg.solve(
            Hr, np.eye(N)
        )

        cov_error = float(
            np.linalg.norm(
                cov_r-covariance
            )
        )

        maximum_covariance_error = max(
            maximum_covariance_error,
            cov_error
        )

        for u in (
            np.zeros(N),
            expected,
            1e-4*np.cos(
                np.arange(N)+i
            ),
        ):
            original = quadratic(
                H, g, c, displacement+u
            )

            transformed = quadratic(
                Hr, gr, cr, u
            )

            err = abs(
                original-transformed
            )

            maximum_cost_error = max(
                maximum_cost_error,
                err
            )

            need(
                err <= 1e-6*max(
                    1.0, abs(original)
                ),
                'QUADRATIC_RECENTER_INVARIANCE'
            )

        need(
            opt_error < 1e-6,
            'RECENTERED_OPTIMUM'
        )

        need(
            cov_error < 1e-12,
            'RECENTERED_COVARIANCE'
        )

    return {
        'segment_id': segment_id,
        'window_count': len(groups),
        'retained_state_dimension': N,
        'coordinate_recentering_trials': 3,
        'maximum_quadratic_value_abs_error':
            maximum_cost_error,
        'maximum_recentered_optimum_l2_error':
            maximum_optimum_error,
        'maximum_recentered_covariance_l2_error':
            maximum_covariance_error,
        'schur_vs_prior_full_batch_cost_abs_error':
            abs(
                optimal_cost
                - upstream['full_batch_optimum_cost']
            ),
        'original_frozen_jacobians_recomputed_by_recenter':
            False,
        'exact_local_gaussian_coordinate_change': True,
        'nonlinear_prior_relinearization_performed': False,
        'information_carried_across_gap': False,
    }


def numerical_jacobian(xi, xj, pre, L):
    """Finite-difference actual whitened nonlinear residual."""

    xi = vector(xi, 'xi')
    xj = vector(xj, 'xj')

    def residual(a, b):
        r = whitened_inertial_residual(
            a, b, (pre, L)
        )

        need(
            r.shape == (N,)
            and np.isfinite(r).all(),
            'NONLINEAR_RESIDUAL'
        )

        return r

    base = residual(xi, xj)

    Ai = np.zeros((N, N))
    Aj = np.zeros((N, N))

    for col in range(N):
        perturb = np.zeros(N)
        perturb[col] = EPS

        Ai[:, col] = (
            residual(xi+perturb, xj)
            - residual(xi-perturb, xj)
        ) / (2*EPS)

        Aj[:, col] = (
            residual(xi, xj+perturb)
            - residual(xi, xj-perturb)
        ) / (2*EPS)

    need(
        np.isfinite(Ai).all()
        and np.isfinite(Aj).all(),
        'NONFINITE_JACOBIAN'
    )

    return base, Ai, Aj


def nonlinear_audit(groups):
    """Test Jacobian drift at changed manufactured states.

    The result is a diagnostic only. It does not authorize
    refreshing a marginalized prior without eliminated factors.
    """

    need(
        len(groups) >= 2,
        'NEED_TWO_CONSECUTIVE_FACTORS'
    )

    xi = rolling.synthetic_anchor()

    first = fusion.make_factor(
        groups[0][2]
    )

    middle = rolling.constructed_endpoint(
        xi,
        first['preintegration']
    )

    second = fusion.make_factor(
        groups[1][2]
    )

    last = rolling.constructed_endpoint(
        middle,
        second['preintegration']
    )

    pre = second['preintegration']
    L = second['whitener']

    original, Ai, Aj = numerical_jacobian(
        middle, last, pre, L
    )

    d_middle = (
        2e-4*np.sin(
            np.arange(N)+0.37
        )
    )

    d_last = (
        2e-4*np.cos(
            np.arange(N)+0.73
        )
    )

    shifted, Ai_new, Aj_new = numerical_jacobian(
        middle+d_middle,
        last+d_last,
        pre, L
    )

    predicted = (
        original
        + Ai@d_middle
        + Aj@d_last
    )

    error = float(
        np.linalg.norm(
            shifted-predicted
        )
    )

    relative = error/max(
        1.0,
        float(np.linalg.norm(shifted))
    )

    drift = float(
        (
            np.linalg.norm(Ai_new-Ai)
            + np.linalg.norm(Aj_new-Aj)
        )
        / max(
            1.0,
            float(
                np.linalg.norm(Ai)
                + np.linalg.norm(Aj)
            )
        )
    )

    need(
        math.isfinite(relative)
        and math.isfinite(drift)
        and relative < 0.05,
        'NONLINEAR_TAYLOR_DIAGNOSTIC'
    )

    need(
        drift > 1e-10,
        'NO_DETECTABLE_JACOBIAN_CHANGE'
    )

    return {
        'synthetic_state_perturbation_max_abs':
            2e-4,
        'linear_prediction_relative_error':
            relative,
        'relinearized_jacobian_relative_change':
            drift,
        'nonlinear_residual_evaluated_at_shifted_state': True,
        'new_jacobians_evaluated_for_audit': True,
        'eliminated_prior_jacobians_refreshed': False,
        'frozen_prior_claimed_fully_nonlinear': False,
        'independent_reference_used': False,
    }


def run_case(packets):
    parts, gaps = schur.segment_groups(
        packets
    )

    prior_rows = []
    nonlinear_rows = []

    for i, groups in enumerate(parts):
        prior_rows.append(
            audit_segment(groups, i)
        )

        if len(groups) >= 2:
            nonlinear_rows.append(
                nonlinear_audit(groups)
            )

    need(
        len(parts) == gaps+1,
        'SEGMENT_GAUGE_POLICY'
    )

    need(
        len(nonlinear_rows) > 0,
        'NO_NONLINEAR_AUDIT'
    )

    return {
        'segments': len(parts),
        'timestamp_gaps_rejected': gaps,
        'prior_recentered_segment_count':
            len(prior_rows),
        'nonlinear_jacobian_audits':
            len(nonlinear_rows),
        'segment_results': prior_rows,
        'nonlinear_audits': nonlinear_rows,
        'cross_gap_prior_carry_count': 0,
        'frozen_information_recentered_without_relinearizing': True,
        'physically_qualified_motion_factors_created': False,
    }


def execute(r88, source_sha):
    need(
        r88.get('status') == 'PASS_SOFTWARE_ONLY'
        and r88.get('scientific_gates_closed') == 11
        and r88.get('real_sensor_factor_admission') is False,
        'R88_BOUNDARY'
    )

    names = (
        'continuous',
        'single_gap',
        'accel_injection',
        'gyro_injection'
    )

    scenarios = {}

    for name in names:
        packets = gap.fixture(name)
        result = run_case(packets)

        need(
            result['segments']
            == r88['scenarios'][name]['segments'],
            'R88_SEGMENT_LINEAGE'
        )

        need(
            result['timestamp_gaps_rejected']
            == r88['scenarios'][name][
                'rejected_gap_pairs'
            ],
            'R88_GAP_LINEAGE'
        )

        scenarios[name] = result

        print(
            'R89_SYNTHETIC_CASE_PASS='
            + name
            + ' segments='
            + str(result['segments']),
            flush=True
        )

    need(
        scenarios['continuous']['segments'] == 1
        and scenarios['single_gap']['segments'] == 2
        and scenarios['single_gap'][
            'cross_gap_prior_carry_count'
        ] == 0,
        'CLEAN_GAP_POLICY'
    )

    return {
        'schema': SCHEMA,
        'status': 'PASS_SOFTWARE_ONLY',
        'r88_report_sha256': source_sha,
        'scenario_count': len(scenarios),
        'scenarios': scenarios,
        'exact_coordinate_recentering_verified': True,
        'frozen_schur_prior_is_local_gaussian_only': True,
        'fresh_nonlinear_jacobian_changes_measured': True,
        'marginalized_prior_relinearization_authorized': False,
        'eliminated_factor_information_reconstructed': False,
        'probabilistic_nonlinear_consistency_proven': False,
        'physical_clock_or_extrinsics_qualified': False,
        'real_pose_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'raw_rosbags_or_gt_opened': False,
        'confirmation_test_accessed': False,
        'scientific_gates_closed': 11,
    }


if __name__ == '__main__':
    import sys
    from pathlib import Path

    source, destination = map(
        Path, sys.argv[1:]
    )

    raw = source.read_bytes()

    report = execute(
        json.loads(raw),
        digest(raw)
    )

    with (
        destination /
        'r89_prior_relinearization_consistency_v1.json'
    ).open('xb') as f:
        f.write(canonical(report))

    print('R89_FROZEN_PRIOR_AND_RELINEARIZATION_AUDIT=PASS')
