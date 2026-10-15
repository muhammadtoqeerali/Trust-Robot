#!/usr/bin/env python3
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
    assert os.geteuid()!=0 and __import__('pwd').getpwuid(os.geteuid()).pw_name == 'kios'
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
