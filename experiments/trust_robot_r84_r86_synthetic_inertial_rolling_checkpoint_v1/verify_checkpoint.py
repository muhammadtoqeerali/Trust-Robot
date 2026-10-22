"""R87 stand-alone integrity, cross-phase and fail-closed verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA = 'TRUST_ROBOT_R84_R86_SYNTHETIC_INERTIAL_ROLLING_CHECKPOINT_V1'
BASE = '885bf22f7454a85cee53b82f5d6a5cbd7d3eff3e'
CASES = ('continuous', 'single_gap', 'accel_injection', 'gyro_injection')

def need(ok, why):
    if not ok:
        raise ValueError('R87_DENIED:' + why)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def obj(root, rel):
    return json.loads((root / rel).read_bytes())

def check(root):
    need(root.is_dir() and not root.is_symlink(), 'ROOT')

    m = obj(root, 'checkpoint_manifest_v1.json')

    need(
        m.get('schema') == SCHEMA
        and m.get('parent_commit') == BASE,
        'IDENTITY'
    )
    need(
        m.get('branch') == 'kios-isaacsim-v15-integration',
        'BRANCH'
    )

    pins = m.get('source_sha256')
    meta = m.get('metadata_sha256')

    need(
        type(pins) is dict
        and len(pins) == 12
        and m.get('source_count') == 12,
        'SOURCE_COUNT'
    )
    need(
        type(meta) is dict
        and set(meta) == {'README.md', 'verify_checkpoint.py'},
        'META'
    )

    names = {
        f'evidence/{p}/{category}/{name}'
        for p, values in {
            'r84': {
                'dev': ('r84_gap_frontend.py', 'test_r84.py'),
                'result': (
                    'r84_synthetic_inertial_gap_frontend_v1.json',
                    'r84_independent_validation_v1.json'
                )
            },
            'r85': {
                'dev': ('r85_fusion.py', 'test_r85.py'),
                'result': (
                    'r85_synthetic_gap_aware_fusion_v1.json',
                    'r85_independent_validation_v1.json'
                )
            },
            'r86': {
                'dev': ('r86_rolling.py', 'test_r86.py'),
                'result': (
                    'r86_synthetic_rolling_optimization_v1.json',
                    'r86_independent_validation_v1.json'
                )
            }
        }.items()
        for category, seq in values.items()
        for name in seq
    }

    need(set(pins) == names, 'SOURCE_ALLOWLIST')

    expected = (
        set(pins)
        | set(meta)
        | {'checkpoint_manifest_v1.json'}
    )

    need(len(expected) == 15, 'EXACT_FILE_COUNT')

    dirs = set()

    for name in expected:
        part = pathlib.PurePosixPath(name)
        need(
            not part.is_absolute()
            and '..' not in part.parts,
            'PATH'
        )
        dirs.update(
            '/'.join(part.parts[:i])
            for i in range(1, len(part.parts))
        )

    need(
        {
            str(p.relative_to(root))
            for p in root.rglob('*')
        } == expected | dirs,
        'FILE_DIRECTORY_ALLOWLIST'
    )

    for name in dirs:
        p = root / name
        need(
            p.is_dir() and not p.is_symlink(),
            'DIR:' + name
        )

    for name in expected:
        info = (root / name).lstat()
        need(
            stat.S_ISREG(info.st_mode)
            and info.st_nlink == 1
            and 0 < info.st_size <= 4000000,
            'FILE:' + name
        )

    for name, pin in {**pins, **meta}.items():
        need(
            type(pin) is str
            and len(pin) == 64
            and sha((root / name).read_bytes()) == pin,
            'SHA:' + name
        )

    def artifact(phase, filename):
        return f'evidence/{phase}/result/{filename}'

    reports = {
        'r84': artifact(
            'r84', 'r84_synthetic_inertial_gap_frontend_v1.json'
        ),
        'r85': artifact(
            'r85', 'r85_synthetic_gap_aware_fusion_v1.json'
        ),
        'r86': artifact(
            'r86', 'r86_synthetic_rolling_optimization_v1.json'
        )
    }

    receipts = {
        p: artifact(p, p + '_independent_validation_v1.json')
        for p in ('r84', 'r85', 'r86')
    }

    data = {
        p: obj(root, name)
        for p, name in reports.items()
    }

    for p, report in data.items():
        v = obj(root, receipts[p])

        need(
            report.get('status') == 'PASS_SOFTWARE_ONLY'
            and report.get('scientific_gates_closed') == 11,
            p + ':STATUS'
        )
        need(
            v.get('status') == 'PASS'
            and v.get('scientific_gates_closed') == 11,
            p + ':RECEIPT_STATUS'
        )
        need(
            v.get('result_sha256') == pins[reports[p]],
            p + ':RECEIPT_RESULT'
        )

        engine_name = {
            'r84': 'gap_frontend.py',
            'r85': 'fusion.py',
            'r86': 'rolling.py'
        }[p]

        need(
            v.get('engine_sha256') ==
            pins[f'evidence/{p}/dev/{p}_' + engine_name],
            p + ':RECEIPT_ENGINE'
        )
        need(
            v.get('tests_sha256') ==
            pins[f'evidence/{p}/dev/test_{p}.py'],
            p + ':RECEIPT_TEST'
        )
        need(
            report.get(
                'scenario_count',
                report.get('synthetic_cases_executed')
            ) == 4,
            p + ':CASE_COUNT'
        )
        need(
            set(report['scenarios']) == set(CASES),
            p + ':CASE_NAMES'
        )

    need(
        data['r85'].get('r84_report_sha256') == pins[reports['r84']],
        'R84_R85_LINEAGE'
    )
    need(
        data['r86'].get('r84_report_sha256') == pins[reports['r84']]
        and data['r86'].get('r85_report_sha256') == pins[reports['r85']],
        'R84_R86_LINEAGE'
    )
    need(
        obj(root, receipts['r85']).get('r84_report_sha256') ==
        pins[reports['r84']],
        'R85_RECEIPT_PARENT'
    )

    for p in ('r84', 'r85', 'r86'):
        need(
            data[p].get(
                'raw_rosbags_or_gt_opened',
                data[p].get('rosbags_or_gt_opened')
            ) is False,
            p + ':RAW'
        )
        need(
            data[p].get('confirmation_test_accessed') is False,
            p + ':CONFIRMATION'
        )

    r84, r85, r86 = (
        data[p]
        for p in ('r84', 'r85', 'r86')
    )

    need(
        r84.get('recorded_imu_preintegration_performed') is False
        and r84.get('real_pose_factors_authorized') is False
        and r84.get('health_training_authorized') is False
        and r84.get('ate_rpe_authorized') is False,
        'R84_DENIAL'
    )
    need(
        r85.get('cross_gap_factors_constructed') == 0
        and r85.get('recorded_sensor_pose_factors_constructed') == 0
        and r85.get('real_estimator_optimization_executed') is False
        and r85.get('constructed_endpoint_is_independent_truth') is False,
        'R85_DENIAL'
    )
    need(
        r86.get('nonlinear_optimization_implemented') is True
        and r86.get('independent_reference_accuracy_claimed') is False
        and r86.get('probabilistic_schur_marginalization_implemented') is False
        and r86.get('real_lidar_or_imu_factor_execution') is False
        and r86.get('ate_rpe_computed') is False,
        'R86_DENIAL'
    )

    for case in CASES:
        a = r84['scenarios'][case]
        b = r85['scenarios'][case]
        c = r86['scenarios'][case]

        need(
            a['safe_window_count'] ==
            b['safe_factor_count'] ==
            c['nonlinear_window_solves'],
            'WINDOW_COUNTS:' + case
        )
        need(
            a['gap_count'] ==
            b['rejected_gap_pairs'] ==
            c['rejected_gap_pairs'],
            'GAP_COUNTS:' + case
        )
        need(
            b['segment_count'] ==
            c['segments_with_independent_anchors'],
            'SEGMENTS:' + case
        )
        need(
            b['bridging_gap_factors'] ==
            c['cross_gap_factor_count'] == 0,
            'CROSS_GAP:' + case
        )
        need(
            c['global_chain_estimated_across_gaps'] is False
            and c['real_sensor_factors_admitted'] is False,
            'SOLVER_BOUNDARY:' + case
        )
        need(
            c['nonlinear_15d_optimizer_executed'] is True,
            'SOLVER:' + case
        )
        need(
            len(b['edges']) == len(c['windows']),
            'EDGE_SOLVE_COUNT:' + case
        )
        need(
            c['inertial_pairs_integrated'] +
            c['rejected_gap_pairs'] ==
            c['input_synthetic_packets'] - 1,
            'PAIR_ACCOUNTING:' + case
        )

        for e, w in zip(b['edges'], c['windows']):
            need(
                e['from_node'] == w['from_node']
                and e['to_node'] == w['to_node']
                and e['segment_id'] == w['segment_id'],
                'EDGE_BINDING:' + case
            )
            need(
                w['jacobian_rank'] == 15
                and w['jacobian_columns'] == 15,
                'LOCAL_RANK:' + case
            )
            need(
                w['initial_residual_norm'] >
                100 * w['final_residual_norm']
                and w['final_residual_norm'] < 1e-6,
                'RESIDUAL_REDUCTION:' + case
            )
            need(
                w['constructed_endpoint_state_error_norm'] < 1e-4,
                'CONSTRUCTED_CLOSURE:' + case
            )
            need(
                w['real_measurement_factor_executable'] is False
                and w['constructed_endpoint_independent_reference'] is False
                and w['schur_marginalization_applied'] is False,
                'WINDOW_DENIAL:' + case
            )
            need(
                e['real_factor_executable'] is False,
                'INERTIAL_EDGE_DENIAL:' + case
            )

        need(
            sum(
                w['synthetic_anchor_reset_here'] is True
                for w in c['windows']
            ) == c['segments_with_independent_anchors'],
            'GAUGE_ANCHORS:' + case
        )

    need(
        (
            r86['scenarios']['continuous'][
                'segments_with_independent_anchors'
            ],
            r86['scenarios']['single_gap'][
                'segments_with_independent_anchors'
            ]
        ) == (1, 2),
        'EXPECTED_SEGMENTS'
    )
    need(
        r86['scenarios']['single_gap']['rejected_gap_pairs'] == 1,
        'EXPECTED_GAP'
    )

    for name in (
        'recorded_sensor_factors_executed',
        'physical_clock_and_extrinsic_qualified',
        'independent_gt_accuracy_demonstrated',
        'health_training_authorized',
        'ate_rpe_authorized',
        'schur_marginalization_implemented',
        'original_gt_or_rosbags_archived',
        'private_verona_reports_archived',
        'confirmation_test_accessed'
    ):
        need(
            m.get(name) is False,
            'CHECKPOINT_DENIAL:' + name
        )

    need(
        m.get('scientific_gates_closed') == 11
        and m.get('r84_r85_r86_regression_tests') == 63,
        'CHECKPOINT_GATES'
    )

    for name in pins:
        raw = (root / name).read_bytes()
        need(
            not any(
                v in raw
                for v in (
                    b'/home/kios/',
                    b'/mnt/hdd16T/',
                    b'C:\\Users\\'
                )
            ),
            'PRIVATE_PATH:' + name
        )

    print('R87_STANDALONE_VERIFIER=PASS')
    print('R87_EXACT_SOURCE_FILES=12_SHA256_VERIFIED')
    print('R87_R84_R86_LINEAGE_AND_ROLLING_CHECKS=PASS')
    print('R87_ELEVEN_SCIENTIFIC_GATES=ALL_CLOSED')

if __name__ == '__main__':
    need(
        len(sys.argv) == 3 and sys.argv[1] == 'verify',
        'ARGUMENTS'
    )
    check(pathlib.Path(sys.argv[2]))
