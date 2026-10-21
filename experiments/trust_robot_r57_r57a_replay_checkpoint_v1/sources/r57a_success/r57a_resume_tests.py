#!/usr/bin/env python3
"""R57 targeted repair: fix argv forwarding without modifying prior evidence."""

import ast
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

A, OLD_DEV, OLD_OUT, DEV, OUT = map(
    pathlib.Path, sys.argv[1:]
)

MAP = {
    'r51': (
        'trust_robot_r51_clock_evidence_dev_v1',
        'trust_robot_r51_clock_evidence_result_v1',
        'test_r51.py'
    ),
    'r52': (
        'trust_robot_r52_clock_sensitivity_dev_v1',
        'trust_robot_r52_clock_sensitivity_result_v1',
        'test_r52.py'
    ),
    'r53': (
        'trust_robot_r53_timing_receipt_boundary_dev_v1',
        'trust_robot_r53_timing_receipt_boundary_result_v1',
        'test_r53.py'
    ),
    'r54': (
        'trust_robot_r54_author_request_packet_dev_v1',
        'trust_robot_r54_author_request_packet_result_v1',
        'test_r54.py'
    ),
    'r55': (
        'trust_robot_r55_gt_source_acquisition_dev_v1',
        'trust_robot_r55_gt_source_acquisition_result_v1',
        'test_r55.py'
    ),
    'r55f': (
        'trust_robot_r55f_official_gt_manual_fallback_dev_v1',
        'trust_robot_r55f_official_gt_manual_fallback_result_v1',
        'test_r55f.py'
    )
}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024), b''
        ):
            h.update(chunk)
    return h.hexdigest()

def need(condition, message):
    if not condition:
        raise RuntimeError('R57A_DENIED:' + message)

manifest = json.loads(
    (A / 'manifest.json').read_text()
)

need(len(manifest['files']) == 39, 'ARCHIVE_INVENTORY')

need(
    manifest['ground_truth_status'] == 'NOT_ACQUIRED'
    and manifest['scientific_gates'] == 'ALL_11_CLOSED',
    'SCIENCE'
)

old_launcher = OLD_OUT / 'r57_offline_test_launcher.py'
old_failure = (
    OLD_OUT / 'test_logs/r51_synthetic_negative_replay.log'
)
old_replay = OLD_DEV / 'r57_replay.py'

pins = {
    str(path): digest(path)
    for path in (
        old_launcher,
        old_failure,
        old_replay
    )
}

original = old_launcher.read_text(encoding='utf-8')

needle = (
    'sys.path.insert(0,str(target.parent));'
    'sys.argv=[str(target)]'
)

replacement = (
    'sys.path.insert(0,str(target.parent));'
    'sys.argv=[str(target),str(target.parent),'
    'str(pathlib.Path(sys.argv[2]).resolve()),'
    'str(target.parent.parent)]'
)

need(
    original.count(needle) == 1,
    'EXACT_LAUNCHER_PATCH_SITE'
)

patched = original.replace(needle, replacement)

need(
    patched.replace(replacement, needle) == original,
    'ONLY_ARGUMENT_FORWARDING_CHANGED'
)

launcher = DEV / 'r57a_offline_test_launcher_fixed.py'
launcher.write_text(patched, encoding='utf-8')

ast.parse(patched, filename=str(launcher))

print(
    'R57A_LAUNCHER_ARGV_CONTRACT=REPAIRED_COPY_ONLY',
    flush=True
)

logs = OUT / 'test_logs'
logs.mkdir()

results = {}

with tempfile.TemporaryDirectory(
    prefix='r57a_test_copy_',
    dir=str(OUT)
) as tmp:

    root = pathlib.Path(tmp)

    for phase, (dev, res, test) in MAP.items():

        filename = 'evidence/' + dev + '/' + test

        need(
            filename in manifest['files'],
            'MISSING_TEST_' + phase
        )

        source = A / filename

        need(
            digest(source) ==
            manifest['files'][filename]['sha256'],
            'TEST_SHA_' + phase
        )

        destination = root / phase
        destination.mkdir()

        shutil.copytree(
            A / 'evidence' / dev,
            destination / dev
        )

        shutil.copytree(
            A / 'evidence' / res,
            destination / res
        )

        executable = destination / dev / test

        need(
            digest(executable) == digest(source),
            'COPIED_TEST_SHA_' + phase
        )

        env = dict(os.environ)

        env.update(
            PYTHONDONTWRITEBYTECODE='1',
            PYTHONNOUSERSITE='1',
            PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
            OPENBLAS_NUM_THREADS='1',
            OMP_NUM_THREADS='1',
            MKL_NUM_THREADS='1'
        )

        try:
            p = subprocess.run(
                [
                    sys.executable,
                    '-B',
                    str(launcher),
                    str(executable),
                    str(destination / res)
                ],
                cwd=str(destination),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=90,
                check=False
            )

            rc = p.returncode
            data = p.stdout

        except subprocess.TimeoutExpired as ex:
            rc = 124
            data = (
                (ex.stdout or b'')
                + b'\nR57A_TIMEOUT\n'
            )

        need(
            len(data) <= 1024 * 1024,
            'OUTPUT_CAP_' + phase
        )

        logfile = logs / (phase + '_replay.log')
        logfile.write_bytes(data)

        results[phase] = {
            'exit_code': rc,
            'log_sha256': digest(logfile),
            'original_test_sha256': digest(source),
            'log_bytes': len(data)
        }

        print(
            'R57A_' + phase.upper() + '_TEST_REPLAY='
            + ('PASS' if rc == 0 else 'FAILED')
            + ' EXIT=' + str(rc),
            flush=True
        )

        if rc != 0:
            print(
                'R57A_FAILURE_TAIL='
                + data[-2500:].decode(
                    'utf-8', 'replace'
                ),
                flush=True
            )
            break

# Confirm that original R57 failed evidence was not modified.
for path, value in pins.items():
    need(
        digest(pathlib.Path(path)) == value,
        'PRIOR_R57_CHANGED'
    )

for phase, detail in results.items():
    dev, res, test = MAP[phase]
    filename = 'evidence/' + dev + '/' + test

    need(
        digest(A / filename)
        == detail['original_test_sha256'],
        'ARCHIVE_TEST_CHANGED_' + phase
    )

status = (
    'PASS'
    if len(results) == 6
    and all(v['exit_code'] == 0 for v in results.values())
    else 'INCOMPLETE'
)

report = {
    'schema':
        'trust_robot_r57a_targeted_argument_forwarding_repair_v1',
    'status': status,
    'original_failure':
        'R57_R51_TEST_LAUNCH_MISSING_SYS_ARGV_1',
    'original_failure_preserved': True,
    'original_r57_evidence_sha256': pins,
    'patched_launcher_sha256': digest(launcher),
    'launcher_patch_scope':
        'COPY_ONLY_SYS_ARGV_FORWARDING',
    'prior_r57_39_byte_replays':
        'PASS_REPORTED_IN_ORIGINAL_TERMINAL',
    'prior_r57_2_tamper_rejections':
        'PASS_REPORTED_IN_ORIGINAL_TERMINAL',
    'tests_completed': results,
    'official_gt_status': 'NOT_ACQUIRED',
    'r43_eleven_gates': 'CLOSED',
    'real_pose_factors_health_ate_rpe': 'DENIED',
    'raw_bag_opened_by_repair': False,
    'confirmation_test_accessed_by_repair': False,
    'git_modified_by_repair': False
}

with (
    OUT / 'r57a_replay_report_v1.json'
).open('x', encoding='utf-8') as f:
    json.dump(report, f, indent=2, sort_keys=True)
    f.write('\n')

print(
    'R57A_REPAIR_REPLAY_STATUS=' + status,
    flush=True
)

print(
    'R57A_COMPLETED_TESTS=' + str(len(results)),
    flush=True
)

if status != 'PASS':
    print(
        'R57A_NEXT=TARGET_ONLY_FIRST_REMAINING_FAILED_TEST',
        flush=True
    )
else:
    print(
        'R57A_NEXT=R58_DOCUMENTATION_AND_GUARDED_GITHUB_PUBLICATION',
        flush=True
    )
