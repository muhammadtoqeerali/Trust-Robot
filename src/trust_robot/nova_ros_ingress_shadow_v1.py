"""Offline-only Nova ROS-message metadata projection.

No rclpy import, ROS graph, device I/O, sensor payload reads,
physical clock qualification, pose computation or health weights.
ROS message type names are checks, not physical identity attestation.
"""
from __future__ import annotations

from trust_robot.nova_schema_shadow_v1 import TOPICS, ShadowDenied, validate, review

SCHEMA = 'TRUST_ROBOT_R135_A50_14_NOVA_ROS_INGRESS_SHADOW_V1'

BY_TOPIC = {
    record[0]: (key, record[1])
    for key, record in TOPICS.items()
}


class IngressDenied(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise IngressDenied(reason)


def exact_int(x, name):
    require(
        type(x) is int and x >= 0,
        'Invalid integer: ' + name
    )
    return x


def project_metadata(topic, message, sequence):
    """Project selected ROS header/layout fields; never access .data."""

    require(
        type(topic) is str and topic in BY_TOPIC,
        'Unknown ROS topic'
    )

    require(
        type(sequence) is int
        and 0 <= sequence <= 1000000,
        'Invalid sequence'
    )

    stream, ros_type = BY_TOPIC[topic]

    require(
        type(message).__name__ == ros_type.rsplit('/', 1)[-1],
        'Unexpected message class name'
    )

    try:
        header = message.header

        sec = exact_int(header.stamp.sec, 'sec')
        ns = exact_int(header.stamp.nanosec, 'nanosec')

        require(ns < 1000000000, 'Invalid nanoseconds')

        stamp = sec * 1000000000 + ns

        require(stamp > 0, 'Zero header timestamp')

        frame = header.frame_id

        require(type(frame) is str, 'Invalid frame')

        if stream.endswith('IMAGE'):
            detail = {
                'width': message.width,
                'height': message.height,
                'encoding': message.encoding,
            }

        elif stream.endswith('INFO'):
            require(
                len(message.k) == 9
                and len(message.d) <= 64,
                'CameraInfo array length'
            )

            detail = {
                'width': message.width,
                'height': message.height,
                'distortion_model': message.distortion_model,
                'distortion_count': len(message.d),
                'k': [float(value) for value in message.k],
            }

        elif stream == 'LIDAR':
            require(
                len(message.fields) <= 32,
                'Too many LiDAR fields'
            )

            detail = {
                'width': message.width,
                'height': message.height,
                'point_step': message.point_step,
                'row_step': message.row_step,
                'fields': [
                    [f.name, f.offset, f.datatype, f.count]
                    for f in message.fields
                ],
                'is_dense': message.is_dense,
            }

        else:
            detail = {
                'orientation_declared':
                    message.orientation_covariance[0] != -1.0,
                'angular_cov_first':
                    float(message.angular_velocity_covariance[0]),
                'linear_cov_first':
                    float(message.linear_acceleration_covariance[0]),
            }

        row = {
            'stream': stream,
            'topic': topic,
            'ros_type': ros_type,
            'frame_id': frame,
            'sequence': sequence,
            'header_stamp_ns': stamp,
            'source_kind': 'PHYSICAL_UNQUALIFIED',
            'detail': detail,
        }

        validate(row)

        return row

    except IngressDenied:
        raise

    except (
        AttributeError,
        IndexError,
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        ShadowDenied,
    ) as exc:
        raise IngressDenied(
            'Malformed or incompatible Nova ROS metadata'
        ) from exc


def review_projected(rows):
    """No estimator, pose, reliability label or factor admission."""
    return review(rows)
