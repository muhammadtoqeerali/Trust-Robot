"""R134-A37 bounded synthetic camera/IMU diagnostics.

Untrusted, non-authoritative residuals only.
No pose, factors, covariance, health, probability,
calibration estimation, external callbacks or I/O.

Angular bearing distinctness is not independent
visual or physical support.
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from statistics import median

SCHEMA = 'TRUST_ROBOT_R134_A37_CAMERA_IMU_SHADOW_V2'
STATUS = 'UNTRUSTED_DIAGNOSTIC_ONLY'

MAX_RAYS = 96
MAX_SAMPLES = 512
MAX_STEPS = 64
MAX_INTERVAL_NS = 200_000_000
MAX_GAP_NS = 20_000_000
MIN_RAY_SEPARATION_RAD = 1e-5


class ShadowInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ModeResidual:
    name: str
    median_deg: float
    p90_deg: float


@dataclass(frozen=True, slots=True)
class ShadowReport:
    schema: str
    status: str
    bearing_pair_count: int
    integration_steps: int
    modes: tuple[ModeResidual, ...]


def _num(x):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ShadowInputError('Expected finite real number')
    return float(x)


def _vec(v, *, unit=False, rate=False):
    if type(v) not in (list, tuple) or len(v) != 3:
        raise ShadowInputError('Expected 3-vector')

    a = tuple(_num(x) for x in v)

    if unit and abs(sum(x*x for x in a)-1.0) > 1e-5:
        raise ShadowInputError('Non-unit bearing')

    if rate and any(abs(x) > 1000 for x in a):
        raise ShadowInputError(
            'Gyro exceeds computational safety limit'
        )

    return a


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (
        a[1]*b[2]-a[2]*b[1],
        a[2]*b[0]-a[0]*b[2],
        a[0]*b[1]-a[1]*b[0]
    )


def _matvec(a, v):
    return tuple(_dot(row, v) for row in a)


def _matmul(a, b):
    return tuple(
        tuple(
            sum(a[i][k]*b[k][j] for k in range(3))
            for j in range(3)
        )
        for i in range(3)
    )


_IDENTITY = (
    (1.,0.,0.),
    (0.,1.,0.),
    (0.,0.,1.)
)


def _frame(r):
    if type(r) not in (tuple, list) or len(r) != 3:
        raise ShadowInputError('Frame rotation shape')

    a = tuple(_vec(row) for row in r)

    for i in range(3):
        for j in range(3):
            expected = 1. if i == j else 0.

            if abs(_dot(a[i],a[j])-expected) > 1e-5:
                raise ShadowInputError(
                    'Nonorthogonal frame rotation'
                )

    if abs(
        _dot(a[0],_cross(a[1],a[2]))-1
    ) > 1e-5:
        raise ShadowInputError(
            'Improper frame rotation'
        )

    return a


def _exp(v):
    theta = math.sqrt(_dot(v,v))

    if theta < 1e-14:
        return _IDENTITY

    x,y,z = (a/theta for a in v)

    skew = (
        (0.,-z,y),
        (z,0.,-x),
        (-y,x,0.)
    )

    square = _matmul(skew,skew)

    s = math.sin(theta)
    c = 1-math.cos(theta)

    return tuple(
        tuple(
            (1. if i == j else 0.)
            + s*skew[i][j]
            + c*square[i][j]
            for j in range(3)
        )
        for i in range(3)
    )


def _bearing_distance(a,b):
    cr = _cross(a,b)

    return math.atan2(
        math.sqrt(_dot(cr,cr)),
        _dot(a,b)
    )


def _unique_bearings(pairs):
    # Reject nearly identical origins or endpoints.
    # This is NOT proof of independent visual evidence.
    for j in range(len(pairs)):
        for i in range(j):
            if (
                _bearing_distance(
                    pairs[i][0],pairs[j][0]
                ) < MIN_RAY_SEPARATION_RAD
                or
                _bearing_distance(
                    pairs[i][1],pairs[j][1]
                ) < MIN_RAY_SEPARATION_RAD
            ):
                raise ShadowInputError(
                    'Duplicate/near-duplicate bearing support'
                )


def _rate_at(samples,timestamps,t):
    if not timestamps[0] <= t <= timestamps[-1]:
        raise ShadowInputError(
            'Missing IMU coverage'
        )

    idx = bisect_left(timestamps,t)

    if (
        idx < len(timestamps)
        and timestamps[idx] == t
    ):
        return samples[idx][1]

    lo,hi = idx-1,idx

    f = (
        (t-timestamps[lo])
        /(timestamps[hi]-timestamps[lo])
    )

    return tuple(
        (1-f)*samples[lo][1][j]
        + f*samples[hi][1][j]
        for j in range(3)
    )


def _increments(samples,begin,end,rci):
    timestamps = tuple(t for t,_ in samples)

    if not (
        timestamps[0] <= begin < end <= timestamps[-1]
    ):
        raise ShadowInputError(
            'Missing IMU coverage'
        )

    left = bisect_right(timestamps,begin)
    right = bisect_left(timestamps,end)

    nodes = [
        (
            begin,
            _rate_at(samples,timestamps,begin)
        )
    ]

    nodes.extend(samples[left:right])

    nodes.append((
        end,
        _rate_at(samples,timestamps,end)
    ))

    if len(nodes)-1 > MAX_STEPS:
        raise ShadowInputError(
            'IMU interval-count budget exceeded'
        )

    increments = []

    for (t0,w0),(t1,w1) in zip(
        nodes,nodes[1:]
    ):
        dt = t1-t0

        if not 0 < dt <= MAX_GAP_NS:
            raise ShadowInputError(
                'IMU interpolation gap'
            )

        body = tuple(
            (w0[i]+w1[i])*0.5*dt*1e-9
            for i in range(3)
        )

        increments.append(
            _matvec(rci,body)
        )

    return tuple(increments)


def _p90(a):
    a = sorted(a)
    x = .9*(len(a)-1)
    i = int(x)

    if i == len(a)-1:
        return a[i]

    return (
        a[i]
        +(a[i+1]-a[i])*(x-i)
    )


def evaluate(
    bearing_pairs,
    imu_samples,
    r_cam_imu,
    start_ns,
    end_ns,
    time_shift_ns=0
):
    """Return untrusted diagnostics, never authority."""

    rci = _frame(r_cam_imu)

    if any(
        type(t) is not int
        for t in (
            start_ns,end_ns,time_shift_ns
        )
    ):
        raise ShadowInputError(
            'Timestamps must be integers'
        )

    if not (
        0 <= start_ns < end_ns
        and end_ns-start_ns <= MAX_INTERVAL_NS
        and abs(time_shift_ns) <= 250_000_000
    ):
        raise ShadowInputError(
            'Interval or time shift out of bounds'
        )

    if (
        type(bearing_pairs) is not tuple
        or not 5 <= len(bearing_pairs) <= MAX_RAYS
    ):
        raise ShadowInputError(
            'Bearing-pair budget or shape'
        )

    pairs = []

    for pair in bearing_pairs:
        if type(pair) is not tuple or len(pair) != 2:
            raise ShadowInputError(
                'Invalid bearing pair'
            )

        pairs.append((
            _vec(pair[0],unit=True),
            _vec(pair[1],unit=True)
        ))

    _unique_bearings(pairs)

    if (
        type(imu_samples) is not tuple
        or not 2 <= len(imu_samples) <= MAX_SAMPLES
    ):
        raise ShadowInputError(
            'IMU sample budget or shape'
        )

    samples = []

    for row in imu_samples:
        if (
            type(row) is not tuple
            or len(row) != 2
            or type(row[0]) is not int
            or row[0] < 0
        ):
            raise ShadowInputError(
                'Invalid IMU sample'
            )

        samples.append((
            row[0],
            _vec(row[1],rate=True)
        ))

    if any(
        a[0] >= b[0]
        for a,b in zip(samples,samples[1:])
    ):
        raise ShadowInputError(
            'IMU samples nonmonotonic'
        )

    steps = _increments(
        samples,
        start_ns+time_shift_ns,
        end_ns+time_shift_ns,
        rci
    )

    modes = []

    for label,sign in (
        ('ZERO',0),
        ('NEGATIVE_GYRO',-1),
        ('POSITIVE_GYRO',1)
    ):
        cumulative = _IDENTITY

        if sign:
            for step in steps:
                rotation = _exp(
                    tuple(sign*x for x in step)
                )

                cumulative = _matmul(
                    rotation,cumulative
                )

        errors = [
            math.degrees(
                _bearing_distance(
                    _matvec(cumulative,a),b
                )
            )
            for a,b in pairs
        ]

        modes.append(ModeResidual(
            label,
            round(median(errors),9),
            round(_p90(errors),9)
        ))

    return ShadowReport(
        SCHEMA,
        STATUS,
        len(pairs),
        len(steps),
        tuple(modes)
    )
