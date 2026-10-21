import json
import pathlib
import tempfile
import unittest
import r82_temporal as m

S = '/camera/imu'

def item(i):
    return {
        'schema': m.REC_SCHEMA,
        'trajectory_id': 'room_02',
        'split_role': 'train',
        'source_stream_id': S,
        'modality': 'imu',
        'selected_reader_index': i,
        'stream_index': i,
        'bag_record_time_ns': 1000+i*100,
        'header_stamp_ns': 100+i*10,
        'feature_values': [float(i), 9.8],
    }

class TemporalTests(unittest.TestCase):

    def run_sample(self, items):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            src = root/'source.jsonl'
            out = root/'out.jsonl'

            data = b''.join(
                m.canon(x) for x in items
            )

            src.write_bytes(data)

            result = m.process(
                src, out, 'room_02',
                S, len(items),
                __import__('hashlib').sha256(
                    data
                ).hexdigest()
            )

            rows = [
                json.loads(line)
                for line in out.read_bytes().splitlines()
            ]

            return result, rows

    def test_positive(self):
        a, rows = self.run_sample([
            item(i) for i in range(260)
        ])

        self.assertEqual(
            a['derived_window_count'], 2
        )

        self.assertEqual(
            [r['record_count'] for r in rows],
            [256, 4]
        )

        self.assertAlmostEqual(
            rows[0]['feature_mean'][0], 127.5
        )

        self.assertFalse(
            rows[1]['factor_executable']
        )

    def test_determinism(self):
        data = [item(i) for i in range(4)]

        self.assertEqual(
            self.run_sample(data),
            self.run_sample(data)
        )

    def reject(self, modify):
        arr = [item(i) for i in range(4)]
        modify(arr)

        with self.assertRaises(
            (
                m.EvidenceError,
                ValueError,
                TypeError,
                KeyError
            )
        ):
            self.run_sample(arr)

    def test_wrong_trajectory(self):
        self.reject(
            lambda a: a[1].update(
                trajectory_id='hall_02'
            )
        )

    def test_wrong_stream(self):
        self.reject(
            lambda a: a[0].update(
                source_stream_id='/handsfree/imu'
            )
        )

    def test_wrong_split(self):
        self.reject(
            lambda a: a[0].update(
                split_role='confirmation_test'
            )
        )

    def test_noncontiguous(self):
        self.reject(
            lambda a: a[2].update(
                stream_index=99
            )
        )

    def test_reader_index(self):
        self.reject(
            lambda a: a[2].update(
                selected_reader_index=1
            )
        )

    def test_nonfinite(self):
        self.reject(
            lambda a: a[0].update(
                feature_values=[float('nan'), 0.0]
            )
        )

    def test_new_health_field(self):
        self.reject(
            lambda a: a[0].update(
                health_probability=0.9
            )
        )

    def test_missing_feature(self):
        self.reject(
            lambda a: a[0].update(
                feature_values=[2.0]
            )
        )

    def test_negative_stamp(self):
        self.reject(
            lambda a: a[0].update(
                header_stamp_ns=-1
            )
        )

    def test_welford(self):
        w = m.Window(1)

        for x in (1., 2., 3., 4.):
            w.push([x], None)

        self.assertAlmostEqual(
            w.row(
                'room_02', S, 0
            )['feature_population_std'][0],
            (1.25)**0.5
        )

    def test_absent_windows_not_fabricated(self):
        self.assertEqual(
            m.STREAMS['/handsfree/imu'][1],
            'imu'
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
