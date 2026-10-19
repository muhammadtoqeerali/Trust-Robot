"""Independently traverse R18-selected chunks and verify all R19 source receipts."""
import hashlib,json,pathlib,struct,sys
import r18_verify as independent
from trust_robot.camera_imu_observation_adapter import validate_receipt_payload,content_sha256
from trust_robot.lidar_frontend import EXPECTED_FIELDS, EXPECTED_POINT_STEP, EXPECTED_FRAME_ID

def need(ok,msg):
    if not ok:raise ValueError('R19_INDEPENDENT_FAIL:'+msg)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def js(path):return json.loads(path.read_text())

def main(bag,r17_path,r18_path,r19_path):
    index=js(r17_path);samples=js(r18_path);result=js(r19_path)
    need(result['schema']=='TRUST_ROBOT_R19_RECORDED_FRONTEND_PROVENANCE_V1' and
         result['trajectory_id']=='room_02' and result['split']=='train','IDENTITY')
    need(result['r17_report_sha256']==sha(r17_path.read_bytes()) and
         result['r18_report_sha256']==sha(r18_path.read_bytes()),'REPORT_LINEAGE')
    need(result['bag_sha256']==samples['recording_sha256']==index['file_sha256'],'BAG_SOURCE')
    requested={}
    for topic,group in samples['samples'].items():
        for pos,s in enumerate(group):
            k=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
            need(k not in requested,'DUPLICATE_R18_SAMPLE')
            requested[k]=(topic,pos,s)
    need(len(requested)==8,'R18_COUNT')
    conn={c['id']:c for c in index['connections']}
    reconstructed={}
    with bag.open('rb') as file:
        for offset in sorted({k[0] for k in requested}):
            for cid,ts,raw in independent.chunk_messages(file,offset,conn):
                k=(offset,cid,ts,sha(raw))
                if k in requested:
                    need(k not in reconstructed,'MULTIPLE_MATCHED_MESSAGES')
                    topic,pos,s=requested[k]
                    need(len(raw)==s['serialized_message_bytes'],'LENGTH')
                    need(len(raw)>=16,'ROS_HEADER_SIZE')
                    seq,sec,ns,n=struct.unpack_from('<IIII',raw,0)
                    need(ns<10**9 and 16+n<=len(raw),'ROS_HEADER_BOUNDS')
                    frame=raw[16:16+n].decode('utf-8')
                    need(seq==s['sequence'] and sec*10**9+ns==s['header_stamp_ns'] and
                         frame==s['frame_id'],'HEADER_VALUES')
                    reconstructed[k]=raw
    need(len(reconstructed)==8,'EIGHT_RECOMPUTED')
    receipts=result['camera_imu_existing_adapter_receipts']
    need(set(receipts)==set(samples['samples'])-{'/velodyne_points'},'CAMERA_IMU_TOPICS')
    checked=0
    for topic,entries in receipts.items():
        need(len(entries)==2,'RECEIPT_GROUP_COUNT')
        for j,item in enumerate(entries):
            source=item['source'];receipt=item['receipt']
            candidate=samples['samples'][topic][j]
            k=(source['chunk_offset'],source['connection_id'],source['bag_record_time_ns'],source['serialized_message_sha256'])
            need(k in reconstructed and k in requested and requested[k][:2]==(topic,j),'RECEIPT_ORIGIN')
            body=reconstructed[k]
            validate_receipt_payload(receipt)
            need(receipt['serialized_payload_sha256']==sha(body) and
                 receipt['serialized_payload_size_bytes']==len(body),'RECEIPT_RAW_BYTES')
            need(receipt['message_index']==j and
                 item['message_index_scope']=='two_sample_subset_not_full_recording_ordinal' and
                 receipt['trajectory_or_session_id']=='room_02' and receipt['split_role']=='train' and
                 receipt['source_stream_id']==topic and receipt['message_type']==conn[source['connection_id']]['message_type'] and
                 receipt['bag_record_time_ns']==candidate['bag_record_time_ns'] and
                 receipt['header_stamp_ns']==candidate['header_stamp_ns'],'RECEIPT_IDENTITY')
            need(source['frame_id']==candidate['frame_id'] and
                 source['serialized_message_bytes']==len(body) and
                 item['receipt_content_sha256']==content_sha256(receipt),'RECEIPT_HASH_AND_FRAME')
            checked+=1
    need(checked==result['camera_imu_receipt_count']==6,'RECEIPT_TOTAL')
    lidar=result['lidar_nonfactor_observation_receipts'];need(len(lidar)==2,'LIDAR_COUNT')
    for j,item in enumerate(lidar):
        source=item['source'];sample=samples['samples']['/velodyne_points'][j]
        k=(source['chunk_offset'],source['connection_id'],source['bag_record_time_ns'],source['serialized_message_sha256'])
        need(k in reconstructed and requested[k][:2]==('/velodyne_points',j),'LIDAR_BYTES')
        need(sha(reconstructed[k])==sample['serialized_message_sha256'] and
             source['frame_id']==sample['frame_id'],'LIDAR_SOURCE')
        for name in ('point_count','point_step','point_fields','point_payload_bytes','point_payload_sha256'):
            need(item[name]==sample[name],'LIDAR_METADATA_'+name)
        expected_layout=(tuple(f['name'] for f in sample['point_fields'])==tuple(EXPECTED_FIELDS) and
                         sample['point_step']==EXPECTED_POINT_STEP and
                         sample['frame_id']==EXPECTED_FRAME_ID and
                         sample['is_bigendian'] is False)
        need(item['frontend_layout_candidate_compatible'] is expected_layout,'LIDAR_LAYOUT_CLAIM')
        need(source['serialized_message_bytes']==len(reconstructed[k]) and
             source['sample_subset_index']==j,'LIDAR_PROVENANCE_FIELDS')
        for name in ('registration_executed','relative_pose_computed','factor_execution_authorized'):
            need(item[name] is False,'LIDAR_GATE_'+name)
    need(result['lidar_observation_count']==2,'LIDAR_TOTAL')
    for name in ('encoded_image_pixels_decoded','lidar_xyz_points_materialized','image_odometry_performed',
                 'scan_registration_performed','imu_preintegration_performed','bag_record_time_used_as_measurement_time',
                 'header_stamp_physical_capture_semantics_verified','cross_modal_temporal_association_performed',
                 'physical_sync_verified','full_extrinsics_verified','real_sensor_factor_execution_authorized',
                 'health_model_training_authorized','ground_truth_scored','raw_recording_modified','github_modified'):
        need(result[name] is False,'SCIENCE_GATE_'+name)
    need(result['real_pose_factors_generated']==0 and result['health_labels']==0,'ZERO_FACTORS_HEALTH')
    need(result['selected_chunk_offsets']==sorted({k[0] for k in requested}),'CHUNK_INDEX')
    print('R19_INDEPENDENT_RECORDED_MESSAGE_HASHES=8_VERIFIED')
    print('R19_INDEPENDENT_CAMERA_IMU_EXISTING_CONTRACTS=6_VERIFIED')
    print('R19_INDEPENDENT_LIDAR_NONFACTOR_OBSERVATIONS=2_VERIFIED')
    print('R19_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':main(*map(pathlib.Path,sys.argv[1:5]))
