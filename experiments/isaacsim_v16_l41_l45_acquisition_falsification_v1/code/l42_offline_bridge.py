"""L42: offline L37 hook-to-L40 SQLite outbox compatibility bridge.

Not a simulator acquisition or an authorized live-hook integration.
No measurement source is captured or independently attested.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

BASE = '8d5a1701df3e9d755ac0a4b5adda2845873f52eb'
PINS = {
    'candidate': '4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec',
    'guard': 'b6bcabaf081bb1d6bf31b0ff907369bef841cf012d33b4ec407efd9bd6d94965',
    'protocol': '1df54c21a92bbf48387b48e1b78a0b71ea0298767005df7e3f7548f307a99736',
    'contract': 'ee8dfaa3a0f95813d29efa68f65a3222a39cce5e12cf855c4c3508791dcc05f9',
    'fixture': 'b2fa0728d1aa867d162bae7e463f7bf353b058222d2700eaf392cd271ed97736',
    'l41report': '67e0be9b1da5944cf41a3bfeccdfdd5110e5e672de6c4fc7370bf3fa1914e798',
    'l41validation': 'e1507fa4233bc918246a518c4a3b56c474149f843030cd238d7887fcc91a3a84',
}
MODALITIES = ('camera', 'lidar', 'imu')


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump(path, obj):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def run_protocol(args, action, db, folder, expect_ok=True):
    command = [
        sys.executable, '-B', args.protocol, action,
        '--db', str(db), '--receipts', str(folder),
        '--candidate', args.candidate,
        '--contract', args.contract,
        '--fixture', args.fixture,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=25)
    if expect_ok:
        need(result.returncode == 0, f'{action} failure: {result.stdout} {result.stderr}')
    else:
        need(result.returncode == 3, f'{action} replay unexpectedly succeeded/failed differently')
        need('NONCE_OR_SESSION_ALREADY_CONSUMED' in result.stdout,
             f'Unexpected {action} denial: {result.stdout}')
    return result.stdout.strip()


def test_runtime_guard(path, candidate_root):
    spec = importlib.util.spec_from_file_location('l42_test_l37_guard', path)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    root = Path(candidate_root)
    try:
        guard.preflight_gate(root, root/'multimodal_scene_v5.usda',
                             root/'multimodal_probe_validation_v15.json',
                             root/'multimodal_probe_results_v15')
    except PermissionError as exc:
        need(str(exc) == 'L37_LIVE_SIMULATOR_LAUNCH_NOT_AUTHORIZED',
             'Preflight denied for unexpected reason')
    else:
        raise ValueError('Preflight mistakenly allowed live launch')
    try:
        guard.seal_after_capture(root, root/'multimodal_probe_results_v15'/'l29_runtime_envelope_v1')
    except PermissionError as exc:
        need(str(exc) == 'L37_LIVE_CAPTURE_SEAL_NOT_QUALIFIED',
             'Sealing denied for unexpected reason')
    else:
        raise ValueError('Sealing mistakenly allowed live capture')


def main(a):
    for name, expected in PINS.items():
        p = Path(getattr(a, name))
        need(p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1,
             'Missing or unsafe pinned input '+name)
        need(sha(p) == expected, 'Pinned input hash mismatch '+name)
    source = Path(a.candidate).read_text(encoding='utf-8')
    guard_source = Path(a.guard).read_text(encoding='utf-8')
    ast.parse(source)
    ast.parse(guard_source)
    need(source.index('from l37_runtime_guard import preflight_gate') <
         source.index('from isaacsim import SimulationApp'),
         'L37 gate misplaced')
    need(source.index('from l37_runtime_guard import seal_after_capture') >
         source.index('    _l29_export('), 'L37 seal misplaced')
    need(source.index('from l37_runtime_guard import seal_after_capture') <
         source.index('print("MULTIMODAL_RUNTIME=PASS", flush=True)'),
         'L37 success marker misplaced')
    l41 = load(a.l41report)
    need(l41['readiness_verdict'] == 'LIVE_CAPTURE_DENIED_SCIENCE_GATES_CLOSED',
         'L41 readiness gate')
    test_runtime_guard(a.guard, Path(a.candidate).parent)

    folder = Path(a.session)
    need(not folder.exists(), 'Session output collision')
    folder.mkdir(mode=0o700)
    receipts = folder/'receipts'
    receipts.mkdir(mode=0o700)
    db = folder/'registry.sqlite'

    trace = []
    for action in ('issue','publish','admit','publish'):
        trace.append({'action': action, 'response': run_protocol(a,action,db,receipts)})
    trace.append({'action':'replay_admit', 'response': run_protocol(a,'admit',db,receipts,False)})
    for action in ('seal','publish'):
        trace.append({'action': action, 'response': run_protocol(a,action,db,receipts)})
    trace.append({'action':'replay_seal','response':run_protocol(a,'seal',db,receipts,False)})
    trace.append({'action':'status','response':run_protocol(a,'status',db,receipts)})
    need(trace[-1]['response'] == 'L40_FINAL_STATE=SEALED', 'Final outbox state')

    connection = sqlite3.connect('file:'+str(db.resolve())+'?mode=ro',uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        need(connection.execute('PRAGMA quick_check').fetchone()[0]=='ok','SQLite integrity')
        session_rows = connection.execute('SELECT session_id,nonce_hash,state FROM sessions').fetchall()
        outbox = connection.execute('SELECT stage,payload,digest,published FROM outbox ORDER BY stage').fetchall()
    finally:
        connection.close()
    need(len(session_rows)==1 and session_rows[0][2]=='SEALED','Session state')
    need(len(outbox)==3,'Outbox count')
    names = ('challenge_v1.json','admission_v1.json','seal_v1.json')
    digests = {}
    for index, row in enumerate(outbox):
        stage, body, digest, published = row
        need(stage==index and published==1,'Outbox stage')
        need(hashlib.sha256(body).hexdigest()==digest,'Outbox digest')
        need((receipts/names[index]).read_bytes()==body,'Outbox published bytes mismatch')
        digests[names[index]]=digest

    plan = {
        'schema': 'TRUST_ROBOT_L42_HOOK_OUTBOX_BINDING_CONTRACT_V1',
        'parent_commit': BASE,
        'source_sha256': dict(PINS),
        'hook_binding_mode':'STATIC_HOOK_COMPATIBILITY_PLUS_SEPARATE_OFFLINE_OUTBOX_SESSION',
        'preflight_hook':'BEFORE_SIMULATIONAPP_IMPORT_FAIL_CLOSED',
        'postexport_hook':'AFTER_L29_EXPORT_FAIL_CLOSED',
        'L40_outbox_bound_candidate_sha256': PINS['candidate'],
        'L40_outbox_fixture_sha256': PINS['fixture'],
        'session_binding_fields': [
            'session_id','nonce_hash','challenge_receipt_sha256',
            'admission_receipt_sha256','seal_receipt_sha256',
            'candidate_source_sha256','scene_source_sha256',
            'run_identity','modality_id','payload_sha256',
            'capture_counter','measurement_clock_domain',
            'capture_time_semantics','independent_witness_signature',
        ],
        'future_modalities': [
            {'modality':m,'capture_count':0,'payload_hashes':[],
             'capture_identity_verified':False,'clock_semantics_verified':False}
            for m in MODALITIES
        ],
        'actual_scene_source_verified':False,
        'new_runtime_metadata_rebound':False,
        'acquisition_time_receipt_binding_implemented':False,
        'independent_hardware_witness_implemented':False,
        'live_simulator_launch_authorized':False,
        'pose_factors_authorized':0,
        'health_labels_generated':0,
        'next_phase':'L43_ADVERSARIAL_CAPTURE_SESSION_BINDING',
    }
    dump(a.plan,plan)
    report = {
        'schema':'TRUST_ROBOT_L42_OFFLINE_HOOK_OUTBOX_COMPATIBILITY_V1',
        'parent_commit':BASE,
        'builder_source_sha256':sha(__file__),
        'binding_contract_sha256':sha(a.plan),
        'source_sha256':dict(PINS),
        'session_id':session_rows[0][0],
        'nonce_sha256':session_rows[0][1],
        'registry_sha256':sha(db),
        'outbox_receipts_sha256':digests,
        'outbox_records':3,
        'registry_state':'SEALED',
        'subprocess_trace':trace,
        'pre_simulator_guard_denied':True,
        'postexport_guard_denied':True,
        'replay_admit_denied':True,
        'replay_seal_denied':True,
        'offline_fixture_only':True,
        'source_clock_verified':False,
        'live_simulator_launch_authorized':False,
        'simulator_executed':False,
        'actual_per_modality_payloads':0,
        'new_sensor_measurements':0,
        'physical_sync_verified':False,
        'independent_source_authenticity_verified':False,
        'hardware_attestation_verified':False,
        'independent_6dof_reference_verified':False,
        'real_power_loss_durability_verified':False,
        'pose_factors_authorized':0,
        'health_labels_generated':0,
        'git_commit_or_push_performed':False,
    }
    dump(a.report,report)
    print('L42_L37_RUNTIME_HOOKS=DENIED_AS_DESIGNED')
    print('L42_L40_SEPARATE_PROCESS_OUTBOX=PASS')
    print('L42_REPLAY_ADMIT_AND_SEAL=REJECTED')
    print('L42_OUTBOX_PUBLISHED_RECEIPTS=3')
    print('L42_NEW_SENSOR_MEASUREMENTS=0')
    print('L42_OFFLINE_HOOK_TO_OUTBOX_COMPATIBILITY=PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for field in (*PINS,'session','plan','report'):
        parser.add_argument('--'+field,required=True)
    main(parser.parse_args())
