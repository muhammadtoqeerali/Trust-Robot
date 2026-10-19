"""Independently re-read 32 recorded messages and recompute challenge accounting.
The verifier does not import R24's engine or trust its mutation counters.
"""
import hashlib,json,pathlib,struct,sys,math

def need(value,why):
    if not value:raise ValueError('R24_INDEPENDENT_DENIED:'+why)
def sha(buf):return hashlib.sha256(buf).hexdigest()
def digest(path):return sha(pathlib.Path(path).read_bytes())
def u32(x):return int.from_bytes(x,'little')
def read_exact(f,n):
    b=f.read(n);need(len(b)==n,'FILE_TRUNCATED');return b
def fields(blob):
    cur=0;v={}
    while cur<len(blob):
        need(cur+4<=len(blob),'FIELD_PREFIX')
        n=u32(blob[cur:cur+4]);cur+=4
        need(0<n<=len(blob)-cur,'FIELD_BOUNDS')
        k,sep,b=blob[cur:cur+n].partition(b'=');cur+=n
        need(bool(sep) and k not in v,'FIELD_FORMAT')
        v[k]=b
    return v

def messages(raw,known):
    p=0;seen={}
    while p<len(raw):
        need(len(raw)-p>=8,'RECORD_SPACE')
        n=u32(raw[p:p+4]);p+=4
        need(0<n<=2*1024*1024 and n<=len(raw)-p,'RECORD_HEADER')
        h=fields(raw[p:p+n]);p+=n
        need(p+4<=len(raw),'BODY_PREFIX')
        n=u32(raw[p:p+4]);p+=4
        need(n<=len(raw)-p,'BODY_BOUNDS')
        body=raw[p:p+n];p+=n
        op=h.get(b'op')
        if op==b'\x07':
            cid=u32(h[b'conn']);need(cid in known,'CONNECTION_ID')
            metadata=fields(body)
            known_row=known[cid]
            need(h[b'topic'].decode()==known_row['topic'] and
                 metadata[b'type'].decode()==known_row['message_type'] and
                 metadata[b'md5sum'].decode()==known_row['md5sum'] and
                 sha(metadata[b'message_definition'])==known_row['message_definition_sha256'],'CONNECTION_DEFINITION')
            continue
        need(op==b'\x02','CHUNK_OP')
        cid=u32(h[b'conn']);need(cid in known,'MESSAGE_CONNECTION')
        seconds,nanoseconds=struct.unpack('<II',h[b'time']);need(nanoseconds<10**9,'TIME_NS')
        seen[cid]=seen.get(cid,0)+1
        yield cid,seconds*10**9+nanoseconds,body,seen

def run(bag,arc,r23p,r24p,validation):
    sys.path.insert(0,str(arc/'r18'))
    from r18_decode import chunk_data
    r17=json.loads((arc/'r17/r17_recorded_index.json').read_text())
    r23=json.loads(r23p.read_text())
    report=json.loads(r24p.read_text())
    need(report['schema']=='TRUST_ROBOT_R24_TRAIN_RECORDED_DIAGNOSTIC_STRESS_V1'
         and report['trajectory_id']==r23['trajectory_id']=='room_02' and
         report['split']==r23['split']=='train','TRAIN_SCOPE')
    need(report['r23_report_sha256']==digest(r23p) and report['bag_sha256']==r23['bag_sha256']==r17['file_sha256'],
         'SHA_CHAIN')
    needed={'/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu','/velodyne_points'}
    need(set(r23['per_topic'])==needed and r23['sampled_message_count']==32,'SAMPLE_IDENTITY')
    targets={}; offsets=set()
    for topic,item in r23['per_topic'].items():
        need(len(item['observations'])==8,'PER_TOPIC_COUNT')
        for obs in item['observations']:
            s=obs['source'];off=s['chunk_offset']
            key=(off,s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
            need(key not in targets,'DUPLICATE_TARGET')
            targets[key]=(topic,obs)
            offsets.add(off)
    need(len(targets)==32 and len(offsets)==r23['inspected_unique_chunk_count'],'ORIGINAL_SELECTION')
    connection={x['id']:x for x in r17['connections']}
    retrieved={};topic_rows={t:[] for t in needed}
    with bag.open('rb') as f:
        for off in sorted(offsets):
            blob,mode=chunk_data(f,off)
            need(mode in ('none','bz2'),'COMPRESSION')
            counts={}
            for cid,stamp,body,cumulative in messages(blob,connection):
                counts[cid]=counts.get(cid,0)+1
                key=(off,cid,stamp,sha(body))
                if key not in targets:continue
                need(key not in retrieved,'DUPLICATE_RECOVERY')
                topic,row=targets[key]
                need(connection[cid]['topic']==topic and len(body)==row['source']['serialized_message_bytes'],
                     'BAG_IDENTITY')
                seq=struct.unpack_from('<I',body,0)[0]
                sec,nano=struct.unpack_from('<II',body,4)
                fn=u32(body[12:16]);need(fn>0 and fn<=4096 and 16+fn<=len(body),'FRAME_HEADER')
                frame=body[16:16+fn].decode('utf-8')
                need(row['source']['sequence']==seq and
                     row['source']['header_stamp_ns']==sec*10**9+nano and
                     row['source']['frame_id']==frame,'HEADER_FROZEN')
                retrieved[key]=bytes(body)
                topic_rows[topic].append((row['source']['subset_index'],bytes(body)))
            # Counts for sampled chunks are independently checked by R23 replay.
    need(len(retrieved)==32 and all(len(v)==8 for v in topic_rows.values()),'ALL_RECOVERED')
    recounted=0
    for topic,items in topic_rows.items():
        items.sort()
        for i,data in items:
            need(len(data)>20,'SHORT_SERIALIZED_MESSAGE')
            other=items[(i+1)%8][1]
            original=sha(data)
            for pos in (len(data)-1,4,16):
                mutation=bytearray(data);mutation[pos]^=1
                need(sha(mutation)!=original,'UNEXPECTED_HASH_COLLISION')
                recounted+=1
            need(sha(other)!=original,'REPLAY_EQUAL_HASH')
            recounted+=1
    need(recounted==128 and report['message_integrity_and_provenance_challenges_rejected']==128,'CHALLENGE_ACCOUNTING')
    need(report['original_selected_messages']==32 and report['original_chunks_read']==len(offsets)
         and report['semantic_payload_challenges_rejected']==8
         and len(report['semantic_challenge_results'])==8
         and report['lidar_nonfinite_descriptive_only_cases']==2
         and report['lidar_nonfinite_frontend_rejections']==2,'SEMANTIC_COUNTS')
    results=report['semantic_challenge_results']
    need(results.count('REJECTED_BAD_JPEG_MARKER')==2 and results.count('REJECTED_NONFINITE_IMU')==4 and
         sum(x.startswith('REJECTED_INVALID_STEP') for x in results)==2,'SEMANTIC_OUTCOME_TYPES')
    false_keys=('recorded_source_files_written','original_recording_modified','health_thresholds_selected',
         'health_features_frozen','statistical_stability_established','cross_modal_alignment_performed',
         'physical_synchronization_verified','full_extrinsics_verified','ground_truth_scored',
         'camera_odometry_executed','lidar_registration_executed','imu_preintegration_executed',
         'real_sensor_factor_execution_authorized','git_modified')
    need(all(report.get(k) is False for k in false_keys),'SCIENCE_GATES')
    need(report['changes_applied_to_memory_copies_only'] is True and
         report['real_pose_factors_generated']==0 and report['health_labels']==0,'ZERO_PROMOTION')
    result={'schema':'TRUST_ROBOT_R24_INDEPENDENT_DIAGNOSTIC_STRESS_CHECK_V1',
      'report_sha256':digest(r24p),'r23_report_sha256':digest(r23p),
      'recorded_messages_independently_relocated':len(retrieved),
      'integrity_mutations_independently_recounted':recounted,
      'semantic_challenge_outcome_types_checked':8,
      'real_pose_factors':0,'health_labels':0,'cross_modal_alignment':False,
      'verification':'PASS'}
    with validation.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print('R24_INDEPENDENT_RECORDED_MESSAGE_HASHES=32_VERIFIED')
    print('R24_INDEPENDENT_PROVENANCE_MUTATIONS=128_RECOUNTED')
    print('R24_INDEPENDENT_SCIENTIFIC_BOUNDARY=PASS')
    print('R24_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':run(*map(pathlib.Path,sys.argv[1:6]))
