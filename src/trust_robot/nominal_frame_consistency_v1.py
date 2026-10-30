"""R135-A27-7: internal SE(3) consistency of pinned nominal URDF geometry.

All matrices are T_target_source; they are not measured physical extrinsics.
Tests of orthogonality, composition, and nominal claims cannot establish
sensor mounting, frame aliases, calibration uncertainty, or factor permission.
"""
from __future__ import annotations

import hashlib
import json
import math

from trust_robot.nominal_frame_graph_v1 import (
    FrameGraphError, relative_transform, validate_graph,
)

SCHEMA = 'TRUST_ROBOT_R135_A27_7_FRAME_CONSISTENCY_V1'
TOLERANCE = 1e-9  # Numerical internal-consistency tolerance; NOT physical uncertainty.


def require(condition, message):
    if not condition:
        raise FrameGraphError(message)


def matmul(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(4))
             for j in range(4)] for i in range(4)]


def identity():
    return [[float(i == j) for j in range(4)] for i in range(4)]


def deviation(a, b):
    return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))


def checked_matrix(m):
    require(type(m) in (list, tuple) and len(m) == 4,
            'Matrix must be 4x4')
    require(all(type(row) in (list, tuple) and len(row) == 4 for row in m),
            'Matrix rows must contain four values')
    require(all(type(v) in (float, int) and math.isfinite(v)
                for row in m for v in row), 'Nonfinite or boolean transform')
    require(max(abs(a-b) for a, b in zip(m[3], (0, 0, 0, 1))) < TOLERANCE,
            'Invalid homogeneous matrix last row')
    return m


def rotation_error(m):
    checked_matrix(m)
    rtr = [[sum(m[k][i]*m[k][j] for k in range(3))
            for j in range(3)] for i in range(3)]
    error = max(abs(rtr[i][j] - float(i == j))
                for i in range(3) for j in range(3))
    a, b, c = m[0][:3], m[1][:3], m[2][:3]
    det = (a[0]*(b[1]*c[2]-b[2]*c[1])
           - a[1]*(b[0]*c[2]-b[2]*c[0])
           + a[2]*(b[0]*c[1]-b[1]*c[0]))
    return max(error, abs(det - 1))


def audit_nominal_consistency(document, frames):
    root, _ = validate_graph(document)
    require(all(j['type'] == 'fixed' for j in document['joints']),
            'Full geometry consistency requires fixed joints')
    require(type(frames) is list and 2 <= len(frames) <= 16
            and len(set(frames)) == len(frames)
            and all(type(f) is str and f in document['links'] for f in frames),
            'Invalid bounded frame list')
    require('bmi088_frame' not in frames, 'Unverified physical IMU frame')
    names = sorted(set(frames) | {root})
    matrices = {(src, dst): relative_transform(document, src, dst)
                for src in names for dst in names}
    max_orth = max(rotation_error(m) for m in matrices.values())
    max_inverse = max(
        deviation(matmul(matrices[(a,b)], matrices[(b,a)]), identity())
        for a in names for b in names
    )
    max_cycle = max(
        deviation(matmul(matrices[(b,c)], matrices[(a,b)]), matrices[(a,c)])
        for a in names for b in names for c in names
    )
    require(max(max_orth, max_inverse, max_cycle) <= TOLERANCE,
            'Nominal SE(3) algebra consistency failed')
    trace = [
        [src, dst, [[round(float(v), 12) for v in row]
                    for row in matrices[(src, dst)]]]
        for src in names for dst in names
    ]
    digest = hashlib.sha256(json.dumps(
        trace, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('ascii')).hexdigest()
    return {
        'schema': SCHEMA,
        'status': 'NOMINAL_INTERNAL_SE3_CONSISTENCY_ONLY',
        'root_frame': root,
        'frame_count': len(names),
        'pair_checks': len(names)**2,
        'composition_checks': len(names)**3,
        'max_rotation_orthogonality_and_det_error': max_orth,
        'max_inverse_closure_error': max_inverse,
        'max_composition_error': max_cycle,
        'nominal_transform_trace_sha256': digest,
        'numeric_tolerance_not_calibration_uncertainty': TOLERANCE,
        'bmi088_frame_transform': None,
        'physical_sensor_extrinsics_qualified': False,
        'real_factor_admission': 'DENIED',
        'm2dgr_gates': '11_CLOSED',
    }


def check_nominal_claim(document, claim):
    require(type(claim) is dict and set(claim) == {
        'source_frame', 'target_frame', 'T_target_source', 'scope',
    }, 'Unexpected transform claim fields')
    require(claim['scope'] == 'NOMINAL_URDF_ONLY',
            'Physical claim not authorized')
    matrix = checked_matrix(claim['T_target_source'])
    require(rotation_error(matrix) <= TOLERANCE,
            'Claim is not a proper rigid transform')
    expected = relative_transform(
        document, claim['source_frame'], claim['target_frame'])
    require(deviation(matrix, expected) <= TOLERANCE,
            'Matrix/direction differs from nominal URDF')
    return {
        'status': 'NOMINAL_CLAIM_CONSISTENT_NOT_CALIBRATED',
        'physically_qualified': False,
        'real_factor_admission': 'DENIED',
    }


def qualify_physical_extrinsic(*args, **kwargs):
    raise FrameGraphError('Nominal geometry cannot qualify physical extrinsics')
