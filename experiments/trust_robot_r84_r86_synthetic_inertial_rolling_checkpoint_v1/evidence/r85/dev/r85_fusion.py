"""R85 synthetic-only gap-aware 15D inertial factor graph interface.

Consumes R84 synthetic packet partitions.
Reuses existing analytic preintegration, 15D full covariance
whitening and residual evaluation.

No real M2DGR motion factor execution or calibration claim.
"""

from __future__ import annotations

import hashlib
import json
import math

import numpy as np

import r84_gap_frontend as gap

from trust_robot.analytic_inertial_15d import G

from trust_robot.analytic_imu_preintegration import (
    preintegrate,
)

from trust_robot.analytic_preintegrated_fusion import (
    COVARIANCE_FLOOR_STD,
    factor_whitener,
    whitened_inertial_residual,
)


SCHEMA = (
    'TRUST_ROBOT_R85_SYNTHETIC_GAP_AWARE_INERTIAL_FUSION_V1'
)


class FusionAdmissionError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise FusionAdmissionError(reason)


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            allow_nan=False
        ) + '\n'
    ).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def make_consistent_endpoint(pre):
    """Manufactured endpoint for mathematical residual closure only.

    The endpoint is deliberately constructed from the IMU factor.
    It is not independent truth or a localization estimate.
    """

    xi = np.zeros(15, dtype=np.float64)

    xi[:3] = [0.1, -0.2, 0.05]
    xi[6:9] = [0.25, -0.08, 0.11]

    xj = xi.copy()

    T = float(pre['total_dt'])

    xj[:3] = (
        xi[:3]
        + xi[6:9]*T
        + 0.5*G*T*T
        + pre['delta_p']
    )

    xj[3:6] = pre['delta_R'].as_rotvec()

    xj[6:9] = (
        xi[6:9]
        + G*T
        + pre['delta_v']
    )

    return xi, xj


def make_factor(readings):
    """Build a development-only factor using existing frozen math."""

    pre = preintegrate(list(readings))

    P = np.asarray(
        pre['covariance'],
        dtype=np.float64
    )

    L = factor_whitener(pre)

    need(
        P.shape == (15, 15)
        and L.shape == (15, 15),
        'FACTOR_DIMENSIONS'
    )

    need(
        np.isfinite(P).all()
        and np.isfinite(L).all(),
        'NONFINITE_COVARIANCE'
    )

    need(
        np.allclose(P, P.T, atol=1e-12),
        'COVARIANCE_SYMMETRY'
    )

    eigenvalues = np.linalg.eigvalsh(P)

    need(
        float(eigenvalues.min()) >= -1e-12,
        'COVARIANCE_PSD'
    )

    expected = (
        P
        + COVARIANCE_FLOOR_STD**2
        * np.eye(15)
    )

    reconstruction_error = float(
        np.max(np.abs(L @ L.T - expected))
    )

    need(
        reconstruction_error < 1e-10,
        'FULL_COVARIANCE_WHITENER'
    )

    xi, xj = make_consistent_endpoint(pre)

    residual = whitened_inertial_residual(
        xi,
        xj,
        (pre, L)
    )

    need(
        residual.shape == (15,)
        and np.isfinite(residual).all(),
        'WHITENED_RESIDUAL'
    )

    norm = float(
        np.linalg.norm(residual)
    )

    need(
        norm < 1e-6,
        'CONSISTENT_SYNTHETIC_ENDPOINT_CLOSURE'
    )

    return {
        'preintegration': pre,
        'whitener': L,
        'synthetic_start_state': xi,
        'synthetic_consistent_end_state': xj,
        'residual_norm': norm,
        'covariance_reconstruction_error':
            reconstruction_error,
        'covariance_trace': float(np.trace(P)),
        'covariance_min_eigenvalue':
            float(eigenvalues.min()),
    }


def build_graph(packets):
    """Construct permitted synthetic inertial edges.

    Segment IDs change at timestamp gaps.
    The graph NEVER inserts an edge between gap-separated segments.
    """

    groups, gap_count = gap.partition(packets)

    nodes = {}
    edges = []
    last_end = None
    segment = -1
    integrated = 0

    for index, (start, end, readings) in enumerate(groups):

        need(
            type(start) is int
            and type(end) is int
            and end > start,
            'WINDOW_TIME'
        )

        if last_end is None or start != last_end:
            if last_end is not None:
                need(
                    start > last_end,
                    'SEGMENT_ORDER'
                )

            segment += 1

        need(
            1 <= len(readings) <= gap.MAX_WINDOW_STEPS,
            'WINDOW_STEPS'
        )

        factor = make_factor(readings)

        pre = factor['preintegration']

        need(
            abs(
                float(pre['total_dt'])
                - (end-start)/1e9
            ) < 1e-10,
            'WINDOW_DURATION'
        )

        previous_node = f's{segment}:t{start}'
        current_node = f's{segment}:t{end}'

        for key, timestamp in (
            (previous_node, start),
            (current_node, end)
        ):
            node = {
                'node_id': key,
                'segment_id': segment,
                'synthetic_timestamp_ns': timestamp,
                'state_dimension': 15,
                'physical_state_estimated': False,
            }

            if key in nodes:
                need(
                    nodes[key] == node,
                    'NODE_ID_COLLISION'
                )
            else:
                nodes[key] = node

        edge = {
            'window_index': index,
            'segment_id': segment,
            'from_node': previous_node,
            'to_node': current_node,
            'sample_count': len(readings),
            'synthetic_dt_s': float(
                pre['total_dt']
            ),
            'covariance_dimension': 15,
            'full_correlated_whitening': True,
            'covariance_trace':
                factor['covariance_trace'],
            'covariance_min_eigenvalue':
                factor['covariance_min_eigenvalue'],
            'covariance_reconstruction_max_error':
                factor['covariance_reconstruction_error'],
            'whitened_residual_norm_at_constructed_endpoint':
                factor['residual_norm'],
            'endpoint_reference_independent': False,
            'synthetic_only': True,
            'real_factor_executable': False,
        }

        need(
            edge['from_node'] != edge['to_node'],
            'SELF_EDGE'
        )

        edges.append(edge)

        integrated += len(readings)
        last_end = end

    segments = segment + 1

    need(
        segments > 0
        and gap_count == segments-1,
        'UNACCOUNTED_TIMESTAMP_GAP'
    )

    need(
        integrated + gap_count == len(packets)-1,
        'SAMPLE_PAIR_ACCOUNTING'
    )

    need(
        len(edges) == len(groups),
        'EDGE_COUNT'
    )

    need(
        len(nodes) == len(edges)+segments,
        'NODE_CONTINUITY'
    )

    for edge in edges:
        a = nodes[edge['from_node']]
        b = nodes[edge['to_node']]

        need(
            a['segment_id'] == b['segment_id'],
            'CROSS_GAP_EDGE'
        )

        need(
            a['synthetic_timestamp_ns']
            < b['synthetic_timestamp_ns'],
            'EDGE_TIME_ORDER'
        )

    # No optimizer is run. Only a manufactured endpoint is
    # used to test the existing factor residual implementation.

    return {
        'source': 'ANALYTIC_FIXTURE',
        'input_packet_count': len(packets),
        'segment_count': segments,
        'safe_factor_count': len(edges),
        'integrated_sample_pairs': integrated,
        'rejected_gap_pairs': gap_count,
        'node_count': len(nodes),
        'nodes': [
            nodes[k]
            for k in sorted(
                nodes,
                key=lambda k: (
                    nodes[k]['segment_id'],
                    nodes[k]['synthetic_timestamp_ns']
                )
            )
        ],
        'edges': edges,
        'bridging_gap_factors': 0,
        'interpolation_performed': False,
        'full_15d_whitening_exercised': True,
        'nonlinear_solver_executed': False,
        'physical_clock_qualified': False,
        'real_factor_admission': False,
    }


def execute(r84_report):
    need(
        r84_report.get('status') ==
        'PASS_SOFTWARE_ONLY',
        'R84_STATUS'
    )

    need(
        r84_report.get('scientific_gates_closed') == 11,
        'R84_GATES'
    )

    need(
        r84_report.get('real_pose_factors_authorized') is False
        and r84_report.get(
            'recorded_imu_preintegration_performed'
        ) is False,
        'R84_SCIENTIFIC_BOUNDARY'
    )

    scenarios = {}

    cases = (
        'continuous',
        'single_gap',
        'accel_injection',
        'gyro_injection'
    )

    for name in cases:
        packets = gap.fixture(name)

        # Verify that the frozen R84 diagnostics and
        # the current R84 implementation agree.
        original = gap.analyze(packets)

        need(
            original == r84_report['scenarios'][name],
            'R84_REPLAY_MISMATCH:'+name
        )

        scenarios[name] = build_graph(packets)

    clean = scenarios['continuous']
    damaged = scenarios['single_gap']

    need(
        clean['safe_factor_count'] == 2
        and clean['segment_count'] == 1
        and clean['integrated_sample_pairs'] == 8
        and clean['rejected_gap_pairs'] == 0,
        'CLEAN_GRAPH'
    )

    need(
        damaged['safe_factor_count'] == 2
        and damaged['segment_count'] == 2
        and damaged['integrated_sample_pairs'] == 7
        and damaged['rejected_gap_pairs'] == 1,
        'GAP_GRAPH'
    )

    need(
        all(
            e['segment_id'] == 0
            for e in clean['edges']
        ),
        'CLEAN_SEGMENT'
    )

    need(
        [
            e['segment_id']
            for e in damaged['edges']
        ] == [0, 1],
        'GAP_SEGMENT_BOUNDARY'
    )

    need(
        all(
            s['bridging_gap_factors'] == 0
            and s['real_factor_admission'] is False
            and s['nonlinear_solver_executed'] is False
            for s in scenarios.values()
        ),
        'EXECUTION_BOUNDARY'
    )

    return {
        'schema': SCHEMA,
        'status': 'PASS_SOFTWARE_ONLY',
        'source': 'ANALYTIC_FIXTURE',
        'scenarios': scenarios,
        'scenario_count': 4,
        'algorithm':
            'R84_SEGMENTS_PLUS_FROZEN_15D_INERTIAL_PREINTEGRATION_AND_WHITENING',
        'factor_graph_interface_implemented': True,
        'full_correlated_covariance_whitening': True,
        'bias_sensitive_preintegrator_reused': True,
        'constructed_endpoint_residual_closure_verified': True,
        'constructed_endpoint_is_independent_truth': False,
        'cross_gap_factors_constructed': 0,
        'recorded_sensor_pose_factors_constructed': 0,
        'real_estimator_optimization_executed': False,
        'actual_sensor_timebase_qualified': False,
        'camera_imu_lidar_alignment_performed': False,
        'health_probability_or_label_estimated': False,
        'ate_rpe_computed': False,
        'rosbags_or_gt_opened': False,
        'confirmation_test_accessed': False,
        'scientific_gates_closed': 11,
    }


if __name__ == '__main__':
    import sys
    from pathlib import Path

    report_path, output_dir = map(
        Path, sys.argv[1:]
    )

    original_raw = report_path.read_bytes()

    original = json.loads(original_raw)

    output = execute(original)

    output['r84_report_sha256'] = sha(
        original_raw
    )

    target = (
        output_dir /
        'r85_synthetic_gap_aware_fusion_v1.json'
    )

    with target.open('xb') as f:
        f.write(canonical(output))

    print('R85_SYNTHETIC_GAP_AWARE_FUSION_INTERFACE=PASS')
