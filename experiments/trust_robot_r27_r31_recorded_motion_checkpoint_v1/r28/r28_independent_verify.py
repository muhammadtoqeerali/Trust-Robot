"""R28 independent raw-byte extraction, brute-force NN/Kabsch and gate verifier."""
import hashlib,json,math,pathlib,struct,sys
import numpy as np

TOPIC='/velodyne_points'
N=512
SUBSETS=('linspace','cell_centers','random_seed_20261019','middle_window')
INITIALS=('identity','yaw_plus_5deg','x_plus_0p25m')

def need(ok,reason):
    if not ok:raise ValueError('R28_INDEPENDENT_DENIED:'+reason)
def sha(data):return hashlib.sha256(data).hexdigest()
def sha_file(p):return sha(pathlib.Path(p).read_bytes())
def index_set(width,name):
    if name=='linspace':return np.linspace(0,width-1,N,dtype=np.int64)
    if name=='cell_centers':return np.array([int((i+0.5)*width/N) for i in range(N)],dtype=np.int64)
    if name=='random_seed_20261019':return np.sort(np.random.default_rng(20261019).choice(width,size=N,replace=False)).astype(np.int64)
    if name=='middle_window':return np.arange((width-N)//2,(width-N)//2+N,dtype=np.int64)
    raise ValueError('UNKNOWN_SELECTION')
def unpack_xyz(message,decoder):
    c=decoder.Cursor(message);h=decoder.header(c)
    height,width,n=c.number(),c.number(),c.number()
    need(height==1 and N<=width<=500000 and n==6 and h['frame_id']=='velodyne','MSG_SHAPE')
    fields=[(c.text(256),c.number(),c.take(1)[0],c.number()) for _ in range(n)]
    need(fields[:3]==[('x',0,7,1),('y',4,7,1),('z',8,7,1)],'XYZ_FIELDS')
    endian=c.bool();step,row=c.number(),c.number();size=c.number()
    need(not endian and step==22 and row==22*width and size==row and size<=8*1024*1024,'XYZ_LAYOUT')
    raw=c.take(size).tobytes();dense=c.bool();c.done()
    need(dense,'DENSE')
    return raw,width,h

def brute_registration(prev,current,name):
    Q=np.eye(3);t=np.zeros(3)
    if name=='yaw_plus_5deg':
        a=np.deg2rad(5);Q=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
    elif name=='x_plus_0p25m':t[0]=0.25
    else:need(name=='identity','INIT')
    def nearest(points):
        diff=points[:,None,:]-prev[None,:,:]
        distance=np.einsum('ijk,ijk->ij',diff,diff)
        idx=np.argmin(distance,axis=1)
        return np.sqrt(distance[np.arange(N),idx]),idx
    start,_=nearest(current@Q.T+t)
    for _ in range(10):
        _,idx=nearest(current@Q.T+t)
        srcmean=current.mean(axis=0);dst=prev[idx];dstmean=dst.mean(axis=0)
        H=np.einsum('ni,nj->ij',current-srcmean,dst-dstmean)
        u,sv,vh=np.linalg.svd(H)
        correction=np.eye(3);correction[-1,-1]=np.linalg.det(vh.T@u.T)
        Q=vh.T@correction@u.T;t=dstmean-Q@srcmean
    end,idx=nearest(current@Q.T+t)
    target=prev[idx]
    H=np.einsum('ni,nj->ij',current-current.mean(axis=0),target-target.mean(axis=0))
    sv=np.linalg.svd(H,compute_uv=False)
    return Q,t,float(np.sqrt(np.mean(start**2))),float(np.sqrt(np.mean(end**2))),float(np.median(end)),sv

def verify(repo,bag,archive,r27_source,r27_report,r27_verify,report,output):
    sys.path.insert(0,str(archive/'r18'))
    import r18_decode as decoder
    r17p=archive/'r17/r17_recorded_index.json';r18p=archive/'r18/r18_bounded_recorded_samples.json'
    r17=json.loads(r17p.read_text());r18=json.loads(r18p.read_text());r27=json.loads(pathlib.Path(r27_report).read_text())
    d=json.loads(pathlib.Path(report).read_text())
    need(d['schema']=='TRUST_ROBOT_R28_RECORDED_LIDAR_SENSITIVITY_V1' and d['trajectory_id']=='room_02' and d['split']=='train','IDENTITY')
    need(d['github_baseline']=='d1c8aa7811619d096865f9b5f23a0ca7e940fa81','BASELINE')
    expected={'r17':sha_file(r17p),'r18':sha_file(r18p),'r27_source':sha_file(r27_source),
              'r27_report':sha_file(r27_report),'r27_independent_validation':sha_file(r27_verify)}
    need(d['upstream_sha256']==expected,'SOURCE_DIGESTS')
    need(d['authenticated_bag_sha256']==r17['file_sha256']==r18['recording_sha256']==r27['bag_sha256'],'BAG_LINEAGE')
    need(d['subsets']==list(SUBSETS) and d['initializations']==list(INITIALS) and
         d['points_per_scan_per_case']==512 and d['fixed_iterations']==10 and len(d['cases'])==12 and len(d['relative_to_baseline'])==12,'DESIGN')
    for k in ('observability_established','relative_pose_accuracy_established','physical_capture_time_verified','cross_modal_alignment_performed',
              'full_extrinsics_verified','health_training_authorized','m2dgr_scoring_authorized','raw_recording_modified','git_modified'):
        need(d[k] is False,'GATE:'+k)
    for k in ('candidate_factors_admitted','health_labels_generated'):
        need(type(d[k]) is int and d[k]==0,'ZERO:'+k)
    need(d['selection_policy']=='descriptive_only_no_quality_threshold','SCOPE')
    conn={x['id']:x for x in r17['connections']}
    objects=[]
    with pathlib.Path(bag).open('rb') as f:
        for i,s in enumerate(r18['samples'][TOPIC]):
            raw,compression=decoder.chunk_data(f,s['chunk_offset'])
            need(compression in r18['compression_methods'],'COMPRESSION')
            found=[]
            for cid,time,view in decoder.messages(raw,conn):
                if cid==s['connection_id'] and time==s['bag_record_time_ns'] and sha(view)==s['serialized_message_sha256']:
                    found.append(view.tobytes())
            need(len(found)==1 and len(found[0])==s['serialized_message_bytes'],'SOURCE_BYTES')
            data,width,h=unpack_xyz(found[0],decoder)
            need(sha(data)==s['point_payload_sha256'] and width==s['point_count'] and
                 h['header_stamp_ns']==s['header_stamp_ns'] and h['sequence']==s['sequence'],'POINT_CLOUD_SOURCE')
            objects.append((data,width))
    need(d['source_scan_point_counts']==[w for _,w in objects] and
         d['source_scan_message_hashes']==[s['serialized_message_sha256'] for s in r18['samples'][TOPIC]],'SCAN_LINKS')
    base=None;computed=[];max_rotation=0.;max_translation=0.;finals=[]
    for subset in SUBSETS:
        scans=[];hashes=[]
        for raw,width in objects:
            idx=index_set(width,subset)
            need(len(np.unique(idx))==N,'SELECTED_INDEX_UNIQUE')
            pts=np.array([struct.unpack_from('<fff',raw,int(j)*22) for j in idx],dtype='<f8')
            need(bool(np.isfinite(pts).all()),'SAMPLES_FINITE')
            sv=np.linalg.svd(pts-pts.mean(axis=0),compute_uv=False)
            rank=int(np.linalg.matrix_rank(pts-pts.mean(axis=0)))
            hashes.append({'indices_sha256':sha(idx.tobytes()),'xyz_f64le_sha256':sha(pts.tobytes()),
              'geometry':{'numerical_rank':rank,'singular_values':sv.tolist(),
                'smallest_over_largest':float(sv[-1]/sv[0]) if sv[0]>0 else 0.}})
            scans.append(pts)
        for init in INITIALS:
            i=len(computed);entry=d['cases'][i]
            need(entry['subset']==subset and entry['initial']==init,'ORDER')
            for a,b in zip(entry['selected_scans'],hashes):
                need(a['indices_sha256']==b['indices_sha256'] and a['xyz_f64le_sha256']==b['xyz_f64le_sha256'],'SAMPLE_HASH')
                for k in ('numerical_rank','singular_values','smallest_over_largest'):
                    need(np.allclose(a['geometry'][k],b['geometry'][k],atol=1e-8,rtol=1e-8),'GEOMETRY:'+k)
            Q,t,first,last,median,svals=brute_registration(scans[0],scans[1],init)
            reg=entry['registration']
            for name,a,b in (('rotation',reg['rotation_previous_from_current'],Q),('translation',reg['translation_previous_from_current_m'],t),
                ('initial_rmse',reg['initial_rmse_m'],first),('final_rmse',reg['final_rmse_m'],last),
                ('median',reg['final_median_nn_m'],median),('cross_svals',reg['cross_covariance_singular_values'],svals),
                ('ratio',reg['cross_covariance_ratio_min_max'],float(svals[-1]/svals[0]) if svals[0]>0 else 0.)):
                need(np.allclose(a,b,atol=2e-6,rtol=2e-6),'BRUTE:'+name+':'+str(i))
            need(reg['iterations']==10 and reg['is_pose_factor'] is False and reg['initialization']==init,'CASE_GATES')
            if base is None:base=(Q,t,last)
            rot_delta=math.degrees(math.acos(float(np.clip((np.trace(Q@base[0].T)-1)/2,-1,1))))
            trans_delta=float(np.linalg.norm(t-base[1])); rmse_delta=last-base[2]
            difference=d['relative_to_baseline'][i]
            need(difference['subset']==subset and difference['initial']==init and
                 np.allclose([difference['rotation_delta_deg'],difference['translation_delta_m'],difference['rmse_delta_m']],
                 [rot_delta,trans_delta,rmse_delta],atol=2e-5,rtol=2e-5),'DELTA:'+str(i))
            max_rotation=max(max_rotation,rot_delta);max_translation=max(max_translation,trans_delta)
            finals.append(last);computed.append(i)
    ex=d['sensitivity_extrema']
    for key,val in [('max_translation_delta_m',max_translation),('max_rotation_delta_deg',max_rotation),
                    ('min_final_rmse_m',min(finals)),('max_final_rmse_m',max(finals))]:
        need(np.allclose(ex[key],val,atol=2e-5,rtol=2e-5),'EXTREMUM:'+key)
    numeric=d['manufactured_numeric_geometry']
    need(numeric['planar_rank']==2 and numeric['line_rank']==1 and numeric['not_recorded_sensor_conditions'] is True,'NUMERIC_DEGENERACY')
    need(np.allclose(numeric['planar_values'][-1],0,atol=1e-8) and
         np.allclose(numeric['line_values'][1:],0,atol=1e-8),'NUMERIC_SINGULAR_VALUES')
    summary={'schema':'TRUST_ROBOT_R28_INDEPENDENT_RECORDED_SENSITIVITY_V1',
      'report_sha256':sha_file(report),'source_message_hashes_verified':2,'cases_recomputed':12,
      'registrations_computed_by':'independent_raw_struct_xyz_and_dense_bruteforce_nn_svd',
      'original_bag_modified':False,'real_pose_factors_admitted':0,
      'scientific_accuracy_qualified':False}
    with pathlib.Path(output).open('x') as f:json.dump(summary,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print('R28_INDEPENDENT_RECORDING_MESSAGES=2_RELOCATED')
    print('R28_INDEPENDENT_SAMPLE_HASHES=8_VERIFIED')
    print('R28_INDEPENDENT_BRUTE_FORCE_CASES=12_NUMERIC_MATCH')
    print('R28_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':verify(*(pathlib.Path(x) for x in sys.argv[1:9]))
