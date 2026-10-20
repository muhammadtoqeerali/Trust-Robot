"""TRAIN gyroscope 3-sample windows: numerical SO3 only, never pose."""
import hashlib, json, math, pathlib, struct, sys
import numpy as np
from scipy.spatial.transform import Rotation
import r18_decode as ros

TOPICS=('/camera/imu','/handsfree/imu')
FRAMES={
 '/camera/imu':'camera_imu_optical_frame',
 '/handsfree/imu':'base_link'
}
N=8
LOOKAHEAD=12
FLAGS=(
 'physical_capture_time_verified',
 'imu_bias_calibrated',
 'gravity_compensation_performed',
 'imu_preintegration_executed',
 'gyro_rotation_physically_qualified',
 'orientation_pose_measurement_authorized',
 'metric_velocity_estimated',
 'metric_position_estimated',
 'full_extrinsics_verified',
 'cross_modal_alignment_performed',
 'ground_truth_scored',
 'health_model_training_authorized',
 'm2dgr_scoring_authorized',
 'real_sensor_factor_execution_authorized',
 'statistical_stability_established',
 'raw_recording_modified',
 'github_modified'
)

def need(ok,why):
    if not ok:
        raise ValueError('R36_DENIED:'+why)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads(pathlib.Path(p).read_text())

def schedule(bag,index):
    need(
        index['schema']=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1'
        and index['trajectory_id']=='room_02'
        and index['chunk_count']==5182
        and index['connection_count']==15,
        'R17_IDENTITY'
    )
    conns={c['id']:c for c in index['connections']}
    ids={}
    for topic in TOPICS:
        found=[
            c['id'] for c in index['connections']
            if c['topic']==topic
            and c['message_type']=='sensor_msgs/Imu'
        ]
        need(len(found)==1,'IMU_TOPIC')
        ids[topic]=found[0]

    chunks={t:[] for t in TOPICS}
    totals={t:0 for t in TOPICS}

    with bag.open('rb') as f:
        need(
            ros.read_exact(f,13)==b'#ROSBAG V2.0\n',
            'BAG_HEADER'
        )
        hdr,_=ros.file_record(f,8192)
        need(hdr.get(b'op')==b'\x03','FILE_HEADER')
        pos=struct.unpack('<Q',hdr[b'index_pos'])[0]
        need(pos==index['index_position'],'INDEX_POSITION')
        f.seek(pos)

        for _ in range(index['connection_count']):
            h,_=ros.file_record(f)
            need(h.get(b'op')==b'\x07','CONNECTION_INDEX')

        used=set()
        for _ in range(index['chunk_count']):
            h,data=ros.file_record(f)
            need(h.get(b'op')==b'\x06','CHUNK_LEDGER')
            off=struct.unpack('<Q',h[b'chunk_pos'])[0]
            need(off not in used,'DUPLICATE_CHUNK')
            used.add(off)
            qty=ros.u32(h[b'count'])
            need(0<qty<=15 and len(data)==8*qty,'LEDGER_SIZE')

            ledger={}
            for k in range(qty):
                cid,count=struct.unpack_from('<II',data,8*k)
                need(
                    cid in conns and cid not in ledger
                    and count>0,
                    'LEDGER_CONNECTION'
                )
                ledger[cid]=count

            for topic,cid in ids.items():
                count=ledger.get(cid,0)
                totals[topic]+=count
                if count>=3:
                    chunks[topic].append((off,ledger))

    need(
        totals=={
            t:index['required_stream_counts'][t]
            for t in TOPICS
        },
        'MESSAGE_TOTALS'
    )
    need(
        all(
            len(chunks[t])>=N+LOOKAHEAD
            for t in TOPICS
        ),
        'INSUFFICIENT_TRIPLE_CHUNKS'
    )
    return chunks,conns,ids

def parse_imu(body):
    c=ros.Cursor(body)
    hdr=ros.header(c)
    vals=struct.unpack('<37d',c.take(296))
    c.done()
    need(all(math.isfinite(x) for x in vals),'IMU_FINITE')
    return hdr,{
        'gyro_rad_s':[float(x) for x in vals[13:16]],
        'specific_force_m_s2':[float(x) for x in vals[25:28]],
        'orientation_norm_as_recorded':
            float(math.sqrt(sum(x*x for x in vals[:4]))),
        'orientation_covariance_unknown_sentinel':
            bool(vals[4]==-1.0)
    }

def get_triple(f,off,ledger,conns,cid,topic):
    raw,compression=ros.chunk_data(f,off)
    need(compression in ('none','bz2'),'COMPRESSION')
    observed={}
    messages=[]

    for source,bagtime,view in ros.messages(raw,conns):
        observed[source]=observed.get(source,0)+1
        if source!=cid:
            continue

        body=bytes(view)
        hdr,signal=parse_imu(body)
        need(hdr['frame_id']==FRAMES[topic],'FRAME')
        messages.append((
            dict(
                hdr,
                chunk_offset=off,
                connection_id=cid,
                bag_record_time_ns=bagtime,
                serialized_message_bytes=len(body),
                serialized_message_sha256=sha(body)
            ),
            signal
        ))

    need(
        observed==ledger
        and len(messages)==ledger[cid],
        'CHUNK_MESSAGE_COUNT'
    )

    for k in range(len(messages)-2):
        seq=[
            messages[k+j][0]['sequence']
            for j in range(3)
        ]
        times=[
            messages[k+j][0]['header_stamp_ns']
            for j in range(3)
        ]
        if (
            seq[1]==seq[0]+1
            and seq[2]==seq[1]+1
            and 0<times[1]-times[0]<=100_000_000
            and 0<times[2]-times[1]<=100_000_000
        ):
            return messages[k:k+3]
    return None

def numerics(items):
    need(len(items)==3,'TRIPLE_SIZE')
    delta=[
        items[i+1][0]['header_stamp_ns']
        -items[i][0]['header_stamp_ns']
        for i in range(2)
    ]
    need(
        all(0<d<=100_000_000 for d in delta),
        'HEADER_GAPS'
    )

    rotations=[]
    for i,dt_ns in enumerate(delta):
        g0=np.asarray(
            items[i][1]['gyro_rad_s'],
            dtype=np.float64
        )
        g1=np.asarray(
            items[i+1][1]['gyro_rad_s'],
            dtype=np.float64
        )
        rotations.append(
            (g0+g1)*0.5*(dt_ns*1e-9)
        )

    R=(
        Rotation.from_rotvec(rotations[1])
        *Rotation.from_rotvec(rotations[0])
    )
    matrix=R.as_matrix()

    need(
        bool(np.isfinite(matrix).all())
        and abs(np.linalg.det(matrix)-1.0)<1e-10,
        'SO3_NUMERICAL'
    )

    vector=rotations[0]+rotations[1]
    return {
        'header_gaps_ns':delta,
        'midpoint_gyro_component_increments_rad':
            [v.tolist() for v in rotations],
        'nominal_gyro_sum_rotvec_rad':vector.tolist(),
        'two_step_composed_rotation_matrix_diagnostic':
            matrix.tolist(),
        'two_step_composed_rotation_angle_rad_diagnostic':
            float(R.magnitude()),
        'nominal_vector_sum_angle_rad':
            float(np.linalg.norm(vector)),
        'rotation_is_calibrated_robot_pose':False,
        'factor':None,
        'translation_m':None,
        'velocity_m_s':None
    }

def safety(r):
    need(
        r.get('schema')==
            'TRUST_ROBOT_R36_TRAIN_GYRO_THREE_SAMPLE_WINDOWS_V1'
        and r.get('trajectory_id')=='room_02'
        and r.get('split')=='train',
        'TRAIN_SCOPE'
    )
    need(
        r.get('window_count_per_stream')==8
        and r.get('source_message_count')==48
        and r.get('total_time_intervals')==32
        and set(r.get('streams',{}))==set(TOPICS),
        'COUNTS'
    )
    need(
        all(r.get(k) is False for k in FLAGS),
        'SCIENTIFIC_FLAGS'
    )
    need(
        all(
            type(r.get(k)) is int and r[k]==0
            for k in (
                'real_pose_factors_generated',
                'health_labels_generated',
                'new_sensor_acquisitions'
            )
        ),
        'SCIENTIFIC_COUNTS'
    )

    seen=set()
    for topic in TOPICS:
        windows=r['streams'][topic]
        need(
            len(windows)==8
            and [
                w['window_index'] for w in windows
            ]==list(range(8)),
            'WINDOW_SEQUENCE'
        )

        for w in windows:
            messages=w['messages']
            samples=w['samples']
            n=w['gyro_numerics']

            need(
                len(messages)==len(samples)==3,
                'WINDOW_TRIPLE'
            )
            need(
                len({
                    a['chunk_offset'] for a in messages
                })==1
                and all(
                    a['frame_id']==FRAMES[topic]
                    for a in messages
                ),
                'FRAME_CONSISTENCY'
            )
            need(
                all(
                    messages[j+1]['sequence']
                    ==messages[j]['sequence']+1
                    and 0<
                    messages[j+1]['header_stamp_ns']
                    -messages[j]['header_stamp_ns']
                    <=100_000_000
                    for j in range(2)
                ),
                'MONOTONIC_TRIPLE'
            )

            for a in messages:
                key=(
                    topic,
                    a['chunk_offset'],
                    a['serialized_message_sha256']
                )
                need(
                    key not in seen,
                    'DUPLICATE_SOURCE'
                )
                seen.add(key)

            need(
                n['factor'] is None
                and n['translation_m'] is None
                and n['velocity_m_s'] is None
                and n['rotation_is_calibrated_robot_pose']
                    is False,
                'NONFACTOR'
            )

            m=np.asarray(
                n['two_step_composed_rotation_matrix_diagnostic'],
                dtype=np.float64
            )
            need(
                m.shape==(3,3)
                and bool(np.isfinite(m).all())
                and np.linalg.norm(
                    m.T@m-np.eye(3)
                )<1e-8
                and abs(np.linalg.det(m)-1)<1e-8,
                'ORTHOGONALITY'
            )

    need(len(seen)==48,'UNIQUE_48')

def run(bag,r17p,r34p,r35p,out):
    index,r34,r35=map(
        load,(r17p,r34p,r35p)
    )
    need(
        index['file_sha256']
        ==r34['authenticated_bag_sha256']
        ==r35['authenticated_bag_sha256']
        and r34['trajectory_id']
        ==r35['trajectory_id']=='room_02'
        and r34['split']==r35['split']=='train',
        'SOURCE_BINDING'
    )
    need(
        r35['r34_source_report_sha256']
        ==sha(r34p.read_bytes())
        and r35['real_sensor_factor_execution_authorized']
            is False
        and r35['r35_reopened_raw_rosbag'] is False,
        'UPSTREAM_GATES'
    )

    eligible,conns,ids=schedule(bag,index)
    windows={}
    selected={}

    with bag.open('rb') as f:
        for topic in TOPICS:
            entries=eligible[topic]
            starts=[
                i*(len(entries)-LOOKAHEAD-1)//(N-1)
                for i in range(N)
            ]
            need(
                len(set(starts))==N,
                'ANCHOR_DISTINCT'
            )

            rows=[]
            for k,start in enumerate(starts):
                chosen=None

                for rank in range(
                    start,start+LOOKAHEAD+1
                ):
                    off,ledger=entries[rank]
                    trio=get_triple(
                        f,off,ledger,conns,
                        ids[topic],topic
                    )
                    if trio is not None:
                        chosen=(rank,trio)
                        break

                need(
                    chosen is not None,
                    'NO_VALID_TRIPLE_WINDOW:'
                    +topic+':'+str(k)
                )

                rank,trio=chosen
                row={
                    'window_index':k,
                    'anchor_eligible_rank':start,
                    'selected_eligible_rank':rank,
                    'messages':[v[0] for v in trio],
                    'samples':[v[1] for v in trio],
                    'gyro_numerics':numerics(trio),
                    'physically_qualified_rotation':False
                }
                rows.append(row)

                gaps=[
                    d*1e-6
                    for d in row['gyro_numerics'][
                        'header_gaps_ns'
                    ]
                ]
                angle=row['gyro_numerics'][
                    'two_step_composed_rotation_angle_rad_diagnostic'
                ]
                print(
                    'R36_STREAM=%s WINDOW=%d '
                    'HEADER_DT_MS=%.5f,%.5f '
                    'ANGLE_RAD=%.9f'
                    %(topic,k,gaps[0],gaps[1],angle)
                )

            windows[topic]=rows
            selected[topic]=len(entries)

    report={
        'schema':
            'TRUST_ROBOT_R36_TRAIN_GYRO_THREE_SAMPLE_WINDOWS_V1',
        'trajectory_id':'room_02',
        'split':'train',
        'github_baseline':
            'ebfd02b0ef8ad79b2e6a9810897fcb71efec2e87',
        'authenticated_bag_sha256':index['file_sha256'],
        'source_report_sha256':{
            'r17':sha(r17p.read_bytes()),
            'r34':sha(r34p.read_bytes()),
            'r35':sha(r35p.read_bytes())
        },
        'sampling_rule':
            'eight_index_spaced_three_or_more_IMU_message_chunk_anchors_first_valid_consecutive_triple_within_12_eligible_chunks',
        'eligible_chunks_with_three_or_more_stream_messages':
            selected,
        'window_count_per_stream':8,
        'source_message_count':48,
        'total_time_intervals':32,
        'streams':windows,
        'numerical_convention':
            'left_composed_exp_of_trapezoid_gyro_vectors_nominal_header_dt_in_native_sensor_axes',
        'interpretation':
            'gyro_only_SO3_numerical_exercises_not_physically_qualified_orientation_estimates',
        'real_pose_factors_generated':0,
        'health_labels_generated':0,
        'new_sensor_acquisitions':0,
        **{k:False for k in FLAGS}
    }

    safety(report)

    with out.open('x') as f:
        json.dump(
            report,f,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        f.write('\n')

    print('R36_AUTHENTIC_THREE_SAMPLE_GYRO_WINDOWS=16')
    print('R36_AUTHENTIC_IMU_MESSAGES=48')
    print('R36_SO3_ROTATIONS=NUMERICAL_ONLY_NOT_PHYSICALLY_QUALIFIED')

if __name__=='__main__':
    run(
        *(pathlib.Path(x) for x in sys.argv[1:6])
    )
