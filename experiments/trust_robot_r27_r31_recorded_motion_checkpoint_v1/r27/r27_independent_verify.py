"""Independently revisit recorded messages, extract XYZ and brute-force Kabsch."""
import hashlib
import json
import pathlib
import struct
import sys
import numpy as np

TOPIC='/velodyne_points'
N=512

def need(ok,msg):
    if not ok:raise ValueError('R27_INDEPENDENT_FAIL:'+msg)

def sha(blob):return hashlib.sha256(blob).hexdigest()

def read_scan(body, decoder):
    c=decoder.Cursor(body)
    h=decoder.header(c)
    height,width,n=c.number(),c.number(),c.number()
    need(height==1 and width>=N and n==6 and h['frame_id']=='velodyne','FORMAT')
    fields=[]
    for _ in range(n):
        fields.append((c.text(256),c.number(),c.take(1)[0],c.number()))
    need(fields[:3]==[('x',0,7,1),('y',4,7,1),('z',8,7,1)],'XYZ_FIELDS')
    endian=c.bool();step,row=c.number(),c.number();ns=c.number()
    need(not endian and step==22 and row==width*22 and ns==row,'BYTES')
    raw=c.take(ns).tobytes()
    dense=c.bool();c.done()
    need(dense,'LIDAR_DENSITY')
    indexes=np.linspace(0,width-1,N,dtype=np.int64)
    xyz=np.empty((N,3),dtype='<f8')
    for i,j in enumerate(indexes):
        xyz[i]=struct.unpack_from('<fff',raw,int(j)*22)
    need(bool(np.isfinite(xyz).all()),'NONFINITE')
    return xyz,indexes,dict(header_stamp_ns=h['header_stamp_ns'],
         frame_id=h['frame_id'], point_count_total=width)

def matrix(src,dst):
    a,b=src.mean(axis=0),dst.mean(axis=0)
    H=np.einsum('ni,nj->ij',src-a,dst-b)
    u,sv,vh=np.linalg.svd(H)
    diag=np.eye(3);diag[2,2]=np.sign(np.linalg.det(vh.T@u.T))
    Q=vh.T@diag@u.T
    t=b-Q@a
    need(np.isfinite(Q).all() and np.isfinite(t).all(),'SVD')
    return Q,t

def brute(prev,current):
    Q=np.eye(3);t=np.zeros(3)
    def nn(q):
        dist2=np.sum((q[:,None,:]-prev[None,:,:])**2,axis=2)
        idx=np.argmin(dist2,axis=1)
        return np.sqrt(dist2[np.arange(N),idx]),idx
    start,_=nn(current)
    for _ in range(10):
        _,ind=nn(current@Q.T+t)
        Q,t=matrix(current,prev[ind])
    residual,_=nn(current@Q.T+t)
    return Q,t,float(np.sqrt(np.mean(start**2))),float(np.sqrt(np.mean(residual**2))),float(np.median(residual)),float(residual.max())

def verify(repo,bag,arc,report,output):
    sys.path.insert(0,str(arc/'r18'))
    import r18_decode as decoder
    recorded=json.loads(pathlib.Path(report).read_text())
    r17p=arc/'r17/r17_recorded_index.json'
    r18p=arc/'r18/r18_bounded_recorded_samples.json'
    r17=json.loads(r17p.read_text());r18=json.loads(r18p.read_text())
    need(recorded['schema']=='TRUST_ROBOT_R27_TRAIN_LIDAR_SINGLE_PAIR_REGISTRATION_DIAGNOSTIC_V1' and
         recorded['trajectory_id']=='room_02' and recorded['split']=='train','REPORT_SCOPE')
    need(recorded['bag_sha256']==r17['file_sha256']==r18['recording_sha256'],'SOURCE_SHA')
    need(recorded['r17_report_sha256']==sha(r17p.read_bytes()) and
         recorded['r18_report_sha256']==sha(r18p.read_bytes()),'SOURCE_REPORTS')
    need(recorded['github_parent']=='d1c8aa7811619d096865f9b5f23a0ca7e940fa81','BASELINE')
    need(recorded['algorithm']=='bounded_10_iteration_identity_initialized_point_to_point_nearest_neighbor_kabsch', 'ALGORITHM')
    for k in ('real_sensor_factor_execution_authorized','physical_capture_semantics_verified',
              'cross_modal_synchronization_verified','full_extrinsics_verified',
              'independent_ground_truth_scored','m2dgr_scoring_authorized',
              'health_training_authorized','raw_sensor_modified','git_modified'):
        need(recorded[k] is False,'BOUNDARY_'+k)
    for k in ('new_raw_sensor_acquisitions','real_pose_factors_generated','health_labels_generated'):
        need(type(recorded[k]) is int and recorded[k]==0,'ZERO_'+k)
    need(len(recorded['scans'])==2 and recorded['scans'][0]['chunk_offset']!=recorded['scans'][1]['chunk_offset'],'TWO_SCANS')
    conn={x['id']:x for x in r17['connections']}
    expected=r18['samples'][TOPIC]
    observations=[]
    with pathlib.Path(bag).open('rb') as f:
        for ix,s in enumerate(expected):
            off=s['chunk_offset']
            raw,mode=decoder.chunk_data(f,off)
            need(mode in r18['compression_methods'],'COMPRESSION')
            found=[]
            for cid,bag_time,view in decoder.messages(raw,conn):
                if (cid,bag_time,sha(view))==(s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256']):
                    found.append(bytes(view))
            need(len(found)==1,'RELOCATION_'+str(ix))
            xyz,point_indices,info=read_scan(found[0],decoder)
            bound=recorded['scans'][ix]
            need(all(bound[k]==s[k] for k in ('chunk_offset','connection_id','bag_record_time_ns','serialized_message_sha256','serialized_message_bytes','header_stamp_ns','frame_id')),'SOURCE_IDENTITIES')
            need(bound['point_count_total']==info['point_count_total'] and bound['selected_point_count']==N,'POINT_COUNTS')
            need(bound['selected_indices_sha256']==sha(point_indices.tobytes()) and
                 bound['selected_xyz_float64_le_sha256']==sha(xyz.astype('<f8').tobytes()),'SELECTED_XYZ_DIGEST')
            observations.append(xyz)
    Q,t,before,after,median,maxd=brute(*observations)
    c=recorded['registration_diagnostic']
    need(c['fixed_iterations']==10 and c['deterministic_points_per_scan']==N and
         c['convergence_claimed'] is False and c['candidate_registered_as_factor'] is False and
         c['independent_pose_accuracy_claimed'] is False and c['physical_scan_time_qualified'] is False,'SCOPE')
    comparisons=[
        (np.asarray(c['rotation_previous_from_current']),Q,'ROTATION'),
        (np.asarray(c['translation_previous_from_current_m']),t,'TRANSLATION'),
        (c['identity_nearest_neighbor_rmse_m'],before,'INITIAL_RMSE'),
        (c['candidate_nearest_neighbor_rmse_m'],after,'FINAL_RMSE'),
        (c['candidate_median_nn_distance_m'],median,'MEDIAN'),
        (c['candidate_max_nn_distance_m'],maxd,'MAX'),
        (c['determinant'],float(np.linalg.det(Q)),'DETERMINANT')
    ]
    for x,y,name in comparisons:
        need(np.allclose(x,y,atol=1e-6,rtol=1e-6),'BRUTE_FORCE_'+name)
    summary={
        'schema':'TRUST_ROBOT_R27_INDEPENDENT_NUMERICAL_CHECK_V1',
        'source_report_sha256':sha(pathlib.Path(report).read_bytes()),
        'authenticated_scans_relocated':2,'sampled_xyz_points_per_scan':N,
        'registration_recomputed_by':'numpy_pairwise_distance_argmin_and_independent_svd',
        'brute_force_kabsch_numerically_agrees':True,
        'scientific_real_factor_execution_authorized':False,
        'ground_truth_pose_scored':False,
    }
    with pathlib.Path(output).open('x',encoding='utf-8') as f:
        json.dump(summary,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    print('R27_INDEPENDENT_RECORDED_SOURCE_HASHES=2_VERIFIED')
    print('R27_INDEPENDENT_XYZ_SELECTION=1024_POINTS_VERIFIED')
    print('R27_INDEPENDENT_BRUTE_FORCE_REGISTRATION=NUMERIC_MATCH')
    print('R27_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':
    verify(*(pathlib.Path(x) for x in sys.argv[1:6]))
