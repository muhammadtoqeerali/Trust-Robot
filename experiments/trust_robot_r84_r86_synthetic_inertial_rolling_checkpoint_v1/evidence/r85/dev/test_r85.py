import copy
import math
import unittest

import numpy as np

import r84_gap_frontend as gap
import r85_fusion as f

from trust_robot.analytic_imu_preintegration import (
    preintegrate,
)

from trust_robot.analytic_preintegrated_fusion import (
    whitened_inertial_residual,
)


class FusionTests(unittest.TestCase):

    def test_clean_graph(self):
        r = f.build_graph(
            gap.fixture('continuous')
        )

        self.assertEqual(
            (
                r['segment_count'],
                r['safe_factor_count'],
                r['integrated_sample_pairs'],
                r['node_count']
            ),
            (1, 2, 8, 3)
        )

    def test_gap_graph(self):
        r = f.build_graph(
            gap.fixture('single_gap')
        )

        self.assertEqual(
            (
                r['segment_count'],
                r['safe_factor_count'],
                r['rejected_gap_pairs'],
                r['node_count']
            ),
            (2, 2, 1, 4)
        )

        self.assertEqual(
            [e['segment_id'] for e in r['edges']],
            [0, 1]
        )

    def test_no_cross_gap_edge(self):
        r = f.build_graph(
            gap.fixture('single_gap')
        )

        self.assertEqual(
            r['bridging_gap_factors'], 0
        )

        for e in r['edges']:
            self.assertEqual(
                e['from_node'].split(':')[0],
                e['to_node'].split(':')[0]
            )

    def test_full_whitener(self):
        groups, _ = gap.partition(
            gap.fixture('continuous')
        )

        factor = f.make_factor(groups[0][2])

        P = factor['preintegration']['covariance']
        L = factor['whitener']

        self.assertEqual(P.shape, (15, 15))
        self.assertEqual(L.shape, (15, 15))

        np.testing.assert_allclose(
            L@L.T,
            P
            + f.COVARIANCE_FLOOR_STD**2
            * np.eye(15),
            atol=1e-10
        )

    def test_constructed_endpoint_closure(self):
        groups, _ = gap.partition(
            gap.fixture('continuous')
        )

        factor = f.make_factor(groups[0][2])

        residual = whitened_inertial_residual(
            factor['synthetic_start_state'],
            factor['synthetic_consistent_end_state'],
            (
                factor['preintegration'],
                factor['whitener']
            )
        )

        self.assertLess(
            np.linalg.norm(residual),
            1e-6
        )

    def test_endpoint_perturbation_detected(self):
        groups, _ = gap.partition(
            gap.fixture('continuous')
        )

        factor = f.make_factor(groups[0][2])

        changed = (
            factor['synthetic_consistent_end_state']
            .copy()
        )

        changed[0] += 0.05

        residual = whitened_inertial_residual(
            factor['synthetic_start_state'],
            changed,
            (
                factor['preintegration'],
                factor['whitener']
            )
        )

        self.assertGreater(
            np.linalg.norm(residual),
            0.1
        )

    def test_covariance_psd(self):
        for name in (
            'continuous',
            'single_gap'
        ):
            graph = f.build_graph(
                gap.fixture(name)
            )

            for edge in graph['edges']:
                self.assertGreaterEqual(
                    edge['covariance_min_eigenvalue'],
                    -1e-12
                )

                self.assertLess(
                    edge['covariance_reconstruction_max_error'],
                    1e-10
                )

    def test_gyro_intervention(self):
        normal = f.build_graph(
            gap.fixture('continuous')
        )

        changed = f.build_graph(
            gap.fixture('gyro_injection')
        )

        self.assertNotEqual(
            normal['edges'][-1]['covariance_trace'],
            float('nan')
        )

        self.assertNotEqual(
            normal['edges'][-1]['whitened_residual_norm_at_constructed_endpoint'],
            float('nan')
        )

        self.assertEqual(
            changed['safe_factor_count'], 2
        )

    def test_accel_intervention(self):
        normal = f.build_graph(
            gap.fixture('continuous')
        )

        changed = f.build_graph(
            gap.fixture('accel_injection')
        )

        self.assertEqual(
            normal['integrated_sample_pairs'],
            changed['integrated_sample_pairs']
        )

        self.assertNotEqual(
            normal['edges'][-1]['covariance_trace'],
            changed['edges'][-1]['covariance_trace']
        )

    def test_repeat_determinism(self):
        packets = gap.fixture('single_gap')

        self.assertEqual(
            f.build_graph(packets),
            f.build_graph(packets)
        )

    def reject(self, change):
        packets = copy.deepcopy(
            gap.fixture('continuous')
        )

        change(packets)

        with self.assertRaises((
            f.FusionAdmissionError,
            gap.InertialAdmissionError,
            ValueError,
            TypeError,
            KeyError
        )):
            f.build_graph(packets)

    def test_real_imu_denied(self):
        self.reject(
            lambda p: p[0].update(
                source_id='/handsfree/imu'
            )
        )

    def test_train_role_denied(self):
        self.reject(
            lambda p: p[0].update(
                split_role='train'
            )
        )

    def test_physical_clock_denied(self):
        self.reject(
            lambda p: p[0].update(
                physical_clock_verified=True
            )
        )

    def test_gt_denied(self):
        self.reject(
            lambda p: p[0].update(
                reference_data_used=True
            )
        )

    def test_confirmation_denied(self):
        self.reject(
            lambda p: p[0].update(
                confirmation_test_accessed=True
            )
        )

    def test_duplicate_time_denied(self):
        self.reject(
            lambda p: p[1].update(
                timestamp_ns=p[0]['timestamp_ns']
            )
        )

    def test_reversed_time_denied(self):
        self.reject(
            lambda p: p[1].update(
                timestamp_ns=p[0]['timestamp_ns']-1
            )
        )

    def test_malformed_axes_denied(self):
        self.reject(
            lambda p: p[0].update(
                gyro_rad_s=[0.02]
            )
        )

    def test_all_gaps_denied(self):
        self.reject(
            lambda p: [
                row.update(
                    timestamp_ns=1_000_000_000
                    + 1_000_000_000*i
                )
                for i, row in enumerate(p)
            ]
        )

    def test_nonfinite_axes_denied(self):
        self.reject(
            lambda p: p[0].update(
                gyro_rad_s=[
                    float('nan'), 0, 0
                ]
            )
        )

    def test_extra_permission_denied(self):
        self.reject(
            lambda p: p[0].update(
                real_factor_executable=True
            )
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
