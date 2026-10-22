"""Independent SHA-pinned R98/R99 checkpoint verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R98_R99_NONLINEAR_PRIOR_CHECKPOINT_V1'
BASE='2520ae6611bc48ddf9bbcd8ce775e29bf7ddc7fb'
BRANCH='kios-isaacsim-v15-integration'

PINS={
 'evidence/r98/dev/r98_nonlinear_audit.py':
 '108ee66b3fcc47338e380b8014a86b075a8e90b3e11469a61356dbcd3fac7908',
 'evidence/r98/dev/test_r98.py':
 'eb290b785cefe4b5d730828cac621c77c9e9633b038a5f6f2c6df9b807fb2ef1',
 'evidence/r98/result/r98_nonlinear_joint_audit_v1.json':
 '3321b300f7f5bc9a27f9c2b81e1fdbe4a46504cc1c3c89a8f9a30d397ae88042',
 'evidence/r98/result/r98_independent_validation_v1.json':
 'd2a61a1408f85c0876d5bee2bd9c9ca7be49eafa09b67ece382739a2d1515b7d',
 'evidence/r99/dev/r99_prior_witness.py':
 'bfd88a57447930931275fd7b1c219effdb9fa97de7bc6697e654e1e0e5e870c8',
 'evidence/r99/dev/test_r99.py':
 '8b489f0dd63aff47881c6cb975e51d735e515b00eb51c8da58072366bcc9766e',
 'evidence/r99/result/r99_nonlinear_prior_lifecycle_v1.json':
 '00bd9f75e41b2c0e3d763c137170ebc6c696d9e79a0c7bdb1bdd703a95bd78b6',
 'evidence/r99/result/r99_independent_validation_v1.json':
 '8354386e472e50a75f8f6af500709263842724bd55c708ef5dff7dddbf54483a',
}

DOCS={
 'AGENTS.md',
 'docs/TRUST_ROBOT_PROJECT_STATE.md',
 'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R98_R99_NONLINEAR_PRIOR_CHECKPOINT_V1.md',
}

def need(ok,reason):
    if not ok:
        raise ValueError('R100_CHECKPOINT_DENIED:'+reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+'\n'
    ).encode()

def obj(root,name):
    return json.loads((root/name).read_bytes())

def check(root):
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
        and m.get('source_count')==8,
        'SOURCE_PINS'
    )

    meta=m.get('metadata_sha256')

    need(
        type(meta) is dict
        and set(meta)=={
            'README.md','verify_checkpoint.py'
        },
        'METADATA'
    )

    docs=m.get('documentation_sha256')

    need(
        type(docs) is dict and set(docs)==DOCS,
        'DOCUMENTATION'
    )

    expected=set(PINS)|set(meta)|{
        'checkpoint_manifest_v1.json'
    }

    directories=set()

    for name in expected:
        path=pathlib.PurePosixPath(name)

        need(
            not path.is_absolute()
            and '..' not in path.parts,
            'ARCHIVE_PATH'
        )

        for i in range(1,len(path.parts)):
            directories.add(
                '/'.join(path.parts[:i])
            )

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

    for name in expected:
        p=root/name
        s=p.lstat()

        need(
            stat.S_ISREG(s.st_mode)
            and s.st_nlink==1
            and 0<s.st_size<2000000,
            'ARCHIVE_REGULAR_FILE:'+name
        )

    # Construct forbidden paths without accidentally
    # matching this verifier's own source.
    forbidden=(
        b'/home/' + b'kios/',
        b'/mnt/' + b'hdd16T/',
        b'C:' + b'\\Users\\',
    )

    for name,pin in {**PINS,**meta}.items():
        raw=(root/name).read_bytes()

        need(
            type(pin) is str
            and len(pin)==64
            and sha(raw)==pin,
            'SHA:'+name
        )

        need(
            not any(x in raw for x in forbidden),
            'PRIVATE_PATH:'+name
        )

    a=obj(
        root,
        'evidence/r98/result/r98_nonlinear_joint_audit_v1.json'
    )
    b=obj(
        root,
        'evidence/r99/result/r99_nonlinear_prior_lifecycle_v1.json'
    )
    va=obj(
        root,
        'evidence/r98/result/r98_independent_validation_v1.json'
    )
    vb=obj(
        root,
        'evidence/r99/result/r99_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R98_SYNTHETIC_NONLINEAR_JOINT_AUDIT_V1',
        'R98_SCHEMA'
    )
    need(
        b.get('schema')==
        'TRUST_ROBOT_R99_SYNTHETIC_NONLINEAR_PRIOR_WITNESS_V1',
        'R99_SCHEMA'
    )

    need(
        a.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY'
        and b.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY',
        'SOFTWARE_STATUS'
    )

    need(
        a.get('nonlinear_solver_cases')==3
        and a.get('nonlinear_windows_audited')==12
        and a.get('schur_marginalizations_reported')==9
        and len(a.get('cases',{}))==3,
        'R98_COUNTS'
    )

    local=a.get('local_nonlinear_schur_audit',{})

    need(
        local.get('retained_nodes')==[1,2]
        and local.get('information_relative_error',1)>=0
        and local.get('information_relative_error',1)<1e-6
        and local.get('gradient_relative_error',1)>=0
        and local.get('gradient_relative_error',1)<1e-6
        and local.get('reduced_energy_difference_abs_error',1)<1e-5,
        'R98_LOCAL_SCHUR'
    )

    need(
        a.get('true_s6_nonlinear_se3_residuals_executed')
        is True,
        'R98_SE3_RESIDUAL'
    )

    need(
        b.get('nonlinear_solver_scenarios')==3
        and b.get('nonlinear_windows')==12
        and b.get('actual_marginalizations_independently_checked')==9
        and len(b.get('cases',{}))==3,
        'R99_COUNTS'
    )

    need(
        b.get('all_prior_inheritance_checks_passed')
        is True
        and b.get('all_schur_normal_equations_checked')
        is True
        and b.get('instrumentation_restored') is True,
        'R99_LIFECYCLE'
    )

    genesis=sha(
        b'R99_SYNTHETIC_LOCAL_WITNESS_GENESIS_V1'
    )

    for case in b['cases'].values():
        events=case.get('events')

        need(
            type(events) is list
            and len(events)==3
            and case.get('marginalization_events')==3
            and case.get('factor_reuse_count')==0
            and case.get(
                'instrumented_vs_uninstrumented_state_max_error',
                1
            )<1e-8,
            'R99_CASE'
        )

        prior_out=None
        previous=genesis
        used_imu=set()
        used_pose=set()

        for i,e in enumerate(events):
            need(type(e) is dict,'EVENT')

            payload=dict(e)
            claimed=payload.pop('event_digest',None)

            need(
                claimed==sha(canonical(payload)),
                'EVENT_HASH'
            )

            need(
                e.get('event_index')==i
                and e.get('eliminated_node')==i
                and e.get('input_nodes')==[i,i+1,i+2]
                and e.get('retained_nodes')==[i+1,i+2],
                'EVENT_ORDER'
            )

            need(
                e.get('previous_event_digest')==previous,
                'EVENT_CHAIN'
            )

            if prior_out is not None:
                need(
                    e.get('input_prior_digest')==prior_out,
                    'PRIOR_INHERITANCE'
                )

            imu={
                tuple(edge)
                for edge in e['consumed_imu_edges']
            }

            pose=set(e['consumed_pose_ids'])

            need(
                len(imu)==len(e['consumed_imu_edges'])
                and len(pose)==len(e['consumed_pose_ids'])
                and not (imu & used_imu)
                and not (pose & used_pose),
                'FACTOR_REUSE'
            )

            used_imu.update(imu)
            used_pose.update(pose)

            need(
                e['information_relative_error']<1e-6
                and e['gradient_relative_error']<1e-6
                and e['energy_difference_error']<1e-5,
                'EVENT_SCHUR'
            )

            need(
                e['synthetic_only'] is True
                and e['real_sensor_factor_executable'] is False
                and e['physical_clock_verified'] is False,
                'EVENT_PHYSICAL_BOUNDARY'
            )

            previous=claimed
            prior_out=e['output_prior_digest']

        need(
            used_imu=={(0,1),(1,2),(2,3)},
            'IMU_LIFECYCLE'
        )

    for report in (a,b):
        need(
            report.get('scientific_gates_closed')==11,
            'REPORT_GATES'
        )

        for name in (
            'health_training_authorized',
            'ate_rpe_authorized',
            'confirmation_test_accessed',
        ):
            need(
                report.get(name) is False,
                'REPORT_DENIAL:'+name
            )

    for name in (
        'r95_gaussian_prior_merged_into_s6',
        'independent_ground_truth_scoring',
        'physical_capture_time_verified',
        'physical_extrinsics_verified',
        'real_sensor_factors_authorized',
        'original_gt_or_rosbags_opened',
    ):
        need(a.get(name) is False,'R98_DENIAL:'+name)

    for name in (
        'r95_gaussian_backend_merged_into_s6',
        'event_digest_is_trusted_source_authentication',
        'recorded_source_factors_executed',
        'physical_clock_or_extrinsics_verified',
        'independent_ground_truth_scoring',
        'raw_gt_or_rosbags_opened',
    ):
        need(b.get(name) is False,'R99_DENIAL:'+name)

    need(
        va.get('schema')==
        'TRUST_ROBOT_R98_INDEPENDENT_NONLINEAR_AUDIT_V1'
        and va.get('status')=='PASS'
        and va.get('regression_tests')==22,
        'R98_VALIDATION'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R99_INDEPENDENT_VALIDATION_V1'
        and vb.get('status')=='PASS'
        and vb.get('regression_tests')==33,
        'R99_VALIDATION'
    )

    for receipt,phase,engine,test,report in (
        (
            va,'r98','r98_nonlinear_audit.py',
            'test_r98.py','r98_nonlinear_joint_audit_v1.json'
        ),
        (
            vb,'r99','r99_prior_witness.py',
            'test_r99.py','r99_nonlinear_prior_lifecycle_v1.json'
        ),
    ):
        need(
            receipt.get('engine_sha256')==
            PINS[f'evidence/{phase}/dev/{engine}']
            and receipt.get('tests_sha256')==
            PINS[f'evidence/{phase}/dev/{test}']
            and receipt.get('report_sha256')==
            PINS[f'evidence/{phase}/result/{report}'],
            'RECEIPT_HASH:'+phase
        )

        need(
            receipt.get('scientific_gates_closed')==11,
            'RECEIPT_GATES'
        )

    need(
        vb.get('r98_report_sha256')==
        PINS['evidence/r98/result/r98_nonlinear_joint_audit_v1.json'],
        'R98_R99_LINEAGE'
    )

    need(
        va.get('s6_source_sha256')==
        vb.get('s6_source_sha256')==
        m.get('s6_source_sha256'),
        'S6_LINEAGE'
    )

    need(
        m.get('source_count')==8
        and m.get('archived_regression_tests')==55
        and m.get('r98_test_count')==22
        and m.get('r99_test_count')==33
        and m.get('scientific_gates_closed')==11,
        'MANIFEST_GATES_AND_COUNTS'
    )

    for key in (
        'real_sensor_factor_execution_authorized',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_archived',
        'r95_backend_merged_into_s6',
        'qualified_author_response_ingested',
    ):
        need(
            m.get(key) is False,
            'MANIFEST_DENIAL:'+key
        )

    print('R100_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R100_EIGHT_SOURCE_SHA256=PASS')
    print('R100_R98_R99_RESULT_LINEAGE=PASS')
    print('R100_NINE_NONLINEAR_PRIOR_EVENTS=PASS')
    print('R100_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3 and sys.argv[1]=='verify',
        'ARGUMENTS'
    )
    check(pathlib.Path(sys.argv[2]))
