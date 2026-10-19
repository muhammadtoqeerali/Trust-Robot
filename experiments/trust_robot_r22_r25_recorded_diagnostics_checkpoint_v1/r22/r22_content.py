"""TRAIN-only real sample content diagnostics; no feature or pose-factor admission."""
import hashlib, json, math, pathlib, struct, sys
import cv2
import numpy as np

def need(ok, reason):
    if not ok: raise ValueError('R22_DENIED:' + reason)

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    d=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): d.update(chunk)
    return d.hexdigest()

def image_diagnostic(image_bytes):
    need(type(image_bytes) is bytes and 64<=len(image_bytes)<=4_194_304, 'IMAGE_COMPRESSED_BOUNDS')
    need(image_bytes.startswith(b'\xff\xd8') and image_bytes.endswith(b'\xff\xd9'), 'JPEG_MARKERS')
    img=cv2.imdecode(np.frombuffer(image_bytes,dtype=np.uint8),cv2.IMREAD_GRAYSCALE)
    need(img is not None and img.ndim==2 and img.dtype==np.uint8,'JPEG_DECODE')
    height,width=img.shape
    need(1<=height<=4096 and 1<=width<=4096 and width*height<=16_000_000,'IMAGE_SIZE')
    mean,std=cv2.meanStdDev(img)
    return {'width':int(width),'height':int(height),'decoded_pixel_count':int(img.size),
        'grayscale_mean':float(mean[0,0]),'grayscale_stddev':float(std[0,0]),
        'grayscale_min':int(img.min()),'grayscale_max':int(img.max()),
        'jpeg_payload_sha256':sha(image_bytes)}

def imu_diagnostic(raw):
    need(type(raw) is bytes and len(raw)==296,'IMU_FIXED_37_DOUBLE_BYTES')
    vals=struct.unpack('<37d',raw)
    need(all(math.isfinite(v) for v in vals),'NONFINITE_IMU_FIELD')
    orientation=vals[:4]; angular=vals[13:16]; linear=vals[25:28]
    return {'orientation_norm':math.sqrt(sum(x*x for x in orientation)),
        'angular_velocity_norm_rad_s':math.sqrt(sum(x*x for x in angular)),
        'linear_acceleration_norm_m_s2':math.sqrt(sum(x*x for x in linear)),
        'orientation_covariance_unknown_sentinel': vals[4] == -1.0,
        'angular_covariance_unknown_sentinel': vals[16] == -1.0,
        'linear_covariance_unknown_sentinel': vals[28] == -1.0}

def lidar_diagnostic(binary, descriptors, width, height, point_step, row_step, bigendian):
    need(type(binary) is bytes and 0 < len(binary)<=8*1024*1024,'LIDAR_PAYLOAD_BYTES')
    need(type(width) is int and 3<=width<=500_000 and height==1,'LIDAR_UNORGANIZED')
    need(point_step==22 and row_step==width*22 and not bigendian and len(binary)==row_step,'LIDAR_CONTIGUOUS')
    need(type(descriptors) is list and [f.get('name') for f in descriptors]==
         ['x','y','z','intensity','ring','time'],'LIDAR_FIELDS')
    for i,name in enumerate(('x','y','z')):
        f=descriptors[i]
        need(f.get('name')==name and f.get('offset')==4*i and f.get('datatype')==7 and f.get('count')==1,'XYZ_LAYOUT')
    # Explicit read-only strided views; never register scans or filter estimator input.
    xyz=np.column_stack([np.ndarray(shape=(width,),dtype='<f4',buffer=binary,offset=4*i,strides=(22,))
                         for i in range(3)]).astype(np.float64)
    good=np.all(np.isfinite(xyz),axis=1)
    count=int(np.count_nonzero(good))
    need(count>0,'ALL_XYZ_NONFINITE')
    finite=xyz[good]
    ranges=np.sqrt(np.sum(finite*finite,axis=1))
    need(bool(np.isfinite(ranges).all()),'NONFINITE_RANGES')
    return {'point_count':width,'finite_xyz_count':count,'nonfinite_xyz_count':width-count,
        'all_xyz_finite':bool(count==width),
        'xyz_min_m':[float(x) for x in finite.min(axis=0)],
        'xyz_max_m':[float(x) for x in finite.max(axis=0)],
        'range_min_m':float(ranges.min()),'range_max_m':float(ranges.max()),
        'point_payload_sha256':sha(binary),
        'nonfinite_points_excluded_from_descriptive_statistics_only':bool(count!=width)}

def diagnostic(topic, message, decoder):
    c=decoder.Cursor(message)
    h=decoder.header(c)
    if topic=='/camera/color/image_raw/compressed':
        fmt=c.text(256); n=c.number(); raw=c.take(n).tobytes(); c.done()
        need('jpeg' in fmt.lower() or 'jpg' in fmt.lower(),'CAMERA_ENCODING_DECLARATION')
        result=image_diagnostic(raw)
        result['camera_format_as_recorded']=fmt
    elif topic in ('/camera/imu','/handsfree/imu'):
        raw=c.take(296).tobytes(); c.done()
        result=imu_diagnostic(raw)
    elif topic=='/velodyne_points':
        height,width,nf=c.number(),c.number(),c.number()
        need(1<=nf<=32,'LIDAR_FIELD_COUNT')
        desc=[]
        for _ in range(nf):
            desc.append({'name':c.text(256),'offset':c.number(),
                'datatype':c.take(1)[0],'count':c.number()})
        endian=c.bool(); step,row_step=c.number(),c.number(); n=c.number()
        need(0<n<=8*1024*1024,'LIDAR_BYTE_COUNT')
        raw=c.take(n).tobytes(); dense=c.bool(); c.done()
        result=lidar_diagnostic(raw,desc,width,height,step,row_step,endian)
        result['is_dense_flag_as_recorded']=dense
    else:
        raise ValueError('R22_DENIED:UNKNOWN_TOPIC')
    return dict(result,header_stamp_ns=h['header_stamp_ns'],frame_id=h['frame_id'],sequence=h['sequence'])

def validate_upstream(r17,r18,r19,r20):
    need(r17['schema']=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1','R17_SCHEMA')
    need(r18['schema']=='TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1','R18_SCHEMA')
    need(r19['schema']=='TRUST_ROBOT_R19_RECORDED_FRONTEND_PROVENANCE_V1','R19_SCHEMA')
    need(r20['schema']=='TRUST_ROBOT_R20_RECORDER_BOUNDARY_REVIEW_V1','R20_SCHEMA')
    for x in (r17,r18,r19,r20):
        need(x['trajectory_id']=='room_02' and x['split']=='train','TRAIN_ONLY')
    bag=r17['file_sha256']
    need(bag==r18['recording_sha256']==r19['bag_sha256']==r20['authenticated_bag_sha256'],'BAG_IDENTITY')
    need(r18['sampled_message_count']==8 and r19['camera_imu_receipt_count']==6 and
         r19['lidar_observation_count']==2 and r20['regression_tests_passed']==197,'PRIOR_COUNTS')
    for key in ('physical_sync_verified','full_sensor_extrinsics_verified',
                'independent_reference_association_verified','real_sensor_factor_execution_authorized',
                'm2dgr_scoring_authorized'):
        if key in r20: need(r20[key] is False,'R20_GATE:'+key)
    need(r19['real_pose_factors_generated']==0 and r20['new_real_pose_factors']==0,
         'POSE_FACTOR_GATE')
    need(r19['health_labels']==0 and r20['health_labels']==0,'HEALTH_GATE')
    need(r18['cross_stream_alignment_performed'] is False and
         r19['cross_modal_temporal_association_performed'] is False,'ALIGNMENT_GATE')
    need(r18['physical_sync_verified'] is False and r19['physical_sync_verified'] is False,
         'PHYSICAL_SYNC')
    need(r18['extrinsics_verified'] is False and r19['full_extrinsics_verified'] is False,
         'EXTRINSICS')

def run(repo,bag,arc,out):
    sys.path.insert(0,str(arc/'r18'))
    import r18_decode as decoder
    r17p,r18p,r19p,r20p=(arc/rel for rel in ('r17/r17_recorded_index.json',
        'r18/r18_bounded_recorded_samples.json','r19/r19_recorded_frontend_contract_v1.json',
        'r20/r20_recorder_readiness_review_v1.json'))
    r17,r18,r19,r20=(json.loads(p.read_text()) for p in (r17p,r18p,r19p,r20p))
    validate_upstream(r17,r18,r19,r20)
    need(sha_file(bag)==r17['file_sha256'],'RECORDED_FILE_HASH')
    import trust_robot.m2dgr_sensor_admission as admission
    snap=admission.load_frozen_snapshot(repo)
    need(snap['by_id']['room_02']['split']=='train' and
         all(x is False for x in snap['scientific_gates'].values()),'FROZEN_SCIENTIFIC_GATES')
    try: admission.require_real_factor_execution(snap,'room_02')
    except admission.SensorAdmissionError: pass
    else: raise ValueError('R22_DENIED:FACTOR_GATE_OPEN')
    indexed={x['id']:x for x in r17['connections']}
    targets={}
    for topic,items in r18['samples'].items():
        need(topic in decoder.NEEDED and len(items)==2,'FOUR_TOPICS_TWO_SAMPLES')
        for index,s in enumerate(items):
            key=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
            need(key not in targets,'DUPLICATE_SAMPLE')
            targets[key]=(topic,index,s)
    need(len(targets)==8,'EIGHT_SAMPLES')
    offsets=sorted({key[0] for key in targets})
    need(len(offsets)<=4,'CHUNK_BUDGET')
    result={topic:[None,None] for topic in decoder.NEEDED}
    seen=set()
    with bag.open('rb') as handle:
        for off in offsets:
            raw,mode=decoder.chunk_data(handle,off)
            need(mode in r18['compression_methods'],'COMPRESSION_IDENTITY')
            for cid,record_time,view in decoder.messages(raw,indexed):
                key=(off,cid,record_time,sha(view))
                if key not in targets:continue
                need(key not in seen,'DUPLICATE_RECORDED_MESSAGE')
                topic,index,s=targets[key]
                need(len(view)==s['serialized_message_bytes'],'SERIALIZED_SIZE')
                body=view.tobytes()
                decoded=decoder.decode(topic,body)
                need(all(decoded.get(k)==v for k,v in s.items() if k in decoded),
                     'R18_REDECODE_DISAGREEMENT')
                diag=diagnostic(topic,body,decoder)
                need(diag['header_stamp_ns']==s['header_stamp_ns'] and
                     diag['frame_id']==s['frame_id'] and diag['sequence']==s['sequence'],
                     'RECORDED_HEADER_DISAGREEMENT')
                result[topic][index]={'source':{'chunk_offset':off,'connection_id':cid,
                    'bag_record_time_ns':record_time,'serialized_message_sha256':key[3],
                    'serialized_message_bytes':len(view),'sample_subset_index':index},
                    'descriptive_signal':diag}
                seen.add(key)
    need(len(seen)==8 and all(all(v is not None for v in items) for items in result.values()),
         'SAMPLE_COVERAGE')
    report={'schema':'TRUST_ROBOT_R22_TRAIN_ONLY_SIGNAL_DIAGNOSTICS_V1',
        'trajectory_id':'room_02','split':'train','github_baseline':'76685f1a6a97fb8e0750224bb927f1b094e63203',
        'bag_sha256':r17['file_sha256'],
        'frozen_source_report_sha256':{x:sha_file(p) for x,p in zip(('r17','r18','r19','r20'),(r17p,r18p,r19p,r20p))},
        'sampling_rule':r18['sampling_rule'],'new_sensor_measurements':0,
        'sample_count':8,'sensor_stream_count':4,'signals':result,
        'scope':'DESCRIPTIVE_TWO_SAMPLE_TRAIN_ONLY_CANDIDATES_NOT_SELECTED_FEATURES',
        'decoded_camera_pixels':True,'materialized_lidar_xyz_for_descriptive_statistics_only':True,
        'real_lidar_scan_registration_executed':False,'camera_odometry_executed':False,
        'imu_preintegration_executed':False,'cross_modal_alignment_performed':False,
        'physical_time_semantics_verified':False,'sensor_extrinsics_verified':False,
        'independent_ground_truth_scored':False,'health_features_frozen':False,
        'health_labels_generated':0,'real_pose_factors_generated':0,
        'real_sensor_factor_execution_authorized':False,
        'raw_recording_modified':False,'github_modified':False}
    with out.open('x',encoding='utf-8') as f:json.dump(report,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    print('R22_AUTHENTIC_TRAIN_SAMPLE_CONTENT=8_DECODED')
    for topic,items in result.items():
        if topic=='/camera/color/image_raw/compressed':
            print('R22_CAMERA_IMAGES='+','.join(str(x['descriptive_signal']['width'])+'x'+str(x['descriptive_signal']['height']) for x in items))
        if topic=='/velodyne_points':
            print('R22_LIDAR_XYZ_COUNTS='+','.join(str(x['descriptive_signal']['finite_xyz_count'])+'/'+str(x['descriptive_signal']['point_count']) for x in items))
        print('R22_TOPIC_SAMPLES='+topic+' COUNT='+str(len(items)))
    print('R22_FRONTEND_DIAGNOSTIC_ONLY=PASS')

if __name__=='__main__':
    run(*map(pathlib.Path,sys.argv[1:5]))
