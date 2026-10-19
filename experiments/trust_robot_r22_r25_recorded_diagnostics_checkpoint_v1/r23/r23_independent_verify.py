"""Rebuild sampling schedule from the bag index, relocate each message,
recompute source hashes and independent R22 numeric measurements."""
import hashlib, json, math, pathlib, struct, sys

def need(x,s):
    if not x:raise ValueError('R23_INDEPENDENT_DENIED:'+s)
def u32(x):return int.from_bytes(x,'little')
def u64(x):return int.from_bytes(x,'little')
def sha(x):return hashlib.sha256(x).hexdigest()
def filehash(p):return sha(pathlib.Path(p).read_bytes())
def exact(f,n):
    data=f.read(n);need(len(data)==n,'TRUNCATION');return data

def fields(blob):
    p=0;result={}
    while p<len(blob):
        need(p+4<=len(blob),'FIELD_LENGTH')
        n=u32(blob[p:p+4]);p+=4
        need(0<n<=len(blob)-p,'FIELD_BOUNDS')
        k,sep,v=blob[p:p+n].partition(b'=');p+=n
        need(k and sep and k not in result,'FIELD_DUPLICATE')
        result[k]=v
    return result

def rec(f):
    n=u32(exact(f,4));need(0<n<=2*1024*1024,'RECORD_HEADER')
    h=fields(exact(f,n));size=u32(exact(f,4));need(size<=8*1024*1024,'RECORD_DATA')
    return h,exact(f,size)

def expected_schedule(bag,r17,needed):
    conn={int(v['id']):v['topic'] for v in r17['connections']}
    eligible={topic:[] for topic in needed};ledgers={};last=-1
    with bag.open('rb') as f:
        need(exact(f,13)==b'#ROSBAG V2.0\n','MAGIC')
        head,_=rec(f);need(head[b'op']==b'\x03' and u64(head[b'index_pos'])==r17['index_position'],'INDEX_POS')
        f.seek(r17['index_position'])
        for _ in range(r17['connection_count']):
            h,_=rec(f);need(h[b'op']==b'\x07','CONNECTION')
        for _ in range(r17['chunk_count']):
            h,data=rec(f);need(h[b'op']==b'\x06','CHUNK_INFO')
            offset=u64(h[b'chunk_pos']);n=u32(h[b'count']);need(len(data)==8*n and last<offset<r17['index_position'],'LEDGER_SIZE')
            last=offset;ledger={}
            for i in range(n):
                cid,count=struct.unpack_from('<II',data,i*8)
                need(cid in conn and cid not in ledger and count>0,'CHUNK_ENTRY')
                ledger[cid]=count
            ledgers[offset]=ledger
            for topic in needed:
                if any(conn.get(cid)==topic for cid in ledger):eligible[topic].append(offset)
        need(f.tell()==bag.stat().st_size,'TRAILING_INDEX')
    selection={}
    for topic, offsets in eligible.items():
        need(len(offsets)>=8,'INSUFFICIENT_CHUNKS:'+topic)
        selection[topic]=[offsets[(len(offsets)-1)*i//7] for i in range(8)]
        need(len(set(selection[topic]))==8,'DUPLICATES')
    return selection, {t:len(v) for t,v in eligible.items()},ledgers

def chunk_messages(raw,conn):
    p=0;counts={}
    while p<len(raw):
        need(len(raw)-p>=8,'CHUNK_RECORD_TRUNCATED')
        hsize=u32(raw[p:p+4]);p+=4
        need(0<hsize<=2*1024*1024 and hsize<=len(raw)-p,'CHUNK_HEADER')
        h=fields(raw[p:p+hsize]);p+=hsize
        need(len(raw)-p>=4,'CHUNK_BODY_LENGTH')
        n=u32(raw[p:p+4]);p+=4
        need(n<=len(raw)-p,'CHUNK_DATA')
        payload=raw[p:p+n];p+=n
        if h[b'op']==b'\x07':
            cid=u32(h[b'conn']);need(cid in conn,'EMBEDDED_CONN_ID')
            m=fields(payload);k=conn[cid]
            need(h[b'topic'].decode()==k['topic'] and m[b'type'].decode()==k['message_type']
                 and m[b'md5sum'].decode()==k['md5sum']
                 and sha(m[b'message_definition'])==k['message_definition_sha256'],'EMBEDDED_CONN_VALIDATION')
            continue
        need(h[b'op']==b'\x02','CHUNK_OP')
        cid=u32(h[b'conn']);need(cid in conn,'MESSAGE_CONNECTION')
        sec,nano=struct.unpack('<II',h[b'time']);need(nano<1000000000,'TIME_NANOSECONDS')
        t=sec*1000000000+nano
        counts[cid]=counts.get(cid,0)+1
        yield cid,t,payload,counts

def verify(bag,arc,r22dev,reportp,verify_path):
    sys.path.insert(0,str(arc/'r18'));sys.path.insert(0,str(r22dev))
    import r18_decode as decoder
    from r22_independent_verify import check
    r17p=arc/'r17/r17_recorded_index.json';r18p=arc/'r18/r18_bounded_recorded_samples.json'
    r17=json.loads(r17p.read_text());r18=json.loads(r18p.read_text())
    report=json.loads(reportp.read_text())
    need(report['schema']=='TRUST_ROBOT_R23_INDEX_STRATIFIED_TRAIN_DIAGNOSTICS_V1' and report['trajectory_id']=='room_02' and report['split']=='train','IDENTITY')
    need(report['bag_sha256']==r17['file_sha256']==r18['recording_sha256'],'BAG_SHA')
    need(report['source_hashes']=={'r17_report_sha256':filehash(r17p),'r18_report_sha256':filehash(r18p),
       'r22_report_sha256':filehash(r22dev.parent/'trust_robot_r22_train_content_result_v1/r22_recorded_content_diagnostics_v1.json')},'REPORT_SHA_LINKS')
    expected,available,ledger=expected_schedule(bag,r17,decoder.NEEDED)
    need(set(report['per_topic'])==set(decoder.NEEDED) and report['selected_per_topic']==8
         and report['sampled_message_count']==32 and report['required_topics']==4,'SAMPLE_BOUND')
    by_offset={}
    for topic in decoder.NEEDED:
        entry=report['per_topic'][topic]
        need(entry['selected_chunk_offsets']==expected[topic] and entry['index_eligible_chunk_count']==available[topic], 'INDEX_SELECTION')
        need(entry['selected_message_count']==8 and entry['index_record_count']==r17['required_stream_counts'][topic],'INDEX_COUNTS')
        need(math.isclose(entry['selected_message_percent_of_full_topic'],100.0*8/r17['required_stream_counts'][topic],rel_tol=1e-13),'COVERAGE_FRACTION')
        need(math.isclose(entry['selected_chunk_percent_of_eligible'],100.0*8/available[topic],rel_tol=1e-13),'CHUNK_FRACTION')
        need(entry['qualitative_stability_inference_authorized'] is False,'STABILITY_CLAIM')
        for i,s in enumerate(entry['observations']):
            source=s['source'];off=expected[topic][i]
            need(source['chunk_offset']==off and source['subset_index']==i,'OBSERVATION_POSITION')
            by_offset.setdefault(off,{})[topic]=(i,s)
    need(report['inspected_unique_chunk_count']==len(by_offset) and 8<=len(by_offset)<=32,'UNIQUE_CHUNKS')
    for key in ('health_features_selected','statistical_stability_established','random_sampling_claimed',
                'cross_modal_pairing_performed','physical_capture_sync_verified','extrinsics_verified',
                'reference_ground_truth_scored','lidar_registration_executed','image_odometry_executed',
                'imu_preintegration_executed','real_sensor_factor_execution_authorized',
                'raw_bag_modified','github_modified'):
        need(report[key] is False,'SCIENTIFIC_GATE:'+key)
    need(report['real_pose_factors_generated']==0 and report['health_labels_created']==0,'ZERO_COUNTS')
    indexed={int(x['id']):x for x in r17['connections']}
    verified=0
    with bag.open('rb') as f:
        for off in sorted(by_offset):
            raw,mode=decoder.chunk_data(f,off)
            observed={};seen=set()
            for cid,t,body,counts in chunk_messages(raw,indexed):
                observed[cid]=observed.get(cid,0)+1
                topic=indexed[cid]['topic']
                if topic not in by_offset[off] or topic in seen:continue
                index,s=by_offset[off][topic];source=s['source']
                need(source=={'chunk_offset':off,'connection_id':cid,'bag_record_time_ns':t,
                     'serialized_message_sha256':sha(body),'serialized_message_bytes':len(body),
                     'subset_index':index,'header_stamp_ns':s['descriptive_signal']['header_stamp_ns'],
                     'frame_id':s['descriptive_signal']['frame_id'],'sequence':s['descriptive_signal']['sequence']},'SERIALIZED_MESSAGE_PROVENANCE')
                check(topic,bytes(body),s['descriptive_signal'],decoder)
                verified+=1;seen.add(topic)
            need(observed==ledger[off],'CHUNK_LEDGER')
            need(seen==set(by_offset[off]),'MISSING_OBSERVATIONS')
    need(verified==32,'RECOMPUTED_SAMPLES')
    # Independently recompute recorded aggregate ranges (not a statistical qualification).
    for topic,item in report['per_topic'].items():
        if topic=='/camera/color/image_raw/compressed':keys=('grayscale_mean','grayscale_stddev')
        elif topic in ('/camera/imu','/handsfree/imu'):keys=('angular_velocity_norm_rad_s','linear_acceleration_norm_m_s2','orientation_norm')
        else:keys=('point_count','finite_xyz_count','range_min_m','range_max_m')
        for key in keys:
            values=[s['descriptive_signal'][key] for s in item['observations']]
            expect=item['descriptive_ranges'][key]
            for computed,target in ((min(values),expect['min']), (max(values),expect['max']), (math.fsum(values)/8,expect['mean'])):
                need(math.isclose(computed,target,rel_tol=1e-12,abs_tol=1e-12),'RANGE_RECOMPUTATION:'+key)
            need(expect['observed_sample_count']==8,'RANGE_SAMPLE_COUNT')
    validation={'schema':'TRUST_ROBOT_R23_INDEPENDENT_STRATIFIED_CONTENT_VERIFY_V1',
        'report_sha256':filehash(reportp),'source_bag_sha256':r17['file_sha256'],
        'independently_relocated_serialized_messages':32,'numeric_diagnostics_recomputed':32,
        'sampling_schedule_rebuilt_from_real_bag_index':True,'exact_chunk_ledgers_verified':True,
        'health_features_frozen':False,'pose_factors_admitted':0,
        'cross_modal_time_association':False,'independent_ground_truth_scored':False,'verification':'PASS'}
    with verify_path.open('x',encoding='utf-8') as f:json.dump(validation,f,sort_keys=True,indent=2);f.write('\n')
    print('R23_INDEPENDENT_SAMPLING_SCHEDULE=RECONSTRUCTED')
    print('R23_INDEPENDENT_SERIALIZED_MESSAGE_HASHES=32_VERIFIED')
    print('R23_INDEPENDENT_SENSOR_DIAGNOSTICS=32_RECOMPUTED')
    print('R23_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':verify(*map(pathlib.Path,sys.argv[1:6]))
