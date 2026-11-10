"""R135-A40-3: synthetic-only paired observability falsification.

Compares published aggregate diagnostics with their restricted public projection.
No real data, physical time binding, health supervision, attack attribution,
trained probabilities, estimator factor admission, or robot control.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from math import isfinite
from typing import Any

from trust_robot import synthetic_diagnostic_stress_v1 as stress

SCHEMA = 'trust_robot_synthetic_observability_falsification_v1'
SOURCE_ROLE = 'MANUFACTURED_FIXTURES_ONLY_NO_REAL_SENSOR_OR_DATASET'
# Labels below identify design operations, not physical faults or attacks.
CASES = (
    ('both_header_common_shift', 'camera', 'numeric_clock_common_shift', 'NO_DIAGNOSTIC_CHANGE'),
    ('both_recorder_common_shift', 'camera', 'recorder_clock_common_shift', 'NO_DIAGNOSTIC_CHANGE'),
    ('camera_zero_location_swap', 'camera', 'zero_flag_relocation', 'NO_DIAGNOSTIC_CHANGE'),
    ('camera_ordinal_swap', 'camera', 'ordered_header_swap', 'DETAIL_ONLY_CHANGE'),
    ('camera_recorder_small_jitter', 'camera', 'recorder_axis_jitter', 'DETAIL_ONLY_CHANGE'),
    ('right_recorder_small_offset', 'camera', 'recorder_axis_shift', 'DETAIL_ONLY_CHANGE'),
    ('imu_sign_inversion', 'imu', 'direction_flip_equal_norm', 'NO_DIAGNOSTIC_CHANGE'),
    ('imu_axis_permutation', 'imu', 'axis_permutation_equal_norm', 'NO_DIAGNOSTIC_CHANGE'),
    ('imu_sample_reverse', 'imu', 'temporal_reorder_equal_distribution', 'NO_DIAGNOSTIC_CHANGE'),
    ('imu_bias', 'imu', 'vector_magnitude_change', 'DETAIL_ONLY_CHANGE'),
    ('imu_noise', 'imu', 'deterministic_vector_noise', 'DETAIL_ONLY_CHANGE'),
    ('lidar_slot_redistribution', 'lidar', 'constant_total_slots', 'NO_DIAGNOSTIC_CHANGE'),
    ('lidar_message_reverse', 'lidar', 'layout_order_reversal', 'NO_DIAGNOSTIC_CHANGE'),
    ('lidar_field_layout_change', 'lidar', 'field_layout_histogram', 'DETAIL_ONLY_CHANGE'),
    ('lidar_slots_removed', 'lidar', 'reported_slots_removed', 'PUBLIC_SUMMARY_CHANGE'),
    ('camera_zero_flags_added', 'camera', 'payload_boolean_marker', 'PUBLIC_SUMMARY_CHANGE'),
    ('right_header_offset', 'camera', 'numeric_header_mismatch', 'PUBLIC_SUMMARY_CHANGE'),
    ('right_message_removed', 'camera', 'record_list_removal', 'PUBLIC_SUMMARY_CHANGE'),
    ('right_delivery_burst', 'camera', 'recorder_burst_and_gap', 'PUBLIC_SUMMARY_CHANGE'),
)
EXCLUDED_NOT_REPRESENTABLE = (
    'camera_pixel_blur', 'camera_stale_pixel_content', 'lidar_return_geometry',
    'manufacturer_health_register', 'physical_time_source_binding',
)


def paired_fixture(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a fresh manufactured control and a single explicit treatment."""
    if case_id not in {r[0] for r in CASES}:
        raise ValueError('unregistered manufactured case')
    control = stress.manufactured_baseline()
    # The relocation study's separate manufactured control intentionally has
    # one zero marker. A relocation is otherwise impossible from all-nonzero.
    if case_id == 'camera_zero_location_swap':
        control['left'][5]['zero_payload'] = True
    treated = deepcopy(control)
    if case_id == 'both_header_common_shift':
        for lane in ('left', 'right'):
            for f in treated[lane]:
                f['header_ns'] += 10_000_000
    elif case_id == 'both_recorder_common_shift':
        for lane in ('left', 'right'):
            for f in treated[lane]:
                f['recorder_ns'] += 20_000_000
    elif case_id == 'camera_zero_location_swap':
        treated['left'][5]['zero_payload'] = False
        treated['left'][7]['zero_payload'] = True
    elif case_id == 'camera_ordinal_swap':
        treated['left'][3], treated['left'][7] = treated['left'][7], treated['left'][3]
    elif case_id == 'camera_recorder_small_jitter':
        treated['right'][6]['recorder_ns'] += 2_000_000
    elif case_id == 'right_recorder_small_offset':
        for f in treated['right']:
            f['recorder_ns'] += 1_000_000
    elif case_id == 'imu_sign_inversion':
        for f in treated['imu']:
            f['gyro_xyz'][0] *= -1
        # Index zero is zero for some elements; nonzero values still change.
    elif case_id == 'imu_axis_permutation':
        for f in treated['imu']:
            f['gyro_xyz'][0], f['gyro_xyz'][1] = f['gyro_xyz'][1], f['gyro_xyz'][0]
    elif case_id == 'imu_sample_reverse':
        treated['imu'].reverse()
    elif case_id == 'imu_bias':
        treated = stress.apply_case(control, 'imu_bias')
    elif case_id == 'imu_noise':
        treated = stress.apply_case(control, 'imu_noise')
    elif case_id == 'lidar_slot_redistribution':
        treated['lidar'][0]['point_slots'] += 20
        treated['lidar'][1]['point_slots'] -= 20
    elif case_id == 'lidar_message_reverse':
        # Manufacture heterogeneous valid layouts, in both control and treatment.
        control['lidar'][1]['field_count'] = 5
        treated = deepcopy(control)
        treated['lidar'].reverse()
    elif case_id == 'lidar_field_layout_change':
        treated = stress.apply_case(control, 'lidar_layout_shift')
    elif case_id == 'lidar_slots_removed':
        treated = stress.apply_case(control, 'lidar_slots_zeroed')
    elif case_id == 'camera_zero_flags_added':
        treated = stress.apply_case(control, 'camera_zero_benign')
    elif case_id == 'right_header_offset':
        treated = stress.apply_case(control, 'camera_header_perturbation')
    elif case_id == 'right_message_removed':
        treated = stress.apply_case(control, 'camera_message_removal')
    elif case_id == 'right_delivery_burst':
        treated = stress.apply_case(control, 'camera_delivery_burst')
    if control == treated:
        raise AssertionError('synthetic treatment did not change a manufactured input')
    return control, treated


def _canonical(value: Any) -> str:
    """Canonicalize scalar aggregate float noise, without serializing inputs."""
    def walk(x: Any) -> Any:
        if isinstance(x, float):
            if not isfinite(x):
                raise ValueError('nonfinite aggregate')
            return round(x, 9)
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [walk(v) for v in x]
        return x
    return json.dumps(walk(value), sort_keys=True, separators=(',', ':'), allow_nan=False)


def _aggregate_characterization(fixture: dict[str, Any]) -> tuple[dict, dict]:
    # Published diagnostic code is the sole measurement contract. Full view
    # still consists of *aggregates*, not frame records, IMU vectors or scans.
    observed = stress._characterize(fixture)
    detail = {k: observed[k] for k in ('left', 'right', 'join', 'imu', 'lidar')}
    public = observed['safe']
    return detail, public


def _changed_aggregate_fields(control: dict, treated: dict, prefix: str = '') -> list[str]:
    """Return schema field names only; never export sensitive input values."""
    keys = sorted(set(control) | set(treated))
    changed = []
    for k in keys:
        label = f'{prefix}.{k}' if prefix else k
        a, b = control.get(k), treated.get(k)
        if isinstance(a, dict) and isinstance(b, dict):
            changed.extend(_changed_aggregate_fields(a, b, label))
        elif _canonical(a) != _canonical(b):
            changed.append(label)
    return changed


def run_falsification() -> dict:
    rows = []
    for case_id, modality, mechanism, expected in CASES:
        control, treated = paired_fixture(case_id)
        cd, cp = _aggregate_characterization(control)
        td, tp = _aggregate_characterization(treated)
        changed_detail = _changed_aggregate_fields(cd, td)
        changed_public = _changed_aggregate_fields(cp, tp)
        if changed_public and not changed_detail:
            raise AssertionError('public projection changed without detailed aggregates')
        observed = ('PUBLIC_SUMMARY_CHANGE' if changed_public else
                    'DETAIL_ONLY_CHANGE' if changed_detail else 'NO_DIAGNOSTIC_CHANGE')
        if observed != expected:
            raise AssertionError(f'{case_id}: {observed}, expected {expected}')
        rows.append({'case_id': case_id, 'modality': modality,
                     'manufactured_mechanism': mechanism,
                     'visibility': observed, 'changed_detail_fields': changed_detail,
                     'changed_public_fields': changed_public})
    counts = Counter(x['visibility'] for x in rows)
    modalities = {k: {v: sum(row['modality'] == k and row['visibility'] == v for row in rows)
                       for v in ('NO_DIAGNOSTIC_CHANGE', 'DETAIL_ONLY_CHANGE', 'PUBLIC_SUMMARY_CHANGE')}
                  for k in ('camera', 'imu', 'lidar')}
    return {'schema': SCHEMA, 'source_role': SOURCE_ROLE,
            'case_count': len(rows), 'visibility_counts': dict(sorted(counts.items())),
            'visibility_by_modality': modalities,
            'excluded_unrepresented_not_simulated': list(EXCLUDED_NOT_REPRESENTABLE),
            'physical_health_labels_accepted': 0, 'attack_attribution': 'DENIED',
            'physical_clock_sync': 'NOT_QUALIFIED', 'real_factors': 'DENIED',
            'trained_health_model': 'NOT_QUALIFIED', 'robot_control': 'DENIED',
            'train_validation_confirmation_datasets': 'NOT_ACCESSED',
            'interpretation': ('Observational equivalence under manufactured fixtures '
                               'does not prove physical health, attack causation, or no fault'),
            'rows': rows}
