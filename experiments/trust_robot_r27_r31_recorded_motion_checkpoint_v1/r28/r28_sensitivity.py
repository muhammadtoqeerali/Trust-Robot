"""Bounded R28 recorded LiDAR point-subset/initialization sensitivity, never a factor."""
import hashlib, json, math, pathlib, sys
import numpy as np
from scipy.spatial import cKDTree
from trust_robot.m2dgr_sensor_admission import load_frozen_snapshot, require_real_factor_execution, SensorAdmissionError

TOPIC='/velodyne_points'
N=512
STEPS=10
SUBSETS=('linspace','cell_centers','random_seed_20261019','middle_window')
INITIALS=('identity','yaw_plus_5deg','x_plus_0p25m')


def need(ok,reason):
    if not ok: raise ValueError('R28_DENIED:'+reason)
def sha(blob): return hashlib.sha256(blob).hexdigest()
def file_sha(path):
    hasher=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for part in iter(lambda:f.read(8*1024*1024),b''):hasher.update(part)
    return hasher.hexdigest()

def indices(width,kind):
    need(type(width) is int and width>=N and kind in SUBSETS,'SELECTION_INPUT')
    if kind=='linspace': idx=np.linspace(0,width-1,N,dtype=np.int64)
    elif kind=='cell_centers': idx=((np.arange(N,dtype=np.float64)+0.5)*width/N).astype(np.int64)
    elif kind=='random_seed_20261019': idx=np.sort(np.random.default_rng(20261019).choice(width,size=N,replace=False)).astype(np.int64)
    else: idx=np.arange((width-N)//2,(width-N)//2+N,dtype=np.int64)
    need(len(np.unique(idx))==N and idx.min()>=0 and idx.max()<width,'INDEX_UNIQUENESS')
    return idx

def initial(which):
    need(which in INITIALS,'INIT_NAME')
    Q=np.eye(3,dtype=np.float64);t=np.zeros(3)
    if which=='yaw_plus_5deg':
        angle=math.radians(5.0);c,s=math.cos(angle),math.sin(angle)
        Q=np.array([[c,-s,0.0],[s,c,0.0],[0,0,1.0]])
    if which=='x_plus_0p25m': t[0]=0.25
    return Q,t

def kabsch(source,dest):
    aa=source.mean(axis=0);bb=dest.mean(axis=0)
    H=(source-aa).T@(dest-bb)
    U,_,Vt=np.linalg.svd(H)
    D=np.diag([1.,1.,np.linalg.det(Vt.T@U.T)])
    Q=Vt.T@D@U.T;t=bb-Q@aa
    need(np.isfinite(Q).all() and np.isfinite(t).all() and abs(np.linalg.det(Q)-1)<1e-8,'KABSCH')
    return Q,t

def register(prev,now,start):
    need(prev.shape==now.shape==(N,3) and np.isfinite(prev).all() and np.isfinite(now).all(),'REGISTRATION_INPUT')
    Q,t=initial(start);tree=cKDTree(prev)
    start_d,_=tree.query(now@Q.T+t,k=1,workers=1)
    for _ in range(STEPS):
        _,matches=tree.query(now@Q.T+t,k=1,workers=1)
        Q,t=kabsch(now,prev[matches])
    d,match=tree.query(now@Q.T+t,k=1,workers=1)
    need(bool(np.isfinite(d).all()),'RESIDUALS')
    C=(now-now.mean(axis=0)).T@(prev[match]-prev[match].mean(axis=0))
    sv=np.linalg.svd(C,compute_uv=False)
    return {'initialization':start,'rotation_previous_from_current':Q.tolist(),
       'translation_previous_from_current_m':t.tolist(),
       'initial_rmse_m':float(np.sqrt(np.mean(start_d**2))),
       'final_rmse_m':float(np.sqrt(np.mean(d**2))),
       'final_median_nn_m':float(np.median(d)),
       'cross_covariance_singular_values':sv.tolist(),
       'cross_covariance_ratio_min_max':float(sv[-1]/sv[0]) if sv[0]>0 else 0.,
       'iterations':STEPS,'is_pose_factor':False}

def numerical_geometry(xyz):
    need(xyz.shape==(N,3) and np.isfinite(xyz).all(),'GEOMETRY_INPUT')
    sv=np.linalg.svd(xyz-xyz.mean(axis=0),compute_uv=False)
    return {'numerical_rank':int(np.linalg.matrix_rank(xyz-xyz.mean(axis=0))),
       'singular_values':sv.tolist(),
       'smallest_over_largest':float(sv[-1]/sv[0]) if sv[0]>0 else 0.}

def false_gates(report):
    for k in ('real_sensor_factor_execution_authorized','physical_capture_semantics_verified',
              'cross_modal_synchronization_verified','full_extrinsics_verified',
              'independent_ground_truth_scored','m2dgr_scoring_authorized','health_training_authorized',
              'raw_sensor_modified','git_modified'):
        need(report.get(k) is False,'UPSTREAM_GATE:'+k)
    for k in ('new_raw_sensor_acquisitions','real_pose_factors_generated','health_labels_generated'):
        need(type(report.get(k)) is int and report[k]==0,'UPSTREAM_ZERO:'+k)

def recorded_scans(bag,r17,r18,r27,decoder,prior):
    need(r17['trajectory_id']==r18['trajectory_id']==r27['trajectory_id']=='room_02' and r18['split']==r27['split']=='train','TRAIN_BOUND')
    need(r17['file_sha256']==r18['recording_sha256']==r27['bag_sha256'],'BAG_CHAIN')
    need(len(r18['samples'][TOPIC])==len(r27['scans'])==2,'SAMPLE_SCOPE')
    indexed={i['id']:i for i in r17['connections']}
    outputs=[]
    with pathlib.Path(bag).open('rb') as f:
        for k,s in enumerate(r18['samples'][TOPIC]):
            raw,compression=decoder.chunk_data(f,s['chunk_offset'])
            need(compression in r18['compression_methods'],'COMPRESSION')
            found=[]
            for cid,time,body in decoder.messages(raw,indexed):
                if (cid,time,sha(body))==(s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256']):
                    found.append(body.tobytes())
            need(len(found)==1 and len(found[0])==s['serialized_message_bytes'],'RELOCATION')
            xyz,metadata=prior.pointcloud(found[0],decoder)
            need(metadata['points']==s['point_count'] and metadata['point_payload_sha256']==s['point_payload_sha256'],'PAYLOAD_DIGEST')
            for key in ('header_stamp_ns','frame_id','sequence'):
                need(metadata[key]==s[key],'HEADER_'+key)
            for key in ('chunk_offset','connection_id','bag_record_time_ns','serialized_message_sha256','serialized_message_bytes','header_stamp_ns','frame_id'):
                need(r27['scans'][k][key]==s[key],'R27_SCAN_LINK_'+key)
            base=indices(len(xyz),'linspace');v=xyz[base]
            need(sha(base.tobytes())==r27['scans'][k]['selected_indices_sha256'] and sha(v.astype('<f8').tobytes())==r27['scans'][k]['selected_xyz_float64_le_sha256'],'R27_XYZ_HASH')
            outputs.append(xyz)
    return outputs

def baseline_check(ref,entry):
    d=ref['registration_diagnostic']
    for name,a,b in (('R',entry['rotation_previous_from_current'],d['rotation_previous_from_current']),
       ('t',entry['translation_previous_from_current_m'],d['translation_previous_from_current_m']),
       ('identity',entry['initial_rmse_m'],d['identity_nearest_neighbor_rmse_m']),
       ('final',entry['final_rmse_m'],d['candidate_nearest_neighbor_rmse_m']),
       ('median',entry['final_median_nn_m'],d['candidate_median_nn_distance_m'])):
        need(np.allclose(a,b,rtol=1e-6,atol=1e-6),'R27_BASELINE_'+name)

def run(repo,bag,archive,r27_source,r27_path,r27_verify_path,output):
    sys.path.insert(0,str(archive/'r18'))
    sys.path.insert(0,str(pathlib.Path(r27_source).parent))
    import r18_decode as decoder
    import r27_lidar_motion as prior
    r17p=archive/'r17/r17_recorded_index.json';r18p=archive/'r18/r18_bounded_recorded_samples.json'
    r17=json.loads(r17p.read_text());r18=json.loads(r18p.read_text())
    r27=json.loads(pathlib.Path(r27_path).read_text())
    r27check=json.loads(pathlib.Path(r27_verify_path).read_text())
    need(r27['schema']=='TRUST_ROBOT_R27_TRAIN_LIDAR_SINGLE_PAIR_REGISTRATION_DIAGNOSTIC_V1','R27_SCHEMA')
    need(r27['r17_report_sha256']==file_sha(r17p) and r27['r18_report_sha256']==file_sha(r18p),'LINEAGE')
    need(r27['github_parent']=='d1c8aa7811619d096865f9b5f23a0ca7e940fa81','BASELINE_COMMIT')
    false_gates(r27)
    need(r27check['schema']=='TRUST_ROBOT_R27_INDEPENDENT_NUMERICAL_CHECK_V1' and
       r27check['source_report_sha256']==file_sha(r27_path) and
       r27check['authenticated_scans_relocated']==2 and
       r27check['brute_force_kabsch_numerically_agrees'] is True and
       r27check['scientific_real_factor_execution_authorized'] is False,'R27_INDEPENDENT')
    need(file_sha(bag)==r27['bag_sha256'],'ORIGINAL_BAG_HASH')
    snapshot=load_frozen_snapshot(repo)
    need(snapshot['by_id']['room_02']['split']=='train' and all(v is False for v in snapshot['scientific_gates'].values()),'PHYSICAL_GATES')
    try:require_real_factor_execution(snapshot,'room_02')
    except SensorAdmissionError:pass
    else:raise ValueError('R28_DENIED:REAL_FACTOR_GATE_OPEN')
    clouds=recorded_scans(bag,r17,r18,r27,decoder,prior)
    experiments=[]
    for subset in SUBSETS:
        pts=[clouds[i][indices(len(clouds[i]),subset)] for i in (0,1)]
        hashes=[{'indices_sha256':sha(indices(len(clouds[i]),subset).tobytes()),
          'xyz_f64le_sha256':sha(np.asarray(pts[i],dtype='<f8').tobytes()),
          'geometry':numerical_geometry(pts[i])} for i in (0,1)]
        for init in INITIALS:
            d=register(pts[0],pts[1],init)
            if subset=='linspace' and init=='identity': baseline_check(r27,d)
            experiments.append({'subset':subset,'initial':init,'selected_scans':hashes,'registration':d})
    need(len(experiments)==12,'CASE_COUNT')
    base=experiments[0]['registration']
    bR=np.asarray(base['rotation_previous_from_current']);bt=np.asarray(base['translation_previous_from_current_m'])
    deltas=[]
    for item in experiments:
        q=np.asarray(item['registration']['rotation_previous_from_current']);t=np.asarray(item['registration']['translation_previous_from_current_m'])
        cosine=(np.trace(q@bR.T)-1.)/2.
        angle=math.degrees(math.acos(float(np.clip(cosine,-1.,1.))))
        deltas.append({'subset':item['subset'],'initial':item['initial'],
           'rotation_delta_deg':float(angle),'translation_delta_m':float(np.linalg.norm(t-bt)),
           'rmse_delta_m':float(item['registration']['final_rmse_m']-base['final_rmse_m'])})
    example=clouds[0][indices(len(clouds[0]),'linspace')]
    planar=example.copy();planar[:,2]=0.0
    line=np.zeros_like(example);line[:,0]=np.arange(N,dtype=np.float64)
    pg=numerical_geometry(planar);lg=numerical_geometry(line)
    need(pg['numerical_rank']==2 and lg['numerical_rank']==1,'DEGENERACY_FIXTURES')
    out={'schema':'TRUST_ROBOT_R28_RECORDED_LIDAR_SENSITIVITY_V1','trajectory_id':'room_02','split':'train',
       'github_baseline':'d1c8aa7811619d096865f9b5f23a0ca7e940fa81',
       'authenticated_bag_sha256':r27['bag_sha256'],
       'upstream_sha256':{'r17':file_sha(r17p),'r18':file_sha(r18p),'r27_source':file_sha(r27_source),
                          'r27_report':file_sha(r27_path),'r27_independent_validation':file_sha(r27_verify_path)},
       'source_scan_message_hashes':[s['serialized_message_sha256'] for s in r18['samples'][TOPIC]],
       'source_scan_point_counts':[len(c) for c in clouds],
       'subsets':list(SUBSETS),'initializations':list(INITIALS),'points_per_scan_per_case':N,
       'fixed_iterations':STEPS,'cases':experiments,'relative_to_baseline':deltas,
       'sensitivity_extrema':{'max_translation_delta_m':max(x['translation_delta_m'] for x in deltas),
                             'max_rotation_delta_deg':max(x['rotation_delta_deg'] for x in deltas),
                             'min_final_rmse_m':min(x['registration']['final_rmse_m'] for x in experiments),
                             'max_final_rmse_m':max(x['registration']['final_rmse_m'] for x in experiments)},
       'manufactured_numeric_geometry':{'planar_rank':pg['numerical_rank'],'line_rank':lg['numerical_rank'],
           'planar_values':pg['singular_values'],'line_values':lg['singular_values'],
           'not_recorded_sensor_conditions':True},
       'selection_policy':'descriptive_only_no_quality_threshold','observability_established':False,
       'relative_pose_accuracy_established':False,'physical_capture_time_verified':False,
       'cross_modal_alignment_performed':False,'full_extrinsics_verified':False,
       'candidate_factors_admitted':0,'health_labels_generated':0,'health_training_authorized':False,
       'm2dgr_scoring_authorized':False,'raw_recording_modified':False,'git_modified':False}
    with pathlib.Path(output).open('x',encoding='utf8') as f:json.dump(out,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    print('R28_REAL_LIDAR_SCANS=2_HASH_BOUND')
    print('R28_SUBSETS=4_INITIALIZATIONS=3_CASES=12')
    print('R28_R27_IDENTITY_BASELINE=RECOMPUTED_AND_MATCHED')
    print('R28_NUMERIC_PLANAR_AND_LINE_RANKS=2_1')
    print('R28_MAX_TRANSLATION_SPREAD_M='+format(out['sensitivity_extrema']['max_translation_delta_m'],'.6f'))
    print('R28_MAX_ROTATION_SPREAD_DEG='+format(out['sensitivity_extrema']['max_rotation_delta_deg'],'.6f'))
    print('R28_RELATIVE_POSE_ACCURACY=NOT_ESTABLISHED')

if __name__=='__main__':run(*(pathlib.Path(x) for x in sys.argv[1:8]))
