"""Recorded TRAIN-only diagnostic challenge: destructive changes exist only in RAM.
No health thresholds, candidate pose factors, cross-modal matching or data export.
"""
import hashlib, json, math, pathlib, struct, sys
from types import SimpleNamespace

TOPICS=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu','/velodyne_points')
def need(ok,why):
    if not ok: raise ValueError('R24_FAIL_CLOSED:'+why)
def sha(data):return hashlib.sha256(data).hexdigest()
def filehash(path):return sha(pathlib.Path(path).read_bytes())
def denied(call):
    try:call()
    except (ValueError,TypeError,KeyError,IndexError,UnicodeDecodeError):return True
    raise AssertionError('R24_ADVERSARIAL_INPUT_ACCEPTED')

def validate_contract(r, r17, bag_sha):
    need(r.get('schema')=='TRUST_ROBOT_R23_INDEX_STRATIFIED_TRAIN_DIAGNOSTICS_V1', 'REPORT_SCHEMA')
    need(r.get('trajectory_id')=='room_02' and r.get('split')=='train' and r.get('bag_sha256')==bag_sha,'TRAIN_BAG_IDENTITY')
    need(r.get('git_baseline')=='76685f1a6a97fb8e0750224bb927f1b094e63203','GIT_LINEAGE')
    need(r.get('sampled_message_count')==32 and r.get('required_topics')==4 and r.get('selected_per_topic')==8,'SAMPLE_BUDGET')
    need(set(r.get('per_topic',{}))==set(TOPICS),'TOPICS')
    need(8<=r.get('inspected_unique_chunk_count',0)<=32,'CHUNK_BUDGET')
    need(r.get('source_chunk_count')==r17['chunk_count'],'SOURCE_CHUNKS')
    for field in ('health_features_selected','statistical_stability_established','random_sampling_claimed',
      'cross_modal_pairing_performed','physical_capture_sync_verified','extrinsics_verified',
      'reference_ground_truth_scored','lidar_registration_executed','image_odometry_executed',
      'imu_preintegration_executed','real_sensor_factor_execution_authorized','raw_bag_modified','github_modified'):
        need(r.get(field) is False,'SCIENTIFIC_GATE:'+field)
    need(type(r.get('real_pose_factors_generated')) is int and r['real_pose_factors_generated']==0 and
      type(r.get('health_labels_created')) is int and r['health_labels_created']==0,'ZERO_SCIENCE_COUNTS')
    seen=set()
    for topic in TOPICS:
        row=r['per_topic'][topic]
        need(row['index_record_count']==r17['required_stream_counts'][topic],'SOURCE_MESSAGE_COUNTS')
        need(row['selected_message_count']==8 and len(row['observations'])==8 and
             len(set(row['selected_chunk_offsets']))==8,'STRATIFICATION')
        need(row.get('qualitative_stability_inference_authorized') is False,'STABILITY_GATE')
        for i,item in enumerate(row['observations']):
            src=item['source']
            need(src['subset_index']==i and src['chunk_offset']==row['selected_chunk_offsets'][i], 'SUBSET_ORDINAL')
            need(type(src['connection_id']) is int and type(src['bag_record_time_ns']) is int,'SOURCE_NUMERIC_TYPES')
            need(type(src['serialized_message_bytes']) is int and src['serialized_message_bytes']>0,'SOURCE_SIZE')
            digest=src['serialized_message_sha256']
            need(type(digest) is str and len(digest)==64 and set(digest)<=set('0123456789abcdef'), 'SOURCE_DIGEST')
            key=(src['chunk_offset'],src['connection_id'],src['bag_record_time_ns'],digest)
            need(key not in seen,'DUPLICATE_SAMPLE')
            seen.add(key)
    need(len(seen)==32,'SAMPLE_UNIQUENESS')

def envelope(topic,payload,source,observed_cid,observed_bag_ns,observed_offset,expected_header,decoder):
    need(type(payload) is bytes and len(payload)==source['serialized_message_bytes'],'BYTE_LENGTH')
    need(sha(payload)==source['serialized_message_sha256'],'SERIALIZED_HASH')
    need(observed_cid==source['connection_id'] and observed_bag_ns==source['bag_record_time_ns']
         and observed_offset==source['chunk_offset'],'BAG_PROVENANCE')
    c=decoder.Cursor(payload)
    header=decoder.header(c)
    need(all(header[k]==source[k] and header[k]==expected_header[k] for k in ('header_stamp_ns','frame_id','sequence')),
         'ORIGINAL_HEADER_BINDING')
    need(topic in TOPICS,'TOPIC_SCOPE')
    return True

def mutate_byte(payload, index):
    need(0<=index<len(payload),'MUTATION_BOUNDS')
    copy=bytearray(payload);copy[index]^=1
    return bytes(copy)

def semantic_perturb(topic,payload,diag,decoder,diagnostic,lidar_frontend):
    """One controlled semantic challenge per message; LiDAR NaN is descriptive only."""
    c=decoder.Cursor(payload)
    h=decoder.header(c)
    changed=bytearray(payload)
    if topic==TOPICS[0]:
        c.text(256);n=c.number();start=c.pos
        need(n>=64 and n<=len(payload)-start,'CAMERA_PAYLOAD_LOCATION')
        changed[start]=0 # guaranteed JPEG SOI mismatch
        need(denied(lambda:diagnostic.diagnostic(topic,bytes(changed),decoder)),'JPEG_INVALID_ACCEPTED')
        return 'REJECTED_BAD_JPEG_MARKER'
    if topic in TOPICS[1:3]:
        start=c.pos
        need(len(payload)==start+296,'IMU_LAYOUT')
        changed[start:start+8]=struct.pack('<d',float('nan'))
        need(denied(lambda:diagnostic.diagnostic(topic,bytes(changed),decoder)),'IMU_NONFINITE_ACCEPTED')
        return 'REJECTED_NONFINITE_IMU'
    need(topic==TOPICS[3],'LIDAR_TOPIC')
    height,width,nf=c.number(),c.number(),c.number()
    descriptors=[]
    for _ in range(nf):
        descriptors.append(SimpleNamespace(name=c.text(256),offset=c.number(),datatype=c.take(1)[0],count=c.number()))
    endian=c.bool();step_at=c.pos;point_step=c.number();row_step=c.number();count=c.number()
    start=c.pos
    need(width>=3 and count==width*22 and count<=len(payload)-start,'POINTCLOUD_LAYOUT')
    altered=bytearray(payload);altered[step_at:step_at+4]=struct.pack('<I',21)
    need(denied(lambda:diagnostic.diagnostic(topic,bytes(altered),decoder)),'POINT_STEP_ACCEPTED')
    # A single NaN may be counted descriptively, but must be refused by the
    # fixed LiDAR frontend's strict XYZ materializer. No registration is run.
    valid=None
    for i in range(width):
        xyz=struct.unpack_from('<fff',payload,start+i*22)
        if all(math.isfinite(x) for x in xyz):
            valid=i;break
    need(valid is not None and diag['finite_xyz_count']>=2,'LIDAR_FINITE_SAMPLE_NOT_AVAILABLE')
    nan_payload=bytearray(payload)
    nan_payload[start+valid*22:start+valid*22+4]=struct.pack('<f',float('nan'))
    observed=diagnostic.diagnostic(topic,bytes(nan_payload),decoder)
    need(observed['finite_xyz_count']==diag['finite_xyz_count']-1 and
         observed['nonfinite_xyz_count']==diag['nonfinite_xyz_count']+1 and
         observed['all_xyz_finite'] is False and
         observed['nonfinite_points_excluded_from_descriptive_statistics_only'] is True,
         'DESCRIPTIVE_NAN_POLICY')
    cloud_data=bytes(nan_payload[start:start+count])
    seconds,nanos=divmod(h['header_stamp_ns'],1_000_000_000)
    cloud=SimpleNamespace(
        header=SimpleNamespace(frame_id=h['frame_id'],stamp=SimpleNamespace(secs=seconds,nsecs=nanos)),
        height=height,width=width,fields=descriptors,is_bigendian=endian,is_dense=True,
        point_step=point_step,row_step=row_step,data=cloud_data)
    try:lidar_frontend.decode_m2dgr_velodyne_xyz(cloud)
    except lidar_frontend.LidarFrontendError as exc:
        need('non-finite' in str(exc),'LIDAR_DENIED_FOR_WRONG_REASON')
    else:raise AssertionError('R24_NONFINITE_LIDAR_FRONTEND_ACCEPTED')
    return 'REJECTED_INVALID_STEP_AND_NONFINITE_FACTOR_INPUT;DESCRIPTIVE_NAN_OBSERVED'

def run(repo,bag,arc,r22dev,r23dev,r23_report,out):
    sys.path[:0]=[str(arc/'r18'),str(r22dev),str(r23dev),str(repo/'src')]
    import r18_decode as decoder
    import r22_content as diagnostic
    from r22_independent_verify import check as check_numeric
    from r23_independent_verify import expected_schedule
    import trust_robot.lidar_frontend as lidar_frontend
    r17=json.loads((arc/'r17/r17_recorded_index.json').read_text())
    record=json.loads(r23_report.read_text())
    validate_contract(record,r17,r17['file_sha256'])
    need(record['source_hashes']=={
        'r17_report_sha256':filehash(arc/'r17/r17_recorded_index.json'),
        'r18_report_sha256':filehash(arc/'r18/r18_bounded_recorded_samples.json'),
        'r22_report_sha256':filehash(r22dev.parent/'trust_robot_r22_train_content_result_v1/r22_recorded_content_diagnostics_v1.json')},'SOURCE_REPORT_CHAIN')
    selection,eligibility,ledgers=expected_schedule(bag,r17,decoder.NEEDED)
    need(all(record['per_topic'][topic]['selected_chunk_offsets']==selection[topic] for topic in TOPICS),'INDEX_SCHEDULE')
    indexed={row['id']:row for row in r17['connections']}
    chosen={}
    for topic in TOPICS:
        for s in record['per_topic'][topic]['observations']:
            src=s['source']; key=(src['chunk_offset'],src['connection_id'],src['bag_record_time_ns'],src['serialized_message_sha256'])
            chosen[key]=(topic,src,s['descriptive_signal'])
    recovered={};by_off={}
    for key in chosen:by_off.setdefault(key[0],set()).add(key)
    need(len(by_off)==record['inspected_unique_chunk_count'] and len(chosen)==32,'SELECTION_SIZE')
    with bag.open('rb') as handle:
        for off in sorted(by_off):
            raw,method=decoder.chunk_data(handle,off)
            need(method in ('none','bz2'),'CHUNK_COMPRESSION')
            observed={}
            for cid,ns,view in decoder.messages(raw,indexed):
                observed[cid]=observed.get(cid,0)+1
                digest=sha(view)
                key=(off,cid,ns,digest)
                if key in chosen:
                    need(key not in recovered,'REPLAYED_SOURCE_IN_CHUNK')
                    topic,src,expected=chosen[key]
                    payload=view.tobytes()
                    envelope(topic,payload,src,cid,ns,off,expected,decoder)
                    check_numeric(topic,payload,expected,decoder)
                    recovered[key]=payload
            need(observed==ledgers[off],'CHUNK_INDEX_LEDGER')
    need(len(recovered)==32,'COMPLETE_RELOCATION')
    grouped={topic:[] for topic in TOPICS}
    for key,(topic,source,desc) in chosen.items():
        grouped[topic].append((source['subset_index'],key,source,desc,recovered[key]))
    for topic in TOPICS:grouped[topic].sort()
    rejections=0
    for topic,items in grouped.items():
        for i,key,src,desc,payload in items:
            for modified in (mutate_byte(payload,len(payload)-1), mutate_byte(payload,4), mutate_byte(payload,16)):
                need(denied(lambda data=modified:envelope(topic,data,src,src['connection_id'],src['bag_record_time_ns'],
                     src['chunk_offset'],desc,decoder)),'SERIALIZED_MUTATION_ACCEPTED')
                rejections+=1
            alternate=items[(i+1)%len(items)][4]
            need(sha(alternate)!=sha(payload),'REPLAY_IDENTICAL_CONTENT')
            need(denied(lambda:envelope(topic,alternate,src,src['connection_id'],src['bag_record_time_ns'],
                 src['chunk_offset'],desc,decoder)),'CROSS_SAMPLE_REPLAY_ACCEPTED')
            rejections+=1
    need(rejections==128,'SOURCE_MUTATION_COUNTS')
    semantic=[]
    for topic,items in grouped.items():
        for i,key,src,desc,payload in items[:2]:
            semantic.append(semantic_perturb(topic,payload,desc,decoder,diagnostic,lidar_frontend))
    need(len(semantic)==8 and sum(x.startswith('REJECTED_INVALID_STEP') for x in semantic)==2,'SEMANTIC_CHALLENGE_COUNTS')
    result={
        'schema':'TRUST_ROBOT_R24_TRAIN_RECORDED_DIAGNOSTIC_STRESS_V1',
        'trajectory_id':'room_02','split':'train','bag_sha256':r17['file_sha256'],
        'r23_report_sha256':filehash(r23_report),
        'source_chunk_count':r17['chunk_count'],
        'original_selected_messages':32,'original_chunks_read':len(by_off),
        'message_integrity_and_provenance_challenges_rejected':rejections,
        'challenge_families':['tail_byte_flip','header_timestamp_byte_flip','header_frame_byte_flip','same_topic_sample_replay'],
        'semantic_payload_challenges_rejected':8,
        'semantic_challenge_results':semantic,
        'lidar_nonfinite_descriptive_only_cases':2,
        'lidar_nonfinite_frontend_rejections':2,
        'changes_applied_to_memory_copies_only':True,
        'recorded_source_files_written':False,
        'original_recording_modified':False,
        'health_thresholds_selected':False,
        'health_features_frozen':False,
        'statistical_stability_established':False,
        'cross_modal_alignment_performed':False,
        'physical_synchronization_verified':False,
        'full_extrinsics_verified':False,
        'ground_truth_scored':False,
        'camera_odometry_executed':False,
        'lidar_registration_executed':False,
        'imu_preintegration_executed':False,
        'real_sensor_factor_execution_authorized':False,
        'real_pose_factors_generated':0,'health_labels':0,'git_modified':False,
        'scope':'IN_MEMORY_FAIL_CLOSED_DIAGNOSTIC_CHALLENGES_ONLY',
    }
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    print('R24_AUTHENTIC_TRAIN_MESSAGES_RELOCATED=32')
    print('R24_INDEXED_CHUNKS_READ='+str(len(by_off)))
    print('R24_PROVENANCE_MUTATIONS_REJECTED='+str(rejections))
    print('R24_CONTENT_LAYOUT_MUTATIONS_REJECTED=8')
    print('R24_LIDAR_NONFINITE_DESCRIPTIVE_CASES=2')
    print('R24_LIDAR_NONFINITE_FRONTEND_DENIALS=2')
    print('R24_SCIENTIFIC_ADMISSION=DENIED')

if __name__=='__main__':run(*map(pathlib.Path,sys.argv[1:8]))
