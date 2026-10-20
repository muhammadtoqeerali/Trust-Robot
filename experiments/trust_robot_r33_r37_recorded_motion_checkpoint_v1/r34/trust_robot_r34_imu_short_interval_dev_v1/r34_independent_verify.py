"""R34 independent ROS1 source relocation and IMU arithmetic verification."""
import hashlib,json,math,pathlib,struct,sys
import r18_decode as ros
import r34_imu as engine

def need(ok,why):
    if not ok:raise ValueError('R34_INDEPENDENT_DENIED:'+why)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def close(x,y):
    if type(x) is bool or type(y) is bool:return x is y
    if x is None or y is None:return x is None and y is None
    if isinstance(x,(tuple,list)) and isinstance(y,(tuple,list)):
        return len(x)==len(y) and all(close(a,b) for a,b in zip(x,y))
    if isinstance(x,(int,float)) and isinstance(y,(int,float)):
        return math.isclose(x,y,abs_tol=1e-11,rel_tol=1e-9)
    return x==y

def parse(body):
    c=ros.Cursor(body); h=ros.header(c)
    val=struct.unpack('<37d',c.take(296));c.done()
    need(all(math.isfinite(v) for v in val),'FINITE_FIELDS')
    g=list(val[13:16]);a=list(val[25:28]);q=list(val[:4])
    return h,{'gyro_rad_s':g,'specific_force_m_s2':a,
      'gyro_norm_rad_s':math.hypot(*g),'specific_force_norm_m_s2':math.hypot(*a),
      'orientation_norm_as_recorded':math.sqrt(sum(x*x for x in q)),
      'orientation_covariance_unknown_sentinel':val[4]==-1.,
      'angular_covariance_unknown_sentinel':val[16]==-1.,
      'linear_covariance_unknown_sentinel':val[28]==-1.}

def recompute(a,b,dt_ns):
    dt=dt_ns/1000000000
    gyro=[dt*(a['gyro_rad_s'][i]+b['gyro_rad_s'][i])/2 for i in range(3)]
    force=[dt*(a['specific_force_m_s2'][i]+b['specific_force_m_s2'][i])/2 for i in range(3)]
    return {'observed_header_dt_s_not_verified_capture_time':dt,
        'mean_gyro_rad_s':[g/dt for g in gyro],
        'gyro_trapezoid_component_integrals_rad':gyro,
        'gyro_integral_vector_norm_rad':math.sqrt(sum(x*x for x in gyro)),
        'mean_specific_force_m_s2':[x/dt for x in force],
        'raw_specific_force_component_integrals_m_s':force,
        'specific_force_is_gravity_compensated':False,
        'rotation_estimate':None,'velocity_estimate':None,'position_estimate':None,'preintegration_factor':None}

def verify(bag,r17p,r18p,r33p,reportp,out):
    info=json.loads(r17p.read_text());r18=json.loads(r18p.read_text());r33=json.loads(r33p.read_text())
    report=json.loads(reportp.read_text());engine.safety(report)
    need(report['authenticated_bag_sha256']==info['file_sha256']==r18['recording_sha256']==r33['authenticated_bag_sha256'],'BAG_LINK')
    need(report['source_report_sha256']=={'r17':sha(r17p.read_bytes()),'r18':sha(r18p.read_bytes()),'r33':sha(r33p.read_bytes())},'REPORT_PINS')
    conns={c['id']:c for c in info['connections']}
    ids={t:next(c['id'] for c in info['connections'] if c['topic']==t) for t in engine.TOPICS}
    found={t:[] for t in engine.TOPICS}
    totals={t:0 for t in engine.TOPICS}
    with bag.open('rb') as f:
        need(ros.read_exact(f,13)==b'#ROSBAG V2.0\n','MAGIC')
        h,_=ros.file_record(f,8192)
        need(h.get(b'op')==b'\x03','HEADER')
        f.seek(struct.unpack('<Q',h[b'index_pos'])[0])
        for i in range(info['connection_count']):
            h,_=ros.file_record(f)
            need(h.get(b'op')==b'\x07','CONNECTION')
        for _ in range(info['chunk_count']):
            h,data=ros.file_record(f)
            need(h.get(b'op')==b'\x06','CHUNK_INFO')
            n=ros.u32(h[b'count'])
            need(len(data)==8*n,'LEDGER')
            records=[struct.unpack_from('<II',data,8*j) for j in range(n)]
            need(len({cid for cid,_ in records})==n and all(cid in conns and qty>0 for cid,qty in records),'LEDGER_IDS')
            ledger=dict(records)
            offset=struct.unpack('<Q',h[b'chunk_pos'])[0]
            for topic,cid in ids.items():
                count=ledger.get(cid,0);totals[topic]+=count
                if count>=2:found[topic].append((offset,ledger))
        need(totals=={t:info['required_stream_counts'][t] for t in engine.TOPICS},'MESSAGE_COUNTS')
        need(report['eligible_chunks_per_stream']=={t:len(v) for t,v in found.items()},'ELIGIBLE_COUNTS')
        checked=0
        for topic in engine.TOPICS:
            chunks=found[topic]
            picks=[chunks[i*(len(chunks)-1)//7] for i in range(8)]
            for k,(off,ledger) in enumerate(picks):
                pair=report['streams'][topic][k]
                need(pair['pair_index']==k,'PAIR_NUMBER')
                raw,mode=ros.chunk_data(f,off)
                observed={};got=[]
                for cid,bagtime,data in ros.messages(raw,conns):
                    observed[cid]=observed.get(cid,0)+1
                    if cid!=ids[topic] or len(got)==2:continue
                    blob=bytes(data)
                    header,signals=parse(blob)
                    got.append((dict(header,chunk_offset=off,connection_id=cid,
                        bag_record_time_ns=bagtime,serialized_message_bytes=len(blob),
                        serialized_message_sha256=sha(blob)),signals))
                need(observed==ledger and len(got)==2,'CHUNK_MESSAGE_COUNTS')
                for j,(rec,signals) in enumerate(got):
                    need(rec==pair['messages'][j],'MESSAGE_SOURCE')
                    need(all(close(value,pair['samples'][j][key]) for key,value in signals.items()),'RAW_IMU_VALUES')
                dt=got[1][0]['header_stamp_ns']-got[0][0]['header_stamp_ns']
                need(dt==pair['observed_header_gap_ns'] and dt>0,'SAMPLE_DT')
                independently=recompute(got[0][1],got[1][1],dt)
                need(all(close(v,pair['diagnostic'][key]) for key,v in independently.items()),'ARITHMETIC')
                checked+=2
    need(checked==32,'RECORD_COUNT')
    result={'schema':'TRUST_ROBOT_R34_INDEPENDENT_TWO_IMU_INTERVALS_V1',
        'source_report_sha256':sha(reportp.read_bytes()),'original_imu_messages_relocated':32,
        'independent_trapezoid_intervals_recomputed':16,
        'independent_chunk_schedule_rebuilt':True,'physical_capture_time_verified':False,
        'bias_and_gravity_calibrated':False,'imu_preintegration_or_pose_factor_authorized':False}
    with out.open('x') as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    print('R34_INDEPENDENT_ORIGINAL_IMU_MESSAGES=32_VERIFIED')
    print('R34_INDEPENDENT_SAME_STREAM_INTERVALS=16_RECOMPUTED')
    print('R34_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':verify(*map(pathlib.Path,sys.argv[1:7]))
