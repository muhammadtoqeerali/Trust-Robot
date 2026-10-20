"""R34: two same-stream IMU messages per chunk, TRAIN only; NOT preintegration."""
import hashlib, json, math, pathlib, struct, sys
import r18_decode as ros

TOPICS=('/camera/imu','/handsfree/imu')
PAIRS=8
FLAGS=(
 'physical_capture_time_verified','imu_bias_calibrated','gravity_compensation_performed',
 'imu_preintegration_executed','metric_velocity_estimated','metric_position_estimated',
 'cross_modal_alignment_performed','full_extrinsics_verified','ground_truth_scored',
 'health_model_training_authorized','real_sensor_factor_execution_authorized',
 'm2dgr_scoring_authorized','statistical_stability_established',
 'raw_recording_modified','github_modified'
)

def need(ok,why):
    if not ok: raise ValueError('R34_DENIED:'+why)

def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(pathlib.Path(path).read_text())

def schedule(bag,info):
    need(info['schema']=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1' and
         info['trajectory_id']=='room_02' and info['chunk_count']==5182 and
         info['connection_count']==15,'INDEX_IDENTITY')
    conns={row['id']:row for row in info['connections']}
    stream_ids={}
    for topic in TOPICS:
        matching=[c['id'] for c in info['connections'] if
                  c['topic']==topic and c['message_type']=='sensor_msgs/Imu']
        need(len(matching)==1,'IMU_STREAM:'+topic)
        stream_ids[topic]=matching[0]
    eligible={topic:[] for topic in TOPICS}
    counted={topic:0 for topic in TOPICS}
    with bag.open('rb') as f:
        need(ros.read_exact(f,13)==b'#ROSBAG V2.0\n','BAG_MAGIC')
        h,_=ros.file_record(f,8192)
        need(h.get(b'op')==b'\x03','BAG_HEADER')
        pos=struct.unpack('<Q',h[b'index_pos'])[0]
        need(pos==info['index_position'],'INDEX_POSITION')
        f.seek(pos)
        for _ in range(info['connection_count']):
            h,_=ros.file_record(f)
            need(h.get(b'op')==b'\x07','CONNECTION_INDEX')
        for _ in range(info['chunk_count']):
            h,data=ros.file_record(f)
            need(h.get(b'op')==b'\x06','CHUNK_INDEX')
            offset=struct.unpack('<Q',h[b'chunk_pos'])[0]
            n=ros.u32(h[b'count'])
            need(0<n<=15 and len(data)==8*n,'LEDGER_LENGTH')
            ledger={}
            for i in range(n):
                cid,cnt=struct.unpack_from('<II',data,8*i)
                need(cid in conns and cid not in ledger and cnt>0,'LEDGER_ENTRY')
                ledger[cid]=cnt
            for topic,cid in stream_ids.items():
                num=ledger.get(cid,0)
                counted[topic]+=num
                if num>=2:
                    eligible[topic].append((offset,ledger))
    need(counted=={t:info['required_stream_counts'][t] for t in TOPICS},'STREAM_TOTALS')
    chosen={}
    for topic,items in eligible.items():
        need(len(items)>=PAIRS,'INSUFFICIENT_TWO_IMU_CHUNKS:'+topic)
        indices=[i*(len(items)-1)//(PAIRS-1) for i in range(PAIRS)]
        need(len(set(indices))==PAIRS,'REPEATED_INDEX_ANCHORS')
        chosen[topic]=[items[i] for i in indices]
    return chosen,conns,stream_ids,{t:len(x) for t,x in eligible.items()}

def read_imu(body):
    cursor=ros.Cursor(body)
    head=ros.header(cursor)
    raw=cursor.take(37*8).tobytes()
    cursor.done()
    vals=struct.unpack('<37d',raw)
    need(all(math.isfinite(x) for x in vals),'NONFINITE_IMU')
    quat=vals[:4]; gyro=vals[13:16]; accel=vals[25:28]
    return head,{
      'gyro_rad_s':[float(x) for x in gyro],
      'specific_force_m_s2':[float(x) for x in accel],
      'gyro_norm_rad_s':float(math.sqrt(sum(x*x for x in gyro))),
      'specific_force_norm_m_s2':float(math.sqrt(sum(x*x for x in accel))),
      'orientation_norm_as_recorded':float(math.sqrt(sum(x*x for x in quat))),
      'orientation_covariance_unknown_sentinel':bool(vals[4]==-1.0),
      'angular_covariance_unknown_sentinel':bool(vals[16]==-1.0),
      'linear_covariance_unknown_sentinel':bool(vals[28]==-1.0),
    }

def measure(a,b,dt_ns):
    need(type(dt_ns) is int and dt_ns>0,'NONPOSITIVE_HEADER_INTERVAL')
    dt=dt_ns*1e-9
    av=[(x+y)*0.5 for x,y in zip(a['gyro_rad_s'],b['gyro_rad_s'])]
    sf=[(x+y)*0.5 for x,y in zip(a['specific_force_m_s2'],b['specific_force_m_s2'])]
    return {
      'observed_header_dt_s_not_verified_capture_time':dt,
      'mean_gyro_rad_s':av,
      'gyro_trapezoid_component_integrals_rad':[x*dt for x in av],
      'gyro_integral_vector_norm_rad':math.sqrt(sum((x*dt)**2 for x in av)),
      'mean_specific_force_m_s2':sf,
      'raw_specific_force_component_integrals_m_s':[x*dt for x in sf],
      'specific_force_is_gravity_compensated':False,
      'rotation_estimate':None,'velocity_estimate':None,'position_estimate':None,
      'preintegration_factor':None,
    }

def safety(d):
    need(d.get('schema')=='TRUST_ROBOT_R34_TRAIN_TWO_IMU_BOUNDED_INTERVALS_V1'
         and d.get('trajectory_id')=='room_02' and d.get('split')=='train','TRAIN')
    need(d.get('stream_count')==2 and d.get('pairs_per_stream')==8
         and d.get('serialized_imu_messages_inspected')==32,'COUNTS')
    need(all(d.get(k) is False for k in FLAGS),'CLOSED_GATES')
    need(all(type(d.get(k)) is int and d[k]==0 for k in
         ('real_pose_factors_generated','health_labels_generated','new_sensor_acquisitions')),'ZERO_OUTPUTS')
    need(set(d.get('streams',{}))==set(TOPICS),'STREAM_KEYS')
    seen=set()
    for topic in TOPICS:
        pairs=d['streams'][topic]
        need(len(pairs)==PAIRS and [p['pair_index'] for p in pairs]==list(range(PAIRS)),'PAIR_IDS')
        for pair in pairs:
            sources=pair['messages']
            need(len(sources)==2 and sources[0]['chunk_offset']==sources[1]['chunk_offset']
                 and sources[1]['sequence']==sources[0]['sequence']+1
                 and sources[1]['header_stamp_ns']>sources[0]['header_stamp_ns']
                 and sources[0]['frame_id']==sources[1]['frame_id'],'CONSECUTIVE')
            need(pair['observed_header_gap_ns']==sources[1]['header_stamp_ns']-sources[0]['header_stamp_ns'],'GAP')
            for s in sources:
                key=(topic,s['chunk_offset'],s['serialized_message_sha256'])
                need(key not in seen,'SOURCE_DUPLICATE')
                seen.add(key)
            m=pair['diagnostic']
            need(m['specific_force_is_gravity_compensated'] is False
                 and all(m[field] is None for field in
                  ('rotation_estimate','velocity_estimate','position_estimate','preintegration_factor')),'NONFACTOR')
    need(len(seen)==32,'UNIQUE_COUNT')

def run(bag,r17p,r18p,r33p,out):
    info,r18,r33=map(load,(r17p,r18p,r33p))
    need(info['trajectory_id']==r18['trajectory_id']==r33['trajectory_id']=='room_02'
         and r18['split']==r33['split']=='train'
         and info['file_sha256']==r18['recording_sha256']==r33['authenticated_bag_sha256'],'SOURCE_CHAIN')
    need(r33['real_sensor_factor_execution_authorized'] is False
         and r33['real_pose_factors_generated']==0,'PRIOR_SCIENCE_GATE')
    chosen,conns,stream_ids,eligible=schedule(bag,info)
    original={t:r18['samples'][t][0] for t in TOPICS}
    streams={}
    with bag.open('rb') as f:
        for topic,selected in chosen.items():
            rows=[]
            cid=stream_ids[topic]
            for k,(offset,ledger) in enumerate(selected):
                raw,mode=ros.chunk_data(f,offset)
                need(mode in r18['compression_methods'],'COMPRESSION_METHOD')
                counts={};messages=[]
                for source_cid,bag_time,view in ros.messages(raw,conns):
                    counts[source_cid]=counts.get(source_cid,0)+1
                    if source_cid!=cid:continue
                    if len(messages)>=2:continue
                    body=bytes(view)
                    head,signals=read_imu(body)
                    meta=dict(head,chunk_offset=offset,connection_id=cid,
                        bag_record_time_ns=bag_time,
                        serialized_message_bytes=len(body),
                        serialized_message_sha256=sha(body))
                    messages.append((meta,signals))
                need(counts==ledger and len(messages)==2,'INDEX_RECORD_COUNTS')
                if offset==original[topic]['chunk_offset']:
                    need(all(messages[0][0][key]==original[topic][key]
                             for key in ('sequence','frame_id','header_stamp_ns','bag_record_time_ns','serialized_message_sha256')),
                         'R18_FIRST_MESSAGE_REPLAY')
                a,b=messages
                need(b[0]['sequence']==a[0]['sequence']+1
                     and b[0]['header_stamp_ns']>a[0]['header_stamp_ns']
                     and a[0]['frame_id']==b[0]['frame_id'],'IMU_ORDER')
                dt=b[0]['header_stamp_ns']-a[0]['header_stamp_ns']
                rows.append({'pair_index':k,'messages':[a[0],b[0]],
                             'samples':[a[1],b[1]],'observed_header_gap_ns':dt,
                             'diagnostic':measure(a[1],b[1],dt)})
                print('R34_STREAM=%s PAIR=%d DT_MS=%.6f GYRO_INTEGRAL_RAD=%.9f' %
                     (topic,k,dt*1e-6,rows[-1]['diagnostic']['gyro_integral_vector_norm_rad']))
            streams[topic]=rows
    report={
        'schema':'TRUST_ROBOT_R34_TRAIN_TWO_IMU_BOUNDED_INTERVALS_V1',
        'trajectory_id':'room_02','split':'train',
        'github_baseline':'ebfd02b0ef8ad79b2e6a9810897fcb71efec2e87',
        'authenticated_bag_sha256':info['file_sha256'],
        'source_report_sha256':{'r17':sha(r17p.read_bytes()),'r18':sha(r18p.read_bytes()),'r33':sha(r33p.read_bytes())},
        'sampling_rule':'eight_evenly_spaced_chunks_with_at_least_two_same_stream_IMU_messages_per_topic',
        'eligible_chunks_per_stream':eligible,'stream_count':2,'pairs_per_stream':8,
        'serialized_imu_messages_inspected':32,'streams':streams,
        'interpretation':'raw_gyro_and_specific_force_two_sample_descriptive_trapezoids_not_pose_or_preintegration',
        'real_pose_factors_generated':0,'health_labels_generated':0,'new_sensor_acquisitions':0,
        **{k:False for k in FLAGS}
    }
    safety(report)
    with out.open('x') as f:
        json.dump(report,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print('R34_REAL_IMU_STREAMS=2')
    print('R34_RECORDED_TWO_SAMPLE_INTERVALS=16')
    print('R34_RECORDED_IMU_MESSAGES=32')
    print('R34_NO_GRAVITY_COMPENSATION_OR_PREINTEGRATION=CONFIRMED')

if __name__=='__main__':run(*map(pathlib.Path,sys.argv[1:6]))
