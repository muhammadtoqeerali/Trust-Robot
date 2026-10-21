"""Independent cross-check of the exported fail-closed bridge report."""
import hashlib
import json
import pathlib
import sys

repo, r76, output = map(pathlib.Path, sys.argv[1:])

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

p = output / 'r77_intake_sensor_factor_boundary_v1.json'
r = load(p)
c = load(r76 / 'r76_source_intake_contract_v1.json')

assert r['schema'] == (
    'TRUST_ROBOT_R77_INTAKE_SENSOR_FACTOR_GATE_BRIDGE_V1'
)
assert r['git_baseline'] == (
    'c1f59bb5e38bdfece14798031c0d911441b28de8'
)
assert r['status'] == 'PASS_SOFTWARE_ONLY'
assert r['trajectory'] == 'room_02'
assert r['split'] == 'train'

assert set(r['candidate_claim_names']) == set(
    c['historical_r43_gates']
)

assert (
    r['historical_gates_checked']
    == r['synthetic_claim_shapes_validated']
    == 11
)

assert r['historical_timing_receipts_checked'] == (
    len(c['historical_r53_receipts'])
) == 5

assert r['frozen_inputs_sha256'] == (
    c['frozen_evidence_sha256']
)

assert r['r76_contract_sha256'] == sha(
    r76 / 'r76_source_intake_contract_v1.json'
)

assert r['r76_independent_validation_sha256'] == sha(
    r76 / 'r76_independent_validation_v1.json'
)

assert r['m2dgr_sensor_admission_gate_rejected'] is True
assert r['multimodal_recorded_factor_gate_rejected'] is True
assert r['gt_recovery_status_preserved'] is True

for key in (
    'apparently_filled_author_candidate_admitted',
    'new_physical_evidence_received',
    'physical_frame_qualified',
    'physical_clock_qualified',
    'real_pose_factors_authorized',
    'health_training_authorized',
    'ate_rpe_authorized',
    'confirmation_test_accessed',
    'raw_gt_or_rosbag_opened',
):
    assert r[key] is False, key

assert r['scientific_gates_closed'] == 11

for rel, pin in r['frozen_inputs_sha256'].items():
    if rel == 'r43':
        name = (
            'experiments/trust_robot_r39_r43_sensor_qualification_checkpoint_v1/'
            'r43/trust_robot_r43_source_acquisition_protocol_result_v1/'
            'r43_unfilled_source_receipts_v1.json'
        )
    elif rel == 'r53':
        name = (
            'experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/'
            'evidence/trust_robot_r53_timing_receipt_boundary_result_v1/'
            'r53_unfilled_physical_timing_receipts_v1.json'
        )
    elif rel == 'r74':
        name = (
            'experiments/trust_robot_r70_r74_scientific_admissibility_checkpoint_v1/'
            'evidence/result/r74_scientific_admissibility_v1.json'
        )
    else:
        raise AssertionError(rel)

    assert sha(repo / name) == pin

contents = p.read_text(encoding='utf-8')

for bad in (
    '/home/kios/',
    '/mnt/hdd16T/',
    '"evidence_fields"',
    '"source_reference"',
    '"source_sha256"',
):
    assert bad not in contents, bad

v = {
    'schema':
        'TRUST_ROBOT_R77_INDEPENDENT_GATE_BRIDGE_VALIDATION_V1',
    'status': 'PASS',
    'primary_result_sha256': sha(p),
    'r76_lineage_verified': True,
    'historical_gate_replay': True,
    'existing_sensor_factor_gates_remained_closed': True,
    'raw_gt_or_rosbag_opened': False,
    'confirmation_test_accessed': False,
    'physical_sources_qualified': 0,
    'scientific_gates_closed': 11,
}

with (
    output / 'r77_independent_validation_v1.json'
).open('x', encoding='utf-8') as f:
    json.dump(v, f, sort_keys=True, indent=2)
    f.write('\n')

print('R77_INDEPENDENT_SOURCE_CROSSCHECK=PASS')
print('R77_INDEPENDENT_SANITIZATION=PASS')
print('R77_INDEPENDENT_SCIENCE_DENIAL=PASS')
