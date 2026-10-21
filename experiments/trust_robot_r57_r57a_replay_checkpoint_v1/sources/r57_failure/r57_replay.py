#!/usr/bin/env python3
"""R57 independent archive verification and isolated test replays."""

import ast
import hashlib
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile

A, E, OUT = map(pathlib.Path, sys.argv[1:4])

MAP = {
    "r51": (
        "trust_robot_r51_clock_evidence_dev_v1",
        "trust_robot_r51_clock_evidence_result_v1",
        "test_r51.py",
        "852613e76d272ae1fb312e9dee27ee08bf7cf41e81889aed7495763d3b565602"
    ),
    "r52": (
        "trust_robot_r52_clock_sensitivity_dev_v1",
        "trust_robot_r52_clock_sensitivity_result_v1",
        "test_r52.py",
        "093b1722e23d8e9db92c2ae6dfb173978fbb56041144d64d53388183dcea5210"
    ),
    "r53": (
        "trust_robot_r53_timing_receipt_boundary_dev_v1",
        "trust_robot_r53_timing_receipt_boundary_result_v1",
        "test_r53.py",
        "9e2a8b5cf30bad5d67a1776c7bfabafb6f3b7dd1b79a93429e8f34aca8096309"
    ),
    "r54": (
        "trust_robot_r54_author_request_packet_dev_v1",
        "trust_robot_r54_author_request_packet_result_v1",
        "test_r54.py",
        "ac924e0ff77fbe161bc299255802d47fc602da78e9d83bbe0da89d8dd24801d0"
    ),
    "r55": (
        "trust_robot_r55_gt_source_acquisition_dev_v1",
        "trust_robot_r55_gt_source_acquisition_result_v1",
        "test_r55.py",
        "899ed3a8582d6fed4d8d211b99729dc2d0a4b7db75cb5a0855b9600192efb65e"
    ),
    "r55f": (
        "trust_robot_r55f_official_gt_manual_fallback_dev_v1",
        "trust_robot_r55f_official_gt_manual_fallback_result_v1",
        "test_r55f.py",
        "22a0ed923ab1057c1bbee38314f4886918dd543e3f43d0bfd0c2c7e27b36bdd8"
    )
}

def need(condition, reason):
    if not condition:
        raise RuntimeError('R57_DENIED:' + reason)

def sha(path):
    h = hashlib.sha256()

    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)

    return h.hexdigest()

def invoke(cmd, cwd, timeout=90, env=None):
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False
    )
    return result.returncode, result.stdout

manifest = json.loads(
    (A / 'manifest.json').read_text(encoding='utf-8')
)
files = manifest['files']

need(len(files) == 39, 'COUNT')

need(
    manifest['phase_file_counts'] == {
        'r51': 6,
        'r52': 6,
        'r53': 7,
        'r54': 7,
        'r55': 7,
        'r55f': 6
    },
    'PHASE_COUNTS'
)

need(
    manifest['ground_truth_status'] == 'NOT_ACQUIRED'
    and manifest['scientific_gates'] == 'ALL_11_CLOSED',
    'SCIENCE'
)

need(
    manifest['confirmation_test_accessed'] is False
    and manifest['raw_bag_opened'] is False,
    'SCOPE'
)

need(
    set(manifest['independent_report_sha256']) == set(MAP),
    'PHASE_SET'
)

checks = 0

for relative, meta in sorted(files.items()):
    archived = A / relative
    original = pathlib.Path(meta['source'])

    st = archived.lstat()
    src = original.lstat()

    need(
        stat.S_ISREG(st.st_mode) and st.st_nlink == 1,
        'ARCHIVE_REGULAR:' + relative
    )

    need(
        stat.S_ISREG(src.st_mode) and src.st_nlink == 1,
        'SOURCE_REGULAR:' + relative
    )

    need(
        st.st_size == src.st_size == meta['bytes'],
        'BYTE_SIZE:' + relative
    )

    need(
        sha(archived) == sha(original) == meta['sha256'],
        'BYTE_IDENTITY:' + relative
    )

    if archived.suffix == '.json':
        json.loads(archived.read_text(encoding='utf-8'))

    if archived.suffix == '.py':
        ast.parse(archived.read_bytes(), filename=relative)

    checks += 1

for phase, (dev, res, test, expected) in MAP.items():
    need(
        manifest['independent_report_sha256'][phase] == expected,
        'EXPECTED_REPORT_SHA:' + phase
    )

    matches = [
        k for k in files
        if k.endswith('/' + phase + '_independent_validation_v1.json')
    ]

    need(
        len(matches) == 1
        and files[matches[0]]['sha256'] == expected,
        'REPORT_SHA:' + phase
    )

    obj = json.loads(
        (A / matches[0]).read_text(encoding='utf-8')
    )

    need(isinstance(obj, dict), 'REPORT_OBJECT:' + phase)

    test_names = [
        pathlib.PurePosixPath(f).name
        for f in files
        if '/' + dev + '/' in f
    ]

    need(test in test_names, 'TEST_MISSING:' + phase)

print(
    'R57_INDEPENDENT_ORIGINAL_BYTE_REPLAY='
    + str(checks) + '_PASS',
    flush=True
)

code, output = invoke(
    [sys.executable, '-B', str(A / 'verify_checkpoint.py')],
    A,
    45
)

need(
    code == 0
    and b'R56_STANDALONE_MANIFEST_VERIFIER=PASS' in output,
    'BASELINE_STANDALONE'
)

print('R57_STANDALONE_BASELINE=PASS', flush=True)

# Test the verifier using only disposable copies.
with tempfile.TemporaryDirectory(
    prefix='r57_tamper_', dir=str(OUT)
) as tmp:

    copied = pathlib.Path(tmp) / 'copy'
    shutil.copytree(A, copied)

    sample = copied / next(iter(sorted(files)))

    with sample.open('ab') as f:
        f.write(b'\nR57_NEGATIVE_TAMPER\n')

    code, data = invoke(
        [sys.executable, '-B',
         str(copied / 'verify_checkpoint.py')],
        copied,
        45
    )

    need(code != 0, 'ALTERED_ARTIFACT_ACCEPTED')

    # Repair only the disposable copy.
    shutil.copy2(
        A / sample.relative_to(copied),
        sample
    )

    test_manifest = copied / 'manifest.json'
    altered = json.loads(test_manifest.read_text())
    altered['scientific_gates'] = 'ALL_11_OPEN'

    test_manifest.write_text(
        json.dumps(altered, sort_keys=True, indent=2) + '\n'
    )

    code, data = invoke(
        [sys.executable, '-B',
         str(copied / 'verify_checkpoint.py')],
        copied,
        45
    )

    need(code != 0, 'OPEN_GATES_ACCEPTED')

print(
    'R57_TAMPERED_BYTES_AND_OPEN_GATES=2_REJECTED',
    flush=True
)

# Test scripts run on disposable copies, not the archived sources.
# The launcher blocks Python socket connections and direct opening of
# the original raw-recording and confirmation-test paths.
runner = OUT / 'r57_offline_test_launcher.py'

runner.write_text(
    "import builtins,io,os,pathlib,runpy,socket,sys\n"
    "target=pathlib.Path(sys.argv[1]).resolve()\n"
    "def gate(p):\n"
    " try: s=os.fsdecode(os.fspath(p)).lower()\n"
    " except TypeError: return\n"
    " if \"/recorded_m2dgr_train/\" in s or \"/confirmation_test/\" in s: raise RuntimeError(\"R57_REPLAY_FORBIDDEN_SOURCE\")\n"
    "o=builtins.open; i=io.open; oo=os.open\n"
    "def safe_open(p,*a,**kw): gate(p); return o(p,*a,**kw)\n"
    "def safe_io(p,*a,**kw): gate(p); return i(p,*a,**kw)\n"
    "def safe_os(p,*a,**kw): gate(p); return oo(p,*a,**kw)\n"
    "builtins.open=safe_open;io.open=safe_io;os.open=safe_os\n"
    "class DeniedSocket(socket.socket):\n"
    " def connect(self,*a,**kw): raise RuntimeError(\"R57_REPLAY_NETWORK_DENIED\")\n"
    " def connect_ex(self,*a,**kw): raise RuntimeError(\"R57_REPLAY_NETWORK_DENIED\")\n"
    " def sendto(self,*a,**kw): raise RuntimeError(\"R57_REPLAY_NETWORK_DENIED\")\n"
    "socket.socket=DeniedSocket\n"
    "def no_network(*a,**kw): raise RuntimeError(\"R57_REPLAY_NETWORK_DENIED\")\n"
    "socket.create_connection=no_network;socket.getaddrinfo=no_network\n"
    "sys.path.insert(0,str(target.parent));sys.argv=[str(target)]\n"
    "runpy.run_path(str(target),run_name=\"__main__\")\n",
    encoding='utf-8'
)

ast.parse(runner.read_text())

logs = OUT / 'test_logs'
logs.mkdir(exist_ok=False)

replay = {}

with tempfile.TemporaryDirectory(
    prefix='r57_tests_', dir=str(OUT)
) as tmp:

    temp = pathlib.Path(tmp)

    for phase, (dev, res, test, expected) in MAP.items():
        dst = temp / phase
        dst.mkdir()

        shutil.copytree(
            A / 'evidence' / dev,
            dst / dev
        )
        shutil.copytree(
            A / 'evidence' / res,
            dst / res
        )

        cmd = [
            sys.executable,
            '-B',
            str(runner),
            str(dst / dev / test)
        ]

        env = dict(os.environ)
        env.update({
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
            'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'
        })

        try:
            rc, data = invoke(cmd, dst, 90, env)
        except subprocess.TimeoutExpired as exc:
            data = (exc.stdout or b'') + b'\nTIMEOUT\n'
            rc = 124

        need(
            len(data) < 1024 * 1024,
            'TEST_LOG_TOO_LARGE:' + phase
        )

        log = logs / (
            phase + '_synthetic_negative_replay.log'
        )
        log.write_bytes(data)

        replay[phase] = {
            'returncode': rc,
            'stdout_sha256': sha(log),
            'stdout_bytes': len(data),
            'test_original_sha256':
                files['evidence/' + dev + '/' + test]['sha256']
        }

        print(
            'R57_' + phase.upper() + '_TEST_REPLAY='
            + ('PASS' if rc == 0 else 'FAILED')
            + ' EXIT=' + str(rc),
            flush=True
        )

        if rc != 0:
            print(
                'R57_' + phase.upper() + '_FAILURE_TAIL='
                + data[-2500:].decode('utf-8', 'replace'),
                flush=True
            )
            raise RuntimeError(
                'R57_PHASE_TEST_FAILED:' + phase
            )

# Confirm the protected source archive was not changed.
for relative, meta in files.items():
    need(
        sha(A / relative) == meta['sha256'],
        'POST_REPLAY_ARCHIVE_CHANGED:' + relative
    )

report = {
    'schema': 'TRUST_ROBOT_R57_INDEPENDENT_ARCHIVE_REPLAY_V1',
    'baseline_commit': manifest['base_commit'],
    'archived_source_byte_identities_replayed': checks,
    'independent_report_hashes_verified': 6,
    'standalone_manifest_verification': 'PASS',
    'tamper_negative_controls_rejected': 2,
    'phase_test_replays': replay,
    'official_room_02_gt_acquired': False,
    'physical_reference_clock_frame_qualified': False,
    'r43_scientific_gates_opened': 0,
    'real_sensor_factors_admitted': 0,
    'health_labels_generated': 0,
    'ate_rpe_scores_generated': 0,
    'raw_bag_read': False,
    'confirmation_test_read': False,
    'git_commit_performed': False
}

with (
    OUT / 'r57_independent_archive_replay_v1.json'
).open('x', encoding='utf-8') as f:
    json.dump(report, f, indent=2, sort_keys=True)
    f.write('\n')

print('R57_FULL_TEST_REPLAYS=6_PASS', flush=True)
print('R57_INDEPENDENT_CHECKPOINT_REVIEW=PASS', flush=True)
