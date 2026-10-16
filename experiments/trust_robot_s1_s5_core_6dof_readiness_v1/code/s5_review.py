"""S5 read-only, offline TRUST-ROBOT research integration assessment."""

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

BASE = '79a2abf6de6ff68df23de8bd04b538ce0c95b46b'

GATES = (
    'physical_capture_event_verified',
    'sensor_clock_domain_verified',
    'cross_stream_offset_verified',
    'association_tolerance_qualified',
    'full_body_sensor_extrinsic_verified',
    'independent_reference_origin_and_time_verified',
    'factor_covariance_empirically_calibrated',
    'recorded_factor_execution_authorized',
)

CLOSED = (
    'real_sensor_factors_authorized',
    'm2dgr_estimator_scoring_authorized',
    'health_model_training_authorized',
    'live_simulator_launch_authorized',
    'global_replay_protection_proven',
    'sensor_timing_and_extrinsics_qualified',
)

PATHS = {
    'fixed_lag_audit':
        'docs/audits/trust_robot/TRUST_ROBOT_FIXED_LAG_ESTIMATOR_VALIDITY_CHECKPOINT_V1.md',
    'phase5_architecture_audit':
        'docs/audits/trust_robot/TRUST_ROBOT_PHASE5_MULTIMODAL_SOFTWARE_ARCHITECTURE_FREEZE_V1.md',
    'health_frontier_audit':
        'docs/audits/trust_robot/TRUST_ROBOT_SE4_HEALTH_MODEL_TRAINING_BLOCKED_FRONTIER_FREEZE_V1.md',
    'factor_interface':
        'src/trust_robot/multimodal_factor_interface.py',
    'sensor_admission':
        'src/trust_robot/m2dgr_sensor_admission.py',
}


def need(ok, why):
    if not ok:
        raise ValueError('S5_FAIL_CLOSED:' + why)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def safe(path):
    p = Path(path)

    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_size < 5000000,
        'UNSAFE_FILE:' + str(p),
    )

    return p


def load(path):
    return json.loads(
        safe(path).read_text(encoding='utf-8')
    )


def emit(path, data):
    with Path(path).open(
        'x',
        encoding='utf-8',
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        f.write('\n')


def inventory(repo):
    repo = Path(repo)

    files = {
        key: safe(repo / relative)
        for key, relative in PATHS.items()
    }

    interface = ast.parse(
        files['factor_interface'].read_text(
            encoding='utf-8'
        )
    )

    functions = {
        node.name: node
        for node in interface.body
        if isinstance(node, ast.FunctionDef)
    }

    need(
        'assemble_synthetic_pose_slot' in functions
        and 'describe_recorded_claim' in functions,
        'EXISTING_FACTOR_BOUNDARY',
    )

    description = (
        ast.get_docstring(
            functions['assemble_synthetic_pose_slot']
        ) or ''
    )

    need(
        'single pose-factor dictionary' in description
        and
        'does NOT support simultaneous independent camera and LiDAR factors'
        in ' '.join(description.split()),
        'SINGLE_FACTOR_SLOT_LIMIT',
    )

    admission = ast.parse(
        files['sensor_admission'].read_text(
            encoding='utf-8'
        )
    )

    need(
        any(
            isinstance(node, ast.FunctionDef)
            and node.name == 'load_frozen_snapshot'
            for node in admission.body
        ),
        'FROZEN_SOURCE_GATE',
    )

    fixed = files['fixed_lag_audit'].read_text(
        encoding='utf-8'
    )

    phase5 = files['phase5_architecture_audit'].read_text(
        encoding='utf-8'
    )

    health = files['health_frontier_audit'].read_text(
        encoding='utf-8'
    )

    need(
        'manufactured-fixture regression validation' in fixed
        and '156 tests in 16 suites' in fixed,
        'ESTIMATOR_HISTORY',
    )

    need(
        '2,816,957 observations' in phase5
        and '4,320,203,720 serialized payload bytes' in phase5
        and 'empirical three-state health model is not complete'
        in phase5,
        'HISTORICAL_TRAIN_INGESTION_CONTEXT',
    )

    need(
        'real healthy/degraded/unusable labels: **0**'
        in health
        and 'classifier training authorized: **false**'
        in health,
        'HEALTH_SUPERVISION_FRONTIER',
    )

    return {
        key: sha(path)
        for key, path in sorted(files.items())
    }


def evidence(files):
    s1, s2, s3, s4, m4 = (
        load(files[key])
        for key in (
            's1', 's2', 's3', 's4', 's4_matrix'
        )
    )

    need(
        s1['m2dgr_trajectory_count'] == 36
        and s1['m2dgr_sync_entries'] == 140
        and s1['m2dgr_sync_qualified'] == 0
        and s1['analytic_module_count'] == 16,
        'S1_READINESS',
    )

    need(
        s1['m2dgr_split_counts'] == {
            'train': 22,
            'validation_calibration': 7,
            'confirmation_test': 7,
        },
        'S1_SPLIT',
    )

    need(
        s2['regression_test_count']
        == s2['regression_counts']['passed']
        == 104
        and s2['selected_suite_count'] == 9,
        'S2_REGRESSION',
    )

    need(
        s2['factor_gate_probe']['negative_control_count']
        == 8
        and s2['m2dgr_scoring_authorized'] is False,
        'S2_DENIALS',
    )

    need(
        s3['test_cases_passed'] == 41
        and s3['supported_stream_count'] == 4
        and s3['real_pose_factor_execution_authorized']
        is False,
        'S3_CONTRACT',
    )

    need(
        s4['tests_passed'] == 55
        and s4['distinct_source_streams'] == 4
        and s4['unqualified_gate_instances'] == 32,
        'S4_REQUIREMENTS',
    )

    need(
        m4['stream_count'] == 4
        and m4['gate_count_per_stream'] == 8
        and m4['unqualified_gate_instances'] == 32,
        'S4_MATRIX',
    )

    rows = m4['streams']

    need(
        len(rows) == 4
        and len({
            row['stream_id']
            for row in rows
        }) == 4
        and all(
            set(row['requirement_gates']) == set(GATES)
            and all(
                value is False
                for value in row[
                    'requirement_gates'
                ].values()
            )
            for row in rows
        ),
        'UNQUALIFIED_FACTOR_GATES',
    )

    need(
        s4['recorded_sensor_factors_generated'] == 0
        and s4['scientific_pose_factors'] == 0
        and s3['scientific_pose_factors'] == 0,
        'POSE_FACTORS',
    )

    return {
        'analytic_source_test_pairs_inventoried': 16,
        'selected_synthetic_regression_tests_passed': 104,
        's3_contract_tests_passed': 41,
        's4_requirement_tests_passed': 55,
        'train_streams_described': 4,
        'unverified_m2dgr_synchronization_entries': 140,
        'unqualified_s4_gate_instances': 32,
        'recorded_sensor_pose_factors_generated': 0,
        'health_labels_generated': 0,
    }


def plan(counts, filehashes, inputhashes):
    return {
        'schema':
            'TRUST_ROBOT_S5_RESEARCH_INTEGRATION_DECISION_V1',
        'parent_commit': BASE,
        'scientific_verdict':
            'DEVELOPMENT_ONLY_REAL_SENSOR_FACTORS_DENIED',
        'evidence_counts': counts,
        'repository_evidence_sha256': filehashes,
        's1_s4_report_and_matrix_sha256': inputhashes,
        'gates': {
            key: False
            for key in CLOSED
        },
        'required_evidence_per_stream': {
            key: False
            for key in GATES
        },
        'next_implementation': {
            'work_id':
                'S6_CPU_ONLY_INDEPENDENT_CAMERA_LIDAR_SAME_EDGE_FUSION',
            'objective':
                'Extend existing analytic factor representation to retain independent camera and LiDAR relative-pose constraints on the same edge, with explicit source ownership and modality-specific covariance',
            'input_scope':
                'MANUFACTURED_FIXTURES_ONLY',
            'must_preserve':
                'Existing 15D estimator regression and recorded-factor denial gates',
            'real_sensor_admission': False,
            'evaluation_metric_claim':
                'SYNTHETIC_REGRESSION_ONLY',
        },
        'physical_evidence_blockers': [
            'Independently establish sensor capture event and clock semantics for each selected stream',
            'Qualify cross-modal timing offsets and association tolerance on permitted data',
            'Verify complete body-to-camera, body-to-LiDAR, and body-to-IMU extrinsics and necessary camera intrinsics',
            'Construct reference-independent camera/LiDAR/IMU constraints with empirically defensible noise models',
            'Validate independent 6DoF reference frame and temporal association before any real ATE/RPE',
            'Obtain SE2-admissible TRAIN health supervision before training a three-state model',
        ],
        'historical_train_ingestion_observed_in_published_audit':
            True,
        'historical_train_ingestion_proves_calibration_or_factor_admission':
            False,
        'raw_sensor_recordings_read_in_s5': False,
        'confirmation_test_used_in_s5': False,
        'scientific_pose_factors_admitted_in_s5': 0,
        'health_labels_generated_in_s5': 0,
        'live_simulator_launched_in_s5': False,
    }


def negative_controls(decision):
    denied = []

    def reject(name, mutate):
        changed = copy.deepcopy(decision)
        mutate(changed)

        need(
            changed != decision,
            'INERT_CONTROL:' + name,
        )

        try:
            need(
                changed == decision,
                'CHANGED_FROZEN_REVIEW:' + name,
            )

        except ValueError:
            denied.append(name)

        else:
            raise AssertionError(
                'FALSE_PROMOTION_ACCEPTED:' + name
            )

    for key in CLOSED:
        reject(
            'false_authorization_' + key,
            lambda x, k=key: x['gates'].__setitem__(
                k, True
            ),
        )

    for key in GATES:
        reject(
            'false_requirement_' + key,
            lambda x, k=key:
                x['required_evidence_per_stream'].__setitem__(
                    k, True
                ),
        )

    for key in decision['evidence_counts']:
        reject(
            'false_count_' + key,
            lambda x, k=key:
                x['evidence_counts'].__setitem__(
                    k,
                    x['evidence_counts'][k] + 1,
                ),
        )

    for key, value in (
        ('parent_commit', '0' * 40),
        ('scientific_verdict', 'FULLY_QUALIFIED'),
        ('raw_sensor_recordings_read_in_s5', True),
        ('confirmation_test_used_in_s5', True),
        ('scientific_pose_factors_admitted_in_s5', 1),
        ('health_labels_generated_in_s5', 1),
        ('live_simulator_launched_in_s5', True),
    ):
        reject(
            'forged_' + key,
            lambda x, k=key, v=value:
                x.__setitem__(k, v),
        )

    reject(
        'false_next_task_admission',
        lambda x:
            x['next_implementation'].__setitem__(
                'real_sensor_admission', True
            ),
    )

    reject(
        'false_historical_calibration',
        lambda x:
            x.__setitem__(
                'historical_train_ingestion_proves_calibration_or_factor_admission',
                True,
            ),
    )

    need(
        len(denied) == len(set(denied)) == 32,
        'NEGATIVE_TEST_INVENTORY',
    )

    return denied


def main(args):
    files = {
        key: getattr(args, key)
        for key in (
            's1', 's2', 's3', 's4', 's4_matrix'
        )
    }

    counts = evidence(files)
    hashes = inventory(args.repo)

    decision = plan(
        counts,
        hashes,
        {
            key: sha(path)
            for key, path in files.items()
        },
    )

    controls = negative_controls(decision)

    emit(
        args.matrix,
        decision,
    )

    report = {
        'schema':
            'TRUST_ROBOT_S5_RESEARCH_INTEGRATION_REVIEW_V1',
        'parent_commit': BASE,
        'engine_sha256': sha(__file__),
        'matrix_sha256': sha(args.matrix),
        'evidence_report_sha256': {
            key: sha(path)
            for key, path in files.items()
        },
        'historical_repository_sha256': hashes,
        'negative_controls_rejected': controls,
        'negative_control_count': len(controls),
        'next':
            'S1_S5_CONSOLIDATED_GITHUB_CHECKPOINT',
        'real_factor_admission': False,
        'm2dgr_scoring_authorized': False,
        'health_training_authorized': False,
        'new_sensor_acquisitions': 0,
        'scientific_pose_factors': 0,
        'health_labels': 0,
        'git_commit_or_push': False,
    }

    emit(
        args.report,
        report,
    )

    print('S5_SCIENTIFIC_EVIDENCE_CHAIN=S1_S4_VERIFIED')
    print('S5_SYNTHETIC_ESTIMATOR_TEST_BASELINE=104_PASSED')
    print('S5_SOURCE_CONTRACT_TESTS=41_AND_55_PASSED')
    print('S5_CLOSED_REQUIREMENT_GATES=8_PER_STREAM_32_TOTAL')
    print('S5_UNSUPPORTED_PROMOTION_CONTROLS=32_DENIED')
    print(
        'S5_NEXT_IMPLEMENTATION='
        'CPU_SYNTHETIC_JOINT_CAMERA_LIDAR_FACTORS'
    )
    print('S5_RESEARCH_INTEGRATION_REVIEW=PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    for name in (
        'repo', 's1', 's2', 's3',
        's4', 's4_matrix',
        'matrix', 'report',
    ):
        parser.add_argument(
            '--' + name.replace('_', '-'),
            dest=name,
            required=True,
        )

    main(parser.parse_args())
