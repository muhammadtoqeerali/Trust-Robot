#!/usr/bin/env python3
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
        expected=1.55-float(sensor_positions[step-1,0])
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
