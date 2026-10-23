"""R115 standalone source-pinned checkpoint verification."""

import hashlib
import json
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R113_R114_ATTEMPT_BUDGET_CHECKPOINT_V1'
BASE='eed9d62ba424b0e136d8307b738059bab7c5e44a'
BRANCH='kios-isaacsim-v15-integration'
S6_SHA='a1c9d0b4b9219d1e1b370e5ab5f42fcb25ac53f1b77f005cb42b3497b90bfc9a'

PINS={
    'evidence/r113/dev/r113_bounded.py':
        '5f4e72d41c1c1616ef83a4c3fccaf0d6eb222e840b81f5358898cc869b3c2cb0',

    'evidence/r113/dev/test_r113.py':
        'f3f0bc79445c36e44dc3350fc98f890501d1c7e72e75d17e3be1fcac41d8c15a',

    'evidence/r113/dev/r113_resource_contract_v1.md':
        'b8c985e4bb3c809251323f4154ce0c8e7797cfeee3db416e88599746f9f1a994',

    'evidence/r113/result/r113_bounded_replay_v1.json':
        '07f5bfaa8a82a0ef3154fbd8a21aaaa2cd99c8a4041c090c0bfa62d611c88c07',

    'evidence/r113/result/r113_independent_validation_v1.json':
        '3e7eeee2a9df5383097aa606cf6fd758b46d51a9d323a3cffeae7d9e6d9eec09',

    'evidence/r114/dev/r114_attempts.py':
        '567a10ecb33cdc3c16ecf14755a68c6705208ad7d07ce8885dd70dc5d7db9fa1',

    'evidence/r114/dev/test_r114.py':
        '1c1d659761b140ddf695081bf57004ad160116aa5efd1571c2494b283f49e852',

    'evidence/r114/dev/r114_attempt_budget_contract_v1.md':
        '8e6067c5366e2fdb49217852462a2b31c0705a9d2db218eac91b12afc448e7f0',

    'evidence/r114/result/r114_attempt_budget_v1.json':
        '3b4543a00a10979758878b8867d94fc683dbee73547d6d20bcc92f37867cadd5',

    'evidence/r114/result/r114_independent_validation_v1.json':
        'c720ea5385fc60737f2185ba465ea4649244805dcb28ef242698b5e20e7af4bd',
}

DOCS={
    'AGENTS.md',
    'docs/TRUST_ROBOT_PROJECT_STATE.md',
    'docs/audits/trust_robot/TRUST_ROBOT_KIOS_R113_R114_ATTEMPT_BUDGET_CHECKPOINT_V1.md',
}

def need(ok,reason):
    if not ok:
        raise ValueError('R115_CHECKPOINT_DENIED:'+reason)

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

    docs=m.get('documentation_sha256')

    need(
        type(docs) is dict
        and set(docs)==DOCS,
        'DOCUMENTATION_PINS'
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
            and 0<s.st_size<2_000_000,
            'REGULAR_FILE:'+name
        )

    # Split signatures so the verifier itself does
    # not contain the assembled private-path string.
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
            not any(sig in raw for sig in forbidden),
            'PRIVATE_PATH:'+name
        )

    a=obj(
        root,
        'evidence/r113/result/r113_bounded_replay_v1.json'
    )

    b=obj(
        root,
        'evidence/r114/result/r114_attempt_budget_v1.json'
    )

    va=obj(
        root,
        'evidence/r113/result/r113_independent_validation_v1.json'
    )

    vb=obj(
        root,
        'evidence/r114/result/r114_independent_validation_v1.json'
    )

    need(
        a.get('schema')==
        'TRUST_ROBOT_R113_SYNTHETIC_BOUNDED_REPLAY_V1',
        'R113_SCHEMA'
    )

    need(
        b.get('schema')==
        'TRUST_ROBOT_R114_SYNTHETIC_ATTEMPT_BUDGET_V1',
        'R114_SCHEMA'
    )

    need(
        a.get('status')==
            'PASS_SYNTHETIC_RESOURCE_AND_CANCELLATION_ONLY'
        and b.get('status')==
            'PASS_SYNTHETIC_ATTEMPT_BUDGET_ONLY',
        'REPORT_STATUS'
    )

    need(
        a.get('healthy_sessions')==12
        and a.get('healthy_committed_operations')==60
        and a.get('healthy_total_replay_work_units')==168
        and a.get('maximum_work_units_per_session')==14
        and a.get('maximum_work_units_per_operation')==4,
        'R113_COUNTS'
    )

    need(
        type(a.get('healthy_cases')) is dict
        and len(a['healthy_cases'])==12,
        'R113_CASES'
    )

    for case in a['healthy_cases'].values():
        limit=(
            2e-5 if case.get('recentered') is True
            else 1e-8
        )

        need(
            case.get('acknowledged_operations')==5
            and case.get('replay_work_units')==14
            and case.get('operation_work_ledger')==
                [1,2,3,4,4]
            and case.get('max_operation_work_units')==4
            and case.get('nonlinear_windows')==4
            and case.get('marginalizations')==3
            and case.get('prior_transfers')==
                (3 if case.get('recentered') is True else 0)
            and case.get('factor_ownership_verified') is True
            and 0<=case.get('max_abs_error_vs_s6',1)<limit,
            'R113_CASE_CONTRACT'
        )

    witness=a.get('actual_replay_witness',{})

    need(
        witness.get('actual_candidate_submit_calls')==14
        and witness.get('recorded_work_units')==14
        and witness.get('accounting_exact') is True,
        'R113_REPLAY_WITNESS'
    )

    rejection=a.get('budget_rejections',{})

    need(
        rejection.get('budget_rejections')==3
        and rejection.get(
            'state_unchanged_for_all_rejections'
        ) is True,
        'R113_BUDGET_REJECTIONS'
    )

    owner=a.get('ownership_and_cancellation',{})

    need(
        owner.get(
            'rejected_unauthorized_or_terminal_operations'
        )==7
        and owner.get('cancelled_after_acknowledged_packets')==2
        and owner.get('committed_state_preserved') is True
        and owner.get('cancelled_session_reuse_denied') is True,
        'R113_OWNERSHIP_CANCEL'
    )

    cancellation=a.get('prepublication_cancellation',{})

    need(
        cancellation.get('candidate_published') is False
        and cancellation.get('committed_state_unchanged') is True
        and cancellation.get('acknowledgement_issued') is False
        and cancellation.get('session_terminal') is True,
        'R113_PREPUBLICATION_CANCEL'
    )

    need(
        a.get('injected_solver_failure',{}).get(
            'retry_after_fault_removed'
        ) is True
        and a.get('injected_solver_failure',{}).get(
            'successful_session_work_units'
        )==14,
        'R113_SOLVER_RETRY'
    )

    need(
        b.get('healthy_sessions')==12
        and b.get('healthy_committed_operations')==60
        and b.get('healthy_attempted_work_units')==168
        and b.get('healthy_committed_work_units')==168
        and b.get('injected_failure_stages')==6
        and b.get('failed_candidates_charged')==6
        and b.get('successful_retries')==6,
        'R114_COUNTS'
    )

    need(
        type(b.get('healthy_cases')) is dict
        and len(b['healthy_cases'])==12
        and type(b.get('fault_cases')) is dict
        and len(b['fault_cases'])==6,
        'R114_CASES'
    )

    for case in b['healthy_cases'].values():
        limit=(
            2e-5 if case.get('recentered') is True
            else 1e-8
        )

        need(
            case.get('attempted_work_units')==14
            and case.get('committed_work_units')==14
            and case.get('operation_ledger')==
                [1,2,3,4,4]
            and case.get('acknowledged_operations')==5
            and case.get('nonlinear_windows')==4
            and case.get('marginalizations')==3
            and case.get('prior_transfers')==
                (3 if case.get('recentered') is True else 0)
            and case.get('factor_history_validated') is True
            and 0<=case.get('max_abs_error_vs_s6',1)<limit,
            'R114_HEALTHY_CASE'
        )

    for case in b['fault_cases'].values():
        reserved=case.get('reserved_failed_units')
        observed=case.get(
            'observed_failed_candidate_submissions'
        )

        need(
            type(reserved) is int and 1<=reserved<=4
            and type(observed) is int
            and 0<observed<=reserved
            and case.get('failed_units_retained_after_retry')
                is True
            and case.get('committed_state_unchanged_on_failure')
                is True
            and case.get('failed_attempt_acknowledged') is False
            and case.get('successful_retry') is True
            and case.get('final_committed_work_units')==14
            and case.get('final_attempted_work_units')==
                14+reserved,
            'R114_FAILURE_CHARGE'
        )

    exhaustion=b.get('repeated_failure_exhaustion',{})

    need(
        exhaustion.get('failed_attempts')==3
        and exhaustion.get('failed_work_units_charged')==3
        and exhaustion.get('committed_work_units')==0
        and exhaustion.get(
            'fourth_attempt_rejected_before_execution'
        ) is True
        and exhaustion.get('cancelled_after_exhaustion') is True,
        'R114_EXHAUSTION'
    )

    cancellation=b.get('prepublication_cancellation',{})

    need(
        cancellation.get('work_reserved_before_cancellation')==1
        and cancellation.get('work_refunded') is False
        and cancellation.get('committed_work_units')==0
        and cancellation.get('committed_state_unchanged') is True
        and cancellation.get('candidate_published') is False
        and cancellation.get('session_terminal') is True,
        'R114_CANCELLATION'
    )

    admission=b.get('invalid_admissions',{})

    need(
        admission.get('invalid_operations_rejected')==4
        and admission.get(
            'work_charged_for_rejected_admission'
        )==0
        and admission.get('committed_state_unchanged') is True,
        'R114_ADMISSION'
    )

    witness=b.get('actual_dispatch_witness',{})

    need(
        witness.get('observed_candidate_submit_calls')==14
        and witness.get('reserved_attempt_units')==14
        and witness.get('committed_work_units')==14
        and witness.get('accounting_exact') is True,
        'R114_DISPATCH_WITNESS'
    )

    need(
        a.get('scientific_gates_closed')==11
        and b.get('scientific_gates_closed')==11,
        'SCIENTIFIC_GATES'
    )

    for key in (
        'wall_clock_latency_bound_verified',
        'physical_memory_bound_verified',
        'concurrent_cancellation_safety_verified',
        'durable_cancellation_verified',
        'cryptographic_owner_authentication_verified',
        'private_python_object_isolation_verified',
        'hardware_streaming_verified',
        'r95_backend_imported',
        'real_sensor_factors_authorized',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_opened',
    ):
        need(
            a.get(key) is False,
            'R113_SCIENCE_DENIAL:'+key
        )

    for key in (
        'wall_clock_latency_bound_verified',
        'physical_memory_bound_verified',
        'floating_point_work_bound_verified',
        'concurrent_atomicity_verified',
        'durable_attempt_ledger_verified',
        'cryptographic_owner_authentication_verified',
        'private_python_object_isolation_verified',
        'hardware_streaming_verified',
        'r95_backend_imported',
        'real_sensor_factors_authorized',
        'physical_clock_or_extrinsics_verified',
        'health_training_authorized',
        'ate_rpe_authorized',
        'confirmation_test_accessed',
        'raw_gt_or_rosbags_opened',
    ):
        need(
            b.get(key) is False,
            'R114_SCIENCE_DENIAL:'+key
        )

    need(
        va.get('schema')==
        'TRUST_ROBOT_R113_INDEPENDENT_RESOURCE_VALIDATION_V1'
        and va.get('status')=='PASS'
        and va.get('regression_tests')==47
        and va.get('healthy_sessions')==12
        and va.get('total_replay_work_units')==168
        and va.get('resource_budget_rejections')==3
        and va.get('prepublication_cancellation_verified')
            is True,
        'R113_RECEIPT'
    )

    need(
        vb.get('schema')==
        'TRUST_ROBOT_R114_INDEPENDENT_ATTEMPT_VALIDATION_V1'
        and vb.get('status')=='PASS'
        and vb.get('regression_tests')==54
        and vb.get('healthy_sessions')==12
        and vb.get('injected_failure_stages')==6
        and vb.get('charged_failed_attempts')==6
        and vb.get('repeated_failure_exhaustion_verified')
            is True
        and vb.get('cancellation_work_reservation_verified')
            is True,
        'R114_RECEIPT'
    )

    for receipt,phase,engine,tests,contract,report in (
        (
            va,'r113','r113_bounded.py',
            'test_r113.py',
            'r113_resource_contract_v1.md',
            'r113_bounded_replay_v1.json'
        ),
        (
            vb,'r114','r114_attempts.py',
            'test_r114.py',
            'r114_attempt_budget_contract_v1.md',
            'r114_attempt_budget_v1.json'
        ),
    ):
        prefix='evidence/'+phase+'/'

        need(
            receipt.get('engine_sha256')==
                PINS[prefix+'dev/'+engine]
            and receipt.get('tests_sha256')==
                PINS[prefix+'dev/'+tests]
            and receipt.get('contract_sha256')==
                PINS[prefix+'dev/'+contract]
            and receipt.get('report_sha256')==
                PINS[prefix+'result/'+report],
            'RECEIPT_SHA:'+phase
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
        vb.get('r113_report_sha256')==
        PINS[
            'evidence/r113/result/r113_bounded_replay_v1.json'
        ],
        'R113_R114_LINEAGE'
    )

    need(
        m.get('source_count')==10
        and m.get('r113_test_count')==47
        and m.get('r114_test_count')==54
        and m.get('archived_regression_tests')==101
        and m.get('s6_source_sha256')==S6_SHA
        and m.get('scientific_gates_closed')==11,
        'MANIFEST_COUNTS'
    )

    for key in (
        'real_sensor_factor_execution_authorized',
        'r95_backend_merged_into_s6',
        'hardware_streaming_verified',
        'wall_clock_resource_bound_verified',
        'physical_memory_bound_verified',
        'concurrent_atomic_publication_verified',
        'durable_crash_recovery_verified',
        'cryptographic_ownership_verified',
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

    print('R115_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R115_SOURCE_AND_METADATA_SHA256=12_PASS')
    print('R115_R113_R114_RESULT_LINEAGE=PASS')
    print('R115_REPLAY_AND_FAILURE_CHARGE_AUDIT=PASS')
    print('R115_SCIENTIFIC_GATES=11_CLOSED')

if __name__=='__main__':
    need(
        len(sys.argv)==3
        and sys.argv[1]=='verify',
        'ARGUMENTS'
    )

    verify(pathlib.Path(sys.argv[2]))
