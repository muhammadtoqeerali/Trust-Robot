import copy
import unittest
import numpy as np
import r105_prior_transfer as m
import r104_shared_graph as graph
import s6_joint_fusion as s6
from trust_robot.analytic_schur_marginalization import SquareRootInformationPrior

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()
        cls.g=graph.build('clean',True,13)
        original=s6.marginalize_one
        captured=[]
        def witness(*args,**kwargs):
            prior,diagnostics=original(*args,**kwargs)
            captured.append(prior)
            return prior,diagnostics
        from unittest.mock import patch
        with patch.object(s6,'marginalize_one',side_effect=witness):
            s6.estimate_joint(cls.g['fixture'],cls.g['camera_packets'])
        assert s6.marginalize_one is original and len(captured)==3
        cls.prior=captured[0]

    def transfer(self,**kwargs):
        args={'p':self.prior,'g':self.g,'index':0,
              'pose_ids':m.expected_pose_ids(self.g,0),
              'imu_edges':((0,1),),'delta':m.shift_vector(0)}
        args.update(kwargs)
        return m.transfer(**args)

    def test_schema(self):self.assertEqual(self.report['schema'],m.SCHEMA)
    def test_status(self):self.assertEqual(self.report['status'],'PASS_SYNTHETIC_SOFTWARE_ONLY')
    def test_three_cases(self):self.assertEqual(self.report['scenarios'],3)
    def test_nine_real_transfers(self):self.assertEqual(self.report['real_nonlinear_prior_rebase_transfers'],9)
    def test_twelve_windows(self):self.assertEqual(self.report['nonlinear_windows'],12)
    def test_three_per_case(self):self.assertTrue(all(v['transfers']==3 for v in self.report['cases'].values()))
    def test_prior_residual_exact(self):
        for case in self.report['cases'].values():
            for e in case['events']:self.assertLess(e['max_residual_absolute_error'],1e-8)
    def test_gradient_transform(self):
        for case in self.report['cases'].values():
            for e in case['events']:self.assertLess(e['gradient_transform_relative_error'],1e-9)
    def test_information_preserved(self):
        for case in self.report['cases'].values():
            for e in case['events']:self.assertLess(e['information_relative_error'],1e-11)
    def test_actual_solver_unchanged(self):
        for case in self.report['cases'].values():
            self.assertLess(case['instrumented_vs_original_state_max_abs_error'],2e-5)
    def test_transfer_type(self):self.assertIsInstance(self.transfer()[0],SquareRootInformationPrior)
    def test_new_reference(self):
        new,_=self.transfer()
        np.testing.assert_allclose(new.reference,self.prior.reference+m.shift_vector(0))
    def test_no_mutation_of_original(self):
        old_ref=self.prior.reference.copy();old_offset=self.prior.residual_offset.copy()
        self.transfer()
        np.testing.assert_array_equal(self.prior.reference,old_ref)
        np.testing.assert_array_equal(self.prior.residual_offset,old_offset)
    def test_wrong_prior_index(self):
        with self.assertRaises(m.TransferError):self.transfer(index=1)
    def test_wrong_graph_frame(self):
        g=copy.copy(self.g);g['frame_id']='real_base_link'
        with self.assertRaises(m.TransferError):self.transfer(g=g)
    def test_real_factor_claim(self):
        g=copy.copy(self.g);g['real_sensor_factors_authorized']=True
        with self.assertRaises(m.TransferError):self.transfer(g=g)
    def test_wrong_camera_identity(self):
        with self.assertRaises(m.TransferError):self.transfer(pose_ids=('forged_id',))
    def test_pose_duplicate(self):
        ids=m.expected_pose_ids(self.g,0)
        with self.assertRaises(m.TransferError):self.transfer(pose_ids=ids+ids)
    def test_imu_edge_reuse(self):
        with self.assertRaises(m.TransferError):self.transfer(imu_edges=((1,2),))
    def test_missing_imu(self):
        with self.assertRaises(m.TransferError):self.transfer(imu_edges=())
    def test_out_of_budget_shift(self):
        with self.assertRaises(m.TransferError):self.transfer(delta=np.ones(30))
    def test_nonfinite_shift(self):
        v=m.shift_vector(0);v[0]=float('nan')
        with self.assertRaises(m.TransferError):self.transfer(delta=v)
    def test_wrong_shift_dimension(self):
        with self.assertRaises(m.TransferError):self.transfer(delta=np.zeros(15))
    def test_bad_shift_container(self):
        with self.assertRaises(m.TransferError):self.transfer(delta=[0.]*30)
    def test_inconsistent_node_ownership(self):
        p=SquareRootInformationPrior((2,3),self.prior.reference.copy(),
            self.prior.square_root_information.copy(),self.prior.residual_offset.copy())
        with self.assertRaises(m.TransferError):self.transfer(p=p)
    def test_no_r95_import(self):self.assertFalse(self.report['r95_gaussian_backend_imported'])
    def test_no_relinearization(self):self.assertFalse(self.report['new_nonlinear_factor_jacobian_refresh_performed'])
    def test_no_real_sensor(self):self.assertFalse(self.report['real_sensor_factors_authorized'])
    def test_no_health(self):self.assertFalse(self.report['health_training_authorized'])
    def test_no_ate(self):self.assertFalse(self.report['ate_rpe_authorized'])
    def test_confirmation_sealed(self):self.assertFalse(self.report['confirmation_test_accessed'])
    def test_all_gates_closed(self):self.assertEqual(self.report['scientific_gates_closed'],11)
    def test_determinism(self):self.assertEqual(m.canonical(self.report),m.canonical(m.execute()))

if __name__=='__main__':unittest.main(verbosity=2)
