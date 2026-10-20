"""R33: bounded TRAIN-only adjacent camera-frame pixel diagnostics, never pose factors."""
import hashlib, json, pathlib, struct, sys
import cv2, numpy as np
import r18_decode as ros
import r31_camera as base

TOPIC='/camera/color/image_raw/compressed'
N=8
FLAGS=(
 'physical_capture_time_verified',
 'cross_modal_alignment_performed',
 'camera_intrinsics_physically_verified',
 'metric_scale_established',
 'six_dof_pose_estimated',
 'visual_odometry_authorized',
 'full_extrinsics_verified',
 'ground_truth_scored',
 'health_model_training_authorized',
 'real_sensor_factor_execution_authorized',
 'm2dgr_scoring_authorized',
 'confidence_calibrated',
 'statistical_stability_established',
 'raw_recording_modified',
 'github_modified'
)

def need(ok,why):
    if not ok: raise ValueError('R33_DENIED:'+why)

def digest(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads(pathlib.Path(p).read_text())

def schedule(bag,index):
    need(
        index['schema']=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1'
        and index['chunk_count']==5182
        and index['connection_count']==15,
        'INDEX_SCOPE'
    )
    ids=[
        c['id'] for c in index['connections']
        if c['topic']==TOPIC
        and c['message_type']=='sensor_msgs/CompressedImage'
    ]
    need(
        len(ids)==1 and index['required_stream_counts'][TOPIC]==1113,
        'CAMERA_CONNECTION'
    )
    cid=ids[0]
    conns={x['id']:x for x in index['connections']}
    chunks=[]
    total=0

    with bag.open('rb') as f:
        need(ros.read_exact(f,13)==b'#ROSBAG V2.0\n','BAG_VERSION')
        h,_=ros.file_record(f,8192)
        need(h.get(b'op')==b'\x03','FILE_HEADER')
        position=struct.unpack('<Q',h[b'index_pos'])[0]
        need(position==index['index_position'],'INDEX_POSITION')
        f.seek(position)

        for _ in range(index['connection_count']):
            hh,_=ros.file_record(f)
            need(hh.get(b'op')==b'\x07','INDEX_CONNECTION')

        for _ in range(index['chunk_count']):
            hh,data=ros.file_record(f)
            need(hh.get(b'op')==b'\x06','INDEX_CHUNK')
            offset=struct.unpack('<Q',hh[b'chunk_pos'])[0]
            n=ros.u32(hh[b'count'])
            need(len(data)==8*n and n>0,'CHUNK_LEDGER_SIZE')
            ledger={}
            for j in range(n):
                x,count=struct.unpack_from('<II',data,8*j)
                need(
                    x in conns and x not in ledger and count>0,
                    'CHUNK_LEDGER'
                )
                ledger[x]=count
            if cid in ledger:
                chunks.append((offset,ledger))
                total+=ledger[cid]

    need(
        total==1113
        and len(chunks)==1063
        and len({o for o,_ in chunks})==1063,
        'CAMERA_INDEX_COUNTS'
    )
    anchors=[
        (i*(len(chunks)-2))//(N-1)
        for i in range(N)
    ]
    need(
        len(set(anchors))==N
        and len({j for i in anchors for j in (i,i+1)})==2*N,
        'PAIR_ANCHORS'
    )
    return [(chunks[i],chunks[i+1]) for i in anchors],conns,cid

def get_chunk(f,offset,ledger,conns,cid):
    raw,mode=ros.chunk_data(f,offset)
    need(mode in ('none','bz2'),'COMPRESSION')
    observed={}
    items=[]

    for c,t,view in ros.messages(raw,conns):
        observed[c]=observed.get(c,0)+1
        if c!=cid:
            continue

        body=bytes(view)
        decoded=ros.decode(TOPIC,body)
        cursor=ros.Cursor(body)
        hdr=ros.header(cursor)
        fmt=cursor.text(256)
        n=cursor.number()
        jpg=cursor.take(n).tobytes()
        cursor.done()

        need(
            'jpeg' in fmt.lower()
            and n==decoded['compressed_image_bytes']
            and digest(jpg)==decoded['image_payload_sha256'],
            'JPEG_ENCODING_AND_DIGEST'
        )

        img=cv2.imdecode(
            np.frombuffer(jpg,dtype=np.uint8),
            cv2.IMREAD_GRAYSCALE
        )
        need(
            img is not None
            and img.shape==(480,640)
            and img.dtype==np.uint8,
            'IMAGE_FORMAT'
        )

        record={
            'chunk_offset':offset,
            'connection_id':c,
            'bag_record_time_ns':t,
            'serialized_message_bytes':len(body),
            'serialized_message_sha256':digest(body),
            'jpeg_payload_sha256':digest(jpg),
            'decoded_grayscale_sha256':digest(img.tobytes()),
            'header_stamp_ns':hdr['header_stamp_ns'],
            'frame_id':hdr['frame_id'],
            'sequence':hdr['sequence'],
            'width':640,
            'height':480
        }
        need(
            hdr['frame_id']=='camera_color_optical_frame'
            and decoded['sequence']==hdr['sequence']
            and decoded['header_stamp_ns']==hdr['header_stamp_ns'],
            'HEADER'
        )
        items.append((record,img))

    need(
        observed==ledger and len(items)==ledger[cid],
        'CHUNK_MESSAGE_COUNTS'
    )
    return items

def safety(d):
    need(
        d.get('schema')==
        'TRUST_ROBOT_R33_TRAIN_CAMERA_MULTIPAIR_PIXEL_DIAGNOSTICS_V1'
        and d.get('trajectory_id')=='room_02'
        and d.get('split')=='train',
        'SCOPE'
    )
    need(
        d.get('pair_count')==8
        and d.get('frames_inspected')==16
        and d.get('chunks_read')==16
        and len(d.get('pairs',[]))==8,
        'COUNTS'
    )
    need(all(d.get(k) is False for k in FLAGS),'SCIENTIFIC_FLAGS')
    need(
        all(
            type(d.get(k)) is int and d[k]==0
            for k in (
                'real_pose_factors_generated',
                'health_labels_generated',
                'new_sensor_acquisitions'
            )
        ),
        'SCIENTIFIC_COUNTS'
    )
    need(
        [p.get('pair_index') for p in d['pairs']]==list(range(N)),
        'ORDER'
    )

    unique=set()
    for p in d['pairs']:
        images=p.get('frames',[])
        need(
            len(images)==2
            and images[1]['sequence']==images[0]['sequence']+1
            and images[1]['header_stamp_ns']>images[0]['header_stamp_ns'],
            'ADJACENT_HEADERS'
        )
        need(
            p.get('header_gap_ns')==
            images[1]['header_stamp_ns']-images[0]['header_stamp_ns']>0,
            'TIMING'
        )
        for a in images:
            key=(a['chunk_offset'],a['serialized_message_sha256'])
            need(
                key not in unique
                and a['frame_id']=='camera_color_optical_frame'
                and a['width']==640
                and a['height']==480,
                'FRAME_IDENTITY'
            )
            unique.add(key)

        m=p.get('pixel_motion',{})
        need(
            m.get('metric_translation_m') is None
            and m.get('camera_rotation_radians') is None
            and m.get('camera_pose_factor') is None,
            'NO_POSE'
        )
        need(
            type(m.get('initial_corner_count')) is int
            and type(m.get('forward_backward_consistent_count')) is int
            and 0<=m['forward_backward_consistent_count']
            <=m['initial_corner_count']<=400,
            'TRACK_COUNTS'
        )

    need(len(unique)==16,'UNIQUE_FRAMES')

def run(bag,index_path,r18_path,r31_path,out):
    index,r18,r31=map(
        load,(index_path,r18_path,r31_path)
    )
    need(
        index['trajectory_id']==r18['trajectory_id']
        ==r31['trajectory_id']=='room_02'
        and index['file_sha256']==r18['recording_sha256']
        ==r31['bag_sha256'],
        'RECORDING_CHAIN'
    )
    need(
        r18['split']=='train'
        and r31['split']=='train'
        and r31['real_sensor_factor_execution_authorized'] is False
        and r31['real_pose_factors_generated']==0,
        'TRAIN_GATES'
    )

    pairs,conns,cid=schedule(bag,index)
    results=[]

    with bag.open('rb') as f:
        for k,(left,right) in enumerate(pairs):
            first=get_chunk(f,left[0],left[1],conns,cid)
            second=get_chunk(f,right[0],right[1],conns,cid)
            selected=(first+second)[:2]
            need(len(selected)==2,'MISSING_FRAMES')

            frames=[a[0] for a in selected]
            need(
                frames[1]['sequence']==frames[0]['sequence']+1
                and frames[1]['header_stamp_ns']
                >frames[0]['header_stamp_ns'],
                'NONCONSECUTIVE_SELECTED_FRAMES'
            )
            motion=base.track(
                selected[0][1],selected[1][1]
            )
            if k==0:
                need(
                    len(frames)==len(r31['frames'])==2
                    and all(
                        all(frame.get(key)==value for key,value in old.items())
                        for frame,old in zip(frames,r31['frames'])
                    ),
                    'R31_SOURCE_BASELINE'
                )
                for key,val in r31['pixel_motion'].items():
                    actual=motion[key]
                    if isinstance(val,float):
                        need(
                            actual is not None
                            and bool(np.isclose(
                                val,actual,rtol=1e-8,atol=1e-8
                            )),
                            'R31_MOTION_'+key
                        )
                    else:
                        need(val==actual,'R31_MOTION_'+key)

            results.append({
                'pair_index':k,
                'anchor_chunk_offset':left[0],
                'next_indexed_camera_chunk_offset':right[0],
                'frames':frames,
                'header_gap_ns':
                    frames[1]['header_stamp_ns']
                    -frames[0]['header_stamp_ns'],
                'pixel_motion':motion,
                'metric_pose_qualified':False
            })
            print(
                'R33_PAIR=%d FEATURES=%d TRACKS=%d '
                'MEDIAN_PIXEL_DISPLACEMENT=%s' % (
                    k,
                    motion['initial_corner_count'],
                    motion['forward_backward_consistent_count'],
                    str(motion['median_displacement_px'])
                )
            )

    report={
        'schema':
            'TRUST_ROBOT_R33_TRAIN_CAMERA_MULTIPAIR_PIXEL_DIAGNOSTICS_V1',
        'trajectory_id':'room_02',
        'split':'train',
        'github_baseline':
            'ebfd02b0ef8ad79b2e6a9810897fcb71efec2e87',
        'authenticated_bag_sha256':index['file_sha256'],
        'source_report_sha256':{
            'r17':digest(index_path.read_bytes()),
            'r18':digest(r18_path.read_bytes()),
            'r31':digest(r31_path.read_bytes())
        },
        'sampling_rule':
            'eight_evenly_spaced_camera_chunk_anchors_first_two_adjacent_messages',
        'eligible_camera_chunks':1063,
        'camera_index_messages':1113,
        'pair_count':8,
        'frames_inspected':16,
        'chunks_read':16,
        'pairs':results,
        'pixel_motion_only':True,
        'motion_statistics_not_calibrated':True,
        'real_pose_factors_generated':0,
        'health_labels_generated':0,
        'new_sensor_acquisitions':0,
        **{x:False for x in FLAGS}
    }
    safety(report)

    with out.open('x') as f:
        json.dump(
            report,f,sort_keys=True,indent=2,allow_nan=False
        )
        f.write('\n')

    print('R33_R31_CAMERA_BASELINE=RECOMPUTED_AND_MATCHED')
    print('R33_REAL_CAMERA_FRAME_PAIRS=8')
    print('R33_REAL_CAMERA_FRAMES=16')
    print('R33_PIXEL_DIAGNOSTIC_ONLY=YES')

if __name__=='__main__':
    run(*map(pathlib.Path,sys.argv[1:6]))
