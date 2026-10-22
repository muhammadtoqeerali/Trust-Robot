"""R88 Schur fixed-lag information prior, analytic-only.

Finite-difference linearization of existing covariance-whitened
15D synthetic preintegrated factors. Fixed independent anchor per
continuous segment; no cross-gap edges or real sensor input.

Schur elimination preserves the local Gaussian quadratic, not the
nonlinear full posterior. Synthetic stabilization is explicitly declared.
"""

from __future__ import annotations

import hashlib
import json
import math
import numpy as np

import r84_gap_frontend as gap
import r85_fusion as fusion
import r86_rolling as rolling

from trust_robot.analytic_preintegrated_fusion import (
    whitened_inertial_residual,
)

SCHEMA = 'TRUST_ROBOT_R88_SYNTHETIC_SCHUR_FIXED_LAG_V1'

N = 15
EPS = 1e-6

# Manufactured stabilization; not measured sensor noise.
RIDGE = 10.0


class MarginalizationError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise MarginalizationError(why)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            indent=2,
            allow_nan=False
        ) + '\n'
    ).encode()


def require_spd(H):
    H = np.asarray(H, dtype=np.float64)

    need(
        H.ndim == 2
        and H.shape[0] == H.shape[1]
        and np.isfinite(H).all(),
        'MATRIX'
    )

    need(
        np.max(np.abs(H-H.T)) < 1e-7,
        'MATRIX_NOT_SYMMETRIC'
    )

    try:
        np.linalg.cholesky(H)
    except np.linalg.LinAlgError as exc:
        raise MarginalizationError(
            'NON_POSITIVE_INFORMATION'
        ) from exc

    return H


def schur(Ha, ga, c, Ai, Aj, y):
    """Eliminate the old 15D state from a 30D quadratic.

    Old prior:
        0.5 xa^T Ha xa - ga^T xa + c

    New residual:
        0.5 ||Ai xa + Aj xb - y||^2

    Also includes a declared synthetic unary on xb.
    """

    Ha = require_spd(Ha)

    ga = np.asarray(ga, dtype=float)
    Ai = np.asarray(Ai, dtype=float)
    Aj = np.asarray(Aj, dtype=float)
    y = np.asarray(y, dtype=float)

    need(
        Ha.shape == (N, N)
        and ga.shape == (N,)
        and Ai.shape == (N, N)
        and Aj.shape == (N, N)
        and y.shape == (N,)
        and np.isfinite(ga).all()
        and np.isfinite(Ai).all()
        and np.isfinite(Aj).all()
        and np.isfinite(y).all()
        and math.isfinite(float(c)),
        'SCHUR_INPUTS'
    )

    Haa = require_spd(Ha + Ai.T @ Ai)
    Hab = Ai.T @ Aj
    Hbb = Aj.T @ Aj + RIDGE**2 * np.eye(N)

    ba = ga + Ai.T @ y
    bb = Aj.T @ y

    X = np.linalg.solve(Haa, Hab)
    z = np.linalg.solve(Haa, ba)

    H = Hbb - Hab.T @ X
    H = 0.5 * (H + H.T)

    g = bb - Hab.T @ z

    constant = float(
        c + 0.5*y@y - 0.5*ba@z
    )

    require_spd(H)

    need(
        np.isfinite(g).all()
        and math.isfinite(constant),
        'SCHUR_OUTPUT'
    )

    return H, g, constant


def linearize(xi, xj, pre, L):
    """Differentiate the full-covariance 15D residual."""

    need(
        np.shape(xi) == (N,)
        and np.shape(xj) == (N,),
        'STATE_SHAPE'
    )

    def res(a, b):
        return whitened_inertial_residual(
            a, b, (pre, L)
        )

    base = res(xi, xj)

    need(
        base.shape == (N,)
        and np.isfinite(base).all()
        and np.linalg.norm(base) < 1e-6,
        'CONSTRUCTED_ENDPOINT_RESIDUAL'
    )

    Ai = np.empty((N, N))
    Aj = np.empty((N, N))

    for j in range(N):
        perturb = np.zeros(N)
        perturb[j] = EPS

        Ai[:, j] = (
            res(xi+perturb, xj)
            - res(xi-perturb, xj)
        ) / (2*EPS)

        Aj[:, j] = (
            res(xi, xj+perturb)
            - res(xi, xj-perturb)
        ) / (2*EPS)

    need(
        np.isfinite(Ai).all()
        and np.isfinite(Aj).all(),
        'NONFINITE_LINEARIZATION'
    )

    need(
        np.linalg.matrix_rank(
            Aj, tol=1e-7
        ) == N,
        'RANK_DEFICIENT_ENDPOINT'
    )

    return Ai, Aj, float(np.linalg.norm(base))


def segment_groups(packets):
    groups, gaps = gap.partition(
        packets, max_steps=2
    )

    output = []
    previous = None

    for start, end, readings in groups:
        need(
            start < end and len(readings) > 0,
            'INVALID_WINDOW'
        )

        if previous is None or start != previous:
            output.append([])
        else:
            need(
                start == previous,
                'BAD_SEGMENT_BOUNDARY'
            )

        output[-1].append(
            (start, end, readings)
        )

        previous = end

    need(
        len(output) == gaps+1,
        'SEGMENTS_WITH_UNQUALIFIED_GAP'
    )

    need(
        sum(len(s) for s in output) == len(groups),
        'WINDOW_ACCOUNTING'
    )

    need(
        sum(
            len(r)
            for ss in output
            for _, _, r in ss
        ) + gaps == len(packets)-1,
        'INERTIAL_SAMPLE_ACCOUNTING'
    )

    return output, gaps


def synthetic_factors(groups, segment_id):
    state = rolling.synthetic_anchor()
    factors = []

    for i, (start, end, readings) in enumerate(groups):
        factor = fusion.make_factor(readings)

        pre = factor['preintegration']
        L = factor['whitener']

        need(
            abs(
                pre['total_dt'] - (end-start)/1e9
            ) < 1e-10,
            'DURATION'
        )

        following = rolling.constructed_endpoint(
            state, pre
        )

        Ai, Aj, residual = linearize(
            state, following, pre, L
        )

        # Synthetic whitened measurement perturbation.
        # It is not a real measurement or independent GT.
        t = np.arange(1, N+1, dtype=float)

        y = 0.3 * np.sin(
            (segment_id+1)*(i+2)*t
        )

        factors.append((
            Ai, Aj, y, residual
        ))

        state = following

    return factors


def solve_segment(groups, segment_id):
    factors = synthetic_factors(
        groups, segment_id
    )

    m = len(factors)

    need(m >= 1, 'EMPTY_SEGMENT')

    # Independently assembled full-batch least-squares
    # system. The segment's x0 is a fixed gauge anchor.
    A = np.zeros(
        (2*N*m, N*m), dtype=float
    )

    b = np.zeros(2*N*m, dtype=float)

    for k, (Ai, Aj, y, _) in enumerate(factors):
        first = 2*N*k

        A[
            first:first+N,
            N*k:N*(k+1)
        ] = Aj

        if k:
            A[
                first:first+N,
                N*(k-1):N*k
            ] = Ai

        b[first:first+N] = y

        # Declared manufactured unary stabilization.
        A[
            first+N:first+2*N,
            N*k:N*(k+1)
        ] = RIDGE*np.eye(N)

    # Without the fixed anchor, the inertial-only
    # equations have at least 15 free gauge dimensions.
    unanchored_rows = N*m
    unanchored_columns = N*(m+1)

    need(
        unanchored_columns-unanchored_rows == N,
        'GAUGE_DIMENSION'
    )

    H_batch = require_spd(A.T @ A)

    x_batch = np.linalg.lstsq(
        A, b, rcond=None
    )[0]

    batch_last = x_batch[-N:]

    batch_cost = 0.5*float(
        np.linalg.norm(A @ x_batch-b)**2
    )

    batch_cov_last = np.linalg.solve(
        H_batch, np.eye(N*m)
    )[-N:, -N:]

    # First edge: x0 fixed, x1 active.
    _, J, y, _ = factors[0]

    H = require_spd(
        J.T @ J + RIDGE**2*np.eye(N)
    )

    g = J.T @ y
    c = 0.5*float(y @ y)

    eliminated = 0

    for Ai, Aj, y, _ in factors[1:]:
        H, g, c = schur(
            H, g, c, Ai, Aj, y
        )

        eliminated += 1

    last = np.linalg.solve(H, g)
    cov = np.linalg.solve(H, np.eye(N))

    reduced_cost = (
        0.5*float(last @ H @ last)
        - float(g @ last)
        + c
    )

    solution_error = float(
        np.linalg.norm(last-batch_last)
    )

    covariance_rel = float(
        np.linalg.norm(cov-batch_cov_last)
        / max(
            1e-12,
            np.linalg.norm(batch_cov_last)
        )
    )

    cost_error = abs(
        reduced_cost-batch_cost
    )

    need(
        solution_error < 1e-4,
        'BATCH_STATE_DISAGREEMENT'
    )

    need(
        covariance_rel < 2e-3,
        'BATCH_COVARIANCE_DISAGREEMENT'
    )

    need(
        cost_error < 1e-5,
        'QUADRATIC_COST_NOT_PRESERVED'
    )

    need(
        batch_cost >= 0
        and reduced_cost >= -1e-6,
        'NEGATIVE_OPTIMUM_COST'
    )

    need(
        eliminated == m-1,
        'ELIMINATION_COUNT'
    )

    min_info_eig = float(
        np.linalg.eigvalsh(H).min()
    )

    need(
        min_info_eig > 0,
        'CONDENSED_PRIOR_NOT_SPD'
    )

    return {
        'segment_id': segment_id,
        'window_count': m,
        'synthetic_start_ns': groups[0][0],
        'synthetic_end_ns': groups[-1][1],
        'synthetic_imu_pairs': sum(
            len(rr)
            for _, _, rr in groups
        ),
        'retained_state_dimension': N,
        'eliminated_state_count': eliminated,
        'unanchored_inertial_gauge_dimensions_at_least': N,
        'manufactured_fixed_anchor_applied': True,
        'synthetic_regularization_weight': RIDGE,
        'local_gaussian_prior_schur_applied': True,
        'nonlinear_factor_relinearization_after_schur': False,
        'schur_vs_batch_state_l2_error': solution_error,
        'schur_vs_batch_covariance_relative_error': covariance_rel,
        'schur_vs_batch_optimum_cost_abs_error': cost_error,
        'full_batch_optimum_cost': batch_cost,
        'final_condensed_information_min_eigenvalue':
            min_info_eig,
        'factor_construction_max_endpoint_residual': max(
            q[3] for q in factors
        ),
        'information_across_gap_copied': False,
        'source': 'ANALYTIC_FIXTURE',
    }


def solve_case(packets):
    segments, gaps = segment_groups(packets)

    rows = [
        solve_segment(group, i)
        for i, group in enumerate(segments)
    ]

    need(
        len(rows) == gaps+1,
        'GAP_PRIOR_RESET'
    )

    need(
        all(
            rows[i]['synthetic_end_ns']
            < rows[i+1]['synthetic_start_ns']
            for i in range(len(rows)-1)
        ),
        'CROSS_GAP_SEGMENT_ORDER'
    )

    return {
        'segments': len(rows),
        'rejected_gap_pairs': gaps,
        'safe_imu_factor_windows': sum(
            x['window_count'] for x in rows
        ),
        'marginalized_states': sum(
            x['eliminated_state_count']
            for x in rows
        ),
        'synthetic_imu_pairs': sum(
            x['synthetic_imu_pairs']
            for x in rows
        ),
        'per_segment_information_reset': True,
        'cross_gap_schur_prior_carry_count': 0,
        'segments_results': rows,
    }


def execute(r84, r85, r86, sha84, sha85, sha86):
    need(
        all(
            x.get('status') == 'PASS_SOFTWARE_ONLY'
            and x.get('scientific_gates_closed') == 11
            for x in (r84, r85, r86)
        ),
        'UPSTREAM_STATUS'
    )

    cases = (
        'continuous',
        'single_gap',
        'accel_injection',
        'gyro_injection',
    )

    studies = {}

    for name in cases:
        packets = gap.fixture(name)

        need(
            gap.analyze(packets)
            == r84['scenarios'][name],
            'R84_FIXTURE_LINEAGE'
        )

        need(
            fusion.build_graph(packets)
            == r85['scenarios'][name],
            'R85_FIXTURE_LINEAGE'
        )

        need(
            rolling.solve(packets)
            == r86['scenarios'][name],
            'R86_FIXTURE_LINEAGE'
        )

        studies[name] = solve_case(packets)

        need(
            studies[name]['rejected_gap_pairs']
            == r84['scenarios'][name]['gap_count'],
            'GAP_COUNT_LINEAGE'
        )

        print(
            'R88_SYNTHETIC_CASE_PASS='
            + name
            + ' segments='
            + str(studies[name]['segments']),
            flush=True
        )

    need(
        studies['continuous']['segments'] == 1
        and studies['continuous']['safe_imu_factor_windows'] == 4,
        'CLEAN'
    )

    need(
        studies['single_gap']['segments'] == 2
        and studies['single_gap']['rejected_gap_pairs'] == 1,
        'GAP'
    )

    return {
        'schema': SCHEMA,
        'status': 'PASS_SOFTWARE_ONLY',
        'r84_report_sha256': sha84,
        'r85_report_sha256': sha85,
        'r86_report_sha256': sha86,
        'scenario_count': 4,
        'scenarios': studies,
        'algorithm':
            'SYNTHETIC_FINITE_DIFFERENCE_15D_WHITENED_LINEARIZATION_PLUS_SCHUR',
        'mathematically_equivalent_full_batch_linearized_gaussian_checked':
            True,
        'actual_schur_complement_information_elimination_executed':
            True,
        'local_gaussian_only_not_full_nonlinear_marginalization':
            True,
        'synthetic_unary_stabilization_not_measured_noise':
            True,
        'independent_reference_or_observability_verified': False,
        'real_sensor_factor_admission': False,
        'physical_clock_or_extrinsic_qualified': False,
        'health_training_or_labels_authorized': False,
        'ate_rpe_computed': False,
        'original_rosbags_or_gt_opened': False,
        'confirmation_test_accessed': False,
        'scientific_gates_closed': 11,
    }


if __name__ == '__main__':
    import sys
    from pathlib import Path

    p84, p85, p86, out = map(
        Path, sys.argv[1:]
    )

    b84, b85, b86 = (
        p.read_bytes()
        for p in (p84, p85, p86)
    )

    report = execute(
        json.loads(b84),
        json.loads(b85),
        json.loads(b86),
        digest(b84),
        digest(b85),
        digest(b86),
    )

    with (
        out / 'r88_synthetic_schur_fixed_lag_v1.json'
    ).open('xb') as f:
        f.write(canonical(report))

    print('R88_SYNTHETIC_SCHUR_FIXED_LAG=PASS')
