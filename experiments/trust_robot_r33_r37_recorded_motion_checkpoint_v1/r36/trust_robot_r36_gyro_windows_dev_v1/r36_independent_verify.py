"""Independent original IMU message replay and quaternion arithmetic."""
import hashlib,json,math,pathlib,struct,sys
import numpy as np
import r18_decode as ros

TOPICS=('/camera/imu','/handsfree/imu')
FRAMES={
 '/camera/imu':'camera_imu_optical_frame',
 '/handsfree/imu':'base_link'
}
LOOKAHEAD=12

def need(ok,why):
    if not ok:
        raise ValueError('R36_INDEPENDENT_DENIED:'+why)

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def quaternion(v):
    angle=math.sqrt(sum(x*x for x in v))
    if angle<1e-12:
        scale=0.5-angle*angle/48
    else:
        scale=math.sin(angle/2)/angle
    return (
        math.cos(angle/2),
        v[0]*scale,
        v[1]*scale,
        v[2]*scale
    )

def multiply(a,b):
    w,x,y,z=a
    t,p,q,r=b
    return (
        w*t-x*p-y*q-z*r,
        w*p+x*t+y*r-z*q,
        w*q-x*r+y*t+z*p,
        w*r+x*q-y*p+z*t
    )

def rotmat(q):
    w,x,y,z=q
    return [
        [
            1-2*(y*y+z*z),
            2*(x*y-w*z),
            2*(x*z+w*y)
        ],
        [
            2*(x*y+w*z),
            1-2*(x*x+z*z),
            2*(y*z-w*x)
        ],
        [
            2*(x*z-w*y),
            2*(y*z+w*x),
            1-2*(x*x+y*y)
        ]
    ]

def read_triple(handle,offset,ledger,conns,cid,topic):
    compressed,method=ros.chunk_data(
        handle,offset
    )
    need(method in ('none','bz2'),'COMPRESSION')
    totals={}
    messages=[]

    for current,bagtime,view in ros.messages(
        compressed,conns
    ):
        totals[current]=totals.get(current,0)+1
        if current!=cid:
            continue

        body=bytes(view)
        cursor=ros.Cursor(body)
        header=ros.header(cursor)
        value=struct.unpack(
            '<37d',cursor.take(296)
        )
        cursor.done()

        need(
            all(math.isfinite(v) for v in value),
            'IMU_FINITE'
        )
        need(
            header['frame_id']==FRAMES[topic],
            'FRAME'
        )

        messages.append((
            dict(
                header,
                chunk_offset=offset,
                connection_id=cid,
                bag_record_time_ns=bagtime,
                serialized_message_bytes=len(body),
                serialized_message_sha256=sha(body)
            ),
            {
                'gyro_rad_s':list(value[13:16]),
                'specific_force_m_s2':
                    list(value[25:28]),
                'orientation_norm_as_recorded':
                    math.sqrt(
                        sum(v*v for v in value[:4])
                    ),
                'orientation_covariance_unknown_sentinel':
                    value[4]==-1.0
            }
        ))

    need(
        totals==ledger
        and len(messages)==ledger[cid],
        'INDEX_COUNTS'
    )

    for i in range(len(messages)-2):
        seq=[
            messages[i+j][0]['sequence']
            for j in range(3)
        ]
        times=[
            messages[i+j][0]['header_stamp_ns']
            for j in range(3)
        ]
        if (
            seq[1]==seq[0]+1
            and seq[2]==seq[1]+1
            and 0<times[1]-times[0]<=100_000_000
            and 0<times[2]-times[1]<=100_000_000
        ):
            return messages[i:i+3]

    return None

def reconstruct(bag,index,topic_id):
    conns={
        x['id']:x for x in index['connections']
    }
    chunks={t:[] for t in TOPICS}
    totals={t:0 for t in TOPICS}

    with bag.open('rb') as f:
        need(
            ros.read_exact(f,13)
            ==b'#ROSBAG V2.0\n',
            'VERSION'
        )
        hdr,_=ros.file_record(f,8192)
        need(
            hdr.get(b'op')==b'\x03',
            'BAG_HEADER'
        )
        pos=struct.unpack(
            '<Q',hdr[b'index_pos']
        )[0]
        need(
            pos==index['index_position'],
            'OFFSET'
        )
        f.seek(pos)

        for _ in range(index['connection_count']):
            h,_=ros.file_record(f)
            need(
                h.get(b'op')==b'\x07',
                'CONNECTION'
            )

        for _ in range(index['chunk_count']):
            h,raw=ros.file_record(f)
            need(h.get(b'op')==b'\x06','INFO')
            off=struct.unpack(
                '<Q',h[b'chunk_pos']
            )[0]
            n=ros.u32(h[b'count'])
            need(
                len(raw)==8*n and 0<n<=15,
                'INFO_SIZE'
            )

            entries=[
                struct.unpack_from(
                    '<II',raw,i*8
                )
                for i in range(n)
            ]
            need(
                len({
                    cid for cid,_ in entries
                })==n
                and all(
                    cid in conns and ct>0
                    for cid,ct in entries
                ),
                'INFO_CONNECTIONS'
            )

            ledger=dict(entries)
            for topic,cid in topic_id.items():
                count=ledger.get(cid,0)
                totals[topic]+=count
                if count>=3:
                    chunks[topic].append(
                        (off,ledger)
                    )

    need(
        totals=={
            t:index['required_stream_counts'][t]
            for t in TOPICS
        },
        'SOURCE_COUNTS'
    )
    return chunks,conns

def verify(bag,r17p,r34p,r35p,reportp,out):
    index,r34,r35,report=map(
        load,(r17p,r34p,r35p,reportp)
    )

    need(
        report['schema']==
        'TRUST_ROBOT_R36_TRAIN_GYRO_THREE_SAMPLE_WINDOWS_V1',
        'REPORT_SCHEMA'
    )
    need(
        report['trajectory_id']=='room_02'
        and report['split']=='train'
        and report['source_message_count']==48
        and report['total_time_intervals']==32
        and report['window_count_per_stream']==8,
        'SCOPE'
    )
    need(
        report['authenticated_bag_sha256']
        ==index['file_sha256']
        ==r34['authenticated_bag_sha256']
        ==r35['authenticated_bag_sha256'],
        'BAG_SHA'
    )
    need(
        report['source_report_sha256']=={
            'r17':sha(r17p.read_bytes()),
            'r34':sha(r34p.read_bytes()),
            'r35':sha(r35p.read_bytes())
        },
        'SOURCE_PINS'
    )
    need(
        all(
            report[k] is False
            for k in (
                'physical_capture_time_verified',
                'imu_bias_calibrated',
                'imu_preintegration_executed',
                'orientation_pose_measurement_authorized',
                'real_sensor_factor_execution_authorized',
                'm2dgr_scoring_authorized',
                'health_model_training_authorized',
                'github_modified',
                'raw_recording_modified'
            )
        ),
        'NO_SCIENCE_PROMOTION'
    )
    need(
        report['real_pose_factors_generated']
        ==report['health_labels_generated']==0,
        'ZERO_SCIENCE'
    )

    ids={}
    for topic in TOPICS:
        found=[
            c['id'] for c in index['connections']
            if c['topic']==topic
        ]
        need(len(found)==1,'TOPIC_ID')
        ids[topic]=found[0]

    ledger,conns=reconstruct(
        bag,index,ids
    )
    seen=set()
    checked=0

    with bag.open('rb') as f:
        for topic in TOPICS:
            entries=ledger[topic]
            need(
                report[
                    'eligible_chunks_with_three_or_more_stream_messages'
                ][topic]==len(entries),
                'ELIGIBLE'
            )

            starts=[
                i*(len(entries)-LOOKAHEAD-1)//7
                for i in range(8)
            ]

            for k,start in enumerate(starts):
                result=report['streams'][topic][k]
                need(
                    result['window_index']==k
                    and result['anchor_eligible_rank']==start,
                    'INDEX_SCHEDULE'
                )

                found=None
                for rank in range(
                    start,start+LOOKAHEAD+1
                ):
                    off,counts=entries[rank]
                    raw=read_triple(
                        f,off,counts,conns,
                        ids[topic],topic
                    )
                    if raw is not None:
                        found=(rank,raw)
                        break

                need(
                    found is not None,
                    'INDEPENDENT_SCHEDULE_WINDOW'
                )

                rank,triplet=found
                need(
                    result['selected_eligible_rank']==rank,
                    'SELECTED_RANK'
                )
                need(
                    result['messages']
                    ==[x[0] for x in triplet]
                    and result['samples']
                    ==[x[1] for x in triplet],
                    'RAW_SOURCE_BYTES'
                )

                for meta,_ in triplet:
                    key=(
                        topic,
                        meta['chunk_offset'],
                        meta['serialized_message_sha256']
                    )
                    need(
                        key not in seen,
                        'REPEATED_SOURCE'
                    )
                    seen.add(key)

                dts=[
                    triplet[i+1][0]['header_stamp_ns']
                    -triplet[i][0]['header_stamp_ns']
                    for i in range(2)
                ]

                steps=[]
                for i,dt in enumerate(dts):
                    first=triplet[i][1]['gyro_rad_s']
                    second=triplet[i+1][1]['gyro_rad_s']
                    steps.append([
                        (first[j]+second[j])*0.5*dt/1e9
                        for j in range(3)
                    ])

                q=multiply(
                    quaternion(steps[1]),
                    quaternion(steps[0])
                )
                angle=2*math.atan2(
                    math.sqrt(
                        sum(v*v for v in q[1:])
                    ),
                    abs(q[0])
                )

                numeric=result['gyro_numerics']
                need(
                    numeric['header_gaps_ns']==dts,
                    'INTERVALS'
                )
                need(
                    np.allclose(
                        numeric[
                            'midpoint_gyro_component_increments_rad'
                        ],
                        steps,
                        atol=1e-12,
                        rtol=1e-11
                    ),
                    'INCREMENTS'
                )

                expected=[
                    steps[0][j]+steps[1][j]
                    for j in range(3)
                ]

                need(
                    np.allclose(
                        numeric['nominal_gyro_sum_rotvec_rad'],
                        expected,
                        atol=1e-12,
                        rtol=1e-11
                    ),
                    'VECTOR_SUM'
                )
                need(
                    np.allclose(
                        numeric[
                            'two_step_composed_rotation_matrix_diagnostic'
                        ],
                        rotmat(q),
                        atol=2e-10,
                        rtol=2e-10
                    ),
                    'QUATERNION_ROTATION'
                )
                need(
                    math.isclose(
                        numeric[
                            'two_step_composed_rotation_angle_rad_diagnostic'
                        ],
                        angle,
                        abs_tol=2e-10,
                        rel_tol=2e-10
                    ),
                    'ANGLE'
                )
                need(
                    math.isclose(
                        numeric['nominal_vector_sum_angle_rad'],
                        math.sqrt(
                            sum(z*z for z in expected)
                        ),
                        abs_tol=2e-10,
                        rel_tol=2e-10
                    ),
                    'VECTOR_ANGLE'
                )
                need(
                    numeric['factor'] is None
                    and result[
                        'physically_qualified_rotation'
                    ] is False,
                    'NO_FACTOR'
                )
                checked+=1

    need(
        checked==16 and len(seen)==48,
        'TOTAL_WINDOWS'
    )

    evidence={
        'schema':
            'TRUST_ROBOT_R36_INDEPENDENT_GYRO_WINDOW_REPLAY_V1',
        'source_report_sha256':
            sha(reportp.read_bytes()),
        'independent_index_schedules_rebuilt':2,
        'authentic_imu_messages_relocated':48,
        'independently_recomputed_three_sample_windows':16,
        'numerical_rotation_crosscheck':
            'PURE_PYTHON_QUATERNIONS_MATCH_SCIPY_SO3',
        'physical_rotation_qualified':False,
        'scientific_sensor_factors_authorized':False
    }

    with out.open('x') as f:
        json.dump(
            evidence,f,
            indent=2,
            sort_keys=True,
            allow_nan=False
        )
        f.write('\n')

    print('R36_INDEPENDENT_ROS_SOURCE_MESSAGES=48_VERIFIED')
    print('R36_INDEPENDENT_QUATERNION_SO3_WINDOWS=16_MATCHED')
    print('R36_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':
    verify(
        *(pathlib.Path(x) for x in sys.argv[1:7])
    )
