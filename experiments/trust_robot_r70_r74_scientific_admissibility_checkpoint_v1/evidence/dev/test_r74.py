"""Positive replay and in-memory negative evidence controls."""
import copy
import pathlib
import sys

import r74_review as policy

I = pathlib.Path(sys.argv[1])
R = pathlib.Path(sys.argv[2])

names = (
    'r70_verona_physical_source_inventory_v1.json',
    'r71a_author_source_review_v1.json',
    'r72_verona_source_admissibility_v1.json',
    'r73_transfer_receipt_v1.json',
)

reports = [policy.read_json(I/name) for name in names]

quality = policy.read_json(
    R/'experiments/'
    'trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/'
    'evidence/r67/result/'
    'r67_rebuilt_room_02_reference_quality_v1.json'
)

indoor = policy.read_json(
    R/'manifests/'
    'm2dgr_indoor_reference_origin_semantics_evidence_v1.json'
)

physical = policy.read_json(
    R/'manifests/'
    'm2dgr_reference_physical_semantics_evidence_v1.json'
)

original = [*reports, quality, indoor, physical]

result = policy.validate(*original)
assert result['scientific_gates_closed'] == 11
assert result['physical_qualification']['mocap_to_lidar_se3_verified'] is False

print('R74_POSITIVE_EVIDENCE_REPLAY=PASS')

def challenge(index, mutation):
    values = copy.deepcopy(original)
    mutation(values[index])

    try:
        policy.validate(*values)
    except (ValueError, KeyError, TypeError, AssertionError):
        return

    raise RuntimeError('R74_TAMPER_WAS_ACCEPTED')

challenge(0, lambda x: x.update(readable_candidates=90))
challenge(1, lambda x: x.update(vicon_configuration_candidates=['fake.vsk']))
challenge(2, lambda x: x.update(author_vicon_nominal_rate_hz=40))
challenge(2, lambda x: x.update(clock_synchronization_verified=True))
challenge(2, lambda x: x['source_pins'].update(r71a_review='0'*64))
challenge(2, lambda x: x['claims']['mocap_to_lidar_se3'].update(status='SUPPORTED'))
challenge(3, lambda x: x.update(physical_frame_qualified=True))
challenge(4, lambda x: x['quality_summary'].update(evaluation_ready=True))

print('R74_NEGATIVE_EVIDENCE_CONTROLS=8_REJECTED')
