"""Offline ROS-shaped objects; payload access is an exception."""

import unittest

from test_nova_schema_shadow_v1 import example

from types import SimpleNamespace as NS

from trust_robot.nova_ros_ingress_shadow_v1 import (
    SCHEMA,
    BY_TOPIC,
    IngressDenied,
    project_metadata,
    review_projected,
)


def fake(row):
    detail = row['detail']
    class_name = row['ros_type'].rsplit('/', 1)[-1]

    def forbidden_payload(_):
        raise AssertionError(
            'Raw sensor payload access is forbidden'
        )

    cls = type(
        class_name,
        (),
        {'data': property(forbidden_payload)}
    )

    msg = cls()

    sec, ns = divmod(
        row['header_stamp_ns'],
        1000000000
    )

    msg.header = NS(
        stamp=NS(sec=sec, nanosec=ns),
        frame_id=row['frame_id']
    )

    if row['stream'].endswith('IMAGE'):
        msg.width = detail['width']
        msg.height = detail['height']
        msg.encoding = detail['encoding']

    elif row['stream'].endswith('INFO'):
        msg.width = detail['width']
        msg.height = detail['height']
        msg.distortion_model = detail['distortion_model']
        msg.d = [0.0] * detail['distortion_count']
        msg.k = list(detail['k'])

    elif row['stream'] == 'LIDAR':
        for key in (
            'width',
            'height',
            'point_step',
            'row_step',
            'is_dense',
        ):
            setattr(msg, key, detail[key])

        msg.fields = [
            NS(
                name=x[0],
                offset=x[1],
                datatype=x[2],
                count=x[3]
            )
            for x in detail['fields']
        ]

    else:
        msg.orientation_covariance = [
            -1.0
            if not detail['orientation_declared']
            else 0.0
        ]

        msg.angular_velocity_covariance = [
            detail['angular_cov_first']
        ]

        msg.linear_acceleration_covariance = [
            detail['linear_cov_first']
        ]

    return msg


class IngressTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Entirely manufactured: no physical evidence file reads.
        cls.rows = [
            dict(
                example(
                    stream,
                    i,
                    1_000_000_000 + i * 10_000_000,
                ),
                source_kind='PHYSICAL_UNQUALIFIED',
            )
            for stream in (
                'LEFT_IMAGE',
                'RIGHT_IMAGE',
                'LEFT_INFO',
                'RIGHT_INFO',
                'LIDAR',
                'IMU',
            )
            for i in range(3)
        ]
        assert len(cls.rows) == 18

    def baseline(self, stream='LEFT_IMAGE'):
        return next(
            x for x in self.rows
            if x['stream'] == stream
        )

    def check_denied(
        self,
        row,
        msg=None,
        topic=None,
        sequence=None,
    ):
        with self.assertRaises(IngressDenied):
            project_metadata(
                topic if topic is not None else row['topic'],
                msg if msg is not None else fake(row),
                sequence if sequence is not None
                else row['sequence'],
            )

    def test_01_schema(self):
        self.assertIn('A50_14', SCHEMA)
        self.assertEqual(len(BY_TOPIC), 6)

    def test_02_roundtrip_18_manufactured_unqualified_metadata_rows(self):
        projected = [
            project_metadata(
                r['topic'],
                fake(r),
                r['sequence']
            )
            for r in self.rows
        ]

        self.assertEqual(projected, self.rows)

        result = review_projected(projected)

        self.assertEqual(result['record_count'], 18)
        self.assertEqual(result['real_factor_count'], 0)
        self.assertEqual(
            result['real_factor_admission'],
            'DENIED'
        )
        self.assertFalse(result['all_manufactured'])
        self.assertEqual(
            result['m2dgr_gates'],
            '11_CLOSED'
        )

    def test_03_unknown_topic(self):
        self.check_denied(
            self.baseline(),
            topic='/cmd_vel'
        )

    def test_04_wrong_message_class(self):
        row = self.baseline()

        self.check_denied(
            row,
            msg=NS(header=fake(row).header)
        )

    def test_05_boolean_sequence(self):
        self.check_denied(
            self.baseline(),
            sequence=True
        )

    def test_06_negative_sequence(self):
        self.check_denied(
            self.baseline(),
            sequence=-1
        )

    def test_07_zero_timestamp(self):
        row = self.baseline()
        msg = fake(row)

        msg.header.stamp.sec = 0
        msg.header.stamp.nanosec = 0

        self.check_denied(row, msg=msg)

    def test_08_nanosecond_overflow(self):
        row = self.baseline()
        msg = fake(row)

        msg.header.stamp.nanosec = 1000000000

        self.check_denied(row, msg=msg)

    def test_09_wrong_frame(self):
        row = self.baseline()
        msg = fake(row)

        msg.header.frame_id = 'map'

        self.check_denied(row, msg=msg)

    def test_10_camera_dimension_drift(self):
        row = self.baseline()
        msg = fake(row)

        msg.width = 1280

        self.check_denied(row, msg=msg)

    def test_11_lidar_fields_drift(self):
        row = self.baseline('LIDAR')
        msg = fake(row)

        msg.fields[-1].offset = 20

        self.check_denied(row, msg=msg)

    def test_12_imu_missing_covariance(self):
        row = self.baseline('IMU')
        msg = fake(row)

        msg.angular_velocity_covariance = []

        self.check_denied(row, msg=msg)


if __name__ == '__main__':
    unittest.main()
