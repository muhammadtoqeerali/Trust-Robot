import copy
import dataclasses
import inspect
import unittest

import numpy as np

import r99_prior_witness as m
import s6_joint_fusion as s6

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.multimodal_factor_interface import (
    SyntheticPoseFactor,
)

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def sample_events(self):
        return copy.deepcopy(
            self.report['cases']['clean_joint']['events']
        )

    def rejected_chain(self,mutate):
        events=self.sample_events()
        mutate(events)

        with self.assertRaises(m.WitnessError):
            m.verify_chain(events)

    def test_schema(self):
        self.assertEqual(
            self.report['schema'],m.SCHEMA
        )

    def test_pass(self):
        self.assertEqual(
            self.report['status'],
            'PASS_SYNTHETIC_SOFTWARE_ONLY'
        )

    def test_three_cases(self):
        self.assertEqual(
            self.report['nonlinear_solver_scenarios'],3
        )

    def test_twelve_windows(self):
        self.assertEqual(
            self.report['nonlinear_windows'],12
        )

    def test_nine_real_backend_eliminations(self):
        self.assertEqual(
            self.report[
                'actual_marginalizations_independently_checked'
            ],9
        )

    def test_three_eliminations_per_case(self):
        for row in self.report['cases'].values():
            self.assertEqual(
                row['marginalization_events'],3
            )

    def test_prior_chains_pass(self):
        for row in self.report['cases'].values():
            self.assertTrue(
                m.verify_chain(row['events'])
            )

    def test_previous_prior_inherited(self):
        for row in self.report['cases'].values():
            events=row['events']
            for i in (1,2):
                self.assertEqual(
                    events[i]['input_prior_digest'],
                    events[i-1]['output_prior_digest']
                )

    def test_full_schur_information(self):
        for row in self.report['cases'].values():
            for e in row['events']:
                self.assertLess(
                    e['information_relative_error'],1e-6
                )

    def test_full_schur_gradient(self):
        for row in self.report['cases'].values():
            for e in row['events']:
                self.assertLess(
                    e['gradient_relative_error'],1e-6
                )

    def test_reduced_energy(self):
        for row in self.report['cases'].values():
            for e in row['events']:
                self.assertLess(
                    e['energy_difference_error'],1e-5
                )

    def test_no_pose_reuse(self):
        for row in self.report['cases'].values():
            self.assertEqual(row['factor_reuse_count'],0)

    def test_original_solver_unchanged(self):
        for row in self.report['cases'].values():
            self.assertLess(
                row[
                    'instrumented_vs_uninstrumented_state_max_error'
                ],1e-8
            )

    def test_correct_elimination_order(self):
        for row in self.report['cases'].values():
            self.assertEqual(
                [e['eliminated_node'] for e in row['events']],
                [0,1,2]
            )

    def test_camera_off(self):
        self.assertEqual(
            self.report['cases']['clean_camera_off'][
                'same_edge_camera_lidar_count'
            ],0
        )

    def test_camera_lidar_joint(self):
        self.assertEqual(
            self.report['cases']['clean_joint'][
                'same_edge_camera_lidar_count'
            ],2
        )

    def test_no_real_sensor_factors(self):
        self.assertFalse(
            self.report['recorded_source_factors_executed']
        )

    def test_no_gt_scoring(self):
        self.assertFalse(
            self.report['independent_ground_truth_scoring']
        )

    def test_no_health_training(self):
        self.assertFalse(
            self.report['health_training_authorized']
        )

    def test_no_backend_merger_claim(self):
        self.assertFalse(
            self.report[
                'r95_gaussian_backend_merged_into_s6'
            ]
        )

    def test_digest_not_source_authentication(self):
        self.assertFalse(
            self.report[
                'event_digest_is_trusted_source_authentication'
            ]
        )

    def test_bad_case_denied(self):
        with self.assertRaises(m.WitnessError):
            m.run_case('room_02')

    def test_bad_camera_mode_denied(self):
        with self.assertRaises(m.WitnessError):
            m.run_case('clean',camera_enabled='yes')

    def test_bad_seed_denied(self):
        with self.assertRaises(m.WitnessError):
            m.run_case('clean',seed=-1)

    def test_recorded_camera_origin_denied(self):
        _,truth=make_fixture('clean')
        packets=manufactured_camera_packets(
            truth,seed=13
        )

        with self.assertRaises(ValueError):
            dataclasses.replace(
                packets[0],origin='M2DGR'
            )

    def test_no_truth_estimator_api(self):
        self.assertEqual(
            list(
                inspect.signature(
                    s6.estimate_joint
                ).parameters
            ),
            ['fixture','camera_packets']
        )

    def test_challenge_event_digest(self):
        self.rejected_chain(
            lambda e:e[0].update(
                event_digest='invalid'
            )
        )

    def test_challenge_event_payload(self):
        self.rejected_chain(
            lambda e:e[1].update(
                information_relative_error=5.
            )
        )

    def test_challenge_chain_link(self):
        self.rejected_chain(
            lambda e:e[2].update(
                previous_event_digest='stale'
            )
        )

    def test_challenge_reused_imu(self):
        self.rejected_chain(
            lambda e:e[1].update(
                consumed_imu_edges=[[0,1]]
            )
        )

    def test_challenge_false_physical_claim(self):
        self.rejected_chain(
            lambda e:e[0].update(
                physical_clock_verified=True
            )
        )

    def test_rehashed_false_authorization_rejected(self):
        events=self.sample_events()
        events[0][
            'real_sensor_factor_executable'
        ]=True

        body=dict(events[0])
        body.pop('event_digest')
        events[0]['event_digest']=m.digest(body)

        with self.assertRaises(m.WitnessError):
            m.verify_chain(events)

    def test_s6_symbol_restored(self):
        self.assertIs(
            s6.marginalize_one,
            m.original_marginalize
        )

if __name__=='__main__':
    unittest.main(verbosity=2)
