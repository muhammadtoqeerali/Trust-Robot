"""R90: synthetic-only fixed-lag prior integrity and reuse guard.

Checks numerical conditioning, fixed gauge provenance, immutable
linearization identity, segment separation and recentering budget.

The budget and condition limit are engineering test thresholds,
not empirically measured sensor or estimator safety limits.

Reuses the R88 Schur implementation and R89 coordinate transform.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math

import numpy as np

import r84_gap_frontend as gap
import r88_schur as schur
import r89_prior as prior

SCHEMA = 'TRUST_ROBOT_R90_SYNTHETIC_MARGINAL_PRIOR_FAILURE_GUARD_V1'

N = 15
MAX_CONDITION = 1e14
MAX_RECENTER_L2 = 0.01

ANCHOR = 'MANUFACTURED_FIXED_SEGMENT_ANCHOR'
SOURCE = 'ANALYTIC_FIXTURE'

REQUIRED = {
    'H', 'g', 'c', 'segment_id', 'linearization_token',
    'source', 'anchor', 'anchor_fixed', 'reference_used',
    'physical_clock_verified', 'real_factor_executable',
    'nonlinear_refresh_authorized', 'fingerprint',
}


class PriorAdmissionError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise PriorAdmissionError(reason)


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        allow_nan=False,
    ).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def token(segment_id):
    need(
        type(segment_id) is int
        and 0 <= segment_id <= 100,
        'SEGMENT_ID'
    )

    return f'R88_FROZEN_LINEARIZATION_SEGMENT_{segment_id}_V1'


def matrix(H):
    H = np.asarray(H, dtype=float)

    need(
        H.shape == (N, N)
        and np.isfinite(H).all(),
        'INFORMATION_MATRIX'
    )

    need(
        np.max(np.abs(H-H.T)) < 1e-8,
        'ASYMMETRIC_INFORMATION'
    )

    H = 0.5*(H+H.T)

    try:
        np.linalg.cholesky(H)
    except np.linalg.LinAlgError as exc:
        raise PriorAdmissionError(
            'NONPOSITIVE_OR_UNANCHORED_INFORMATION'
        ) from exc

    condition = float(np.linalg.cond(H))

    need(
        math.isfinite(condition)
        and condition <= MAX_CONDITION,
        'ILL_CONDITIONED_INFORMATION'
    )

    return H, condition


def vector(x):
    x = np.asarray(x, dtype=float)

    need(
        x.shape == (N,)
        and np.isfinite(x).all(),
        'INFORMATION_VECTOR'
    )

    return x


def fingerprint(record):
    """Local accidental-tampering integrity check, not a signature."""

    payload = {
        key: (
            record[key].tolist()
            if isinstance(record[key], np.ndarray)
            else record[key]
        )
        for key in sorted(REQUIRED-{'fingerprint'})
    }

    return digest(payload)


def validate(record):
    need(
        type(record) is dict
        and set(record) == REQUIRED,
        'PRIOR_FIELDS'
    )

    need(
        type(record['segment_id']) is int,
        'SEGMENT_TYPE'
    )

    need(
        record['linearization_token'] ==
            token(record['segment_id']),
        'LINEARIZATION_IDENTITY'
    )

    need(
        record['source'] == SOURCE,
        'REAL_SENSOR_PRIOR_DENIED'
    )

    need(
        record['anchor'] == ANCHOR
        and record['anchor_fixed'] is True,
        'UNANCHORED_GAUGE_DENIED'
    )

    for name in (
        'reference_used',
        'physical_clock_verified',
        'real_factor_executable',
        'nonlinear_refresh_authorized',
    ):
        need(
            record[name] is False,
            'SCIENTIFIC_DENIAL:' + name
        )

    H, condition = matrix(record['H'])
    g = vector(record['g'])

    c = record['c']

    need(
        type(c) in (int, float)
        and math.isfinite(c),
        'PRIOR_CONSTANT'
    )

    need(
        type(record['fingerprint']) is str
        and record['fingerprint'] == fingerprint(record),
        'PRIOR_FINGERPRINT_MISMATCH'
    )

    return H, g, float(c), condition


def make_record(H, g, c, segment_id):
    record = {
        'H': np.array(H, dtype=float, copy=True),
        'g': np.array(g, dtype=float, copy=True),
        'c': float(c),
        'segment_id': segment_id,
        'linearization_token': token(segment_id),
        'source': SOURCE,
        'anchor': ANCHOR,
        'anchor_fixed': True,
        'reference_used': False,
        'physical_clock_verified': False,
        'real_factor_executable': False,
        'nonlinear_refresh_authorized': False,
    }

    # Validate numerical values before JSON fingerprinting.
    # Reject invalid priors with our typed admission error.
    Hgood, _ = matrix(record['H'])
    vector(record['g'])
    need(math.isfinite(record['c']), 'PRIOR_CONSTANT')

    need(
        Hgood.shape == (N, N),
        'RECORD_CONSTRUCTION'
    )

    record['fingerprint'] = fingerprint(record)
    validate(record)

    return record


def validate_without_fingerprint(record):
    temp = dict(record)
    temp['fingerprint'] = fingerprint({
        **record,
        'fingerprint': '',
    })
    return validate(temp)


def admit(record, segment_id, expected_token, displacement,
          operation='EXACT_COORDINATE_RECENTER'):

    H, g, c, condition = validate(record)

    need(
        type(segment_id) is int
        and segment_id == record['segment_id'],
        'CROSS_GAP_PRIOR_REUSE_DENIED'
    )

    need(
        expected_token == record['linearization_token'],
        'STALE_LINEARIZATION_DENIED'
    )

    need(
        operation == 'EXACT_COORDINATE_RECENTER',
        'NONLINEAR_REFRESH_DENIED'
    )

    d = vector(displacement)
    size = float(np.linalg.norm(d))

    need(
        size <= MAX_RECENTER_L2,
        'OUTSIDE_SYNTHETIC_RECENTER_BUDGET'
    )

    Hr, gr, cr = prior.recenter(
        H, g, c, d,
        operation='EXACT_COORDINATE_RECENTER'
    )

    old_optimum = np.linalg.solve(H, g)
    new_optimum = np.linalg.solve(Hr, gr)

    optimum_error = float(
        np.linalg.norm(
            new_optimum - (old_optimum-d)
        )
    )

    old_cov = np.linalg.solve(H, np.eye(N))
    new_cov = np.linalg.solve(Hr, np.eye(N))

    covariance_error = float(
        np.linalg.norm(old_cov-new_cov)
    )

    test_u = 1e-4*np.sin(np.arange(N)+0.23)

    cost_error = abs(
        prior.quadratic(H, g, c, d+test_u)
        - prior.quadratic(Hr, gr, cr, test_u)
    )

    need(
        optimum_error < 1e-6
        and covariance_error < 1e-12
        and cost_error < 1e-5,
        'RECENTER_INVARIANCE'
    )

    return {
        'segment_id': segment_id,
        'condition_number': condition,
        'coordinate_shift_l2': size,
        'optimum_transform_l2_error': optimum_error,
        'covariance_invariance_l2_error': covariance_error,
        'quadratic_energy_abs_error': cost_error,
        'frozen_jacobians_modified': False,
        'real_sensor_factor_executable': False,
    }


def expect_rejected(fn, label):
    try:
        fn()
    except (
        PriorAdmissionError,
        schur.MarginalizationError,
        prior.PriorConsistencyError,
    ):
        return label

    raise PriorAdmissionError(
        'FAIL_OPEN_ATTACK:' + label
    )


def audit_case(packets):
    segments, gaps = schur.segment_groups(packets)

    rows = []
    rejected = []

    for segment_id, groups in enumerate(segments):
        H, g, c = prior.construct_condensed_prior(
            groups, segment_id
        )

        record = make_record(
            H, g, c, segment_id
        )

        numeric = prior.audit_segment(
            groups, segment_id
        )

        need(
            numeric['schur_vs_prior_full_batch_cost_abs_error']
            < 1e-5,
            'R89_FULL_BATCH_LINEAGE'
        )

        trials = []

        for i in range(3):
            d = (
                2e-4
                * np.sin(np.arange(N)+segment_id+i)
            )

            trials.append(
                admit(
                    record,
                    segment_id,
                    token(segment_id),
                    d
                )
            )

        zero = np.zeros(N)

        rejected.append(expect_rejected(
            lambda: admit(
                record,
                segment_id+1,
                token(segment_id),
                zero
            ),
            'CROSS_SEGMENT'
        ))

        rejected.append(expect_rejected(
            lambda: admit(
                record,
                segment_id,
                'FORGED_LINEARIZATION',
                zero
            ),
            'STALE_LINEARIZATION'
        ))

        rejected.append(expect_rejected(
            lambda: admit(
                record,
                segment_id,
                token(segment_id),
                np.ones(N)*0.1
            ),
            'EXCESSIVE_RECENTER'
        ))

        rejected.append(expect_rejected(
            lambda: admit(
                record,
                segment_id,
                token(segment_id),
                zero,
                operation='NONLINEAR_RELINEARIZE'
            ),
            'NONLINEAR_REFRESH'
        ))

        changed = copy.deepcopy(record)
        changed['H'][0, 0] *= 1.01

        rejected.append(expect_rejected(
            lambda: validate(changed),
            'MATRIX_TAMPER'
        ))

        changed = copy.deepcopy(record)
        changed['source'] = 'RECORDED_M2DGR'

        rejected.append(expect_rejected(
            lambda: validate(changed),
            'REAL_SOURCE'
        ))

        rows.append({
            'segment_id': segment_id,
            'safe_factor_windows': len(groups),
            'information_matrix_dimension': N,
            'local_gaussian_recenter_trials': len(trials),
            'max_condition_number': max(
                t['condition_number']
                for t in trials
            ),
            'max_optimum_transform_error': max(
                t['optimum_transform_l2_error']
                for t in trials
            ),
            'max_covariance_invariance_error': max(
                t['covariance_invariance_l2_error']
                for t in trials
            ),
            'max_quadratic_energy_error': max(
                t['quadratic_energy_abs_error']
                for t in trials
            ),
            'adversarial_rejections': 6,
            'fixed_synthetic_gauge_anchor': True,
            'frozen_linearization_identity_preserved': True,
            'nonlinear_eliminated_factors_relinearized': False,
            'information_crossing_timestamp_gap': False,
        })

    need(
        len(segments) == gaps+1,
        'GAP_SEGMENT_ACCOUNTING'
    )

    need(
        len(rejected) == 6*len(segments),
        'ADVERSARIAL_COUNT'
    )

    return {
        'segments': len(segments),
        'rejected_timestamp_gaps': gaps,
        'accepted_local_recentering_trials': 3*len(segments),
        'adversarial_rejections': len(rejected),
        'attack_classes': sorted(set(rejected)),
        'segment_results': rows,
        'cross_gap_prior_carry_count': 0,
        'real_factor_admission': False,
        'probabilistic_nonlinear_consistency_proven': False,
    }


def execute(r88, r89, sha88, sha89):
    for name, source in (
        ('R88', r88),
        ('R89', r89),
    ):
        need(
            source.get('status') == 'PASS_SOFTWARE_ONLY'
            and source.get('scientific_gates_closed') == 11,
            name + '_LINEAGE'
        )

    need(
        r89['r88_report_sha256'] == sha88,
        'R88_R89_SOURCE_BINDING'
    )

    names = (
        'continuous',
        'single_gap',
        'accel_injection',
        'gyro_injection',
    )

    scenarios = {}

    for name in names:
        result = audit_case(
            gap.fixture(name)
        )

        need(
            result['segments'] ==
            r89['scenarios'][name]['segments'],
            'R89_SEGMENTS'
        )

        need(
            result['rejected_timestamp_gaps'] ==
            r88['scenarios'][name]['rejected_gap_pairs'],
            'R88_TIMESTAMP_GAPS'
        )

        scenarios[name] = result

        print(
            'R90_SYNTHETIC_ATTACK_AUDIT_PASS='
            + name
            + ' rejected='
            + str(result['adversarial_rejections']),
            flush=True
        )

    need(
        scenarios['continuous']['segments'] == 1
        and scenarios['single_gap']['segments'] == 2,
        'EXPECTED_SEGMENTS'
    )

    total_segments = sum(
        s['segments']
        for s in scenarios.values()
    )

    need(
        total_segments == 5,
        'TOTAL_SEGMENTS'
    )

    return {
        'schema': SCHEMA,
        'status': 'PASS_SOFTWARE_ONLY',
        'r88_report_sha256': sha88,
        'r89_report_sha256': sha89,
        'scenario_count': 4,
        'segment_count': total_segments,
        'accepted_local_recentering_trials': sum(
            x['accepted_local_recentering_trials']
            for x in scenarios.values()
        ),
        'adversarial_rejections': sum(
            x['adversarial_rejections']
            for x in scenarios.values()
        ),
        'scenarios': scenarios,
        'local_integrity_fingerprints_checked': True,
        'synthetic_condition_limit': MAX_CONDITION,
        'synthetic_recenter_l2_budget': MAX_RECENTER_L2,
        'thresholds_are_empirical_safety_limits': False,
        'exact_local_gaussian_recentering_only': True,
        'nonlinear_marginal_prior_refresh_authorized': False,
        'physical_observability_demonstrated': False,
        'real_sensor_factors_authorized': False,
        'physical_clock_or_extrinsics_qualified': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'rosbags_or_gt_opened': False,
        'confirmation_test_accessed': False,
        'scientific_gates_closed': 11,
    }


if __name__ == '__main__':
    import sys
    from pathlib import Path

    p88, p89, out = map(
        Path, sys.argv[1:]
    )

    raw88 = p88.read_bytes()
    raw89 = p89.read_bytes()

    report = execute(
        json.loads(raw88),
        json.loads(raw89),
        hashlib.sha256(raw88).hexdigest(),
        hashlib.sha256(raw89).hexdigest(),
    )

    target = (
        out /
        'r90_fixed_lag_prior_failure_audit_v1.json'
    )

    with target.open('xb') as f:
        f.write(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
                allow_nan=False
            ).encode() + b'\n'
        )

    print('R90_FIXED_LAG_PRIOR_FAILURE_AUDIT=PASS')
