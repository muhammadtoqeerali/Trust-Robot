import importlib.util
import pathlib
import unittest

src = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'trust_robot' / 'unlabelled_multimodal_diagnostics_v1.py'
spec = importlib.util.spec_from_file_location('diag', src)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)

def frame(t, r, zero=False):
    return {'header_ns': t, 'recorder_ns': r, 'zero_payload': zero}

class DiagnosticsTest(unittest.TestCase):
    def test_camera(self):
        x = d.camera_diagnostics([frame(0,0,True), frame(33000000,4000000,False), frame(66000000,80000000,True)])
        self.assertEqual((x['count'],x['zero_payload_count'],x['first_nonzero_ordinal'],x['zero_after_first_nonzero']), (3,2,1,1))
        self.assertEqual(x['recorder_burst_lt_10ms'],1)
        self.assertEqual(x['recorder_gap_ge_50ms'],1)
        self.assertIn('ZERO_IMAGE_PAYLOAD_OBSERVED',x['observation_flags'])
        self.assertNotIn('healthy',str(x).lower())

    def test_empty(self):
        self.assertEqual(d.camera_diagnostics([])['count'],0)
        self.assertEqual(d.numeric_header_join([],[])['numeric_equal_header_count'],0)
        self.assertEqual(d.imu_descriptive_diagnostics([])['angular_speed_norm_rad_s']['count'],0)
        self.assertEqual(d.lidar_structural_diagnostics([])['reported_point_slots'],0)

    def test_header_join_never_sync_claim(self):
        l = [frame(100,1000,True),frame(200,2000)]
        r = [frame(100,51001000,True),frame(300,3100)]
        x=d.numeric_header_join(l,r)
        self.assertEqual((x['numeric_equal_header_count'],x['left_only_header_count'],x['right_only_header_count'],x['both_zero'],x['matched_arrival_delta_abs_gt_20ms']), (1,1,1,1,1))
        self.assertIn('NO_PHYSICAL_SYNCHRONIZATION',x['interpretation'])

    def test_duplicate_header_rejected(self):
        with self.assertRaises(ValueError):
            d.numeric_header_join([frame(1,1),frame(1,2)],[])

    def test_negative_reverse_flag(self):
        x=d.camera_diagnostics([frame(5,5),frame(4,3)])
        self.assertIn('HEADER_NUMERIC_REVERSAL',x['observation_flags'])
        self.assertIn('RECORDER_NUMERIC_REVERSAL',x['observation_flags'])

    def test_strict_camera_schema(self):
        for f in [frame(-1,0),frame(0,-1), {'header_ns':1,'recorder_ns':2,'zero_payload':1}, {'header_ns':1,'recorder_ns':2,'zero_payload':False,'secret':7}]:
            with self.subTest(f=f), self.assertRaises(ValueError): d.camera_diagnostics([f])

    def test_imu_vector(self):
        x=d.imu_descriptive_diagnostics([{'accel_xyz':[0,0,9.7],'gyro_xyz':[0.003,0.004,0]}])
        self.assertAlmostEqual(x['angular_speed_norm_rad_s']['mean'],0.005)
        self.assertAlmostEqual(x['acceleration_norm_m_s2']['mean'],9.7)

    def test_imu_rejects_invalid(self):
        for v in [float('nan'), float('inf'), 1e308, '1']:
            with self.subTest(v=str(v)), self.assertRaises(ValueError):
                d.imu_descriptive_diagnostics([{'accel_xyz':[v,v,v], 'gyro_xyz':[0,0,0]}])

    def test_lidar_structure(self):
        x=d.lidar_structural_diagnostics([{'point_slots':100,'point_step_bytes':26,'field_count':6}, {'point_slots':200,'point_step_bytes':26,'field_count':6}])
        self.assertEqual(x['reported_point_slots'],300)
        self.assertEqual(len(x['layouts']),1)
        self.assertIn('NOT_GEOMETRY',x['interpretation'])

    def test_lidar_invalid(self):
        for p in [-1,2000001,1.5]:
            with self.subTest(p=p), self.assertRaises(ValueError):
                d.lidar_structural_diagnostics([{'point_slots':p,'point_step_bytes':26,'field_count':6}])

    def test_bounded(self):
        with self.assertRaises(ValueError): d.camera_diagnostics([frame(0,0)]*20001)
        with self.assertRaises(ValueError): d.lidar_structural_diagnostics([{'point_slots':2,'point_step_bytes':26,'field_count':33}])

    def test_summary_privacy(self):
        l=d.camera_diagnostics([frame(123456789,234567890,True)])
        r=d.camera_diagnostics([frame(123456789,999999999,True)])
        j=d.numeric_header_join([frame(123456789,234567890,True)],[frame(123456789,999999999,True)])
        i=d.imu_descriptive_diagnostics([{'accel_xyz':[0,0,9.7],'gyro_xyz':[0,0,0]}])
        p=d.lidar_structural_diagnostics([{'point_slots':12,'point_step_bytes':26,'field_count':6}])
        s=d.public_summary_only(l,r,j,i,p)
        self.assertEqual(s['physical_sensor_health_labels_accepted'],0)
        self.assertFalse(s['physical_sync_qualified'])
        self.assertNotIn('123456789',str(s))
        self.assertNotIn('999999999',str(s))
        self.assertEqual(s['lidar_reported_point_slots'],12)

if __name__=='__main__': unittest.main()
