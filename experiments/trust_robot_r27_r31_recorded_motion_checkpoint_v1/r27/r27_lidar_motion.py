"""Two genuine TRAIN LiDAR scans -> bounded diagnostic registration; NO factor."""
import hashlib
import json
import pathlib
import sys
from types import SimpleNamespace
import numpy as np
from scipy.spatial import cKDTree
from trust_robot import lidar_frontend as lf
from trust_robot.m2dgr_sensor_admission import (
    load_frozen_snapshot, require_real_factor_execution, SensorAdmissionError)

N = 512
STEPS = 10
TOPIC = '/velodyne_points'

def need(ok, name):
    if not ok:
        raise ValueError('R27_DENIED:' + name)

def file_sha(path):
    d = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for part in iter(lambda: f.read(8 * 1024 * 1024), b''):
            d.update(part)
    return d.hexdigest()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pointcloud(body, decoder):
    c = decoder.Cursor(body)
    h = decoder.header(c)
    height, width, nf = c.number(), c.number(), c.number()
    need(nf == 6, 'POINTFIELD_COUNT')
    fields = []
    for _ in range(nf):
        fields.append(SimpleNamespace(name=c.text(256), offset=c.number(),
                                      datatype=c.take(1)[0], count=c.number()))
    big = c.bool()
    step, row_step = c.number(), c.number()
    size = c.number()
    need(0 < size <= 8*1024*1024, 'POINT_PAYLOAD_BUDGET')
    raw = c.take(size).tobytes()
    dense = c.bool()
    c.done()
    msg = SimpleNamespace(
        header=SimpleNamespace(frame_id=h['frame_id'], stamp=SimpleNamespace(
            secs=h['header_stamp_ns']//1_000_000_000,
            nsecs=h['header_stamp_ns']%1_000_000_000)),
        height=height, width=width, fields=fields, is_bigendian=big,
        point_step=step, row_step=row_step, data=raw, is_dense=dense)
    xyz = lf.decode_m2dgr_velodyne_xyz(msg)
    need(xyz.shape == (width,3) and np.isfinite(xyz).all(), 'FINITE_XYZ')
    return xyz, {'header_stamp_ns':h['header_stamp_ns'], 'frame_id':h['frame_id'],
                 'sequence':h['sequence'], 'points':width,
                 'point_payload_sha256':sha(raw), 'is_dense':dense}

def select_points(xyz):
    need(type(xyz) is np.ndarray and xyz.ndim == 2 and xyz.shape[1] == 3
         and xyz.shape[0] >= N and bool(np.isfinite(xyz).all()), 'SCAN_MATRIX')
    idx = np.linspace(0, xyz.shape[0]-1, N, dtype=np.int64)
    need(len(np.unique(idx)) == N, 'SUBSET_UNIQUE')
    return np.ascontiguousarray(xyz[idx], dtype=np.float64), idx

def rigid(src, dst):
    need(src.shape == dst.shape and src.ndim == 2 and src.shape[1] == 3
         and len(src) == N, 'KABSCH_INPUT_SHAPE')
    a, b = src.mean(axis=0), dst.mean(axis=0)
    cov = (src-a).T @ (dst-b)
    U, _, Vt = np.linalg.svd(cov)
    s = np.diag([1.,1., np.linalg.det(Vt.T @ U.T)])
    R = Vt.T @ s @ U.T
    t = b - R@a
    need(np.isfinite(R).all() and np.isfinite(t).all()
         and abs(np.linalg.det(R)-1.) < 1e-8, 'KABSCH_SOLUTION')
    return R, t

def candidate(prev, current):
    need(prev.shape == current.shape == (N,3), 'REGISTRATION_SHAPE')
    need(np.isfinite(prev).all() and np.isfinite(current).all(), 'REGISTRATION_NONFINITE')
    tree = cKDTree(prev)
    R = np.eye(3)
    t = np.zeros(3)
    identity_distances, _ = tree.query(current, k=1, workers=1)
    need(np.isfinite(identity_distances).all(), 'BASELINE_DISTANCES')
    for _ in range(STEPS):
        transformed = current @ R.T + t
        _, indices = tree.query(transformed, k=1, workers=1)
        R, t = rigid(current, prev[indices])
    final_d, _ = tree.query(current @ R.T + t, k=1, workers=1)
    need(np.isfinite(final_d).all(), 'FINAL_DISTANCES')
    return {
        'fixed_iterations': STEPS,
        'deterministic_points_per_scan': N,
        'rotation_previous_from_current': R.tolist(),
        'translation_previous_from_current_m': t.tolist(),
        'identity_nearest_neighbor_rmse_m':float(np.sqrt(np.mean(identity_distances**2))),
        'candidate_nearest_neighbor_rmse_m':float(np.sqrt(np.mean(final_d**2))),
        'candidate_median_nn_distance_m':float(np.median(final_d)),
        'candidate_max_nn_distance_m':float(np.max(final_d)),
        'determinant':float(np.linalg.det(R)),
        'convergence_claimed':False,
        'independent_pose_accuracy_claimed':False,
        'physical_scan_time_qualified':False,
        'candidate_registered_as_factor':False,
    }

def observations(bag, r17, r18, decoder):
    need(r17['schema']=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1'
         and r18['schema']=='TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1', 'PRIOR_SCHEMA')
    need(r17['trajectory_id']==r18['trajectory_id']=='room_02' and r18['split']=='train', 'TRAIN')
    need(r17['file_sha256']==r18['recording_sha256'], 'BAG_LINEAGE')
    need(set(r18['samples']) == set(decoder.NEEDED), 'FOUR_STREAMS')
    need(r18['physical_sync_verified'] is False and r18['extrinsics_verified'] is False
         and r18['real_pose_factors_generated']==0, 'PRIOR_ADMISSION')
    need(len(r18['samples'][TOPIC])==2, 'LIDAR_PAIR_SAMPLES')
    indexed = {x['id']:x for x in r17['connections']}
    refs = r18['samples'][TOPIC]
    need(len({x['chunk_offset'] for x in refs})==2, 'DISTINCT_CHUNKS')
    by_offset = {x['chunk_offset']:x for x in refs}
    resolved={}
    with pathlib.Path(bag).open('rb') as f:
        for offset in sorted(by_offset):
            s=by_offset[offset]
            raw, mode = decoder.chunk_data(f, offset)
            need(mode in r18['compression_methods'], 'CHUNK_COMPRESSION')
            for cid, stamp, view in decoder.messages(raw, indexed):
                digest=sha(view)
                if (cid,stamp,digest)!=(s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256']):
                    continue
                need(offset not in resolved and len(view)==s['serialized_message_bytes'], 'SOURCE_DUPLICATION')
                need(indexed[cid]['topic']==TOPIC and indexed[cid]['message_type']=='sensor_msgs/PointCloud2', 'LIDAR_ID')
                xyz, meta = pointcloud(view.tobytes(), decoder)
                for key in ('header_stamp_ns','frame_id','sequence'):
                    need(meta[key]==s[key], 'LIDAR_HEADER_'+key)
                need(meta['point_payload_sha256']==s['point_payload_sha256']
                     and meta['points']==s['point_count'], 'SOURCE_POINT_BYTES')
                used, idx=select_points(xyz)
                resolved[offset]=(used, {
                    'chunk_offset':offset, 'connection_id':cid,
                    'bag_record_time_ns':stamp,
                    'serialized_message_sha256':digest,
                    'serialized_message_bytes':len(view),
                    'header_stamp_ns':meta['header_stamp_ns'],
                    'frame_id':meta['frame_id'],
                    'point_count_total':meta['points'],
                    'selected_point_count':N,
                    'selected_indices_sha256':sha(idx.tobytes()),
                    'selected_xyz_float64_le_sha256':sha(used.astype('<f8').tobytes()),
                })
    need(len(resolved)==2, 'REAL_PAIR_NOT_RELOCATED')
    return [resolved[s['chunk_offset']] for s in refs]

def main():
    repo, bag, arc, result = (pathlib.Path(x) for x in sys.argv[1:5])
    sys.path.insert(0,str(arc/'r18'))
    import r18_decode as decoder
    r17p=arc/'r17/r17_recorded_index.json'
    r18p=arc/'r18/r18_bounded_recorded_samples.json'
    r17=json.loads(r17p.read_text())
    r18=json.loads(r18p.read_text())
    need(file_sha(bag)==r17['file_sha256'], 'ORIGINAL_BAG_SHA')
    snapshot=load_frozen_snapshot(repo)
    need(snapshot['by_id']['room_02']['split']=='train'
         and all(v is False for v in snapshot['scientific_gates'].values()), 'PHYSICAL_GATES')
    try: require_real_factor_execution(snapshot, 'room_02')
    except SensorAdmissionError: pass
    else: raise ValueError('R27_DENIED:UNEXPECTED_ADMISSION')
    scan_pair=observations(bag,r17,r18,decoder)
    computed=candidate(scan_pair[0][0], scan_pair[1][0])
    payload={
        'schema':'TRUST_ROBOT_R27_TRAIN_LIDAR_SINGLE_PAIR_REGISTRATION_DIAGNOSTIC_V1',
        'trajectory_id':'room_02', 'split':'train',
        'github_parent':'d1c8aa7811619d096865f9b5f23a0ca7e940fa81',
        'bag_sha256':r17['file_sha256'],
        'r17_report_sha256':file_sha(r17p),
        'r18_report_sha256':file_sha(r18p),
        'sampling_scope':'first_two_authenticated_lidar_messages_from_distinct_indexed_chunks',
        'selected_index_rule':'linspace_512_indices_each_scan',
        'algorithm':'bounded_10_iteration_identity_initialized_point_to_point_nearest_neighbor_kabsch',
        'registration_orientation':'previous_lidar_T_current_lidar_DIAGNOSTIC_ONLY',
        'scans':[x[1] for x in scan_pair],
        'registration_diagnostic':computed,
        'new_raw_sensor_acquisitions':0,
        'real_pose_factors_generated':0,
        'health_labels_generated':0,
        'real_sensor_factor_execution_authorized':False,
        'physical_capture_semantics_verified':False,
        'cross_modal_synchronization_verified':False,
        'full_extrinsics_verified':False,
        'independent_ground_truth_scored':False,
        'm2dgr_scoring_authorized':False,
        'health_training_authorized':False,
        'raw_sensor_modified':False,
        'git_modified':False,
    }
    with result.open('x',encoding='utf8') as f:
        json.dump(payload,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')
    print('R27_REAL_LIDAR_SCANS=2_EXACT_SOURCE_HASH_VERIFIED')
    print('R27_SOURCE_POINT_COUNTS='+','.join(str(x[1]['point_count_total']) for x in scan_pair))
    print('R27_DETERMINISTIC_POINTS_PER_SCAN=512')
    print('R27_REGISTRATION_ITERATIONS=10_FIXED')
    print('R27_IDENTITY_RMSE_M='+format(computed['identity_nearest_neighbor_rmse_m'],'.6f'))
    print('R27_CANDIDATE_RMSE_M='+format(computed['candidate_nearest_neighbor_rmse_m'],'.6f'))
    print('R27_DIAGNOSTIC_MOTION_CANDIDATE=PRODUCED_NOT_ADMITTED')

if __name__=='__main__':
    main()
