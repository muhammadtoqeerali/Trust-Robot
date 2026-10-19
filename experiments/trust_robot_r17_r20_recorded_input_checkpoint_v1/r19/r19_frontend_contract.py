"""Adapt eight sampled, real ROS messages into existing nonfactor contracts."""
import copy, hashlib, json, pathlib, sys
import r18_decode as decoder
from trust_robot.camera_imu_observation_adapter import (
    build_raw_observation_receipt, receipt_payload, receipt_content_sha256,
    validate_receipt_payload,
)
from trust_robot.lidar_frontend import EXPECTED_FIELDS, EXPECTED_POINT_STEP, EXPECTED_FRAME_ID
from trust_robot.m2dgr_sensor_admission import load_frozen_snapshot, require_real_factor_execution, SensorAdmissionError

TOPICS={
    '/camera/color/image_raw/compressed': 'sensor_msgs/CompressedImage',
    '/camera/imu': 'sensor_msgs/Imu',
    '/handsfree/imu': 'sensor_msgs/Imu',
    '/velodyne_points': 'sensor_msgs/PointCloud2',
}

def need(ok,reason):
    if not ok: raise ValueError('R19_FAIL_CLOSED:'+reason)

def sha(data): return hashlib.sha256(data).hexdigest()
def filehash(path): return sha(pathlib.Path(path).read_bytes())
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def validate_inputs(r18,r17,snapshot):
    need(r18.get('schema')=='TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1','R18_SCHEMA')
    need(r17.get('schema')=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1','R17_SCHEMA')
    need(r18.get('trajectory_id')=='room_02' and r18.get('split')=='train' and
         r17.get('trajectory_id')=='room_02','TRAIN_IDENTITY')
    need(r18.get('recording_sha256')==r17.get('file_sha256') and len(r18['recording_sha256'])==64,'BAG_SHA_CHAIN')
    need(snapshot['by_id']['room_02']['split']=='train' and
         all(v is False for v in snapshot['scientific_gates'].values()),'SENSOR_ADMISSION')
    need(set(r18.get('samples',{}))==set(TOPICS),'REQUIRED_STREAMS')
    need(r18.get('sampled_message_count')==8 and r18.get('recorded_streams_decoded')==4 and
         type(r18.get('sampled_chunks')) is int and 1<=r18['sampled_chunks']<=8,'SAMPLE_BOUND')
    for name in ('bag_record_time_is_capture_time_proof','header_stamp_is_capture_time_proof',
                 'cross_stream_alignment_performed','physical_sync_verified','extrinsics_verified',
                 'raw_recording_modified','github_modified'):
        need(r18.get(name) is False,'R18_GATE_'+name)
    need(r18.get('real_pose_factors_generated')==0 and r18.get('health_labels')==0,'R18_SCIENCE_ZERO')
    indexed={c['id']:c for c in r17['connections']}
    need(len(indexed)==r17['connection_count'],'CONNECTION_COUNT')
    expected_frame={s['stream_id']:s['frame_id'] for s in snapshot['by_id']['room_02']['streams']}
    sampled=[]; keys=set()
    for topic in TOPICS:
        group=r18['samples'][topic]
        need(type(group) is list and len(group)==2,'PER_STREAM_SAMPLE_COUNT:'+topic)
        need(group[0]['chunk_offset'] != group[1]['chunk_offset'],'DISTINCT_CHUNKS:'+topic)
        for i,s in enumerate(group):
            need(type(s) is dict,'SAMPLE_SHAPE')
            for name in ('chunk_offset','connection_id','bag_record_time_ns',
                         'header_stamp_ns','serialized_message_bytes','sequence'):
                need(type(s.get(name)) is int and s[name]>=0,'SAMPLE_FIELD_'+name)
            need(s['serialized_message_bytes']>16 and
                 type(s.get('serialized_message_sha256')) is str and
                 len(s['serialized_message_sha256'])==64 and
                 set(s['serialized_message_sha256'])<=set('0123456789abcdef'),'SERIALIZED_HASH')
            need(s.get('frame_id')==expected_frame[topic],'MANIFEST_FRAME_ID:'+topic)
            need(s['connection_id'] in indexed and indexed[s['connection_id']]['topic']==topic and
                 indexed[s['connection_id']]['message_type']==TOPICS[topic],'RECORDED_CONNECTION')
            key=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
            need(key not in keys,'DUPLICATE_SAMPLE')
            keys.add(key);sampled.append((key,topic,i,s))
    need(len(keys)==8,'EIGHT_UNIQUE_SAMPLES')
    return sampled,indexed

def build(repo,bag,r17_path,r18_path,out):
    snapshot=load_frozen_snapshot(repo)
    r17=json.loads(r17_path.read_text())
    r18=json.loads(r18_path.read_text())
    need(r18['r17_report_sha256']==filehash(r17_path),'R17_REPORT_LINEAGE')
    requested,indexed=validate_inputs(r18,r17,snapshot)
    try: require_real_factor_execution(snapshot,'room_02')
    except SensorAdmissionError: pass
    else: raise ValueError('R19_FAIL_CLOSED:REAL_FACTOR_GATE_OPEN')
    target={k:(topic,i,s) for k,topic,i,s in requested}
    remaining=set(target)
    offsets=sorted({k[0] for k in target})
    receipts={topic:[] for topic in TOPICS if topic!='/velodyne_points'}
    lidar=[]; seen=set()
    with bag.open('rb') as handle:
        for offset in offsets:
            raw,mode=decoder.chunk_data(handle,offset)
            need(mode in r18['compression_methods'],'COMPRESSION_PROVENANCE')
            for cid,record_time,view in decoder.messages(raw,indexed):
                body=bytes(view)
                k=(offset,cid,record_time,sha(body))
                if k not in target:continue
                need(k in remaining,'DUPLICATE_RECORDED_BYTES')
                topic,i,s=target[k]
                need(len(body)==s['serialized_message_bytes'],'RECORDED_MESSAGE_LENGTH')
                parsed=decoder.decode(topic,body)
                need(all(s.get(field)==value for field,value in parsed.items()),'RE_DECODE_DISAGREEMENT')
                source={
                    'chunk_offset':offset,'connection_id':cid,
                    'bag_record_time_ns':record_time,
                    'header_stamp_ns':s['header_stamp_ns'],
                    'frame_id':s['frame_id'],
                    'serialized_message_sha256':sha(body),
                    'serialized_message_bytes':len(body),
                    'sample_subset_index':i,
                }
                if topic!='/velodyne_points':
                    receipt=build_raw_observation_receipt(
                        source_stream_id=topic,trajectory_or_session_id='room_02',
                        split_role='train',message_index=i,serialized_payload=body,
                        bag_record_time_ns=record_time,header_stamp_ns=s['header_stamp_ns'],
                        message_type=TOPICS[topic],
                    )
                    payload=receipt_payload(receipt)
                    validate_receipt_payload(payload)
                    receipts[topic].append({
                        'source':source,'receipt':payload,
                        'receipt_content_sha256':receipt_content_sha256(receipt),
                        'message_index_scope':'two_sample_subset_not_full_recording_ordinal',
                    })
                else:
                    # Shape compatibility is descriptive only: no scans are registered.
                    fields=[f['name'] for f in s['point_fields']]
                    compatibility=(tuple(fields)==tuple(EXPECTED_FIELDS) and
                                   s['point_step']==EXPECTED_POINT_STEP and
                                   s['frame_id']==EXPECTED_FRAME_ID and
                                   s['is_bigendian'] is False)
                    lidar.append({
                        'source':source,'point_count':s['point_count'],
                        'point_step':s['point_step'],'point_fields':s['point_fields'],
                        'point_payload_bytes':s['point_payload_bytes'],
                        'point_payload_sha256':s['point_payload_sha256'],
                        'frontend_layout_candidate_compatible':compatibility,
                        'registration_executed':False,
                        'relative_pose_computed':False,
                        'factor_execution_authorized':False,
                    })
                remaining.remove(k);seen.add(k)
    need(not remaining and len(seen)==8,'RECORDED_MESSAGE_RELOCATION')
    for topic in receipts:need(len(receipts[topic])==2,'CAMERA_IMU_COUNT')
    need(len(lidar)==2,'LIDAR_COUNT')
    for topic in receipts:receipts[topic].sort(key=lambda row:row['source']['sample_subset_index'])
    lidar.sort(key=lambda row:row['source']['sample_subset_index'])
    report={
        'schema':'TRUST_ROBOT_R19_RECORDED_FRONTEND_PROVENANCE_V1',
        'trajectory_id':'room_02','split':'train',
        'bag_sha256':r18['recording_sha256'],
        'r17_report_sha256':filehash(r17_path),
        'r18_report_sha256':filehash(r18_path),
        'r18_decoder_source_sha256':filehash(pathlib.Path(decoder.__file__)),
        'r19_engine_source_sha256':filehash(__file__),
        'camera_imu_existing_adapter_receipts':receipts,
        'lidar_nonfactor_observation_receipts':lidar,
        'camera_imu_receipt_count':6,'lidar_observation_count':2,
        'message_index_role':'two_sample_subset_not_full_recording_ordinal',
        'selected_chunk_offsets':offsets,
        'encoded_image_pixels_decoded':False,
        'lidar_xyz_points_materialized':False,
        'image_odometry_performed':False,
        'scan_registration_performed':False,
        'imu_preintegration_performed':False,
        'bag_record_time_used_as_measurement_time':False,
        'header_stamp_physical_capture_semantics_verified':False,
        'cross_modal_temporal_association_performed':False,
        'physical_sync_verified':False,
        'full_extrinsics_verified':False,
        'real_sensor_factor_execution_authorized':False,
        'health_model_training_authorized':False,
        'real_pose_factors_generated':0,'health_labels':0,
        'ground_truth_scored':False,'raw_recording_modified':False,'github_modified':False,
    }
    with out.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print('R19_EXISTING_CAMERA_IMU_ADAPTER_RECEIPTS=6_VALIDATED')
    print('R19_LIDAR_RECORDED_LAYOUT_RECEIPTS=2_VALIDATED')
    print('R19_LIDAR_FRONTEND_LAYOUT_CANDIDATE_COMPATIBLE='+str(sum(x['frontend_layout_candidate_compatible'] for x in lidar)))
    print('R19_RECORDED_MESSAGE_HASHES=8_RECOMPUTED')
    print('R19_RECORDED_FRONTEND_PROVENANCE=PASS')

if __name__=='__main__':
    build(*map(pathlib.Path,sys.argv[1:6]))
