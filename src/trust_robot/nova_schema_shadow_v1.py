"""Nova-shaped ROS metadata validator. No ROS imports or device I/O.

Designed from operator-reported A50-9/A50-10 observations.
Does not qualify physical calibration, time, health, ground
truth, localization or real factor admission.
"""

from __future__ import annotations

import math

from trust_robot.physical_ros_fusion_boundary_v1 import (
    review_batch as a29_review,
)

SCHEMA = 'TRUST_ROBOT_R135_A50_11_NOVA_SCHEMA_SHADOW_V1'

TOPICS = {
    'LEFT_IMAGE': (
        '/front_stereo_camera/left/image_raw',
        'sensor_msgs/msg/Image',
        'front_stereo_camera_left_optical',
    ),
    'RIGHT_IMAGE': (
        '/front_stereo_camera/right/image_raw',
        'sensor_msgs/msg/Image',
        'front_stereo_camera_right_optical',
    ),
    'LEFT_INFO': (
        '/front_stereo_camera/left/camera_info',
        'sensor_msgs/msg/CameraInfo',
        'front_stereo_camera_left_optical',
    ),
    'RIGHT_INFO': (
        '/front_stereo_camera/right/camera_info',
        'sensor_msgs/msg/CameraInfo',
        'front_stereo_camera_right_optical',
    ),
    'LIDAR': (
        '/front_3d_lidar/lidar_points',
        'sensor_msgs/msg/PointCloud2',
        'front_3d_lidar',
    ),
    'IMU': (
        '/front_stereo_imu/imu',
        'sensor_msgs/msg/Imu',
        'bmi088_frame',
    ),
}

LIDAR_FIELDS = (
    ('x', 0, 7, 1),
    ('y', 4, 7, 1),
    ('z', 8, 7, 1),
    ('intensity', 12, 7, 1),
    ('ring', 16, 4, 1),
    ('timestamp', 18, 8, 1),
)

A29_STREAM = {
    'LEFT_IMAGE': 'left_image',
    'RIGHT_IMAGE': 'right_image',
    'LEFT_INFO': 'left_camera_info',
    'RIGHT_INFO': 'right_camera_info',
    'LIDAR': 'lidar',
    'IMU': 'imu',
}


class ShadowDenied(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise ShadowDenied(reason)


def number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def validate(row):
    """Validate exact, payload-free Nova metadata."""

    need(
        type(row) is dict and set(row) == {
            'stream',
            'topic',
            'ros_type',
            'frame_id',
            'sequence',
            'header_stamp_ns',
            'source_kind',
            'detail',
        },
        'Wrong descriptor keys; raw payloads forbidden',
    )

    stream = row['stream']

    need(
        type(stream) is str and stream in TOPICS,
        'Unknown stream',
    )

    topic, ros_type, frame = TOPICS[stream]

    need(
        row['topic'] == topic
        and row['ros_type'] == ros_type
        and row['frame_id'] == frame,
        'Topic/type/frame mismatch',
    )

    need(
        type(row['sequence']) is int
        and 0 <= row['sequence'] <= 1000000,
        'Invalid sequence',
    )

    need(
        type(row['header_stamp_ns']) is int
        and row['header_stamp_ns'] > 0,
        'Invalid header timestamp',
    )

    need(
        row['source_kind'] in (
            'SYNTHETIC',
            'PHYSICAL_UNQUALIFIED',
        ),
        'Source cannot be declared qualified',
    )

    d = row['detail']
    need(type(d) is dict, 'Detail must be a dict')

    if stream.endswith('IMAGE'):
        need(
            set(d) == {
                'width',
                'height',
                'encoding',
            },
            'Image keys',
        )

        need(
            type(d['width']) is int
            and d['width'] == 1920
            and type(d['height']) is int
            and d['height'] == 1200
            and d['encoding'] == 'rgb8',
            'Image layout drift',
        )

    elif stream.endswith('INFO'):
        need(
            set(d) == {
                'width',
                'height',
                'distortion_model',
                'distortion_count',
                'k',
            },
            'CameraInfo keys',
        )

        need(
            type(d['width']) is int
            and d['width'] == 1920
            and type(d['height']) is int
            and d['height'] == 1200
            and d['distortion_model'] == 'rational_polynomial'
            and type(d['distortion_count']) is int
            and d['distortion_count'] == 8,
            'CameraInfo layout drift',
        )

        k = d['k']

        need(
            type(k) is list
            and len(k) == 9
            and all(number(x) for x in k)
            and k[0] > 0
            and k[4] > 0
            and 0 <= k[2] < 1920
            and 0 <= k[5] < 1200,
            'Invalid manufactured intrinsics',
        )

    elif stream == 'LIDAR':
        need(
            set(d) == {
                'width',
                'height',
                'point_step',
                'row_step',
                'fields',
                'is_dense',
            },
            'LiDAR keys',
        )

        need(
            all(
                type(d[k]) is int
                for k in (
                    'width',
                    'height',
                    'point_step',
                    'row_step',
                )
            )
            and (
                d['width'],
                d['height'],
                d['point_step'],
                d['row_step'],
            ) == (128000, 1, 26, 3328000)
            and type(d['is_dense']) is bool
            and d['is_dense'] is False,
            'LiDAR shape drift',
        )

        fields = d['fields']

        need(
            type(fields) is list
            and len(fields) == 6
            and all(
                type(f) in (tuple, list)
                and len(f) == 4
                for f in fields
            )
            and tuple(tuple(f) for f in fields) == LIDAR_FIELDS,
            'LiDAR point fields drift',
        )

    else:
        need(
            set(d) == {
                'orientation_declared',
                'angular_cov_first',
                'linear_cov_first',
            },
            'IMU keys',
        )

        need(
            d['orientation_declared'] is False
            and number(d['angular_cov_first'])
            and d['angular_cov_first'] == 0
            and number(d['linear_cov_first'])
            and d['linear_cov_first'] == 0,
            'IMU declaration drift',
        )

    # Descriptor only. Zero values do not represent
    # measured recorder time or measured payload size.
    return {
        'stream': A29_STREAM[stream],
        'sequence': row['sequence'],
        'header_stamp_ns': row['header_stamp_ns'],
        'recorder_stamp_ns': 0,
        'frame_id': frame,
        'payload_bytes': 0,
        'source_kind': (
            'SYNTHETIC'
            if row['source_kind'] == 'SYNTHETIC'
            else 'PHYSICAL'
        ),
    }


def review(rows):
    """Run Nova schema checks through the existing A29 boundary."""

    need(
        type(rows) is list and 0 < len(rows) <= 256,
        'Bounded nonempty input required',
    )

    descriptors = [validate(row) for row in rows]

    try:
        result = a29_review(descriptors)
    except Exception as exc:
        raise ShadowDenied(
            'A29 fusion boundary denied descriptors'
        ) from exc

    need(
        result['real_factor_admission'] == 'DENIED'
        and result['real_factor_count'] == 0
        and result['estimator_invoked'] is False
        and result['physical_pose_estimated'] is False
        and result['m2dgr_gates'] == '11_CLOSED',
        'Scientific boundary drift',
    )

    counts = {
        k: sum(row['stream'] == k for row in rows)
        for k in TOPICS
    }

    return {
        'schema': SCHEMA,
        'status': 'SCHEMA_ONLY_NOT_PHYSICAL_QUALIFICATION',
        'record_count': len(rows),
        'stream_counts': counts,
        'all_manufactured': all(
            r['source_kind'] == 'SYNTHETIC'
            for r in rows
        ),
        'physical_clock_validated': False,
        'physical_extrinsics_validated': False,
        'intrinsics_independently_calibrated': False,
        'measurement_covariance_calibrated': False,
        'real_health_labels': 0,
        'independent_ground_truth': False,
        'real_factor_count': 0,
        'real_factor_admission': 'DENIED',
        'robot_actuation': 'DENIED',
        'm2dgr_gates': '11_CLOSED',
    }


def create_factors(*args, **kwargs):
    raise ShadowDenied(
        'Physical Nova sensor factor creation DENIED'
    )


def infer_real_health(*args, **kwargs):
    raise ShadowDenied(
        'Real Nova sensor health inference DENIED'
    )
