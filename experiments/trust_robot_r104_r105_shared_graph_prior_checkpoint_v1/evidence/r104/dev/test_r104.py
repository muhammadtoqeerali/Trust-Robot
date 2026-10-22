import copy
import unittest
import numpy as np
import r104_shared_graph as m
import s6_joint_fusion as s6

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def graph(self):
        return m.build('clean',True,13)

    def deny(self,modify):
        g=self.graph()
        modify(g)
        with self.assertRaises((m.GraphAdmissionError,ValueError,KeyError,TypeError)):
            m.validate(g)

    def test_schema(self): self.assertEqual(self.report['schema'],m.SCHEMA)
    def test_status(self): self.assertEqual(self.report['status'],'PASS_SYNTHETIC_SOFTWARE_ONLY')
    def test_three_scenarios(self): self.assertEqual(self.report['scenario_count'],3)
    def test_5_nodes(self): self.assertEqual(self.report['nodes_per_case'],5)
    def test_node_times(self): self.assertEqual(list(m.NODE_TIME_NS),[0,200000000,400000000,600000000,800000000])
    def test_sample_times(self): self.assertEqual(list(m.SAMPLE_TIME_NS),[i*100000000 for i in range(9)])
    def test_four_imu(self): self.assertEqual(self.report['imu_edges_per_case'],4)
    def test_eight_samples(self): self.assertEqual(self.report['imu_samples_per_case'],8)
    def test_no_imu_sample_reuse(self):
        g=self.graph()
        used=[x for edge in sorted(g['imu_owner']) for x in g['imu_owner'][edge]]
        self.assertEqual(used,list(range(8)))
    def test_twelve_solver_windows(self): self.assertEqual(self.report['total_nonlinear_windows'],12)
    def test_nine_marginalizations(self): self.assertEqual(self.report['total_schur_marginalizations'],9)
    def test_joint_same_edge(self): self.assertEqual(self.report['cases']['clean_joint']['same_edge_camera_lidar'],2)
    def test_camera_off(self): self.assertEqual(self.report['cases']['clean_camera_off']['camera_factors'],0)
    def test_lidar_dropout(self):
        a=self.report['cases']
        self.assertLess(a['lidar_dropout_joint']['lidar_factors'],a['clean_joint']['lidar_factors'])
    def test_unique_camera_lidar_ids(self):
        led=self.report['cases']['clean_joint']['pose_ledger']
        self.assertEqual(len(led),len({x['measurement_id'] for x in led}))
    def test_owner_accounting(self):
        for case in self.report['cases'].values():
            self.assertEqual(case['pose_factors'],case['pose_factors_consumed']+case['pose_factors_remaining'])
    def test_factor_time_order(self):
        for row in self.report['cases'].values():
            self.assertTrue(all(f['start_ns']<f['end_ns'] for f in row['pose_ledger']+row['imu_ledger']))
    def test_truth_not_an_estimator_argument(self):
        for row in self.report['cases'].values(): self.assertFalse(row['truth_passed_to_estimator'])
    def test_real_sensor_denied(self): self.assertFalse(self.report['real_sensor_factors_authorized'])
    def test_no_backend_merger(self): self.assertFalse(self.report['r95_prior_imported_into_s6'])
    def test_physical_clock_denied(self): self.assertFalse(self.report['physical_sensor_synchronization_verified'])
    def test_confirmation_denied(self): self.assertFalse(self.report['confirmation_test_accessed'])
    def test_gates(self): self.assertEqual(self.report['scientific_gates_closed'],11)
    def test_invalid_condition(self):
        with self.assertRaises(m.GraphAdmissionError): m.build('room_02')
    def test_bad_camera_mode(self):
        with self.assertRaises(m.GraphAdmissionError): m.build('clean','yes')
    def test_bad_seed(self):
        with self.assertRaises(m.GraphAdmissionError): m.build('clean',True,-1)
    def test_extra_authorization_field(self): self.deny(lambda x:x.update({'physical_factor_override':True}))
    def test_physical_clock_claim(self): self.deny(lambda x:x.update(physical_clock_verified=True))
    def test_physical_extrinsics_claim(self): self.deny(lambda x:x.update(physical_extrinsics_verified=True))
    def test_recorded_factor_claim(self): self.deny(lambda x:x.update(real_sensor_factors_authorized=True))
    def test_confirmation_claim(self): self.deny(lambda x:x.update(confirmation_test_accessed=True))
    def test_wrong_frame(self): self.deny(lambda x:x.update(frame_id='physical_base'))
    def test_recorded_source(self): self.deny(lambda x:x.update(origin='M2DGR'))
    def test_clock_shift(self): self.deny(lambda x:x.update(node_times_ns=tuple(n+1 for n in m.NODE_TIME_NS)))
    def test_bad_sample_clock(self): self.deny(lambda x:x.update(sample_times_ns=m.SAMPLE_TIME_NS[:-1]))
    def test_sample_reuse(self): self.deny(lambda x:x['imu_owner'].__setitem__((1,2),(0,1)))
    def test_missing_imu_factor(self): self.deny(lambda x:x['imu_factors'].pop((2,3)))
    def test_missing_pose_factor(self): self.deny(lambda x:x.update(pose_factors=x['pose_factors'][:-1]))
    def test_duplicate_pose_factor(self): self.deny(lambda x:x.update(pose_factors=x['pose_factors']+(x['pose_factors'][0],)))
    def test_pose_covariance_altered(self):
        from dataclasses import replace
        self.deny(lambda x:x.update(pose_factors=(replace(x['pose_factors'][0],covariance=s6.diag_cov((0.1,)*6)),)+x['pose_factors'][1:]))
    def test_modified_camera_packet(self):
        from dataclasses import replace
        self.deny(lambda x:x.update(camera_packets=(replace(x['camera_packets'][0],measurement_id='new_id'),)+x['camera_packets'][1:]))
    def test_changed_camera_measurement_denied(self):
        from dataclasses import replace
        from trust_robot.clean_backbone import PoseSE3
        def change(g):
            old=g['camera_packets'][0]
            trans=list(old.measurement.translation_m)
            trans[0]+=0.01
            wrong=PoseSE3(tuple(trans),old.measurement.quaternion_wxyz)
            g['camera_packets']=(replace(old,measurement=wrong),)+g['camera_packets'][1:]
        self.deny(change)
    def test_fixture_mutation(self): self.deny(lambda x:x['fixture']['imu'][0].__setitem__('dt_s',0.15))
    def test_rehashed_physical_packet_denied(self):
        g=self.graph()
        g['fixture']['imu'][0]['physical_clock_verified']=True
        import hashlib
        g['fixture_digest']=hashlib.sha256(m.fixture_bytes(g['fixture'])).hexdigest()
        with self.assertRaises(m.GraphAdmissionError): m.validate(g)
    def test_rehashed_recorded_packet_denied(self):
        g=self.graph()
        g['fixture']['imu'][0]['measurement_origin']='M2DGR'
        import hashlib
        g['fixture_digest']=hashlib.sha256(m.fixture_bytes(g['fixture'])).hexdigest()
        with self.assertRaises(m.GraphAdmissionError): m.validate(g)
    def test_altered_preintegration(self): self.deny(lambda x:x['imu_factors'][(0,1)][0].__setitem__('total_dt',1.0))
    def test_idempotent_validation(self):
        g=self.graph(); self.assertTrue(m.validate(g)); self.assertTrue(m.validate(g))
    def test_repeat_determinism(self): self.assertEqual(m.canonical(self.report),m.canonical(m.execute()))

if __name__=='__main__':
    unittest.main(verbosity=2)
