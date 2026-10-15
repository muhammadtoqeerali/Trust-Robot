#!/usr/bin/env bash
set -euo pipefail
umask 077
ulimit -c 0

W=/home/kios/TRUST_ROBOT_ALI
R=$W/github_checkout_v15
PY=$W/venvs/isaac_v15_odometry_v1/bin/python
BASE=00d04bf69610c36f3bd2bbfb11633a993b9a624f
BRANCH=kios-isaacsim-v15-integration
RUN=$W/experiments/isaacsim_v16_readiness_capture_v1
PKG=$R/experiments/isaacsim_v16_recovery_v1
DOC=$R/docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_RECOVERY_FREEZE_V1.md
OUT=$W/experiments/isaacsim_v16_github_checkpoint_result_v1
REMOTE_REPO=muhammadtoqeerali/Trust-Robot

echo '=== 1. STRICT WORKSTATION AND REMOTE PREFLIGHT ==='
[[ "$(id -un)" == kios ]]
[[ "$(readlink -f "$W")" == "$W" ]]
[[ -d "$R/.git" && ! -L "$R" && -x "$PY" ]]
[[ -d "$RUN" && ! -L "$RUN" ]]
[[ -d "$W/experiments" && ! -L "$W/experiments" ]]
[[ "$(git -C "$R" rev-parse HEAD)" == "$BASE" ]]
[[ "$(git -C "$R" branch --show-current)" == "$BRANCH" ]]
[[ -z "$(git -C "$R" status --porcelain)" ]]
[[ ! -e "$PKG" && ! -L "$PKG" ]]
[[ ! -e "$DOC" && ! -L "$DOC" ]]
[[ ! -e "$OUT" && ! -L "$OUT" ]]
[[ -f "$R/AGENTS.md" && ! -L "$R/AGENTS.md" ]]
[[ -n "$(git -C "$R" config user.name)" ]]
[[ -n "$(git -C "$R" config user.email)" ]]
URL="$(git -C "$R" remote get-url origin)"
if [[ ! "$URL" =~ ^(git@github\.com:|https://github\.com/|ssh://git@github\.com/)muhammadtoqeerali/Trust-Robot(\.git)?$ ]]; then
  printf 'UNEXPECTED_GIT_REMOTE=%s\n' "$URL" >&2
  exit 1
fi
REMOTE_HEAD="$(git -C "$R" ls-remote --exit-code origin "refs/heads/$BRANCH" | awk '{print $1}')"
[[ "$REMOTE_HEAD" == "$BASE" ]] || {
  echo "REMOTE_BRANCH_CHANGED_OR_NOT_AT_EXPECTED_BASE=$REMOTE_HEAD" >&2
  exit 1
}
[[ -f "$RUN/multimodal_probe_candidate_v15.py" && ! -L "$RUN/multimodal_probe_candidate_v15.py" ]]
[[ -f "$RUN/multimodal_scene_v5.usda" && ! -L "$RUN/multimodal_scene_v5.usda" ]]
[[ "$(sha256sum "$RUN/multimodal_probe_candidate_v15.py" | awk '{print $1}')" == 1a4416f4ceeda3a41076c31baea1458ae59e73f715517846abd725b216c491cd ]]
[[ "$(sha256sum "$RUN/multimodal_scene_v5.usda" | awk '{print $1}')" == 950a84720a4304fd293cd5d5e8297d56b19dae178d127cf9db390d2da5e7a7ea ]]
mkdir -m 700 "$OUT"
for d in home tmp cache; do mkdir -m 700 "$OUT/$d"; done
export TMPDIR="$OUT/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
# Keep the workstation HOME, SSH credentials and Git configuration intact for push.
echo 'LOCAL_CHECKPOINT=VERIFIED'
echo 'REMOTE_CHECKPOINT=VERIFIED'
echo 'NO_SIMULATOR_OR_GPU_REQUIRED=YES'

echo
echo '=== 2. BUILD VERSIONED REPRODUCIBILITY CHECKPOINT ==='
"$PY" -B - "$R" "$RUN" "$W" "$PKG" "$DOC" <<'PY'
import ast
import hashlib
import json
import shutil
import sys
from pathlib import Path

repo, run, workspace, pkg, doc = map(Path, sys.argv[1:])
assert repo.resolve() == repo and workspace.resolve() == workspace
assert pkg.parent == repo / 'experiments'
assert doc.parent == repo / 'docs/audits/trust_robot'

sources = {
    'V16_19_GMO_SWEEP': ('isaacsim_v16_gmo_sweep_result_v1/gmo_sweep_report_v1.json', '4b24628d5191ba932e4ff0c8989f2d9c28a918c964207ca1b533481f1cb2337c'),
    'V16_20_PRE_POST': ('isaacsim_v16_prepost_lidar_result_v1/prepost_lidar_report_v1.json', '0d28bee52c55e46237f1d037b261b7b5f0705b36e96ae156e41fee60884b3947'),
    'V16_21_RAW_PRESNAPSHOT': ('isaacsim_v16_gmo_presnapshot_result_v1/gmo_presnapshot_report_v1.json', 'e4c748ddefe11d3cd236f6688a63c62593cb197477674e5736251d14ad68dda7'),
    'V16_22_SELF_HIT': ('isaacsim_v16_self_hit_geometry_audit_v1/self_hit_geometry_audit_v1.json', '394380af5cc4f1909c9e11895e679e93584341692f97f5e2680d1b60deb680c9'),
    'V16_23_MOUNT': ('isaacsim_v16_mount_recovery_result_v1/mount_recovery_report_v1.json', '5498b108af625588ea89b86b7829af859b6d22f9ed67549c5493b1e7cfda011e'),
    'V16_24_GMO_XYZ': ('isaacsim_v16_xyz_warmstart_result_v1/xyz_warmstart_report_v1.json', '72eceb98917a7e42f22d22f4877d5a479687b2191d8cdbd851d0ecb9e506282c'),
    'V16_25_EARLY_PRIMING': ('isaacsim_v16_early_replicator_result_v1/early_replicator_report_v1.json', '665209d90f04f28accfc43bd4afe3f3c8972685fd344388ee8540cc3ad474e6b'),
    'V16_26B_FAILURE': ('isaacsim_v16_six_frame_result_v2/six_frame_recovery_report_v2.json', '046b84cb296e58f90ea7fe47f23ada91d701cd1d6a86d3ddb629deead6afdefc'),
    'V16_28_SUCCESS': ('isaacsim_v16_readiness_result_v1/readiness_capture_report_v1.json', 'ab08f15221e2f977321afc5e4983feaf9d815ca91b97f2034b36317638e78d82'),
    'V16_29_PROVENANCE': ('isaacsim_v16_timing_provenance_audit_v1/timing_provenance_report_v1.json', '5e42eb8b0f6469f82a5c003942b5a0c208a020f018a13b91fdd8c26e4574482a'),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def srcfile(path, wanted=None):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.stat().st_size <= 2_000_000, f'Unexpectedly large file: {path}'
    if wanted:
        assert sha(path) == wanted, f'Hash mismatch: {path}'
    return path.read_bytes()

expected_src = '1a4416f4ceeda3a41076c31baea1458ae59e73f715517846abd725b216c491cd'
expected_scene = '950a84720a4304fd293cd5d5e8297d56b19dae178d127cf9db390d2da5e7a7ea'
source_bytes = srcfile(run/'multimodal_probe_candidate_v15.py', expected_src)
scene_bytes = srcfile(run/'multimodal_scene_v5.usda', expected_scene)
meta_bytes = srcfile(run/'multimodal_probe_validation_v15.json')
physics_bytes = srcfile(run/'pilot_results_v1/summary_v1.json')
meta = json.loads(meta_bytes)
assert meta['script_sha256'] == expected_src
assert meta['scene_sha256'] == expected_scene
assert json.loads(physics_bytes)['samples'] == 60
ast.parse(source_bytes.decode('utf-8'))
assert source_bytes.count(f'E = Path("{run}")'.encode()) == 1
assert source_bytes.count(b'READINESS_SELECTED_STEPS') == 1
assert source_bytes.count(b'QUALIFIED_LIDAR_INGESTED') == 1
assert source_bytes.count(b'for step in range(130):') == 1

reports={}
for key, (rel, want) in sources.items():
    p=workspace/'experiments'/rel
    blob=srcfile(p,want)
    reports[key]={'file':p.name,'sha256':want,'bytes':len(blob),'source_relative':rel}
    if key=='V16_28_SUCCESS':
        e=json.loads(blob)
        assert e['runtime_pass'] and e['offline_sensor_file_validation_pass']
        assert e['selected_steps'] == [51,61,71,81,91,101]
        assert e['pose_records'] == 130 and e['imu_records']==130
        assert e['validation_issues']==[]
        assert [r['points'] for r in e['validated_frames']]==[16,16,16,16,16,4]
    if key=='V16_29_PROVENANCE':
        e=json.loads(blob)
        assert e['audit_pass'] and e['issues']==[]
        assert e['cross_sensor_synchronization_verified'] is False
        assert e['camera_exposure_timestamp_verified'] is False

assert not pkg.exists() and not pkg.is_symlink()
pkg.mkdir(mode=0o700)
(pkg/'evidence').mkdir(mode=0o700)
(pkg/'pilot_results_v1').mkdir(mode=0o700)
(pkg/'multimodal_probe_candidate_v15.py').write_bytes(source_bytes)
(pkg/'multimodal_scene_v5.usda').write_bytes(scene_bytes)
(pkg/'multimodal_probe_validation_v15.json').write_bytes(meta_bytes)
(pkg/'pilot_results_v1/summary_v1.json').write_bytes(physics_bytes)
for key,(rel,want) in sources.items():
    dest=pkg/'evidence'/Path(rel).name
    with dest.open('xb') as f:
        f.write(srcfile(workspace/'experiments'/rel,want))

manifest={
    'schema':'TRUST_ROBOT_KIOS_ISAAC_V16_28_29_RECOVERY_CHECKPOINT_V1',
    'publication_date':'2026-10-15',
    'source_predecessor_commit':'00d04bf69610c36f3bd2bbfb11633a993b9a624f',
    'branch':'kios-isaacsim-v15-integration',
    'classification':'OFFLINE_VALIDATED_SYNTHETIC_SENSOR_RECORDING_NOT_SCIENTIFIC_SYNCHRONIZATION',
    'source_sha256':expected_src,
    'scene_sha256':expected_scene,
    'selected_steps':[51,61,71,81,91,101],
    'points_per_lidar_scan':[16,16,16,16,16,4],
    'camera_frames':6,'lidar_frames':6,'imu_records':130,'usd_pose_records':130,
    'camera_exposure_timestamp_verified':False,
    'cross_sensor_synchronization_verified':False,
    'independent_ground_truth_verified':False,
    'physical_hesai_equivalence_verified':False,
    'raw_sensor_payloads_published':False,
    'reports':reports,
}
(pkg/'checkpoint_manifest_v1.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')

readme='''# Isaac Sim V16.28–V16.29 KIOS six-frame recovery

**Status: reproducible source/scene snapshot of a SUCCESSFUL local synthetic runtime and offline-file validation; NOT a scientifically synchronized or physically validated dataset.**

Read [`AGENTS.md`](../../AGENTS.md), [`TRUST_ROBOT_MASTER_CONTEXT.md`](../../TRUST_ROBOT_MASTER_CONTEXT.md), and the [recovery audit](../../docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_RECOVERY_FREEZE_V1.md) first.

## Working recipe (must retain all components)

1. Corrected LiDAR mounting Xform: `Lidar3DMount` translation `(1.2,0,1.5)` under the scaled `Base` cube (nominal world LiDAR position relative to base origin: `(+0.48,0,+0.225)` metres). The original V15 mount `(0,0,0.2)` was inside robot geometry and all 59 original returns were consistent with a front-face self-hit.
2. Keep the **original 16-emitter SOLID_STATE generic OmniLidar** attributes; do not silently swap sensor models.
3. Initialize Replicator with `rep.orchestrator.step(rt_subframes=4, delta_time=0, pause_timeline=False)` **before** 55 stationary `world.step(render=True)` warm-up steps.
4. Use the 130-step scripted robot motion, sampling every ten steps from step 41. Save **raw GMO before** `rep.orchestrator.step` during each candidate capture: later Replicator evaluation was observed to clear previously populated buffers.
5. Interpret `gmo.elementsCoordsType == CoordsType.SPHERICAL`, `frameOfReference == SENSOR`, and the installed `ElementFlags.VALID` bit `64`. GMO x/y/z mean **azimuth degrees / elevation degrees / radius metres**. Convert to sensor-frame Cartesian XYZ with `x=r cos(elev) cos(az)`, `y=r cos(elev) sin(az)`, `z=r sin(elev)`; save only finite VALID returns. No world-frame claim.
6. Collect candidate camera images and qualified LiDAR XYZ separately. **Select the first six consecutive common capture steps spaced ten steps apart** rather than requiring the startup step to work. V16.28 chose `[51,61,71,81,91,101]`.
7. Keep the legacy `IsaacExtractRTXSensorPointCloudNoAccumulator` attachment for diagnostic compatibility, but do **not** use its empty output as the recorder LiDAR input. The qualified GMO-to-XYZ path is the working source.
8. Assert and independently validate six genuine nonblack RGBA images (120x160x4), six sensor-frame XYZ arrays matching source validity-flagged GMO data and calibration-target ranges, 130 IMU and 130 USD pose samples, and persisted index/summary files. Simulator exit code zero alone is not success; require `MULTIMODAL_RUNTIME=PASS` and absence of `SENSOR_RUNTIME_EXCEPTION=YES`.

## Committed files

- `multimodal_probe_candidate_v15.py`: exact SHA-256-pinned V16.28 successful script. The historical KIOS absolute `E` path is preserved intentionally; do not run this file directly from the repository.
- `multimodal_scene_v5.usda`: exact corrected-mount scene from V16.28.
- `multimodal_probe_validation_v15.json` plus `pilot_results_v1/summary_v1.json`: original local source integrity/preflight dependencies.
- `evidence/*.json`: hash-checked compact prior diagnosis, success and timing reports. No raw `.npy`/`.npz` sensor recordings, GPU logs, cache files or secrets are committed.
- `checkpoint_manifest_v1.json`: results and source/report hashes.
- `run_isolated.sh`: guarded KIOS-only sandbox, two GPU checks, 240-second bounded run, and offline validator.
- `prepare_local_run.py`: builds a **new local project-scoped** run copy and updates its source hash, without touching the shared simulator or starting it.
- `verify_local_recording.py`: offline array/flag/geometry/timestamp validator; **does not** establish camera exposure timing or physical synchronization.

## Prepare and independently validate (KIOS only)

```bash
W=/home/kios/TRUST_ROBOT_ALI
R=$W/github_checkout_v15
PY=$W/venvs/isaac_v15_odometry_v1/bin/python
$PY -B $R/experiments/isaacsim_v16_recovery_v1/prepare_local_run.py $W/experiments/isaacsim_v16_recovery_reproduction_NEW_v1
$PY -B $R/experiments/isaacsim_v16_recovery_v1/verify_local_recording.py $W/experiments/isaacsim_v16_readiness_capture_v1
# After preparing a NEW RUN directory, launch it via:
# bash $R/experiments/isaacsim_v16_recovery_v1/run_isolated.sh NEW_RUN_DIR NEW_RESULT_DIR
```

**Preparation is not execution.** Before launching the prepared copy, follow the shared-KIOS GPU/namespace restrictions: `kios` user only; two 15-second-separated GPU checks (>=10,500 MiB free and <=10% utilization); no competing compute except verified immutable GNOME Remote Desktop; new independent RUN/OUT directories; private `bwrap --unshare-net --unshare-user --unshare-pid --unshare-ipc`, read-only root/repo/installation, only RUN/OUT writable; redirected HOME, XDG, TMP, OptiX/CUDA caches; 240s interrupt + 30s kill cap; no sudo, no physical robot, no unisolated simulation. Use the committed `run_isolated.sh` launcher for a new prepared RUN and new OUT. Do not execute the pinned candidate inside this GitHub checkout.

## Explicit limitations and next work

- **V16.28 validated 6 pairs: LiDAR valid-point counts `[16,16,16,16,16,4]`**; the last sample is sparse and remains a quality limitation. Selected startup step 41 was missing in V16.26b; collecting longer and selecting verified pairs resolved the bounded smoke-test requirement.
- **V16.29 timing/provenance audit PASS**, zero issues. Six LiDAR stamps advance at ~0.166666675s per ten motion steps. The GMO minus USD read-step clock difference is ~**+1.033333387 s**, with spread <1e-9s. This is an observed clock-domain relation, **not a calibrated offset**. Never automatically subtract it or claim physical synchronization.
- Camera independent exposure timestamps were **not captured**. Camera–LiDAR cross-sensor sync, calibration quality, moving-ray-time consistency, independent physical ground truth, actual Hesai equivalence, learned sensor-health labels, and localization estimator performance remain **unverified**.
- USD-composed kinematic poses are *not* independently measured reference trajectories.
- Do not overwrite older V15 or V16 experiments. Future development should use new directory names and independent local validation, with versioned evidence and clear gating before claims or further commits.
'''
(pkg/'README.md').write_text(readme)

helper=r'''#!/usr/bin/env python3
"""Prepare a NEW isolated local copy; never starts Isaac Sim."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

W=Path('/home/kios/TRUST_ROBOT_ALI')
P=Path(__file__).resolve().parent

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    assert os.geteuid()!=0 and os.getlogin()=='kios' if False else os.geteuid()!=0
    assert len(sys.argv)==2, 'usage: prepare_local_run.py NEW_ABSOLUTE_RUN_DIRECTORY'
    target=Path(sys.argv[1])
    assert target.is_absolute() and target.parent==W/'experiments'
    assert W.resolve()==W and not target.parent.is_symlink()
    assert target.name not in ('', '.', '..')
    assert not target.exists() and not target.is_symlink()
    manifest=json.loads((P/'checkpoint_manifest_v1.json').read_text())
    source=(P/'multimodal_probe_candidate_v15.py').read_bytes()
    scene=(P/'multimodal_scene_v5.usda').read_bytes()
    assert sha(source)==manifest['source_sha256']
    assert sha(scene)==manifest['scene_sha256']
    old='E = Path("/home/kios/TRUST_ROBOT_ALI/experiments/isaacsim_v16_readiness_capture_v1")'
    text=source.decode()
    assert text.count(old)==1
    text=text.replace(old, f'E = Path("{target}")',1)
    ast.parse(text)
    target.mkdir(mode=0o700)
    for d in ('pilot_results_v1','crash_reports_v15','derived_data_cache',
              'kit_cache','kit_data','kit_logs','direct_rgb_samples',
              'event_clouds','pre_gmo_samples_v1','qualified_xyz_v1'):
        (target/d).mkdir(mode=0o700)
    (target/'multimodal_probe_candidate_v15.py').write_text(text)
    (target/'multimodal_scene_v5.usda').write_bytes(scene)
    (target/'pilot_results_v1/summary_v1.json').write_bytes(
        (P/'pilot_results_v1/summary_v1.json').read_bytes())
    meta=json.loads((P/'multimodal_probe_validation_v15.json').read_text())
    meta['script_sha256']=sha(text.encode())
    meta['status']='NEW_LOCAL_REPRODUCTION_UNEXECUTED_UNVERIFIED'
    (target/'multimodal_probe_validation_v15.json').write_text(
        json.dumps(meta,indent=2,sort_keys=True)+'\n')
    print('PREPARED_NEW_RUN='+str(target))
    print('LOCAL_SOURCE_SHA256='+meta['script_sha256'])
    print('RUN_STATUS=NOT_EXECUTED')
    print('NEXT=USE_VERIFIED_PRIVATE_BWRAP_GPU_RUN_HARNESS')

if __name__=='__main__': main()
'''
# Standardize the tiny identity check (fail closed).
helper=helper.replace("assert os.geteuid()!=0 and os.getlogin()=='kios' if False else os.geteuid()!=0", "assert os.geteuid()!=0 and __import__('pwd').getpwuid(os.geteuid()).pw_name == 'kios'")
ast.parse(helper)
(pkg/'prepare_local_run.py').write_text(helper)

verifier=r'''#!/usr/bin/env python3
"""Offline verification of V16 recovery results; no simulator or writes."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

def read(path):
    assert path.is_file() and not path.is_symlink(), path
    return path.read_bytes()

def load(path): return json.loads(read(path))
def jsonl(path): return [json.loads(x) for x in read(path).decode().splitlines() if x.strip()]

def main():
    assert len(sys.argv)==2, 'usage: verify_local_recording.py ABSOLUTE_RUN_DIRECTORY'
    run=Path(sys.argv[1]); assert run.is_absolute() and run.is_dir() and not run.is_symlink()
    folder=run/'multimodal_probe_results_v15'
    index=load(folder/'capture_index_v15.json')
    summary=load(folder/'summary_v1.json')
    poses=jsonl(folder/'base_pose_series_v15.jsonl')
    imus=jsonl(folder/'imu_v1.jsonl')
    steps=[int(x['step']) for x in index]
    assert len(steps)==6 and len(set(steps))==6
    assert all(steps[i+1]-steps[i]==10 for i in range(5))
    assert len(poses)==len(imus)==130
    assert [x['step'] for x in poses]==list(range(1,131))
    assert [x['step'] for x in imus]==list(range(1,131))
    assert summary['sequence_camera_frames']==6 and summary['sequence_lidar_frames']==6
    assert summary['usd_pose_samples']==130
    pose_times=np.array([x['simulation_step_time_s'] for x in poses],dtype=float)
    imu_times=np.array([x['simulation_step_time_s'] for x in imus],dtype=float)
    assert np.all(np.isfinite(pose_times)) and np.all(np.diff(pose_times)>0)
    assert np.array_equal(pose_times,imu_times)
    sensor_positions=np.array([x['lidar_usd_world_position_m'] for x in poses],dtype=float)
    base_positions=np.array([x['usd_world_position_m'] for x in poses],dtype=float)
    assert sensor_positions.shape==base_positions.shape==(130,3)
    assert np.all(np.isfinite(sensor_positions))
    drift=float(np.max(np.linalg.norm((sensor_positions-base_positions)-(sensor_positions[0]-base_positions[0]),axis=1)))
    assert drift<0.001
    stamps=[]; offsets=[]; all_points=0
    for item in index:
        step=int(item['step'])
        camera=np.load(folder/item['camera_file'],allow_pickle=False)
        cloud=np.load(folder/item['lidar_file'],allow_pickle=False)
        assert camera.shape==(120,160,4) and np.all(np.isfinite(camera))
        assert float(np.mean(np.any(camera[:,:,:3]>0,axis=2)))>=0.01
        assert cloud.ndim==2 and cloud.shape[1]==3 and 0<len(cloud)<=2048
        assert np.all(np.isfinite(cloud)) and np.all(cloud[:,0]>0)
        with np.load(run/'qualified_xyz_v1'/f'lidar_xyz_step_{step:03d}.npz',allow_pickle=False) as raw:
            xyz=raw['xyz']; flags=raw['flags']; stamp=int(raw['timestamp_ns'][0]); frame=int(raw['frame_id'][0])
        assert np.array_equal(xyz,cloud)
        assert len(flags)==len(cloud) and np.all((flags.astype(np.uint64)&64)!=0)
        read_t=float(poses[step-1]['simulation_step_time_s'])
        assert abs(float(item['camera_read_step_time_s'])-read_t)<1e-5
        assert abs(float(item['lidar_read_step_time_s'])-read_t)<1e-5
        assert item['lidar_rendering_time_raw']=='GMO_SENSOR_TIMESTAMP_NS:'+str(stamp)
        expected=1.25-float(sensor_positions[step-1,0])
        hits=int(np.count_nonzero(np.abs(cloud[:,0]-expected)<=0.03))
        assert hits>=0.75*len(cloud)
        all_points+=len(cloud); stamps.append(stamp/1e9); offsets.append(stamp/1e9-read_t)
        print(f'FRAME_PASS step={step} points={len(cloud)} frame_id={frame} target_hits={hits}')
    assert np.all(np.diff(np.array(stamps))>0)
    assert np.max(np.abs(np.diff(stamps)-10/60))<0.01
    print('SELECTED_STEPS=',steps)
    print('CAMERA_FRAMES=6 LIDAR_FRAMES=6 IMU_RECORDS=130 USD_POSE_RECORDS=130')
    print('TOTAL_VALID_LIDAR_POINTS=',all_points)
    print('GMO_MINUS_READ_CLOCK_OFFSET_SPREAD_S=',max(offsets)-min(offsets))
    print('CROSS_SENSOR_EXPOSURE_SYNC_VERIFIED=False')
    print('INDEPENDENT_PHYSICAL_GROUND_TRUTH_VERIFIED=False')
    print('OFFLINE_SENSOR_FILE_VALIDATION=PASS')

if __name__=='__main__': main()
'''
ast.parse(verifier)
(pkg/'verify_local_recording.py').write_text(verifier)

runner='#!/usr/bin/env bash\n# KIOS ONLY. Runs a separately prepared source in read-only shared bwrap sandbox.\nset -euo pipefail\numask 077\nulimit -c 0\nW=/home/kios/TRUST_ROBOT_ALI\nR=$W/github_checkout_v15\nI=/home/kios/isaacsim\nPY=$W/venvs/isaac_v15_odometry_v1/bin/python\n[[ "$#" == 2 ]] || { echo \'Usage: run_isolated.sh ABSOLUTE_PREPARED_RUN_DIR NEW_ABSOLUTE_RESULT_DIR\'; exit 2; }\nRUN=$1\nOUT=$2\n[[ "$(id -un)" == kios && "$(readlink -f "$W")" == "$W" ]]\n[[ -d "$R/.git" && -x "$PY" && -x "$I/python.sh" ]]\n[[ -d "$RUN" && ! -L "$RUN" && -d "$W/experiments" && ! -L "$W/experiments" ]]\n[[ "$(dirname "$RUN")" == "$W/experiments" && "$(dirname "$OUT")" == "$W/experiments" ]]\n[[ "$(readlink -f "$RUN")" == "$RUN" ]]\n[[ ! -e "$OUT" && ! -L "$OUT" ]]\n[[ -z "$(git -C "$R" status --porcelain)" ]]\n[[ -f "$RUN/multimodal_probe_candidate_v15.py" && -f "$RUN/multimodal_probe_validation_v15.json" ]]\n[[ -f "$RUN/multimodal_scene_v5.usda" ]]\n"$PY" -B - "$RUN" <<\'PY\'\nimport hashlib,json,sys\nfrom pathlib import Path\nr=Path(sys.argv[1])\nm=json.loads((r/\'multimodal_probe_validation_v15.json\').read_text())\ndef sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()\nassert sha(r/\'multimodal_probe_candidate_v15.py\')==m[\'script_sha256\']\nassert sha(r/\'multimodal_scene_v5.usda\')==m[\'scene_sha256\']\nassert sha(r/\'multimodal_scene_v5.usda\')==\'950a84720a4304fd293cd5d5e8297d56b19dae178d127cf9db390d2da5e7a7ea\'\nassert f\'E = Path("{r}")\' in (r/\'multimodal_probe_candidate_v15.py\').read_text()\nassert not (r/\'multimodal_probe_results_v15\').exists()\nprint(\'PREPARED_RUN_SOURCE_AND_SCENE=VERIFIED\',flush=True)\nPY\nmkdir -m 700 "$OUT"\nfor d in home cache config data state tmp shm logs optix_cache cuda_cache; do mkdir -m 700 "$OUT/$d"; done\nDEVICES=()\nshopt -s nullglob\nfor node in /dev/nvidiactl /dev/nvidia0 /dev/nvidia-uvm /dev/nvidia-uvm-tools /dev/nvidia-modeset /dev/dri/card[0-9]* /dev/dri/renderD* /dev/random /dev/urandom /dev/null /dev/zero; do\n    if [[ -c "$node" && ! -L "$node" ]]; then DEVICES+=(--dev-bind "$node" "$node"); fi\ndone\nfor node in /dev/nvidiactl /dev/nvidia0 /dev/random /dev/urandom /dev/null /dev/zero; do [[ -c "$node" && ! -L "$node" ]]; done\nHOST_NETNS="$(readlink /proc/self/ns/net)"\nSANDBOX=(/usr/bin/bwrap --die-with-parent --unshare-user --unshare-net --unshare-pid --unshare-ipc --ro-bind / / --bind "$RUN" "$RUN" --bind "$OUT" "$OUT" --bind "$OUT/tmp" /tmp --bind "$OUT/shm" /dev/shm --proc /proc)\nSANDBOX+=("${DEVICES[@]}")\nSANDBOX+=(--chdir "$RUN" --setenv HOME "$OUT/home" --setenv XDG_CACHE_HOME "$OUT/cache" --setenv XDG_CONFIG_HOME "$OUT/config" --setenv XDG_DATA_HOME "$OUT/data" --setenv XDG_STATE_HOME "$OUT/state" --setenv XDG_RUNTIME_DIR "$OUT/tmp" --setenv TMPDIR "$OUT/tmp" --setenv CUDA_CACHE_PATH "$OUT/cuda_cache" --setenv OPTIX_CACHE_PATH "$OUT/optix_cache" --setenv PYTHONDONTWRITEBYTECODE 1 --setenv PYTHONNOUSERSITE 1 --setenv TRUST_ROBOT_HOST_NETNS "$HOST_NETNS")\nSAFE_ENV=(/usr/bin/env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 USER=kios LOGNAME=kios HOME="$OUT/home" XDG_CACHE_HOME="$OUT/cache" XDG_CONFIG_HOME="$OUT/config" XDG_DATA_HOME="$OUT/data" XDG_STATE_HOME="$OUT/state" XDG_RUNTIME_DIR="$OUT/tmp" TMPDIR="$OUT/tmp" CUDA_CACHE_PATH="$OUT/cuda_cache" OPTIX_CACHE_PATH="$OUT/optix_cache" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TRUST_ROBOT_HOST_NETNS="$HOST_NETNS" TRUST_ROBOT_SENSOR_PROBE_ENABLE=1)\ntimeout 45s "${SAFE_ENV[@]}" "${SANDBOX[@]}" /usr/bin/python3 -B -c \'\nimport os,socket\nw="/home/kios/TRUST_ROBOT_ALI"\nfor p in ("/",w,w+"/github_checkout_v15","/home/kios/isaacsim"):\n assert os.statvfs(p).f_flag & os.ST_RDONLY\nassert os.readlink("/proc/self/ns/net")!=os.environ["TRUST_ROBOT_HOST_NETNS"]\nassert {name for _,name in socket.if_nameindex()}=={"lo"}\nprint("PRIVATE_NETWORK_AND_READONLY_HOST=PASS",flush=True)\n\'\ntimeout 80s "$PY" -B - <<\'PY\'\nimport os,stat,subprocess,time\nfrom pathlib import Path\ndef cmd(*a): return subprocess.check_output(a,text=True,timeout=15).strip()\ndef check(i):\n rows=cmd(\'nvidia-smi\',\'--query-gpu=index,memory.free,utilization.gpu\',\'--format=csv,noheader,nounits\').splitlines()\n assert len(rows)==1\n gpu,free,util=map(int,(v.strip() for v in rows[0].split(\',\')))\n assert gpu==0 and free>=10500 and 0<=util<=10\n pids=[v.strip() for v in cmd(\'nvidia-smi\',\'--query-compute-apps=pid\',\'--format=csv,noheader,nounits\').splitlines() if v.strip() and v.strip()!=\'No running processes found\']\n if not pids: ident=(\'NONE\',)\n else:\n  assert len(pids)==1 and pids[0].isdigit()\n  pid=int(pids[0]);p=Path(\'/proc\')/str(pid)\n  assert p.stat().st_uid==os.getuid()\n  exe=os.readlink(p/\'exe\');assert exe==\'/usr/libexec/gnome-remote-desktop-daemon\'\n  f=Path(exe).stat();assert stat.S_ISREG(f.st_mode) and f.st_uid==0 and not(f.st_mode&0o022)\n  ident=(pid,cmd(\'ps\',\'-p\',str(pid),\'-o\',\'lstart=\'),exe)\n print(f\'GPU_CHECK_{i}_PASS free_MiB={free} util_percent={util} background={ident}\',flush=True)\n return ident\na=check(1);time.sleep(15);b=check(2);assert a==b\nprint(\'TWO_GPU_CHECKS=PASS\',flush=True)\nPY\nset +e\ntimeout --signal=INT --kill-after=30s 240s "${SAFE_ENV[@]}" "${SANDBOX[@]}" "$I/python.sh" "$RUN/multimodal_probe_candidate_v15.py" > "$OUT/logs/runtime.log" 2>&1\nRC=$?\nset -e\necho "ISAAC_SIM_EXIT_CODE=$RC"\nif [[ "$RC" != 0 ]] || ! grep -q \'MULTIMODAL_RUNTIME=PASS\' "$OUT/logs/runtime.log" || grep -q \'SENSOR_RUNTIME_EXCEPTION=YES\' "$OUT/logs/runtime.log"; then\n    echo "RUNTIME_NOT_VALIDATED: inspect $OUT/logs/runtime.log" >&2\n    exit 1\nfi\n"$PY" -B "$R/experiments/isaacsim_v16_recovery_v1/verify_local_recording.py" "$RUN"\necho \'RUNTIME_AND_OFFLINE_SENSOR_FILE_CHECKS=PASS\'\necho \'CROSS_SENSOR_EXPOSURE_SYNC=UNVERIFIED\'\necho \'PHYSICAL_GROUND_TRUTH=UNVERIFIED\'\n'
(pkg/'run_isolated.sh').write_text(runner)

freezedoc='''# TRUST-ROBOT: KIOS Isaac Sim V16.28–V16.29 synthetic recovery freeze (2026-10-15)

**Checkpoint:** six camera frames + six validity-qualified GenericModelOutput LiDAR Cartesian sensor-frame scans + 130 IMU readings + 130 USD-composed poses, with runtime PASS, offline sensor-file PASS and offline provenance PASS. **Not a claim of synchronized physical measurements or scientific localization.**

## Authoritative next-agent location

- Working source/scene and reproduction instructions: `experiments/isaacsim_v16_recovery_v1/README.md`.
- SHA-bound input/output receipt: `experiments/isaacsim_v16_recovery_v1/checkpoint_manifest_v1.json`.
- Source predecessor SHA: `00d04bf69610c36f3bd2bbfb11633a993b9a624f`; local branch `kios-isaacsim-v15-integration`.
- Successful original local RUN: `/home/kios/TRUST_ROBOT_ALI/experiments/isaacsim_v16_readiness_capture_v1` (not in Git); compact reports committed to `experiments/isaacsim_v16_recovery_v1/evidence/`.
- **Do not** use the old `docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_CAPTURE_RECOVERY_V1.md` as the latest status: it accurately records the earlier PARTIAL recovery, now superseded by this checkpoint. Preserve the old report as history.

## Diagnoses and repairs (do not regress)

- V16.19 GMO decoded nonempty returns on 44 sampled world steps out of 90; later replication could still fail.
- V16.20 before/after Replicator at steps 51/61/71/81: 4 nonempty packets **before**, zero **after**; capture raw GMO before Replicator evaluation.
- V16.21: preserved raw x/y/z arrays and hashes before rendering invalidated the buffer.
- V16.22: all 59 original LiDAR returns project within 1cm of body x=+0.4m; sensor mount nominally inside `Base` visual geometry. Evidence supports **robot self-hits**, not target returns.
- V16.23: mount parent translate `(0,0,0.2)` -> `(1.2,0,1.5)` under a scaled Base. Live composed sensor xyz matched anticipated position; 64/64 forward projections hit external near-face x=1.25m within 3cm; 0 old self-face matches.
- V16.24: raw GMO coordinate semantics explicitly `CoordsType.SPHERICAL`, `FrameOfReference.SENSOR`, `ElementFlags.VALID=64`. 4 valid XYZ frames/64 target points; stationary 55-step rendering alone insufficient.
- V16.25: one `rep.orchestrator.step(rt_subframes=4, delta_time=0, pause_timeline=False)` before stationary warm-up improved camera to 6/6 and LiDAR to 5/6, but startup capture still unreliable; premotion GMO cache empty.
- V16.26/V16.26b: fixed-step six-frame writer failure (`assert [r["step"] for r in lidar_series] == expected_steps`) because step 41 lacked LiDAR. The V16.26 preparation-only source assertion also failed safely. Do not classify exit code zero as success when runtime logs show `AssertionError`.
- **V16.28:** bounded 130-step acquisition, candidates every 10 steps after step 40, choose earliest six consecutive common valid camera/LiDAR samples. Selected **51,61,71,81,91,101**. Saved 6 real RGBA frames and 6 verified sensor-frame XYZ clouds; points **16,16,16,16,16,4**. Target geometry and originating GMO/VALID flags matched; 130 IMU+pose. `MULTIMODAL_RUNTIME=PASS`, offline file checks passed, zero issues.
- **V16.29:** offline audit on exact V16.28 files: pose/IMU read-step time difference 0; LiDAR mount drift ~5.55e-17m; LiDAR timestamp intervals ~0.166666675s; GMO timestamp minus read-step time **+1.033333387s**, stable spread **7.95e-10s**. Timestamp origins not independently calibrated and camera exposure time absent. Audit PASS with zero issues.

## Scientific/safety boundaries

V16.28 recovers a **synthetic proxy** with simplified kinematic movement and a 16-emitter idealized sensor. The final 4-point scan is sparse. Generic LiDAR is not physical Hesai. Sensor clock offset stability is **not proof of absolute clock agreement**, so never silently subtract an offset. Co-indexed read steps are **not proof of camera exposure synchronization**; actual camera exposure time, physical sensor triggering, independent trajectory ground truth, real sensor calibration, and localization/health-model results remain unverified. Do not use the synthetic scans as empirical health labels. No robots were contacted.

Use private read-only `bwrap`, isolated project-local caches, no network, no sudo, no shared installation writes, two GPU checks 15 seconds apart, and bounded execution. All original V15/V16 local experiments must remain immutable. No bulk recordings or raw logs in Git. The next phase is controlled stabilization and separate scientific timestamp/frame validation; only evidence-supported claims should enter future research milestones.
'''
doc.write_text(freezedoc)

agents=repo/'AGENTS.md'
original_agents=srcfile(agents)
assert b'isaacsim_v16_recovery_v1' not in original_agents
addition='''
## KIOS Isaac Sim V16 recovered acquisition (2026-10-15)

**Read before any new Isaac Sim camera/LiDAR/IMU work:**
`docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_RECOVERY_FREEZE_V1.md`
and `experiments/isaacsim_v16_recovery_v1/README.md`.
The latter contains SHA-pinned successful source, corrected USD mount, compact
experiment reports, local run-preparation utility and offline validator, and KIOS-isolated reproduction launcher.
V16.28 passed 6 synthetic camera / 6 real GMO-derived LiDAR XYZ frame files
plus 130 IMU/pose records; V16.29 provenance audit passed. **Do not claim
cross-sensor exposure synchronization, independently measured ground truth,
physical sensor equivalence or localization performance.** Preserve original
V15/V16 experimental history. No shared-KIOS or physical-robot operations.
'''
with agents.open('ab') as f:
    f.write(addition.encode())

state=repo/'docs/TRUST_ROBOT_PROJECT_STATE.md'
old_state=srcfile(state)
assert b'TRUST-ROBOT KIOS Isaac Sim V16.28 recovery' not in old_state
state_update="""
## TRUST-ROBOT KIOS Isaac Sim V16.28 recovery (2026-10-15)

Independent synthetic runtime, file and provenance checkpoints have now passed
for the **KIOS V16.28 six-frame proxy experiment**: six nonblack camera frames,
six VALID-flagged GMO-to-Cartesian XYZ LiDAR scans, and 130 IMU plus 130 USD
pose records. V16.29 offline provenance and read-step timing audits passed.

This is a separate **synthetic hardware-in-the-loop-free smoke test**; it does
**not** alter the M2DGR physical calibration, synchronization, reference or
evaluation-readiness blocking decisions elsewhere in this state document.
The camera exposure time and cross-sensor synchronization remain unverified;
GMO vs USD read-time offset (+~1.033333387s) is observed, not calibrated.
Do not use synthetic proxy results as physical ground truth, physical robot
performance, or empirical reliability-training labels. The last LiDAR frame
contains only four valid points and must be flagged as sparse.

For exact reproducible source, corrected USD scene, SHA-bound compact evidence,
KIOS sandbox instructions, and the next-agent handoff, read:
`docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_RECOVERY_FREEZE_V1.md`
and `experiments/isaacsim_v16_recovery_v1/README.md`.
"""
with state.open('ab') as f:
    f.write(state_update.encode())

# Recompute hash inventory for all checkpoint files except inventory itself.
inventory=[]
for f in sorted(pkg.rglob('*')):
    if f.is_file() and not f.is_symlink():
        inventory.append(f'{sha(f)}  {f.relative_to(pkg)}')
(pkg/'SHA256SUMS.txt').write_text('\n'.join(inventory)+'\n')
print('WORKING_SOURCE_SHA256=',sha(pkg/'multimodal_probe_candidate_v15.py'))
print('CORRECTED_SCENE_SHA256=',sha(pkg/'multimodal_scene_v5.usda'))
print('COMPACT_EVIDENCE_REPORT_COUNT=',len(sources))
print('NEW_RECOVERY_PACKAGE=',pkg)
print('AGENT_ENTRY_POINT=UPDATED')
print('CHECKPOINT_FILE_PREPARATION=PASS')
PY

echo
echo '=== 3. OFFLINE REPRODUCIBILITY TESTS ==='
bash -n "$PKG/run_isolated.sh"
echo "VERSIONED_SANDBOX_LAUNCHER_SYNTAX=PASS"
"$PY" -B "$PKG/verify_local_recording.py" "$RUN"
"$PY" -B "$PKG/prepare_local_run.py" "$OUT/unused" 2> "$OUT/expected_guard.log" && {
  echo 'GUARD_SHOULD_HAVE_REFUSED_NON_EXPERIMENT_PATH' >&2
  exit 1
} || true
[[ ! -e "$OUT/unused" ]]
"$PY" -B - "$PKG" "$RUN" "$OUT" <<'PY'
import ast,hashlib,json,sys
from pathlib import Path
pkg,run,out=map(Path,sys.argv[1:])
manifest=json.loads((pkg/'checkpoint_manifest_v1.json').read_text())
for name,key in [('multimodal_probe_candidate_v15.py','source_sha256'),('multimodal_scene_v5.usda','scene_sha256')]:
    f=pkg/name
    assert hashlib.sha256(f.read_bytes()).hexdigest()==manifest[key]
for report in manifest['reports'].values():
    f=pkg/'evidence'/report['file']
    assert hashlib.sha256(f.read_bytes()).hexdigest()==report['sha256']
for row in (pkg/'SHA256SUMS.txt').read_text().splitlines():
    checksum,relative=row.split('  ',1)
    assert hashlib.sha256((pkg/relative).read_bytes()).hexdigest()==checksum
for script in ['multimodal_probe_candidate_v15.py','prepare_local_run.py','verify_local_recording.py']:
    ast.parse((pkg/script).read_text())
print('CHECKPOINT_INVENTORY=VERIFIED')
print('VERIFIER_SOURCE_AST=PASS')
print('EVIDENCE_HASHES=PASS')
PY

echo
echo '=== 4. STAGE EXPLICIT FILES ONLY ==='
git -C "$R" add -- AGENTS.md docs/TRUST_ROBOT_PROJECT_STATE.md "${DOC#$R/}" "${PKG#$R/}"
git -C "$R" diff --cached --check
"$PY" -B - "$R" <<'PY'
import subprocess,sys
from pathlib import Path
repo=Path(sys.argv[1]);pkg='experiments/isaacsim_v16_recovery_v1/'
actual=subprocess.check_output(['git','-C',str(repo),'diff','--cached','--name-only','-z']).decode().split('\0')
actual=[s for s in actual if s]
required={'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_ISAACSIM_V16_28_29_RECOVERY_FREEZE_V1.md'}
assert required.issubset(actual),actual
assert all(x in required or x.startswith(pkg) for x in actual),actual
assert len(actual)>=20,len(actual)
print('STAGED_FILE_COUNT=',len(actual))
for x in actual:print('STAGED=',x)
PY

echo
echo '=== 5. VERIFY REMOTE STILL AT EXPECTED PREDECESSOR ==='
[[ "$(git -C "$R" rev-parse HEAD)" == "$BASE" ]]
REMOTE_AGAIN="$(git -C "$R" ls-remote --exit-code origin "refs/heads/$BRANCH" | awk '{print $1}')"
[[ "$REMOTE_AGAIN" == "$BASE" ]] || {
  echo "REMOTE_MOVED_ABORTED_BEFORE_COMMIT=$REMOTE_AGAIN" >&2
  exit 1
}

echo
echo '=== 6. SINGLE CHECKPOINT COMMIT AND FAST-FORWARD PUSH ==='
git -C "$R" commit -m 'Freeze KIOS Isaac Sim V16.28 sensor recovery and V16.29 timing audit'
NEW_HEAD="$(git -C "$R" rev-parse HEAD)"
[[ "$NEW_HEAD" != "$BASE" ]]
git -C "$R" push origin "HEAD:refs/heads/$BRANCH"
REMOTE_FINAL="$(git -C "$R" ls-remote --exit-code origin "refs/heads/$BRANCH" | awk '{print $1}')"
[[ "$REMOTE_FINAL" == "$NEW_HEAD" ]]
[[ -z "$(git -C "$R" status --porcelain)" ]]

echo
echo '=== 7. FINAL CHECKPOINT RECEIPT ==='
echo "GITHUB_REPOSITORY=$REMOTE_REPO"
echo "BRANCH=$BRANCH"
echo "PREDECESSOR_COMMIT=$BASE"
echo "NEW_GITHUB_COMMIT=$NEW_HEAD"
echo 'PUSH_REMOTE_SHA=VERIFIED'
echo 'WORKTREE_CLEAN=YES'
echo 'COMPACT_EVIDENCE_AND_CODE=PUBLISHED'
echo 'RAW_SENSOR_DATA_NOT_PUBLISHED=YES'
echo 'SHARED_ISAAC_SIM=UNCHANGED'
echo 'GPU_USED=NO'
echo 'PHYSICAL_ROBOT_CONTACT=NO'
echo 'CROSS_SENSOR_SYNCHRONIZATION=UNVERIFIED'
echo 'NEXT=REVIEW_PUBLISHED_CHECKPOINT_AND_PLAN_SEPARATE_SYNCHRONIZATION_WORK'
