"""R109 standalone SHA-pinned incremental delivery checkpoint verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R107_R108_INCREMENTAL_DELIVERY_CHECKPOINT_V1'
BASE='ab108fb5913373de44b9ba9b08c1254607c59521'
BRANCH='kios-isaacsim-v15-integration'
S6_SHA='a1c9d0b4b9219d1e1b370e5ab5f42fcb25ac53f1b77f005cb42b3497b90bfc9a'

PINS={
    'evidence/r107/dev/r107_incremental.py':
        '0e9642b1e4187514de2daa20461f7527fe66f7e2fa5b31ca6d63d0bc0fbfb021',

    'evidence/r107/dev/test_r107.py':
        'a2fbfcf982109254428e8475c75a63178d81eb5202da04aea77cf8dc3caf36d8',

    'evidence/r107/dev/r107_incremental_contract_v1.md':
        'af58b8acecda82a11108c4020b172db096ff9166bbb13db7cbf5ba995aee33f6',

    'evidence/r107/result/r107_incremental_integration_v1.json':
        'c370ddbb599a1885727331d916122f8e815d65230e43d701838d0ca985c31017',

    'evidence/r107/result/r107_independent_validation_v1.json':
        '4f5f0a8254963857c713ced3a2e04afaa716070a300e129e0661fc59ba4231be',

    'evidence/r108/dev/r108_delivery.py':
        '66895af848c1081914e11735da036349d04caafdb94bf9f5e62ee19510eb060d',

    'evidence/r108/dev/test_r108.py':
        'a6c7db8c0859068a5b7a6b22b53872a90dad1a0665a39f7bffd2ea347586949b',

    'evidence/r108/dev/r108_delivery_contract_v1.md':
        'f83f7fcdc7dbe867863fd063f701b7ac01dc79df2cb1bc38a433a970d07c7648',

    'evidence/r108/result/r108_delivery_fault_report_v1.json':
        '2280eab26c60d62099cdba83404e4c55fd240402f227dbd1add5250193fc2643',

    'evidence/r108/result/r108_independent_validation_v1.json':
        '267bb689a62eccdbb3cc3442d50e6d8d5158a991b32f6b9b736c2ba92923e753',
}

DOCS={
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R107_R108_INCREMENTAL_DELIVERY_CHECKPOINT_V1.md',
}

def need(flag,reason):
    if not flag:
        raise ValueError(
            'R109_CHECKPOINT_DENIED:'+reason
        )

def sha(data):
    return hashlib.sha256(data).hexdigest()

def obj(root,name):
    return json.loads((root/name).read_bytes())

def verify(root):
    need(
        root.is_dir() and not root.is_symlink(),
        'ARCHIVE_ROOT'
    )

    m=obj(root,'checkpoint_manifest_v1.json')

    need(m.get('schema')==SCHEMA,'SCHEMA')
    need(m.get('parent_commit')==BASE,'PARENT')
    need(m.get('branch')==BRANCH,'BRANCH')

    need(
        m.get('source_sha256')==PINS
        and m.get('source_count')==10,
        'SOURCE_PINS'
    )

    metadata=m.get('metadata_sha256')

    need(
        type(metadata) is dict
        and set(metadata)=={
            'README.md',
            'verify_checkpoint.py',
        },
        'METADATA_PINS'
    )

    documents=m.get('documentation_sha256')

    need(
        type(documents) is dict
        and set(documents)==DOCS,
        'DOCUMENT_PINS'
    )

    expected=set(PINS)|set(metadata)|{
        'checkpoint_manifest_v1.json'
    }

    directories=set()

    for name in expected:
        path=pathlib.PurePosixPath(name)

        need(
            not path.is_absolute()
            and '..' not in path.parts,
            'UNSAFE_PATH'
        )

        for index in range(1,len(path.parts)):
            directories.add(
                '/'.join(path.parts[:index])
            )

    observed={
        p.relative_to(root).as_posix()
        for p in root.rglob('*')
    }

    need(
        observed==expected|directories,
        'EXACT_ARCHIVE_TREE'
    )

    for name in directories:
        p=root/name

        need(
            p.is_dir() and not p.is_symlink(),
            'ARCHIVE_DIRECTORY'
        )

    for name in expected:
        p=root/name
        s=p.lstat()

        need(
            stat.S_ISREG(s.st_mode)
            and s.st_nlink==1
            and 0<s.st_size<2000000,
            'REGULAR_FILE:'+name
        )

    # Deliberately split private-path signatures
    # to avoid matching this verifier's own source.
    forbidden=(
        b'/home/'+b'kios/',
        b'/mnt/'+b'hdd16T/',
        b'C:'+b'\\Users\\',
    )

    for name,pin in {**PINS,**metadata}.items():
        raw=(root/name).read_bytes()

        need(
            type(pin) is str
            and len(pin)==64
            and sha(raw)==pin,
            'SOURCE_SHA:'+name
        )

        need(
            not any(x in raw for x in forbidden),
            'PRIVATE_PATH:'+name
        )

    a=obj(
        root,
        'evidence/r107/result/r107_incremental_integration_v1.json'
    )

    b=obj(
        root,
        'evidence/r108/result/r108_delivery_fault_report_v1.json'
    )

    va=obj(
        root,
        'evidence/r107/result/r107_independent_validation_v1.json'
    )

    vb=obj(
        root,
        'evidence/r108/result/r108_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R107_SYNTHETIC_INCREMENTAL_INTEGRATION_V1',
        'R107_SCHEMA'
    )

    need(
        b.get('schema')==
        'TRUST_ROBOT_R108_BOUNDED_SYNTHETIC_DELIVERY_V1',
        'R108_SCHEMA'
    )

    need(
        a.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY'
        and b.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY',
        'REPORT_STATUS'
    )

    need(
        a.get('scenarios')==3
        and a.get('ordinary_incremental_windows')==12
        and a.get('recentered_incremental_windows')==12
        and a.get('ordinary_schur_marginalizations')==9
        and a.get('recentered_schur_marginalizations')==9
        and a.get('same_graph_prior_transfers')==9,
        'R107_COUNTS'
    )

    need(
        type(a.get('cases')) is dict
        and len(a['cases'])==3,
        'R107_CASES'
    )

    for case in a['cases'].values():
        need(
            case.get('node_count')==5
            and case.get('imu_sample_count')==8
            and case.get('imu_factor_count')==4
            and case.get('ordinary_windows')==4
            and case.get('recentered_windows')==4
            and case.get('ordinary_marginalizations')==3
            and case.get('recentered_marginalizations')==3
            and case.get('recentered_prior_transfers')==3,
            'R107_CASE_COUNTS'
        )

        need(
            0<=case.get('ordinary_vs_s6_max_abs_error',1)<1e-8
            and 0<=case.get('recentered_vs_s6_max_abs_error',1)<2e-5,
            'R107_S6_EQUIVALENCE'
        )

        need(
            case.get('factor_ownership_equivalent') is True
            and case.get('future_factor_consumed') is False
            and case.get('recorded_sensor_factor_executed') is False
            and case.get('admitted_sample_indices')==list(range(8)),
            'R107_FACTOR_ADMISSION'
        )

        need(
            len(case.get('window_ledger',[]))==4
            and len(case.get('elimination_ledger',[]))==3
            and len(case.get('transfer_ledger',[]))==3,
            'R107_EVENT_LEDGER'
        )

    need(
        b.get('synthetic_scenarios')==3
        and b.get('delivery_schedules_per_scenario')==2
        and b.get('solver_modes_per_schedule')==2
        and b.get('total_solver_runs')==12
        and b.get('nonlinear_windows')==48
        and b.get('schur_marginalizations')==36
        and b.get('same_graph_prior_transfers')==18,
        'R108_COUNTS'
    )

    need(
        type(b.get('cases')) is dict
        and len(b['cases'])==3,
        'R108_CASES'
    )

    for case in b['cases'].values():
        runs=case.get('runs')

        need(
            case.get('run_count')==4
            and type(runs) is dict
            and len(runs)==4
            and case.get('synthetic_only') is True,
            'R108_RUNS'
        )

        for name,row in runs.items():
            expected_arrival=(
                [1,2,3,4]
                if name.startswith('ordered')
                else [3,2,1,4]
            )

            need(
                row.get('arrival_order')==expected_arrival
                and row.get('processed_order')==[1,2,3,4]
                and row.get('windows')==4
                and row.get('marginalizations')==3,
                'R108_ORDERING'
            )

            recentered=name.endswith('recentered')

            need(
                row.get('prior_transfers')==
                (3 if recentered else 0),
                'R108_TRANSFER_COUNT'
            )

            threshold=2e-5 if recentered else 1e-8

            need(
                0<=row.get('max_abs_error_vs_s6',1)<threshold,
                'R108_ESTIMATOR_EQUIVALENCE'
            )

            need(
                row.get('pose_ledger_equal') is True
                and row.get('imu_sample_identity_preserved') is True
                and row.get('future_factor_consumed') is False
                and row.get('duplicate_factor_consumed') is False,
                'R108_FACTOR_OWNERSHIP'
            )

    need(
        a.get('scientific_gates_closed')==11
        and b.get('scientific_gates_closed')==11,
        'REPORT_SCIENTIFIC_GATES'
    )

    for key in (
        'original_s6_source_modified',
        'r95_backend_imported',
        'actual_physical_online_streaming_tested',
        'real_sensor_factors_authorized',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_opened',
    ):
        need(
            a.get(key) is False,
            'R107_SCIENCE_DENIAL:'+key
        )

    for key in (
        'future_factor_execution',
        'r95_gaussian_backend_imported',
        'actual_hardware_capture_tested',
        'physical_arrival_jitter_measured',
        'execution_deadlines_verified',
        'transport_authentication_verified',
        'transactional_solver_rollback_proven',
        'real_sensor_factors_authorized',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_opened',
    ):
        need(
            b.get(key) is False,
            'R108_SCIENCE_DENIAL:'+key
        )

    need(
        va.get('schema')==
        'TRUST_ROBOT_R107_INDEPENDENT_INCREMENTAL_VALIDATION_V1'
        and va.get('status')=='PASS'
        and va.get('regression_tests')==38,
        'R107_RECEIPT'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R108_INDEPENDENT_DELIVERY_VALIDATION_V1'
        and vb.get('status')=='PASS'
        and vb.get('regression_tests')==42,
        'R108_RECEIPT'
    )

    for receipt,phase,engine,test,contract,report in (
        (
            va,'r107','r107_incremental.py',
            'test_r107.py',
            'r107_incremental_contract_v1.md',
            'r107_incremental_integration_v1.json',
        ),
        (
            vb,'r108','r108_delivery.py',
            'test_r108.py',
            'r108_delivery_contract_v1.md',
            'r108_delivery_fault_report_v1.json',
        ),
    ):
        prefix='evidence/'+phase+'/'

        need(
            receipt.get('engine_sha256')==
                PINS[prefix+'dev/'+engine]
            and receipt.get('tests_sha256')==
                PINS[prefix+'dev/'+test]
            and receipt.get('contract_sha256')==
                PINS[prefix+'dev/'+contract]
            and receipt.get('report_sha256')==
                PINS[prefix+'result/'+report],
            'RECEIPT_HASH:'+phase
        )

        need(
            receipt.get('parent_git_commit')==BASE
            and receipt.get('s6_source_sha256')==S6_SHA
            and receipt.get('scientific_gates_closed')==11
            and receipt.get('real_sensor_factors_authorized') is False
            and receipt.get('confirmation_test_accessed') is False,
            'RECEIPT_SCIENCE:'+phase
        )

    need(
        vb.get('r107_report_sha256')==
        PINS['evidence/r107/result/r107_incremental_integration_v1.json'],
        'R107_R108_LINEAGE'
    )

    need(
        m.get('r107_test_count')==38
        and m.get('r108_test_count')==42
        and m.get('archived_regression_tests')==80
        and m.get('source_count')==10
        and m.get('s6_source_sha256')==S6_SHA
        and m.get('scientific_gates_closed')==11,
        'MANIFEST_COUNTS'
    )

    for key in (
        'real_sensor_factor_execution_authorized',
        'r95_backend_merged_into_s6',
        'physical_clock_or_extrinsics_verified',
        'hardware_streaming_verified',
        'transport_authentication_verified',
        'solver_transactional_rollback_proven',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_archived',
        'qualified_author_reply_ingested',
    ):
        need(
            m.get(key) is False,
            'MANIFEST_GATES:'+key
        )

    print('R109_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R109_SOURCE_AND_METADATA_SHA256=12_PASS')
    print('R109_R107_R108_LINEAGE=PASS')
    print('R109_INCREMENTAL_AND_REORDERING_AUDIT=PASS')
    print('R109_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3
        and sys.argv[1]=='verify',
        'ARGUMENTS'
    )

    verify(pathlib.Path(sys.argv[2]))
