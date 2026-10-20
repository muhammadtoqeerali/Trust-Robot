"""Independent ROS bag image relocation, schedule, and LK recomputation."""
import hashlib, json, pathlib, struct, sys
import cv2, numpy as np
import r18_decode as ros
import r31_independent_verify as independent

def need(ok,reason):
    if not ok:
        raise ValueError('R33_INDEPENDENT_DENIED:'+reason)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def get(p):
    return json.loads(pathlib.Path(p).read_text())

def verify(bag,index_path,r18_path,r31_path,report_path,out):
    info,older,prior,report=map(
        get,(index_path,r18_path,r31_path,report_path)
    )
    need(
        report['schema']==
        'TRUST_ROBOT_R33_TRAIN_CAMERA_MULTIPAIR_PIXEL_DIAGNOSTICS_V1'
        and report['trajectory_id']=='room_02'
        and report['split']=='train'
        and report['pair_count']==8
        and report['frames_inspected']==16,
        'REPORT_SCOPE'
    )
    need(
        report['authenticated_bag_sha256']
        ==info['file_sha256']
        ==older['recording_sha256']
        ==prior['bag_sha256'],
        'RECORDING_SHA'
    )
    need(
        report['source_report_sha256']=={
            'r17':sha(index_path.read_bytes()),
            'r18':sha(r18_path.read_bytes()),
            'r31':sha(r31_path.read_bytes())
        },
        'SOURCE_PINS'
    )
    need(
        all(report[k] is False for k in (
            'real_sensor_factor_execution_authorized',
            'physical_capture_time_verified',
            'cross_modal_alignment_performed',
            'six_dof_pose_estimated',
            'm2dgr_scoring_authorized',
            'health_model_training_authorized',
            'github_modified',
            'raw_recording_modified'
        )),
        'SCIENTIFIC_FLAGS'
    )
    need(
        report['real_pose_factors_generated']
        ==report['health_labels_generated']==0,
        'ZERO_FACTORS'
    )

    conns={c['id']:c for c in info['connections']}
    ids=[
        c['id'] for c in info['connections']
        if c['topic']=='/camera/color/image_raw/compressed'
    ]
    need(
        len(ids)==1 and info['chunk_count']==5182,
        'CAMERA_CONNECTION'
    )
    cid=ids[0]
    eligible=[]

    with bag.open('rb') as f:
        need(
            ros.read_exact(f,13)==b'#ROSBAG V2.0\n',
            'BAG_HEADER'
        )
        h,_=ros.file_record(f,8192)
        need(h.get(b'op')==b'\x03','FILE_HEADER')
        pos=struct.unpack('<Q',h[b'index_pos'])[0]
        need(pos==info['index_position'],'INDEX_POSITION')
        f.seek(pos)

        for _ in range(info['connection_count']):
            h,_=ros.file_record(f)
            need(h.get(b'op')==b'\x07','INDEX_CONNECTION')

        total=0
        for _ in range(info['chunk_count']):
            h,data=ros.file_record(f)
            need(h.get(b'op')==b'\x06','CHUNK_OP')
            n=ros.u32(h[b'count'])
            need(len(data)==8*n,'LEDGER_SIZE')
            rows=[
                struct.unpack_from('<II',data,8*j)
                for j in range(n)
            ]
            need(
                len(set(c for c,_ in rows))==n
                and all(
                    c in conns and ct>0
                    for c,ct in rows
                ),
                'LEDGER_ITEMS'
            )
            ledger=dict(rows)
            if cid in ledger:
                eligible.append((
                    struct.unpack('<Q',h[b'chunk_pos'])[0],
                    ledger
                ))
                total+=ledger[cid]

        need(
            len(eligible)==1063
            and total==1113
            and len(set(o for o,_ in eligible))==1063,
            'INDEX_CAMERA_COUNTS'
        )
        anchors=[
            (k*(len(eligible)-2))//7
            for k in range(8)
        ]
        need(
            len({j for k in anchors for j in (k,k+1)})==16,
            'ANCHOR_UNIQUENESS'
        )
        need(
            len(report['pairs'])==8
            and report['chunks_read']==16
            and report['eligible_camera_chunks']==1063,
            'REPORT_COUNT'
        )

        used=set()
        for k,a in enumerate(anchors):
            pair=report['pairs'][k]
            need(
                pair['pair_index']==k
                and pair['anchor_chunk_offset']==eligible[a][0]
                and pair['next_indexed_camera_chunk_offset']
                ==eligible[a+1][0],
                'SCHEDULE'
            )
            selected=[]

            for off,expected in (eligible[a],eligible[a+1]):
                observed={}
                raw,mode=ros.chunk_data(f,off)
                need(mode in ('none','bz2'),'COMPRESSION')

                for c,bagtime,body in ros.messages(raw,conns):
                    observed[c]=observed.get(c,0)+1
                    if c!=cid:
                        continue

                    blob=bytes(body)
                    cursor=ros.Cursor(blob)
                    hdr=ros.header(cursor)
                    fmt=cursor.text(256)
                    n=cursor.number()
                    jpg=cursor.take(n).tobytes()
                    cursor.done()

                    need(
                        'jpeg' in fmt.lower()
                        and sha(jpg)==ros.decode(
                            '/camera/color/image_raw/compressed',
                            blob
                        )['image_payload_sha256'],
                        'JPEG_DECODE'
                    )
                    img=cv2.imdecode(
                        np.frombuffer(jpg,dtype=np.uint8),
                        cv2.IMREAD_GRAYSCALE
                    )
                    need(
                        img is not None
                        and img.shape==(480,640),
                        'GRAYSCALE'
                    )

                    selected.append(({
                        'chunk_offset':off,
                        'connection_id':c,
                        'bag_record_time_ns':bagtime,
                        'serialized_message_bytes':len(blob),
                        'serialized_message_sha256':sha(blob),
                        'jpeg_payload_sha256':sha(jpg),
                        'decoded_grayscale_sha256':sha(img.tobytes()),
                        'frame_id':hdr['frame_id'],
                        'header_stamp_ns':hdr['header_stamp_ns'],
                        'sequence':hdr['sequence'],
                        'width':640,
                        'height':480
                    },img))

                need(observed==expected,'CHUNK_LEDGER_MISMATCH')

            selected=selected[:2]
            need(
                len(selected)==2
                and [x[0] for x in selected]==pair['frames'],
                'SOURCE_FRAMES_'+str(k)
            )
            need(
                pair['frames'][1]['sequence']
                ==pair['frames'][0]['sequence']+1
                and pair['header_gap_ns']
                ==pair['frames'][1]['header_stamp_ns']
                -pair['frames'][0]['header_stamp_ns']>0,
                'FRAME_SEQUENCE'
            )

            for rec,_ in selected:
                ident=(
                    rec['chunk_offset'],
                    rec['serialized_message_sha256']
                )
                need(ident not in used,'DUPLICATE_FRAME')
                used.add(ident)

            recalculated=independent.standalone_lk(
                selected[0][1],selected[1][1]
            )
            claimed=pair['pixel_motion']

            for key,val in recalculated.items():
                actual=claimed[key]
                if val is None:
                    need(actual is None,'LK_NONE_'+key)
                elif isinstance(val,int):
                    need(
                        type(actual) is int and actual==val,
                        'LK_COUNT_'+key
                    )
                else:
                    need(
                        type(actual) is float
                        and bool(np.isclose(
                            actual,val,atol=1e-7,rtol=1e-7
                        )),
                        'LK_VALUE_'+key
                    )

            need(
                claimed['metric_translation_m'] is None
                and claimed['camera_pose_factor'] is None
                and pair['metric_pose_qualified'] is False,
                'NO_POSE'
            )

            if k==0:
                need(
                    len(pair['frames'])==len(prior['frames'])==2
                    and all(
                        all(frame.get(key)==value for key,value in old.items())
                        for frame,old in zip(pair['frames'],prior['frames'])
                    ),
                    'R31_SOURCE_REPLAY'
                )
                need(
                    claimed==prior['pixel_motion'],
                    'R31_LK_REPLAY'
                )

    need(len(used)==16,'SOURCE_MESSAGE_COUNT')

    result={
        'schema':
            'TRUST_ROBOT_R33_INDEPENDENT_CAMERA_MULTIPAIR_V1',
        'source_report_sha256':sha(report_path.read_bytes()),
        'independently_reconstructed_index_schedule':True,
        'recorded_camera_messages_verified':16,
        'independently_recomputed_pair_tracks':8,
        'r31_baseline_identical':True,
        'physical_timing_qualified':False,
        'real_sensor_factors_authorized':False
    }

    with out.open('x') as f:
        json.dump(
            result,f,indent=2,sort_keys=True,allow_nan=False
        )
        f.write('\n')

    print('R33_INDEPENDENT_INDEX_SCHEDULE=8_PAIRS_RECONSTRUCTED')
    print('R33_INDEPENDENT_SERIALIZED_IMAGES=16_VERIFIED')
    print('R33_INDEPENDENT_LK_RECOMPUTATIONS=8_NUMERIC_MATCH')
    print('R33_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':
    verify(*map(pathlib.Path,sys.argv[1:7]))
