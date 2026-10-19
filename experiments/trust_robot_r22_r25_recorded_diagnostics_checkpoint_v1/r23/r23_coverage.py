"""Descriptive chunk-ordinal coverage of authentic M2DGR TRAIN observations.
No interpolation, cross-sensor pairing, pose, health model, or threshold selection.
"""
import hashlib, json, math, pathlib, struct, sys

def need(value, reason):
    if not value: raise ValueError('R23_DENIED:' + reason)
def sha(data): return hashlib.sha256(data).hexdigest()
def digest(path): return sha(pathlib.Path(path).read_bytes())

def positions(total, n=8):
    need(type(total) is int and type(n) is int and n==8 and total>=n and total<=1000000, 'STRATUM_SIZE')
    values=[(total-1)*i//(n-1) for i in range(n)]
    need(len(set(values))==n and values[0]==0 and values[-1]==total-1, 'STRATUM_DUPLICATION')
    return values

def chunk_ledger(bag, r17, decoder):
    conn={c['id']:c for c in r17['connections']}
    need(len(conn)==r17['connection_count'] and set(decoder.NEEDED).issubset({c['topic'] for c in conn.values()}), 'INDEX_CONNECTIONS')
    topic_cids={name:{cid for cid,c in conn.items() if c['topic']==name} for name in decoder.NEEDED}
    for name in topic_cids:need(len(topic_cids[name])==1, 'TOPIC_MULTICONNECTION:'+name)
    rows=[]
    with bag.open('rb') as f:
        need(decoder.read_exact(f,13)==b'#ROSBAG V2.0\n','VERSION')
        h,_=decoder.file_record(f,8192)
        need(h.get(b'op')==b'\x03' and struct.unpack('<Q',h[b'index_pos'])[0]==r17['index_position'], 'INDEX_OFFSET')
        f.seek(r17['index_position'])
        for _ in range(r17['connection_count']):
            h,_=decoder.file_record(f)
            need(h.get(b'op')==b'\x07','INDEX_CONNECTION_RECORD')
        last=-1
        totals={cid:0 for cid in conn}
        for _ in range(r17['chunk_count']):
            h,data=decoder.file_record(f)
            need(h.get(b'op')==b'\x06' and decoder.u32(h[b'ver'])==1,'INDEX_CHUNK_INFO')
            offset=struct.unpack('<Q',h[b'chunk_pos'])[0]
            count=decoder.u32(h[b'count'])
            need(last<offset<r17['index_position'] and len(data)==8*count,'INDEX_CHUNK_BOUNDS')
            last=offset
            ledger={}
            for j in range(count):
                cid,n=struct.unpack_from('<II',data,8*j)
                need(cid in conn and cid not in ledger and n>0,'INDEX_CHUNK_COUNT')
                ledger[cid]=n; totals[cid]+=n
            rows.append((offset,ledger))
        need(f.tell()==bag.stat().st_size,'INDEX_TRAILING_BYTES')
    need(sum(totals.values())==sum(x['record_count'] for x in r17['topic_inventory'].values()),'INDEX_TOTAL')
    for topic, cids in topic_cids.items():
        need(sum(totals[cid] for cid in cids)==r17['required_stream_counts'][topic], 'SENSOR_MESSAGE_COUNT')
    return rows, conn, topic_cids

def design(rows, topic_cids):
    selection={}; eligible_count={}
    for topic,cids in topic_cids.items():
        eligible=[offset for offset,counts in rows if any(counts.get(cid,0)>0 for cid in cids)]
        eligible_count[topic]=len(eligible)
        selection[topic]=[eligible[i] for i in positions(len(eligible))]
    need(sum(map(len,selection.values()))==32,'SAMPLE_CAP')
    unique=sorted({offset for offsets in selection.values() for offset in offsets})
    need(8<=len(unique)<=32,'CHUNK_CAP')
    return selection,eligible_count,unique

def limits(items, key):
    values=[s['descriptive_signal'][key] for s in items]
    need(len(values)==8 and all(type(x) in (int,float) and math.isfinite(x) for x in values),'METRIC:'+key)
    return {'min':float(min(values)),'max':float(max(values)),
            'mean':float(math.fsum(values)/len(values)),'observed_sample_count':len(values)}

def summarize(topic, items):
    if topic=='/camera/color/image_raw/compressed':
        return {'observed_image_sizes_px':sorted({str(s['descriptive_signal']['width'])+'x'+str(s['descriptive_signal']['height']) for s in items}),
                'grayscale_mean':limits(items,'grayscale_mean'),
                'grayscale_stddev':limits(items,'grayscale_stddev')}
    if topic in ('/camera/imu','/handsfree/imu'):
        return {'angular_velocity_norm_rad_s':limits(items,'angular_velocity_norm_rad_s'),
                'linear_acceleration_norm_m_s2':limits(items,'linear_acceleration_norm_m_s2'),
                'orientation_norm':limits(items,'orientation_norm')}
    if topic=='/velodyne_points':
        return {'point_count':limits(items,'point_count'),
                'finite_xyz_count':limits(items,'finite_xyz_count'),
                'range_min_m':limits(items,'range_min_m'),
                'range_max_m':limits(items,'range_max_m'),
                'all_xyz_finite_for_selected_samples':all(x['descriptive_signal']['all_xyz_finite'] for x in items)}
    raise ValueError('R23_DENIED:UNKNOWN_STREAM')

def execute(bag,arc,r22dev,r22out,report_path):
    sys.path.insert(0,str(arc/'r18')); sys.path.insert(0,str(r22dev))
    import r18_decode as decoder
    import r22_content as diag
    r17p=arc/'r17/r17_recorded_index.json'
    r18p=arc/'r18/r18_bounded_recorded_samples.json'
    r22p=r22out/'r22_recorded_content_diagnostics_v1.json'
    r17,r18,r22=(json.loads(p.read_text()) for p in (r17p,r18p,r22p))
    need(r17['trajectory_id']==r18['trajectory_id']==r22['trajectory_id']=='room_02' and r18['split']==r22['split']=='train','TRAIN_IDENTITY')
    need(r17['file_sha256']==r18['recording_sha256']==r22['bag_sha256'],'BAG_IDENTITY')
    need(r22['schema']=='TRUST_ROBOT_R22_TRAIN_ONLY_SIGNAL_DIAGNOSTICS_V1' and r22['sample_count']==8 and r22['sensor_stream_count']==4,'R22_SCHEMA')
    need(not r22['cross_modal_alignment_performed'] and not r22['health_features_frozen'] and not r22['real_sensor_factor_execution_authorized'],'R22_GATE')
    rows,conn,topic_cids=chunk_ledger(bag,r17,decoder)
    selection,eligible,offsets=design(rows,topic_cids)
    choices={off:{topic:i for topic,os in selection.items() for i,o in enumerate(os) if o==off} for off in offsets}
    samples={topic:[None]*8 for topic in decoder.NEEDED}
    count_by_offset={off:ledger for off,ledger in rows if off in choices}
    with bag.open('rb') as f:
        for off in offsets:
            raw,method=decoder.chunk_data(f,off)
            need(method in ('none','bz2'),'COMPRESSION_SUPPORT')
            observed={}; found=set()
            for cid,recordtime,body in decoder.messages(raw,conn):
                observed[cid]=observed.get(cid,0)+1
                topic=conn[cid]['topic']
                if topic not in choices[off] or topic in found:continue
                index=choices[off][topic]
                need(cid in topic_cids[topic],'TOPIC_CONNECTION')
                payload=body.tobytes()
                desc=diag.diagnostic(topic,payload,decoder)
                decoded=decoder.decode(topic,payload)
                need(all(decoded[k]==v for k,v in desc.items() if k in decoded),'DECODER_HEADER_DISAGREEMENT')
                samples[topic][index]={
                    'source':{'chunk_offset':off,'connection_id':cid,'bag_record_time_ns':recordtime,
                        'serialized_message_sha256':sha(payload),'serialized_message_bytes':len(payload),
                        'subset_index':index,'header_stamp_ns':desc['header_stamp_ns'],
                        'frame_id':desc['frame_id'],'sequence':desc['sequence']},
                    'descriptive_signal':desc}
                found.add(topic)
            need(observed==count_by_offset[off],'SAMPLED_CHUNK_INDEX_DISAGREEMENT')
            need(found==set(choices[off]),'MISSING_SELECTED_STREAM')
    need(all(len(v)==8 and all(x is not None for x in v) for v in samples.values()),'REQUIRED_32_SAMPLES')
    # First stratified chunk is exactly R18's first eligible chunk, by index design.
    for topic in decoder.NEEDED:
        first=samples[topic][0]['source']; old=r18['samples'][topic][0]
        need(all(first[k]==old[k] for k in ('chunk_offset','connection_id','bag_record_time_ns','serialized_message_sha256','serialized_message_bytes','header_stamp_ns','frame_id','sequence')),'R18_FIRST_SAMPLE_REPRODUCTION')
    by_topic={}
    for topic in decoder.NEEDED:
        count=r17['required_stream_counts'][topic]
        by_topic[topic]={
            'index_record_count':count,
            'index_eligible_chunk_count':eligible[topic],
            'selected_chunk_offsets':selection[topic],
            'selected_message_count':8,
            'selected_message_percent_of_full_topic':100.0*8/count,
            'selected_chunk_percent_of_eligible':100.0*8/eligible[topic],
            'observations':samples[topic],
            'descriptive_ranges':summarize(topic,samples[topic]),
            'qualitative_stability_inference_authorized':False,
        }
    result={'schema':'TRUST_ROBOT_R23_INDEX_STRATIFIED_TRAIN_DIAGNOSTICS_V1',
        'trajectory_id':'room_02','split':'train','bag_sha256':r17['file_sha256'],
        'git_baseline':'76685f1a6a97fb8e0750224bb927f1b094e63203',
        'source_hashes':{'r17_report_sha256':digest(r17p),'r18_report_sha256':digest(r18p),
            'r22_report_sha256':digest(r22p)},
        'sampling_rule':'eight integer-spaced chunk ordinals among chunks containing each named topic; first message of that topic within each selected chunk',
        'selection_based_on_index_metadata_only':True,
        'selected_per_topic':8,'sampled_message_count':32,'required_topics':4,
        'source_chunk_count':r17['chunk_count'],'inspected_unique_chunk_count':len(offsets),
        'indexed_required_stream_messages':sum(r17['required_stream_counts'].values()),
        'per_topic':by_topic,'health_features_selected':False,'health_labels_created':0,
        'statistical_stability_established':False,'random_sampling_claimed':False,
        'cross_modal_pairing_performed':False,'physical_capture_sync_verified':False,
        'extrinsics_verified':False,'reference_ground_truth_scored':False,
        'lidar_registration_executed':False,'image_odometry_executed':False,
        'imu_preintegration_executed':False,'real_pose_factors_generated':0,
        'real_sensor_factor_execution_authorized':False,'raw_bag_modified':False,'github_modified':False,
        'diagnostic_scope':'BOUNDED_DESCRIPTIVE_COVERAGE_ONLY_NOT_A_HEALTH_STABILITY_OR_ACCURACY_CLAIM'}
    with report_path.open('x',encoding='utf-8') as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    print('R23_AUTHENTIC_TRAIN_SAMPLES=32_DECODED')
    print('R23_SELECTED_UNIQUE_CHUNKS='+str(len(offsets)))
    for topic, item in by_topic.items():
        print('R23_TOPIC='+topic+' SAMPLES=8 INDEX_MESSAGES='+str(item['index_record_count'])+
              ' SAMPLED_PERCENT='+format(item['selected_message_percent_of_full_topic'],'.4f')+
              ' ELIGIBLE_CHUNKS='+str(item['index_eligible_chunk_count']))
    print('R23_STATISTICAL_STABILITY=NOT_ESTABLISHED')
    print('R23_FACTOR_ADMISSION=DENIED')

if __name__=='__main__':execute(*map(pathlib.Path,sys.argv[1:6]))
