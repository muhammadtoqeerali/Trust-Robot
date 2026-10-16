"""Separate-process verification of S5 evidence and decision."""

import argparse
import ast
import hashlib
import json
from pathlib import Path

BASE = '79a2abf6de6ff68df23de8bd04b538ce0c95b46b'

GATES = {
    'physical_capture_event_verified',
    'sensor_clock_domain_verified',
    'cross_stream_offset_verified',
    'association_tolerance_qualified',
    'full_body_sensor_extrinsic_verified',
    'independent_reference_origin_and_time_verified',
    'factor_covariance_empirically_calibrated',
    'recorded_factor_execution_authorized',
}

CLOSED = {
    'real_sensor_factors_authorized',
    'm2dgr_estimator_scoring_authorized',
    'health_model_training_authorized',
    'live_simulator_launch_authorized',
    'global_replay_protection_proven',
    'sensor_timing_and_extrinsics_qualified',
}

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


def need(ok, reason):
    if not ok:
        raise AssertionError(
            'S5_VERIFY:' + reason
        )


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def read(path):
    return json.loads(
        Path(path).read_text()
    )


def main(args):
    root = Path(args.repo)

    matrix = read(args.matrix)
    report = read(args.report)

    need(
        matrix['schema']
        == 'TRUST_ROBOT_S5_RESEARCH_INTEGRATION_DECISION_V1'
        and report['schema']
        == 'TRUST_ROBOT_S5_RESEARCH_INTEGRATION_REVIEW_V1',
        'SCHEMAS',
    )

    need(
        matrix['parent_commit']
        == report['parent_commit']
        == BASE
        and report['engine_sha256']
        == sha(args.engine)
        and report['matrix_sha256']
        == sha(args.matrix),
        'LINEAGE',
    )

    files = {
        key: getattr(args, key)
        for key in (
            's1', 's2', 's3', 's4', 's4_matrix'
        )
    }

    expected_hashes = {
        key: sha(path)
        for key, path in files.items()
    }

    need(
        report['evidence_report_sha256']
        == matrix['s1_s4_report_and_matrix_sha256']
        == expected_hashes,
        'EVIDENCE_HASHES',
    )

    expected_repo_hashes = {
        key: sha(root / relative)
        for key, relative in PATHS.items()
    }

    need(
        matrix['repository_evidence_sha256']
        == report['historical_repository_sha256']
        == expected_repo_hashes,
        'REPOSITORY_HASHES',
    )

    s1, s2, s3, s4, s4m = (
        read(files[key])
        for key in (
            's1', 's2', 's3', 's4', 's4_matrix'
        )
    )

    expected_counts = {
        'analytic_source_test_pairs_inventoried':
            s1['analytic_module_count'],
        'selected_synthetic_regression_tests_passed':
            s2['regression_test_count'],
        's3_contract_tests_passed':
            s3['test_cases_passed'],
        's4_requirement_tests_passed':
            s4['tests_passed'],
        'train_streams_described':
            s4m['stream_count'],
        'unverified_m2dgr_synchronization_entries':
            s1['m2dgr_sync_entries'],
        'unqualified_s4_gate_instances':
            s4m['unqualified_gate_instances'],
        'recorded_sensor_pose_factors_generated':
            s4['recorded_sensor_factors_generated'],
        'health_labels_generated':
            s4['health_labels'],
    }

    need(
        matrix['evidence_counts'] == expected_counts
        and (
            expected_counts[
                'selected_synthetic_regression_tests_passed'
            ],
            expected_counts[
                's3_contract_tests_passed'
            ],
            expected_counts[
                's4_requirement_tests_passed'
            ],
        ) == (104, 41, 55),
        'TEST_COUNTS',
    )

    need(
        s1['m2dgr_sync_qualified'] == 0
        and s1['m2dgr_trajectory_count'] == 36
        and s2['m2dgr_scoring_authorized'] is False,
        'M2DGR_GATE',
    )

    need(
        len(s4m['streams']) == 4
        and all(
            set(row['requirement_gates']) == GATES
            and all(
                value is False
                for value in row[
                    'requirement_gates'
                ].values()
            )
            for row in s4m['streams']
        ),
        'S4_EVIDENCE',
    )

    need(
        set(matrix['required_evidence_per_stream'])
        == GATES
        and all(
            value is False
            for value in matrix[
                'required_evidence_per_stream'
            ].values()
        ),
        'CLOSED_REQUIREMENTS',
    )

    need(
        set(matrix['gates']) == CLOSED
        and all(
            value is False
            for value in matrix['gates'].values()
        ),
        'CLOSED_SCIENCE_GATES',
    )

    need(
        matrix['scientific_verdict']
        == 'DEVELOPMENT_ONLY_REAL_SENSOR_FACTORS_DENIED',
        'VERDICT',
    )

    task = matrix['next_implementation']

    need(
        task['work_id']
        == 'S6_CPU_ONLY_INDEPENDENT_CAMERA_LIDAR_SAME_EDGE_FUSION'
        and task['input_scope']
        == 'MANUFACTURED_FIXTURES_ONLY'
        and task['real_sensor_admission'] is False
        and task['evaluation_metric_claim']
        == 'SYNTHETIC_REGRESSION_ONLY',
        'NEXT_TASK',
    )

    source = root / PATHS['factor_interface']

    functions = {
        node.name: node
        for node in ast.parse(
            source.read_text()
        ).body
        if isinstance(node, ast.FunctionDef)
    }

    need(
        'assemble_synthetic_pose_slot' in functions,
        'OLD_ADAPTER',
    )

    need(
        'does NOT support simultaneous independent camera and LiDAR factors'
        in ' '.join(
            (ast.get_docstring(
                functions['assemble_synthetic_pose_slot']
            ) or '').split()
        ),
        'ADAPTER_LIMITATION',
    )

    need(
        matrix[
            'historical_train_ingestion_observed_in_published_audit'
        ] is True
        and matrix[
            'historical_train_ingestion_proves_calibration_or_factor_admission'
        ] is False,
        'HISTORIC_INGEST_SCOPE',
    )

    need(
        matrix['raw_sensor_recordings_read_in_s5']
        is False
        and matrix['confirmation_test_used_in_s5']
        is False
        and matrix['live_simulator_launched_in_s5']
        is False,
        'OFFLINE_GATE',
    )

    need(
        matrix['scientific_pose_factors_admitted_in_s5']
        == 0
        and matrix['health_labels_generated_in_s5']
        == 0,
        'SCIENCE_GATE',
    )

    need(
        len(matrix['physical_evidence_blockers'])
        == 6,
        'PHYSICAL_GAPS',
    )

    controls = report[
        'negative_controls_rejected'
    ]

    need(
        len(controls)
        == report['negative_control_count']
        == 32
        and len(set(controls)) == 32,
        'NEGATIVE_CONTROLS',
    )

    need(
        report['new_sensor_acquisitions'] == 0
        and report['scientific_pose_factors'] == 0
        and report['health_labels'] == 0
        and report['git_commit_or_push'] is False,
        'REPORT_FLAGS',
    )

    result = {
        'schema':
            'TRUST_ROBOT_S5_INDEPENDENT_VALIDATION_V1',
        'engine_sha256': sha(args.engine),
        'verifier_sha256': sha(__file__),
        'matrix_sha256': sha(args.matrix),
        'report_sha256': sha(args.report),
        'independently_checked_source_reports': 5,
        'existing_regression_tests_verified': 104,
        's3_contract_tests_verified': 41,
        's4_contract_tests_verified': 55,
        'closed_gate_instances_verified': 32,
        'false_promotion_controls_reviewed': 32,
        'ready_next_task':
            'S6_CPU_ONLY_INDEPENDENT_CAMERA_LIDAR_SAME_EDGE_FUSION',
        'real_recorded_factor_admission': False,
        'm2dgr_scoring_authorized': False,
        'new_sensor_acquisitions': 0,
        'scientific_pose_factors': 0,
        'health_labels': 0,
    }

    with Path(args.validation).open(
        'x',
        encoding='utf-8',
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write('\n')

    print('S5_INDEPENDENT_PRIOR_PHASES=S1_S4_VERIFIED')
    print(
        'S5_INDEPENDENT_REGRESSION_AND_CONTRACT_TESTS='
        '104_41_55'
    )
    print(
        'S5_INDEPENDENT_CLOSED_GATE_INSTANCES='
        '32_VERIFIED'
    )
    print('S5_INDEPENDENT_SCIENCE_BOUNDARIES=DENIED')
    print('S5_INDEPENDENT_VALIDATION=PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    for name in (
        'repo', 'engine', 's1', 's2',
        's3', 's4', 's4_matrix',
        'matrix', 'report', 'validation',
    ):
        parser.add_argument(
            '--' + name.replace('_', '-'),
            dest=name,
            required=True,
        )

    main(parser.parse_args())
