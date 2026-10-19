"""Record-only falsification, no bag opening and no science promotion."""
import copy,json,sys
from pathlib import Path
from r20_recorder_review import review
r17,r18,r19=map(lambda p:json.loads(Path(p).read_text()),sys.argv[1:4])
assert review(r17,r18,r19)['bounded_samples']==8

def reject(source,mutation):
 items=[copy.deepcopy(r17),copy.deepcopy(r18),copy.deepcopy(r19)]
 mutation(items[source])
 try:review(*items)
 except (ValueError,TypeError,KeyError,IndexError,AssertionError):return
 raise AssertionError('R20_NEGATIVE_CONTROL_ACCEPTED')

src='/camera/color/image_raw/compressed'
mutations=[
 (0,lambda r:r.update(connection_count=14)),
 (0,lambda r:r.update(chunk_count=1)),
 (0,lambda r:r['required_stream_counts'].__setitem__(src,0)),
 (0,lambda r:r.update(bag_record_time_is_capture_time_proof=True)),
 (1,lambda r:r.update(split='confirmation_test')),
 (1,lambda r:r.update(sampled_message_count=7)),
 (1,lambda r:r.update(physical_sync_verified=True)),
 (1,lambda r:r['samples'].__setitem__(src,[])),
 (1,lambda r:r['samples'][src][0].update(frame_id='wrong_frame')),
 (2,lambda r:r.update(camera_imu_receipt_count=5)),
 (2,lambda r:r.update(scan_registration_performed=True)),
 (2,lambda r:r.update(bag_record_time_used_as_measurement_time=True)),
 (2,lambda r:r['camera_imu_existing_adapter_receipts'][src][0].update(receipt_content_sha256='0'*64)),
 (2,lambda r:r['lidar_nonfactor_observation_receipts'][0].update(relative_pose_computed=True)),
 (2,lambda r:r.update(real_pose_factors_generated=1)),
 (2,lambda r:r.update(health_labels=1)),
]
for index,mutate in mutations:reject(index,mutate)
print('R20_METADATA_NEGATIVE_CONTROLS=16_REJECTED')
print('R20_SCIENTIFIC_BOUNDARY_NEGATIVE_TESTS=PASS')
