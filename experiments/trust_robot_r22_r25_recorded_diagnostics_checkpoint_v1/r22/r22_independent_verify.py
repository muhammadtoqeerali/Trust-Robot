"""Independent receipt relocation and numeric recomputation for R22's 8 samples."""
import hashlib,json,math,pathlib,struct,sys
import cv2,numpy as np

def need(condition,label):
    if not condition:raise ValueError('R22_INDEPENDENT_FAIL:'+label)
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(pathlib.Path(p).read_bytes())
def close(a,b,label,rel=1e-7):
    need(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=rel*max(1,abs(a),abs(b)),label)

def check(topic,payload,signal,decoder):
    c=decoder.Cursor(payload)
    header=decoder.header(c)
    need(all(header[k]==signal[k] for k in ('header_stamp_ns','frame_id','sequence')),'HEADER')
    if topic=='/camera/color/image_raw/compressed':
        fmt=c.text(256);n=c.number();raw=c.take(n).tobytes();c.done()
        need(sha(raw)==signal['jpeg_payload_sha256'] and fmt==signal['camera_format_as_recorded'],'CAMERA_SHA_AND_FORMAT')
        image=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_GRAYSCALE)
        need(image is not None and image.ndim==2,'CAMERA_PIXELS')
        h,w=image.shape
        need([w,h,int(image.size),int(image.min()),int(image.max())]==
             [signal['width'],signal['height'],signal['decoded_pixel_count'],signal['grayscale_min'],signal['grayscale_max']],
             'CAMERA_SHAPE_AND_RANGE')
        pixels=image.astype(np.float64)
        avg=float(pixels.sum()/pixels.size)
        deviation=float(np.sqrt(np.square(pixels-avg).sum()/pixels.size))
        close(avg,signal['grayscale_mean'],'CAMERA_MEAN');close(deviation,signal['grayscale_stddev'],'CAMERA_STD')
    elif topic in ('/camera/imu','/handsfree/imu'):
        raw=c.take(296).tobytes();c.done()
        vals=struct.unpack('<37d',raw)
        for key,seq in (('orientation_norm',vals[0:4]),
                        ('angular_velocity_norm_rad_s',vals[13:16]),
                        ('linear_acceleration_norm_m_s2',vals[25:28])):
            close(math.hypot(*seq),signal[key],key)
        for key,offset in (('orientation_covariance_unknown_sentinel',4),
                           ('angular_covariance_unknown_sentinel',16),
                           ('linear_covariance_unknown_sentinel',28)):
            need((vals[offset]==-1.0)==signal[key],'COV_SENTINEL:'+key)
    elif topic=='/velodyne_points':
        height,width,nf=c.number(),c.number(),c.number()
        desc=[]
        for _ in range(nf):
            desc.append((c.text(256),c.number(),c.take(1)[0],c.number()))
        endian=c.bool();step,rowstep=c.number(),c.number();n=c.number()
        raw=c.take(n).tobytes();dense=c.bool();c.done()
        need(height==1 and width==signal['point_count'] and not endian and step==22 and rowstep==width*22
             and len(raw)==width*22 and sha(raw)==signal['point_payload_sha256']
             and dense==signal['is_dense_flag_as_recorded'],'POINTCLOUD_LAYOUT')
        need([x[0] for x in desc]==['x','y','z','intensity','ring','time'],'POINT_FIELDS')
        xyz=[struct.unpack_from('<fff',raw,i*22) for i in range(width)]
        finite=[p for p in xyz if all(math.isfinite(x) for x in p)]
        need(len(finite)==signal['finite_xyz_count'] and width-len(finite)==signal['nonfinite_xyz_count'],
             'FINITE_XYZ_COUNTS')
        need(bool(len(finite)==width)==signal['all_xyz_finite'],'ALL_FINITE_FLAG')
        mins=[min(x[j] for x in finite) for j in range(3)]
        maxs=[max(x[j] for x in finite) for j in range(3)]
        dist=[math.hypot(*p) for p in finite]
        for j in range(3):
            close(mins[j],signal['xyz_min_m'][j],'XYZ_MIN');close(maxs[j],signal['xyz_max_m'][j],'XYZ_MAX')
        close(min(dist),signal['range_min_m'],'RANGE_MIN');close(max(dist),signal['range_max_m'],'RANGE_MAX')
    else:need(False,'TOPIC')

def main(bag,archive,reportp,verificationp):
    sys.path.insert(0,str(archive/'r18'))
    import r18_decode as decoder
    r17=json.loads((archive/'r17/r17_recorded_index.json').read_text())
    r18=json.loads((archive/'r18/r18_bounded_recorded_samples.json').read_text())
    r19=json.loads((archive/'r19/r19_recorded_frontend_contract_v1.json').read_text())
    report=json.loads(reportp.read_text())
    need(report['schema']=='TRUST_ROBOT_R22_TRAIN_ONLY_SIGNAL_DIAGNOSTICS_V1'
         and report['split']=='train' and report['trajectory_id']=='room_02','REPORT_IDENTITY')
    need(report['bag_sha256']==r17['file_sha256']==r18['recording_sha256']==r19['bag_sha256'],'BAG_SHA_LINEAGE')
    need(report['frozen_source_report_sha256']=={
        k:digest(archive/p) for k,p in (('r17','r17/r17_recorded_index.json'),
        ('r18','r18/r18_bounded_recorded_samples.json'),
        ('r19','r19/r19_recorded_frontend_contract_v1.json'),
        ('r20','r20/r20_recorder_readiness_review_v1.json'))},'REPORT_HASH_LINEAGE')
    need(report['sample_count']==8 and report['sensor_stream_count']==4
         and set(report['signals'])==set(decoder.NEEDED),'SAMPLE_SCOPE')
    for key in ('real_lidar_scan_registration_executed','camera_odometry_executed','imu_preintegration_executed',
                'cross_modal_alignment_performed','physical_time_semantics_verified','sensor_extrinsics_verified',
                'independent_ground_truth_scored','health_features_frozen','real_sensor_factor_execution_authorized',
                'raw_recording_modified','github_modified'):
        need(report[key] is False,'SCIENCE_BOUNDARY:'+key)
    need(report['real_pose_factors_generated']==0 and report['health_labels_generated']==0
         and report['new_sensor_measurements']==0,'ZERO_COUNT')
    targets={}
    for topic,items in r18['samples'].items():
        need(len(items)==2 and len(report['signals'][topic])==2,'TOPIC_TWO_SAMPLES')
        for i,s in enumerate(items):
            key=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
            need(key not in targets,'SAMPLE_UNIQUENESS')
            targets[key]=(topic,i,s)
    conn={x['id']:x for x in r17['connections']}
    count=0
    with bag.open('rb') as handle:
        for offset in sorted(set(k[0] for k in targets)):
            raw,mode=decoder.chunk_data(handle,offset)
            need(mode in r18['compression_methods'],'COMPRESSION')
            for cid,t,body in decoder.messages(raw,conn):
                key=(offset,cid,t,sha(body))
                if key not in targets:continue
                topic,i,s=targets.pop(key)
                item=report['signals'][topic][i]
                need(item['source']=={'chunk_offset':offset,'connection_id':cid,
                    'bag_record_time_ns':t,'serialized_message_sha256':sha(body),
                    'serialized_message_bytes':len(body),'sample_subset_index':i},'EXACT_SOURCE_BINDING')
                check(topic,body.tobytes(),item['descriptive_signal'],decoder)
                count+=1
    need(count==8 and not targets,'SOURCE_RELOCATION_AND_RECOMPUTATION')
    verification={'schema':'TRUST_ROBOT_R22_INDEPENDENT_CONTENT_VALIDATION_V1',
        'source_report_sha256':digest(reportp),'real_message_samples_recomputed':8,
        'four_modal_streams_rechecked':4,'train_only':True,'cross_modal_association_performed':False,
        'pose_factors_admitted':0,'health_labels':0,'source_modified':False,
        'verification':'PASS'}
    with verificationp.open('x',encoding='utf-8') as f:
        json.dump(verification,f,sort_keys=True,indent=2);f.write('\n')
    print('R22_INDEPENDENT_REAL_MESSAGE_HASHES=8_VERIFIED')
    print('R22_INDEPENDENT_CAMERA_IMU_LIDAR_VALUES=8_RECOMPUTED')
    print('R22_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':main(*map(pathlib.Path,sys.argv[1:5]))
