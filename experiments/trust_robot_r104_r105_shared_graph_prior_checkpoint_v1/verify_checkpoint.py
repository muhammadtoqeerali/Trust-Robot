"""R106 SHA-pinned checkpoint verifier; independent of source modules."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R104_R105_SHARED_GRAPH_PRIOR_CHECKPOINT_V1'
BASE='b20f4b8a89b4521c509f0856d4e3d4aebe90de37'
S6_SHA='a1c9d0b4b9219d1e1b370e5ab5f42fcb25ac53f1b77f005cb42b3497b90bfc9a'

PINS={
 'evidence/r104/dev/r104_shared_graph.py':
 'd71ac7f805675e88ddc64013f1125f32d1c83eba669b3a8f9ef82bf269a0acb5',

 'evidence/r104/dev/test_r104.py':
 '501ee1a8b97944f4b4f17c26826777b76c246f9d69f4a11e1d3e5032ae9512b6',

 'evidence/r104/dev/r104_graph_contract_v1.md':
 '26c680354f7c1af98e04c3e547bfa8e32f021744fd2359cd944c8565a1f9b541',

 'evidence/r104/result/r104_shared_synthetic_graph_v1.json':
 '635931e0d7f04b8636dd4f90c01b5ea7bbd6595495086f7b471e0e0764e34876',

 'evidence/r104/result/r104_independent_validation_v1.json':
 '85137798ec01210ab461cad5386966390b9fd4e4688e3354809a03862b428c36',

 'evidence/r105/dev/r105_prior_transfer.py':
 '35fc7c1c826719965c55de80a162dd15dc2a8e0fa704f755d89cf3b9d911dbe1',

 'evidence/r105/dev/test_r105.py':
 '38ffe3302754ba720b14cfa3e1fbcc309adcca99586048a5811787395a127b91',

 'evidence/r105/dev/r105_transfer_contract_v1.md':
 '703210f2679e2ee217827e281253ff8932299e737ce44fd49849f6a50e5a2f6a',

 'evidence/r105/result/r105_aligned_prior_transfer_v1.json':
 'dafee59b539fe1b5d553a66a69242fdf3fe66af4f33154d54d13f90dc09f78d6',

 'evidence/r105/result/r105_independent_validation_v1.json':
 'dc766a6633e7f9faf7f8fed85792463603632e73f1771d693db82be382b360ca',
}

DOCS={
 'AGENTS.md',
 'docs/TRUST_ROBOT_PROJECT_STATE.md',
 'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R104_R105_SHARED_GRAPH_PRIOR_CHECKPOINT_V1.md',
}

def need(ok,why):
    if not ok:
        raise ValueError('R106_CHECKPOINT_DENIED:'+why)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def obj(root,path):
    return json.loads((root/path).read_bytes())

def verify(root):
    need(
        root.is_dir() and not root.is_symlink(),
        'ARCHIVE_ROOT'
    )

    m=obj(root,'checkpoint_manifest_v1.json')

    need(m.get('schema')==SCHEMA,'SCHEMA')
    need(m.get('parent_commit')==BASE,'PARENT')
    need(
        m.get('branch')=='kios-isaacsim-v15-integration',
        'BRANCH'
    )

    need(
        m.get('source_sha256')==PINS
        and m.get('source_count')==10,
        'SOURCE_PINS'
    )

    metadata=m.get('metadata_sha256')

    need(
        type(metadata) is dict
        and set(metadata)=={
            'README.md','verify_checkpoint.py'
        },
        'METADATA'
    )

    docs=m.get('documentation_sha256')

    need(
        type(docs) is dict and set(docs)==DOCS,
        'DOCUMENTATION_PINS'
    )

    expected=set(PINS)|set(metadata)|{
        'checkpoint_manifest_v1.json'
    }

    directories=set()

    for name in expected:
        p=pathlib.PurePosixPath(name)

        need(
            not p.is_absolute() and '..' not in p.parts,
            'UNSAFE_ARCHIVE_PATH'
        )

        for i in range(1,len(p.parts)):
            directories.add('/'.join(p.parts[:i]))

    observed={
        str(p.relative_to(root))
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

    # Split signatures so this verifier does not
    # falsely reject its own detection logic.
    forbidden=(
        b'/home/'+b'kios/',
        b'/mnt/'+b'hdd16T/',
        b'C:'+b'\\Users\\',
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

    for name,pin in {**PINS,**metadata}.items():
        raw=(root/name).read_bytes()

        need(
            type(pin) is str
            and len(pin)==64
            and sha(raw)==pin,
            'SOURCE_SHA:'+name
        )

        need(
            not any(sig in raw for sig in forbidden),
            'PRIVATE_PATH:'+name
        )

    a=obj(
        root,
        'evidence/r104/result/r104_shared_synthetic_graph_v1.json'
    )
    b=obj(
        root,
        'evidence/r105/result/r105_aligned_prior_transfer_v1.json'
    )
    va=obj(
        root,
        'evidence/r104/result/r104_independent_validation_v1.json'
    )
    vb=obj(
        root,
        'evidence/r105/result/r105_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R104_SHARED_SYNTHETIC_FACTOR_GRAPH_V1',
        'R104_SCHEMA'
    )

    need(
        b.get('schema')==
        'TRUST_ROBOT_R105_ALIGNED_SYNTHETIC_S6_PRIOR_TRANSFER_V1',
        'R105_SCHEMA'
    )

    need(
        a.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY'
        and b.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY',
        'REPORT_STATUS'
    )

    need(
        a.get('scenario_count')==3
        and a.get('nodes_per_case')==5
        and a.get('imu_samples_per_case')==8
        and a.get('imu_edges_per_case')==4
        and a.get('total_nonlinear_windows')==12
        and a.get('total_schur_marginalizations')==9,
        'R104_GRAPH_COUNTS'
    )

    need(
        type(a.get('cases')) is dict
        and len(a['cases'])==3,
        'R104_CASES'
    )

    for case in a['cases'].values():
        need(
            case.get('imu_factors')==4
            and case.get('nonlinear_windows')==4
            and case.get('marginalizations')==3,
            'R104_CASE_COUNTS'
        )

        need(
            case.get('pose_factors')==
            case.get('pose_factors_consumed')+
            case.get('pose_factors_remaining'),
            'R104_POSE_LEDGER'
        )

        need(
            case.get('imu_samples_used_exactly_once') is True
            and case.get('truth_passed_to_estimator') is False
            and case.get('real_sensor_factors_executed') is False,
            'R104_ADMISSION'
        )

    need(
        b.get('scenarios')==3
        and b.get('nonlinear_windows')==12
        and b.get('real_nonlinear_prior_rebase_transfers')==9,
        'R105_TRANSFER_COUNTS'
    )

    need(
        type(b.get('cases')) is dict
        and len(b['cases'])==3,
        'R105_CASES'
    )

    for case in b['cases'].values():
        events=case.get('events')

        need(
            case.get('transfers')==3
            and type(events) is list
            and len(events)==3,
            'R105_EVENTS'
        )

        need(
            case.get('instrumented_vs_original_state_max_abs_error',1)
            <2e-5,
            'R105_SOLVER_EQUIVALENCE'
        )

        need(
            case.get('factor_identity_audit_unchanged') is True
            and case.get('source_graph_validated') is True
            and case.get('r95_prior_imported') is False
            and case.get('real_sensor_factors_executed') is False,
            'R105_LEDGER'
        )

        for i,e in enumerate(events):
            need(
                e.get('index')==i
                and e.get('retained_nodes')==[i+1,i+2],
                'R105_EVENT_ORDER'
            )

            need(
                e.get('max_residual_absolute_error',1)<1e-8
                and e.get('information_relative_error',1)<1e-11
                and e.get('gradient_transform_relative_error',1)<1e-9,
                'R105_LOCAL_NUMERICS'
            )

            need(
                e.get('returned_to_actual_s6_nonlinear_solver')
                is True
                and e.get('frozen_factor_jacobians_refreshed')
                is False,
                'R105_TRANSFER_BOUNDARY'
            )

    need(
        a.get('scientific_gates_closed')==11
        and b.get('scientific_gates_closed')==11,
        'REPORT_GATES'
    )

    for key in (
        'r95_prior_imported_into_s6',
        'new_estimator_backend_implemented',
        'physical_sensor_synchronization_verified',
        'physical_extrinsics_verified',
        'real_sensor_factors_authorized',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'original_gt_or_rosbags_opened',
    ):
        need(a.get(key) is False,'R104_DENIAL:'+key)

    for key in (
        'r95_gaussian_backend_imported',
        'new_physical_frame_alignment_verified',
        'new_nonlinear_factor_jacobian_refresh_performed',
        'real_sensor_factors_authorized',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'original_gt_or_rosbags_opened',
    ):
        need(b.get(key) is False,'R105_DENIAL:'+key)

    need(
        va.get('schema')==
        'TRUST_ROBOT_R104_INDEPENDENT_GRAPH_VALIDATION_V1'
        and va.get('status')=='PASS'
        and va.get('regression_tests')==48,
        'R104_RECEIPT'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R105_INDEPENDENT_TRANSFER_VALIDATION_V1'
        and vb.get('status')=='PASS'
        and vb.get('regression_tests')==33
        and vb.get('same_graph_recentered_priors_consumed')==9,
        'R105_RECEIPT'
    )

    for receipt,phase,engine,test,contract,report in (
        (
            va,'r104','r104_shared_graph.py',
            'test_r104.py','r104_graph_contract_v1.md',
            'r104_shared_synthetic_graph_v1.json'
        ),
        (
            vb,'r105','r105_prior_transfer.py',
            'test_r105.py','r105_transfer_contract_v1.md',
            'r105_aligned_prior_transfer_v1.json'
        ),
    ):
        need(
            receipt.get('engine_sha256')==
            PINS[f'evidence/{phase}/dev/{engine}']
            and receipt.get('tests_sha256')==
            PINS[f'evidence/{phase}/dev/{test}']
            and receipt.get('contract_sha256')==
            PINS[f'evidence/{phase}/dev/{contract}']
            and receipt.get('report_sha256')==
            PINS[f'evidence/{phase}/result/{report}'],
            'RECEIPT_LINEAGE:'+phase
        )

        need(
            receipt.get('parent_git_commit')==BASE
            and receipt.get('s6_source_sha256')==S6_SHA
            and receipt.get('scientific_gates_closed')==11
            and receipt.get('real_sensor_factors_authorized')
            is False
            and receipt.get('confirmation_test_accessed')
            is False,
            'RECEIPT_SCIENCE:'+phase
        )

    need(
        vb.get('r104_report_sha256')==
        PINS[
            'evidence/r104/result/r104_shared_synthetic_graph_v1.json'
        ],
        'R104_R105_REPORT_LINEAGE'
    )

    need(
        m.get('r104_test_count')==48
        and m.get('r105_test_count')==33
        and m.get('archived_regression_tests')==81
        and m.get('source_count')==10
        and m.get('s6_source_sha256')==S6_SHA
        and m.get('scientific_gates_closed')==11,
        'MANIFEST_COUNTS'
    )

    for key in (
        'real_sensor_factor_execution_authorized',
        'r95_backend_merged_into_s6',
        'physical_clock_or_extrinsics_verified',
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

    print('R106_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R106_SOURCE_AND_METADATA_SHA256=12_PASS')
    print('R106_R104_R105_RESULT_LINEAGE=PASS')
    print('R106_SAME_GRAPH_PRIOR_TRANSFERS=9_VERIFIED')
    print('R106_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3 and sys.argv[1]=='verify',
        'ARGUMENTS'
    )

    verify(pathlib.Path(sys.argv[2]))
