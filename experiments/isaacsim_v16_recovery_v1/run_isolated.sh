#!/usr/bin/env bash
# KIOS ONLY. Runs a separately prepared source in read-only shared bwrap sandbox.
set -euo pipefail
umask 077
ulimit -c 0
W=/home/kios/TRUST_ROBOT_ALI
R=$W/github_checkout_v15
I=/home/kios/isaacsim
PY=$W/venvs/isaac_v15_odometry_v1/bin/python
[[ "$#" == 2 ]] || { echo 'Usage: run_isolated.sh ABSOLUTE_PREPARED_RUN_DIR NEW_ABSOLUTE_RESULT_DIR'; exit 2; }
RUN=$1
OUT=$2
[[ "$(id -un)" == kios && "$(readlink -f "$W")" == "$W" ]]
[[ -d "$R/.git" && -x "$PY" && -x "$I/python.sh" ]]
[[ -d "$RUN" && ! -L "$RUN" && -d "$W/experiments" && ! -L "$W/experiments" ]]
[[ "$(dirname "$RUN")" == "$W/experiments" && "$(dirname "$OUT")" == "$W/experiments" ]]
[[ "$(readlink -f "$RUN")" == "$RUN" ]]
[[ ! -e "$OUT" && ! -L "$OUT" ]]
[[ -z "$(git -C "$R" status --porcelain)" ]]
[[ -f "$RUN/multimodal_probe_candidate_v15.py" && -f "$RUN/multimodal_probe_validation_v15.json" ]]
[[ -f "$RUN/multimodal_scene_v5.usda" ]]
"$PY" -B - "$RUN" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1])
m=json.loads((r/'multimodal_probe_validation_v15.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'multimodal_probe_candidate_v15.py')==m['script_sha256']
assert sha(r/'multimodal_scene_v5.usda')==m['scene_sha256']
assert sha(r/'multimodal_scene_v5.usda')=='950a84720a4304fd293cd5d5e8297d56b19dae178d127cf9db390d2da5e7a7ea'
assert f'E = Path("{r}")' in (r/'multimodal_probe_candidate_v15.py').read_text()
assert not (r/'multimodal_probe_results_v15').exists()
print('PREPARED_RUN_SOURCE_AND_SCENE=VERIFIED',flush=True)
PY
mkdir -m 700 "$OUT"
for d in home cache config data state tmp shm logs optix_cache cuda_cache; do mkdir -m 700 "$OUT/$d"; done
DEVICES=()
shopt -s nullglob
for node in /dev/nvidiactl /dev/nvidia0 /dev/nvidia-uvm /dev/nvidia-uvm-tools /dev/nvidia-modeset /dev/dri/card[0-9]* /dev/dri/renderD* /dev/random /dev/urandom /dev/null /dev/zero; do
    if [[ -c "$node" && ! -L "$node" ]]; then DEVICES+=(--dev-bind "$node" "$node"); fi
done
for node in /dev/nvidiactl /dev/nvidia0 /dev/random /dev/urandom /dev/null /dev/zero; do [[ -c "$node" && ! -L "$node" ]]; done
HOST_NETNS="$(readlink /proc/self/ns/net)"
SANDBOX=(/usr/bin/bwrap --die-with-parent --unshare-user --unshare-net --unshare-pid --unshare-ipc --ro-bind / / --bind "$RUN" "$RUN" --bind "$OUT" "$OUT" --bind "$OUT/tmp" /tmp --bind "$OUT/shm" /dev/shm --proc /proc)
SANDBOX+=("${DEVICES[@]}")
SANDBOX+=(--chdir "$RUN" --setenv HOME "$OUT/home" --setenv XDG_CACHE_HOME "$OUT/cache" --setenv XDG_CONFIG_HOME "$OUT/config" --setenv XDG_DATA_HOME "$OUT/data" --setenv XDG_STATE_HOME "$OUT/state" --setenv XDG_RUNTIME_DIR "$OUT/tmp" --setenv TMPDIR "$OUT/tmp" --setenv CUDA_CACHE_PATH "$OUT/cuda_cache" --setenv OPTIX_CACHE_PATH "$OUT/optix_cache" --setenv PYTHONDONTWRITEBYTECODE 1 --setenv PYTHONNOUSERSITE 1 --setenv TRUST_ROBOT_HOST_NETNS "$HOST_NETNS")
SAFE_ENV=(/usr/bin/env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 USER=kios LOGNAME=kios HOME="$OUT/home" XDG_CACHE_HOME="$OUT/cache" XDG_CONFIG_HOME="$OUT/config" XDG_DATA_HOME="$OUT/data" XDG_STATE_HOME="$OUT/state" XDG_RUNTIME_DIR="$OUT/tmp" TMPDIR="$OUT/tmp" CUDA_CACHE_PATH="$OUT/cuda_cache" OPTIX_CACHE_PATH="$OUT/optix_cache" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TRUST_ROBOT_HOST_NETNS="$HOST_NETNS" TRUST_ROBOT_SENSOR_PROBE_ENABLE=1)
timeout 45s "${SAFE_ENV[@]}" "${SANDBOX[@]}" /usr/bin/python3 -B -c '
import os,socket
w="/home/kios/TRUST_ROBOT_ALI"
for p in ("/",w,w+"/github_checkout_v15","/home/kios/isaacsim"):
 assert os.statvfs(p).f_flag & os.ST_RDONLY
assert os.readlink("/proc/self/ns/net")!=os.environ["TRUST_ROBOT_HOST_NETNS"]
assert {name for _,name in socket.if_nameindex()}=={"lo"}
print("PRIVATE_NETWORK_AND_READONLY_HOST=PASS",flush=True)
'
timeout 80s "$PY" -B - <<'PY'
import os,stat,subprocess,time
from pathlib import Path
def cmd(*a): return subprocess.check_output(a,text=True,timeout=15).strip()
def check(i):
 rows=cmd('nvidia-smi','--query-gpu=index,memory.free,utilization.gpu','--format=csv,noheader,nounits').splitlines()
 assert len(rows)==1
 gpu,free,util=map(int,(v.strip() for v in rows[0].split(',')))
 assert gpu==0 and free>=10500 and 0<=util<=10
 pids=[v.strip() for v in cmd('nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits').splitlines() if v.strip() and v.strip()!='No running processes found']
 if not pids: ident=('NONE',)
 else:
  assert len(pids)==1 and pids[0].isdigit()
  pid=int(pids[0]);p=Path('/proc')/str(pid)
  assert p.stat().st_uid==os.getuid()
  exe=os.readlink(p/'exe');assert exe=='/usr/libexec/gnome-remote-desktop-daemon'
  f=Path(exe).stat();assert stat.S_ISREG(f.st_mode) and f.st_uid==0 and not(f.st_mode&0o022)
  ident=(pid,cmd('ps','-p',str(pid),'-o','lstart='),exe)
 print(f'GPU_CHECK_{i}_PASS free_MiB={free} util_percent={util} background={ident}',flush=True)
 return ident
a=check(1);time.sleep(15);b=check(2);assert a==b
print('TWO_GPU_CHECKS=PASS',flush=True)
PY
set +e
timeout --signal=INT --kill-after=30s 240s "${SAFE_ENV[@]}" "${SANDBOX[@]}" "$I/python.sh" "$RUN/multimodal_probe_candidate_v15.py" > "$OUT/logs/runtime.log" 2>&1
RC=$?
set -e
echo "ISAAC_SIM_EXIT_CODE=$RC"
if [[ "$RC" != 0 ]] || ! grep -q 'MULTIMODAL_RUNTIME=PASS' "$OUT/logs/runtime.log" || grep -q 'SENSOR_RUNTIME_EXCEPTION=YES' "$OUT/logs/runtime.log"; then
    echo "RUNTIME_NOT_VALIDATED: inspect $OUT/logs/runtime.log" >&2
    exit 1
fi
"$PY" -B "$R/experiments/isaacsim_v16_recovery_v1/verify_local_recording.py" "$RUN"
echo 'RUNTIME_AND_OFFLINE_SENSOR_FILE_CHECKS=PASS'
echo 'CROSS_SENSOR_EXPOSURE_SYNC=UNVERIFIED'
echo 'PHYSICAL_GROUND_TRUTH=UNVERIFIED'
