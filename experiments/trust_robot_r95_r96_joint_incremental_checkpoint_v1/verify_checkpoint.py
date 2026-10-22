"""Independent immutable R95/R96 archive verifier."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R95_R96_JOINT_INCREMENTAL_CHECKPOINT_V1'
BASE='dc82664e3d356ea362097a3b54f10f93f962ca8d'
BRANCH='kios-isaacsim-v15-integration'

PINS={
 'evidence/r95/dev/r95_incremental.py':
  '6be155afb10f807b36ba2594cbe6bcd7a76d54a7fcc76040e59ae48c8d47c56b',
 'evidence/r95/dev/test_r95.py':
  '65278a43ba54efe26d0086837b3a0183aeeda260cb28a98a081b2fc338ae5939',
 'evidence/r95/result/r95_incremental_prior_lifecycle_v1.json':
  'f97df9058de6d26fd7eaf7e1f1efcbae34a13522388c8b63f03c34eaab2eedfb',
 'evidence/r95/result/r95_independent_validation_v1.json':
  'c2023b534537a4b711995057912a9574d967e33889c6e713431dab89163a4103',
 'evidence/r96/dev/r96_joint.py':
  '4cf9c78a58e392e5a417feb5f3fde1103a656d7c642b541d42a5b129da55844b',
 'evidence/r96/dev/test_r96.py':
  '2693af9416aea60973f817d504ca13db00956429564b5abd0c3e8b8bf2c43b9c',
 'evidence/r96/result/r96_joint_incremental_gaussian_v1.json':
  'b94fbf3e08265934df1d4cb26af21c3cb4f236852ca7a9f476c6eae1dd0733b3',
 'evidence/r96/result/r96_independent_validation_v1.json':
  'e4eaeb0951d92b5e42ecf76ba157ad0211cb0990afc1febcfac553ba1800e68a',
}

def need(ok,reason):
    if not ok:
        raise ValueError('R97_CHECKPOINT_DENIED:'+reason)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(root,name):
    return json.loads((root/name).read_bytes())

def check(root):
    need(root.is_dir() and not root.is_symlink(),'ROOT')

    manifest=load(root,'checkpoint_manifest_v1.json')

    need(manifest.get('schema')==SCHEMA,'SCHEMA')
    need(manifest.get('parent_commit')==BASE,'PARENT')
    need(manifest.get('branch')==BRANCH,'BRANCH')

    need(
        manifest.get('source_sha256')==PINS
        and manifest.get('source_count')==8,
        'EXACT_SOURCE_PINS'
    )

    meta=manifest.get('metadata_sha256')
    need(
        type(meta) is dict
        and set(meta)=={'README.md','verify_checkpoint.py'},
        'METADATA'
    )

    docs=manifest.get('documentation_sha256')
    need(type(docs) is dict and len(docs)==3,'DOCUMENTATION')

    expected=set(PINS)|set(meta)|{
        'checkpoint_manifest_v1.json'
    }

    dirs=set()
    for name in expected:
        path=pathlib.PurePosixPath(name)
        need(
            not path.is_absolute()
            and '..' not in path.parts,
            'PATH'
        )
        for k in range(1,len(path.parts)):
            dirs.add('/'.join(path.parts[:k]))

    observed={
        str(p.relative_to(root))
        for p in root.rglob('*')
    }

    need(observed==expected|dirs,'EXACT_ARCHIVE_TREE')

    for name in dirs:
        p=root/name
        need(p.is_dir() and not p.is_symlink(),'DIRECTORY')

    for name in expected:
        p=root/name
        st=p.lstat()

        need(
            stat.S_ISREG(st.st_mode)
            and st.st_nlink==1
            and 0<st.st_size<2_000_000,
            'REGULAR_FILE:'+name
        )

    for name,pin in {**PINS,**meta}.items():
        raw=(root/name).read_bytes()
        need(sha(root/name)==pin,'SHA:'+name)

        for private in (
            b'/home/' + b'kios/',
            b'/mnt/' + b'hdd16T/',
            b'C:' + b'\\Users\\',
        ):
            need(private not in raw,'PRIVATE_PATH:'+name)

    a=load(
        root,
        'evidence/r95/result/r95_incremental_prior_lifecycle_v1.json'
    )
    b=load(
        root,
        'evidence/r96/result/r96_joint_incremental_gaussian_v1.json'
    )
    va=load(
        root,
        'evidence/r95/result/r95_independent_validation_v1.json'
    )
    vb=load(
        root,
        'evidence/r96/result/r96_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R95_SYNTHETIC_INCREMENTAL_PRIOR_LIFECYCLE_V1',
        'R95_SCHEMA'
    )
    need(
        b.get('schema')==
        'TRUST_ROBOT_R96_SYNTHETIC_JOINT_INCREMENTAL_GAUSSIAN_V1',
        'R96_SCHEMA'
    )

    need(
        a.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY'
        and b.get('status')=='PASS_SYNTHETIC_SOFTWARE_ONLY',
        'SOFTWARE_STATUS'
    )

    need(
        a.get('incremental_prefix_windows')==16
        and a.get('marginalized_old_states')==11
        and a.get('detected_timestamp_gaps')==1
        and a.get('cross_gap_prior_carries')==0,
        'R95_ACCOUNTING'
    )

    need(
        b.get('total_prefix_evaluations')==28
        and b.get('total_eliminated_old_states')==20
        and len(b.get('cases',{}))==4
        and len(b.get('ablations',{}))==3
        and b.get('information_order_check') is True,
        'R96_ACCOUNTING'
    )

    for report in (a,b):
        need(report.get('scientific_gates_closed')==11,'GATES')
        for name in (
            'confirmation_test_accessed',
            'ate_rpe_authorized',
            'health_training_authorized',
        ):
            need(report.get(name) is False,'DENIAL:'+name)

    for name in (
        'real_sensor_factors_executed',
        'physical_capture_clock_verified',
        'physical_extrinsics_verified',
        'independent_ground_truth_used',
        'original_gt_or_rosbags_opened',
    ):
        need(a.get(name) is False,'R95_DENIAL:'+name)

    for name in (
        'real_sensor_factors_executed',
        's6_nonlinear_pose_factors_executed',
        'physical_clock_verified',
        'physical_extrinsics_verified',
        'physical_covariance_verified',
        'raw_gt_or_rosbags_opened',
    ):
        need(b.get(name) is False,'R96_DENIAL:'+name)

    need(
        va.get('schema')==
        'TRUST_ROBOT_R95_INDEPENDENT_INTEGRATION_VALIDATION_V1'
        and va.get('status')=='PASS'
        and va.get('test_count')==19,
        'R95_RECEIPT'
    )

    need(
        va.get('engine_sha256')==
            PINS['evidence/r95/dev/r95_incremental.py']
        and va.get('tests_sha256')==
            PINS['evidence/r95/dev/test_r95.py']
        and va.get('report_sha256')==
            PINS['evidence/r95/result/r95_incremental_prior_lifecycle_v1.json'],
        'R95_RECEIPT_HASHES'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R96_INDEPENDENT_VALIDATION_V1'
        and vb.get('status')=='PASS',
        'R96_RECEIPT'
    )

    need(
        vb.get('r95_report_sha256')==
            PINS['evidence/r95/result/r95_incremental_prior_lifecycle_v1.json']
        and vb.get('r96_engine_sha256')==
            PINS['evidence/r96/dev/r96_joint.py']
        and vb.get('r96_tests_sha256')==
            PINS['evidence/r96/dev/test_r96.py']
        and vb.get('r96_report_sha256')==
            PINS['evidence/r96/result/r96_joint_incremental_gaussian_v1.json'],
        'R96_RECEIPT_HASHES'
    )

    need(
        va.get('scientific_gates_closed')==11
        and vb.get('scientific_gates_closed')==11,
        'RECEIPT_GATES'
    )

    need(
        manifest.get('archived_regression_tests')==52
        and manifest.get('r95_test_count')==19
        and manifest.get('r96_test_count')==33
        and manifest.get('scientific_gates_closed')==11,
        'MANIFEST_COUNTS'
    )

    for key in (
        'real_sensor_factor_execution_authorized',
        'health_training_authorized',
        'ate_rpe_authorized',
        'physical_clock_or_extrinsics_verified',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_archived',
    ):
        need(manifest.get(key) is False,'MANIFEST_DENIAL:'+key)

    print('R97_STANDALONE_ARCHIVE_VERIFIER=PASS')
    print('R97_EXACT_8_ARTIFACT_SHA256=PASS')
    print('R97_R95_R96_LINEAGE=PASS')
    print('R97_ALL_11_SCIENTIFIC_GATES=CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3 and sys.argv[1]=='verify',
        'ARGUMENTS'
    )
    check(pathlib.Path(sys.argv[2]))
