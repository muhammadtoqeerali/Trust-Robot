import unittest

from trust_robot.nova_schema_shadow_v1 import (
    SCHEMA,
    TOPICS,
    LIDAR_FIELDS,
    ShadowDenied,
    validate,
    review,
    create_factors,
    infer_real_health,
)


def example(stream='LEFT_IMAGE', seq=0, stamp=1000000000):
    topic, typ, frame = TOPICS[stream]

    if stream.endswith('IMAGE'):
        detail = {
            'width': 1920,
            'height': 1200,
            'encoding': 'rgb8',
        }

    elif stream.endswith('INFO'):
        detail = {
            'width': 1920,
            'height': 1200,
            'distortion_model': 'rational_polynomial',
            'distortion_count': 8,
            'k': [
                960.2, 0.0, 956.2,
                0.0, 960.3, 603.4,
                0.0, 0.0, 1.0,
            ],
        }

    elif stream == 'LIDAR':
        detail = {
            'width': 128000,
            'height': 1,
            'point_step': 26,
            'row_step': 3328000,
            'fields': [list(x) for x in LIDAR_FIELDS],
            'is_dense': False,
        }

    else:
        detail = {
            'orientation_declared': False,
            'angular_cov_first': 0.0,
            'linear_cov_first': 0.0,
        }

    return {
        'stream': stream,
        'topic': topic,
        'ros_type': typ,
        'frame_id': frame,
        'sequence': seq,
        'header_stamp_ns': stamp,
        'source_kind': 'SYNTHETIC',
        'detail': detail,
    }


def reject(obj):
    with unittest.TestCase().assertRaises(ShadowDenied):
        validate(obj)


class NovaShadowTests(unittest.TestCase):

    def test_01_schema(self):
        self.assertIn('A50_11', SCHEMA)

    def test_02_left_image(self):
        self.assertEqual(
            validate(example())['stream'],
            'left_image',
        )

    def test_03_right_image(self):
        self.assertEqual(
            validate(example('RIGHT_IMAGE'))['stream'],
            'right_image',
        )

    def test_04_left_info(self):
        self.assertEqual(
            validate(example('LEFT_INFO'))['stream'],
            'left_camera_info',
        )

    def test_05_right_info(self):
        self.assertEqual(
            validate(example('RIGHT_INFO'))['stream'],
            'right_camera_info',
        )

    def test_06_lidar(self):
        self.assertEqual(
            validate(example('LIDAR'))['stream'],
            'lidar',
        )

    def test_07_imu(self):
        self.assertEqual(
            validate(example('IMU'))['stream'],
            'imu',
        )

    def test_08_full_manufactured_batch(self):
        rows = [
            example(k, i, 1000000000 + i * 10000000)
            for k in TOPICS
            for i in range(3)
        ]
        x = review(rows)

        self.assertEqual(x['record_count'], 18)
        self.assertTrue(x['all_manufactured'])
        self.assertEqual(x['real_factor_count'], 0)
        self.assertEqual(
            x['real_factor_admission'],
            'DENIED',
        )

    def test_09_declared_physical_never_qualifies(self):
        a = example()
        a['source_kind'] = 'PHYSICAL_UNQUALIFIED'
        x = review([a])

        self.assertFalse(x['all_manufactured'])
        self.assertFalse(x['physical_clock_validated'])
        self.assertEqual(x['m2dgr_gates'], '11_CLOSED')

    def test_10_reject_extra_payload(self):
        a = example()
        a['data'] = b'raw'
        reject(a)

    def test_11_reject_unknown_topic(self):
        a = example()
        a['topic'] = '/cmd_vel'
        reject(a)

    def test_12_reject_wrong_type(self):
        a = example()
        a['ros_type'] = 'geometry_msgs/msg/Twist'
        reject(a)

    def test_13_reject_bad_frame(self):
        a = example()
        a['frame_id'] = 'map'
        reject(a)

    def test_14_reject_boolean_stamp(self):
        a = example()
        a['header_stamp_ns'] = True
        reject(a)

    def test_15_reject_zero_stamp(self):
        a = example()
        a['header_stamp_ns'] = 0
        reject(a)

    def test_16_reject_wrong_image_shape(self):
        a = example()
        a['detail']['width'] = 1280
        reject(a)

    def test_17_reject_bad_camera_k(self):
        a = example('LEFT_INFO')
        a['detail']['k'][0] = float('nan')
        reject(a)

    def test_18_reject_lidar_schema_shift(self):
        a = example('LIDAR')
        a['detail']['fields'][-1][1] = 20
        reject(a)

    def test_19_reject_imu_calibration_claim(self):
        a = example('IMU')
        a['detail']['calibrated'] = True
        reject(a)

    def test_20_reject_claimed_qualified_source(self):
        a = example()
        a['source_kind'] = 'QUALIFIED'
        reject(a)

    def test_21_reject_duplicate_sequence(self):
        a = example()
        b = example(stamp=1000000001)

        with self.assertRaises(ShadowDenied):
            review([a, b])

    def test_22_reject_time_reversal(self):
        a = example(stamp=1000000001)
        b = example(seq=1, stamp=1000000000)

        with self.assertRaises(ShadowDenied):
            review([a, b])

    def test_23_reject_empty_batch(self):
        with self.assertRaises(ShadowDenied):
            review([])

    def test_24_reject_batch_over_limit(self):
        with self.assertRaises(ShadowDenied):
            review([example()] * 257)

    def test_25_deny_factors(self):
        with self.assertRaises(ShadowDenied):
            create_factors(example())

    def test_26_deny_health(self):
        with self.assertRaises(ShadowDenied):
            infer_real_health(example())

    def test_27_reject_wrong_lidar_stride(self):
        a = example('LIDAR')
        a['detail']['point_step'] = 24
        reject(a)

    def test_28_reject_orientation_claim(self):
        a = example('IMU')
        a['detail']['orientation_declared'] = True
        reject(a)


if __name__ == '__main__':
    unittest.main()
