"""Strict metadata-only challenges: no bag records opened."""
import copy,json,pathlib,sys
from r19_frontend_contract import validate_inputs
from trust_robot.m2dgr_sensor_admission import load_frozen_snapshot
repo,r17_path,r18_path=map(pathlib.Path,sys.argv[1:4])
r17=json.loads(r17_path.read_text());r18=json.loads(r18_path.read_text())
snapshot=load_frozen_snapshot(repo)
assert len(validate_inputs(r18,r17,snapshot)[0])==8

def reject(mutator):
    altered=copy.deepcopy(r18)
    mutator(altered)
    try:validate_inputs(altered,r17,snapshot)
    except (ValueError,KeyError,TypeError):return
    raise AssertionError('R19_INVALID_CONTRACT_ACCEPTED')

def first(r):return r['samples']['/camera/color/image_raw/compressed'][0]
mutations=(
 lambda r:r.update(split='confirmation_test'),
 lambda r:r.update(sampled_message_count=7),
 lambda r:r.update(physical_sync_verified=True),
 lambda r:r.update(recording_sha256='0'*64),
 lambda r:first(r).update(frame_id='invented_frame'),
 lambda r:first(r).update(connection_id=-1),
 lambda r:first(r).update(serialized_message_sha256='bad'),
 lambda r:r['samples']['/camera/imu'].__setitem__(1,copy.deepcopy(r['samples']['/camera/imu'][0])),
 lambda r:r['samples'].__setitem__('/velodyne_points',[]),
 lambda r:first(r).update(header_stamp_ns=-1),
)
for mutation in mutations:reject(mutation)
print('R19_METADATA_CONTRACT_NEGATIVE_CONTROLS=10_REJECTED')
print('R19_FROZEN_TRAIN_AND_ADMISSION_GATES=PASS')
