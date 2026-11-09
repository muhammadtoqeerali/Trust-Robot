"""Prospective camera/IMU health evidence acquisition design; never source admission.

This adds sensor-specific proposed acquisition requirements above the generic
A37-2 artifact-shape checker. No thresholds, status labels, provenance
acceptance, time synchronization, model training, or hardware actions result.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Mapping

from trust_robot.prospective_health_evidence_intake_v1 import (
    GENERIC_ROLES, build_empty_candidate, audit_candidate,
)

SCHEMA = 'TRUST_ROBOT_R135_A37_4_CAMERA_IMU_PROSPECTIVE_ACQUISITION_V1'
STATUS = 'PROSPECTIVE_DESIGN_ONLY_SOURCE_PROTOCOL_NOT_ACCEPTED'

_DESIGNS = {
    'camera': {
        'measurement_role': 'provide image observations for vision-based relative-motion estimation',
        'instrumentation_candidates': (
            'Independent camera device state and exposure/gain telemetry with original acquisition provenance',
            'Independent scene/test-target or controlled imaging condition evidence for the same interval',
            'Independently recorded, explicitly authorized camera intervention and return-to-baseline evidence',
        ),
        'interval_association_requirements': (
            'Identify the exact camera instance, stream, frame sequence and data acquisition session',
            'Record the physical meaning and clock domain of device and image timestamps independently',
            'Bind device/scene evidence to the image measurement interval by an independently verified mechanism',
        ),
        'functional_state_evidence_questions': (
            'What independent observation establishes usable image measurements for the declared vision role?',
            'What independent evidence distinguishes impaired-but-usable imaging from unusable imaging?',
            'How are darkness, occlusion, blur, saturation and disconnection separated from cause attribution?',
        ),
        'cannot_assume': (
            'camera message presence means healthy',
            'camera image brightness or blur diagnostic alone is a health label',
            'camera-info nominal intrinsic values verify physical calibration',
        ),
    },
    'imu': {
        'measurement_role': 'provide angular-rate and acceleration measurements for inertial propagation',
        'instrumentation_candidates': (
            'Independent IMU device self-test, range/saturation, power and temperature-status evidence where supported',
            'Independent stationary or instrumented reference motion evidence from a documented test apparatus',
            'Independently recorded, explicitly authorized IMU impairment intervention and return-to-baseline evidence',
        ),
        'interval_association_requirements': (
            'Identify exact IMU device, axes/units, range setting, stream and acquisition session',
            'Record physical meaning and clock domain of IMU timestamps and independent reference timestamps',
            'Bind diagnostic/reference evidence to the IMU measurement interval by an independently verified mechanism',
        ),
        'functional_state_evidence_questions': (
            'What independent measurement verifies adequate angular-rate and acceleration information?',
            'What independent evidence separates biased/noisy-but-usable from saturated/stuck/unusable?',
            'How are vibration, platform motion and device faults distinguished without guessing from residuals?',
        ),
        'cannot_assume': (
            'IMU message arrival means healthy',
            'IMU vector magnitude or frontend residual alone is a health label',
            'stationary-looking bag proves a physical zero-motion reference',
        ),
    },
}

ROLE_PROOF = {
    'prospective_source_declaration_sha256': (
        'Prospectively documented source identity, declared sensing role, health-state criteria and research partition'
    ),
    'independent_measurement_role_evidence_sha256': (
        'An independently measured functional relationship supporting the declared sensing role, not estimator error'
    ),
    'independent_interval_provenance_sha256': (
        'Traceable evidence for physical measurement interval and independent event-time/clock association'
    ),
    'independent_state_criteria_evidence_sha256': (
        'Independently verified healthy/degraded/unusable state criteria, not diagnostic values as labels'
    ),
}

class AcquisitionDesignError(ValueError):
    pass


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def content_sha256(value: Mapping[str, object]) -> str:
    payload = dict(value)
    payload.pop('content_sha256', None)
    return sha256(_canonical_bytes(payload)).hexdigest()


def _require(ok: bool, why: str) -> None:
    if not ok:
        raise AcquisitionDesignError(why)


def build_design(modality: str) -> dict[str, object]:
    _require(type(modality) is str and modality in _DESIGNS,
             'Only camera and IMU prospective designs are supported')
    proposal = deepcopy(_DESIGNS[modality])
    packet = {
        'schema': SCHEMA,
        'status': STATUS,
        'modality': modality,
        'split_role': 'train',
        'measurement_role': proposal['measurement_role'],
        'instrumentation_candidates': list(proposal['instrumentation_candidates']),
        'interval_association_requirements': list(proposal['interval_association_requirements']),
        'functional_state_evidence_questions': list(proposal['functional_state_evidence_questions']),
        'cannot_assume': list(proposal['cannot_assume']),
        'generic_independent_artifact_roles': list(GENERIC_ROLES),
        'role_proof_requirements': dict(ROLE_PROOF),
        'source_specific_acceptance_protocol_selected': False,
        'physical_event_time_verified': False,
        'real_health_label_count': 0,
        'health_model_training_authorized': False,
        'sensor_suppression_authorized': False,
        'robot_action_authorized': False,
        'physical_intervention_authorized': False,
        'validation_access': False,
        'confirmation_access': False,
        'reference_trajectory_access': False,
    }
    packet['content_sha256'] = content_sha256(packet)
    return packet


def validate_design(packet: Mapping[str, object]) -> dict[str, object]:
    _require(type(packet) is dict, 'design must be an exact dict')
    modality = packet.get('modality')
    _require(type(modality) is str and modality in _DESIGNS,
             'only camera/IMU designs permitted')
    reference = build_design(modality)
    _require(packet == reference, 'design differs from frozen prospective draft')
    _require(packet.get('content_sha256') == content_sha256(packet),
             'design digest mismatch')
    return deepcopy(reference)


def build_empty_intake_packet(modality: str) -> dict[str, object]:
    """Bind A37-2 generic intake gaps, NEVER accept a real supervision source."""
    design = build_design(modality)
    source = build_empty_candidate('a37_4_candidate_' + modality, modality)
    review = audit_candidate(source)
    _require(review['evidence_roles_missing'] == list(GENERIC_ROLES),
             'unexpected independent evidence role set')
    packet = {
        'schema': SCHEMA,
        'packet_kind': 'DRAFT_SENSOR_SPECIFIC_PROSPECTIVE_ACQUISITION_REQUEST',
        'design': design,
        'source_candidate': source,
        'shape_review': review,
        'independent_source_accepted': False,
        'actual_status_telemetry_captured': False,
        'actual_intervention_performed': False,
        'real_healthy_degraded_unusable_labels': 0,
        'model_training_authorized': False,
        'robot_actions_authorized': False,
    }
    packet['content_sha256'] = content_sha256(packet)
    return packet


def validate_empty_intake_packet(packet: Mapping[str, object]) -> dict[str, object]:
    _require(type(packet) is dict, 'packet must be an exact dict')
    design = packet.get('design')
    _require(type(design) is dict, 'design missing')
    validated = validate_design(design)
    expected = build_empty_intake_packet(validated['modality'])
    _require(packet == expected, 'packet differs from empty draft intake')
    _require(packet.get('content_sha256') == content_sha256(packet),
             'packet digest mismatch')
    return deepcopy(expected)


def build_both_draft_packets() -> dict[str, object]:
    packet = {
        'schema': SCHEMA,
        'kind': 'CAMERA_AND_IMU_DRAFT_ACQUISITION_REQUESTS',
        'packets': [build_empty_intake_packet(m) for m in ('camera', 'imu')],
        'lidar_source_protocol_untouched': True,
        'accepted_baseline_nominality_sources': 0,
        'accepted_health_supervision_sources': 0,
        'real_health_labels': 0,
        'real_health_training': 'BLOCKED',
        'physical_factor_admission': 'DENIED',
        'safety_supervisor_execution': 'DENIED',
    }
    packet['content_sha256'] = content_sha256(packet)
    return packet
