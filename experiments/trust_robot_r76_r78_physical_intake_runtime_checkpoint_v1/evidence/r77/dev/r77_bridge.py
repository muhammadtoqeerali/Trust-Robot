"""Software-only integration. Candidate format never authorizes real factors."""
from __future__ import annotations

import hashlib
import json
import pathlib

import r76_intake as intake

from trust_robot.m2dgr_sensor_admission import (
    SensorAdmissionError,
    load_frozen_snapshot,
    require_real_factor_execution,
)

from trust_robot.multimodal_factor_interface import (
    MultimodalFactorError,
    require_recorded_factor_execution,
)

SCHEMA = 'TRUST_ROBOT_R77_INTAKE_SENSOR_FACTOR_GATE_BRIDGE_V1'
BASE = 'c1f59bb5e38bdfece14798031c0d911441b28de8'

FROZEN = {
    'r43': (
        'experiments/trust_robot_r39_r43_sensor_qualification_checkpoint_v1/r43/trust_robot_r43_source_acquisition_protocol_result_v1/r43_unfilled_source_receipts_v1.json',
        '260f799a3d1494052416ba83652c6de79165ba2b29e7b28f9cd14bfd6c5bc622',
    ),
    'r53': (
        'experiments/trust_robot_r51_r55f_evidence_checkpoint_v1/evidence/trust_robot_r53_timing_receipt_boundary_result_v1/r53_unfilled_physical_timing_receipts_v1.json',
        'f4e2d70c8e39d88ee3d6df62c0e7998488dc900398cdc8bd41733b7c1b9548f2',
    ),
    'r74': (
        'experiments/trust_robot_r70_r74_scientific_admissibility_checkpoint_v1/evidence/result/r74_scientific_admissibility_v1.json',
        '22b02194a8899a263484a90e30afd3f95a3fb45d2ccdd7dec8bb8908d59fc98b',
    ),
}

CONTRACT_SHA = (
    'c3d18535c4b622620c35aad4e839f89793d4eb3b1fbddf4828ee8103144f8be6'
)
VALIDATION_SHA = (
    '5c244e64cfb9e891196ad70cc2a5cca10fb8a50914708bd1889d44417e84d311'
)


class BridgeError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise BridgeError(why)


def digest(path):
    return hashlib.sha256(
        pathlib.Path(path).read_bytes()
    ).hexdigest()


def json_file(path, pin):
    path = pathlib.Path(path)

    need(
        path.is_file()
        and not path.is_symlink()
        and digest(path) == pin,
        'SOURCE_INTEGRITY:' + path.name
    )

    return json.loads(
        path.read_text(encoding='utf-8')
    )


def check_contract(contract, validator, gates, timing, pins):
    need(
        contract.get('schema') == intake.CONTRACT_SCHEMA,
        'CONTRACT_SCHEMA'
    )
    need(
        contract.get('git_parent_commit') == BASE,
        'CONTRACT_PARENT'
    )
    need(
        contract.get('frozen_evidence_sha256') == pins,
        'CONTRACT_FROZEN_SOURCE_PINS'
    )
    need(
        contract.get('trajectory_id') == 'room_02'
        and contract.get('split') == 'train',
        'CONTRACT_TRAIN'
    )
    need(
        contract.get('scientific_gates_closed') == 11,
        'CONTRACT_GATES'
    )
    need(
        contract.get('independent_new_sources_qualified') == 0
        and contract.get('new_execution_authorizations') == 0,
        'CONTRACT_AUTHORIZATION'
    )
    need(
        contract.get('original_room_02_gt_recovered_in_later_phase') is True
        and contract.get('historical_r43_raw_gt_status_not_current') is True,
        'CURRENT_GT_DISTINCTION'
    )
    need(
        contract.get('mocap_frame_qualified') is False
        and contract.get('clock_mapping_qualified') is False,
        'CONTRACT_CLOCK_FRAME'
    )
    need(
        set(contract.get('historical_r43_gates', {})) == set(gates),
        'CONTRACT_R43_KEYS'
    )
    need(
        set(contract.get('historical_r53_receipts', {})) == set(timing),
        'CONTRACT_R53_KEYS'
    )

    for name, g in gates.items():
        row = contract['historical_r43_gates'][name]

        need(
            row == {
                'required_fields': sorted(g['required_fields']),
                'historical_status': 'NO_SOURCE_RECEIVED',
                'candidate_is_physical_proof': False,
            },
            'CONTRACT_R43_FIELDS:' + name
        )

    for name, g in timing.items():
        row = contract['historical_r53_receipts'][name]

        need(
            row == {
                'required_fields': sorted(g['fields']),
                'historical_status': 'NO_PHYSICAL_SOURCE_RECEIVED',
                'physical_clock_qualified': False,
            },
            'CONTRACT_R53_FIELDS:' + name
        )

    need(
        validator.get('status') == 'PASS'
        and validator.get('contract_sha256') == CONTRACT_SHA
        and validator.get('source_request_sent') is False
        and validator.get('new_authorizations') == 0
        and validator.get('scientific_gates_closed') == 11,
        'R76_VALIDATION'
    )

    return True


def load_state(repo, r76_output):
    repo = pathlib.Path(repo)
    output = pathlib.Path(r76_output)

    frozen = {
        name: json_file(repo / rel, pin)
        for name, (rel, pin) in FROZEN.items()
    }

    gates, timing = intake.frozen_boundary(
        frozen['r43'],
        frozen['r53'],
        frozen['r74']
    )

    contract = json_file(
        output / 'r76_source_intake_contract_v1.json',
        CONTRACT_SHA
    )
    validation = json_file(
        output / 'r76_independent_validation_v1.json',
        VALIDATION_SHA
    )

    check_contract(
        contract,
        validation,
        gates,
        timing,
        {name: pin for name, (_, pin) in FROZEN.items()}
    )

    snapshot = load_frozen_snapshot(repo)

    need(
        snapshot['by_id'].get('room_02', {}).get('split') == 'train',
        'ROOM_02_SPLIT'
    )
    need(
        len(snapshot['by_id']) == 36,
        'FROZEN_SPLIT_INVENTORY'
    )
    need(
        snapshot['scientific_gates'][
            'real_sensor_factor_execution_authorized'
        ] is False,
        'SENSOR_GATE'
    )

    return gates, timing, snapshot


def assert_real_factor_gates_closed(snapshot):
    try:
        require_real_factor_execution(snapshot, 'room_02')
    except SensorAdmissionError:
        pass
    else:
        raise BridgeError(
            'SENSOR_ADMISSION_UNEXPECTEDLY_GRANTED'
        )

    try:
        require_recorded_factor_execution(snapshot, 'room_02')
    except MultimodalFactorError:
        pass
    else:
        raise BridgeError(
            'MULTIMODAL_FACTOR_UNEXPECTEDLY_GRANTED'
        )

    return True


def assess_candidate(candidate, gates, snapshot):
    # No candidate field is authorization, even if all fields are populated.
    need(
        snapshot['by_id'].get('room_02', {}).get('split') == 'train',
        'ROOM_02_TRAIN_ONLY'
    )

    try:
        shape = intake.validate_candidate(candidate, gates)
    except (intake.IntakeError, KeyError, TypeError) as exc:
        raise BridgeError('BAD_EVIDENCE_CANDIDATE') from exc

    need(
        shape.get('format_valid') is True
        and shape.get('physical_qualification_established') is False
        and shape.get('factor_execution_authorized') is False,
        'CANDIDATE_PROOF_CONFUSION'
    )

    assert_real_factor_gates_closed(snapshot)

    return {
        'schema': SCHEMA,
        'claim_id': shape['claim_id'],
        'trajectory_id': 'room_02',
        'split': 'train',
        'candidate_format_valid': True,
        'source_content_independently_verified': False,
        'recorded_sensor_factor_admitted': False,
        'multimodal_pose_factor_admitted': False,
        'physical_calibration_qualified': False,
        'physical_clock_qualified': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'status': 'FORMAT_VALID_SCIENTIFICALLY_BLOCKED',
    }


def synthetic_candidate(
    claim,
    gates,
    source_class='synthetic_fixture',
    filled=False,
):
    need(claim in gates, 'CLAIM_ID')

    return {
        'schema': intake.CANDIDATE_SCHEMA,
        'claim_id': claim,
        'trajectory_id': 'room_02',
        'split': 'train',
        'source_class': source_class,
        'source_reference': 'author-source:r77_synthetic_not_physical',
        'source_sha256': 'a' * 64,
        'evidence_fields': {
            name: ('SYNTHETIC_UNVERIFIED' if filled else None)
            for name in gates[claim]['required_fields']
        },
        'independent_validation_sha256': None,
        'physical_validation_completed': False,
        'factor_execution_authorized': False,
        'confirmation_test_used': False,
    }


def produce(repo, private, out):
    gates, timing, snapshot = load_state(repo, private)
    claims = []

    for name in sorted(gates):
        result = assess_candidate(
            synthetic_candidate(name, gates),
            gates,
            snapshot
        )

        need(
            result['status'] == 'FORMAT_VALID_SCIENTIFICALLY_BLOCKED',
            'CLAIM_' + name
        )
        claims.append(name)

    # Even an apparently filled author-source candidate is unqualified.
    apparent = assess_candidate(
        synthetic_candidate(
            'mocap_body_to_lidar_physically_verified',
            gates,
            source_class='author_source_candidate',
            filled=True
        ),
        gates,
        snapshot
    )

    need(
        apparent['physical_calibration_qualified'] is False,
        'FABRICATED_PHYSICAL_APPROVAL'
    )

    output = {
        'schema': SCHEMA,
        'status': 'PASS_SOFTWARE_ONLY',
        'git_baseline': BASE,
        'trajectory': 'room_02',
        'split': 'train',
        'historical_gates_checked': len(gates),
        'historical_timing_receipts_checked': len(timing),
        'candidate_claim_names': claims,
        'synthetic_claim_shapes_validated': len(claims),
        'apparently_filled_author_candidate_admitted': False,
        'm2dgr_sensor_admission_gate_rejected': True,
        'multimodal_recorded_factor_gate_rejected': True,
        'gt_recovery_status_preserved': True,
        'new_physical_evidence_received': False,
        'physical_frame_qualified': False,
        'physical_clock_qualified': False,
        'real_pose_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'confirmation_test_accessed': False,
        'raw_gt_or_rosbag_opened': False,
        'scientific_gates_closed': 11,
        'frozen_inputs_sha256': {
            name: pin for name, (_, pin) in FROZEN.items()
        },
        'r76_contract_sha256': CONTRACT_SHA,
        'r76_independent_validation_sha256': VALIDATION_SHA,
    }

    target = pathlib.Path(out) / (
        'r77_intake_sensor_factor_boundary_v1.json'
    )

    with target.open('x', encoding='utf-8') as f:
        json.dump(output, f, sort_keys=True, indent=2)
        f.write('\n')

    print('R77_HISTORICAL_CLAIMS=11_FORMAT_ONLY')
    print('R77_HISTORICAL_TIMING=5_UNFILLED')
    print('R77_M2DGR_SENSOR_AND_FACTOR_GATES=2_REJECTED')
    print('R77_AUTHOR_LIKE_COMPLETE_CANDIDATE=NOT_AUTHORIZED')
    print('R77_RESULT=SOFTWARE_ONLY_GATE_BRIDGE_PASS')


if __name__ == '__main__':
    import sys
    produce(*sys.argv[1:])
