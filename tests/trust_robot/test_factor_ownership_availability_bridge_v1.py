import unittest
from unittest.mock import patch
from trust_robot import factor_ownership_availability_bridge_v1 as a

class OwnershipContractTests(unittest.TestCase):
    def test_complete_32_pattern_space(self):
        patterns = a.all_patterns()
        self.assertEqual(len(patterns), 32)
        self.assertEqual(
            len({tuple(x['missing_frames']) for x in patterns}), 32
        )

    def test_clean_all_seven_frontend_edges(self):
        x = a.model([True] * 9)
        self.assertEqual(x['lidar_factor_count'], 7)
        self.assertEqual(x['required_shadow_holds'], [])

    def test_middle_dropout_is_two_holds(self):
        mask = [True] * 9
        mask[4] = False
        x = a.model(mask)
        self.assertEqual(x['required_shadow_holds'], [2, 3])
        self.assertEqual(x['missing_node_frames'], [4])
        self.assertEqual(x['lidar_factor_count'], 3)

    def test_first_dropout_only_first_hold(self):
        mask = [True] * 9
        mask[0] = False
        self.assertEqual(a.model(mask)['required_shadow_holds'], [1])

    def test_last_dropout_only_last_hold(self):
        mask = [True] * 9
        mask[8] = False
        self.assertEqual(a.model(mask)['required_shadow_holds'], [4])

    def test_two_distant_dropouts(self):
        mask = [True] * 9
        mask[0] = mask[8] = False
        self.assertEqual(a.model(mask)['required_shadow_holds'], [1, 4])

    def test_all_dropout_has_zero_factors(self):
        mask = [True] * 9
        for k in a.FRAMES:
            mask[k] = False
        self.assertEqual(a.model(mask)['lidar_factor_count'], 0)
        self.assertEqual(
            a.model(mask)['required_shadow_holds'], [1, 2, 3, 4]
        )

    def test_skip_edge_survives_middle_dropout(self):
        mask = [True] * 9
        mask[2] = False
        keys = a.model(mask)['lidar_edge_keys']
        self.assertIn([2, 3], keys)
        self.assertNotIn([0, 1], keys)

    def test_non_node_mask_not_claimed(self):
        mask = [True] * 9
        mask[3] = False
        self.assertEqual(a.model(mask), a.model([True] * 9))

    def test_bad_mask_rejected(self):
        for bad in (
            [], [True] * 8, [True] * 10,
            [True] * 8 + [1], 'bad', None
        ):
            with self.subTest(bad=bad), self.assertRaises(a.BridgeViolation):
                a.model(bad)

    def test_wrong_missing_frames_rejected(self):
        for bad in ((1,), (4,4), (4,2.0), [4], ('4',)):
            with self.subTest(bad=bad), self.assertRaises(a.BridgeViolation):
                a.mutate_fixture(bad)

    def test_real_sources_denied_before_solver(self):
        for origin in (
            'NOVA_RECORDED', 'M2DGR', 'NOVA_LIVE',
            None, 7, {}
        ):
            with self.subTest(origin=origin), self.assertRaises(a.BridgeViolation):
                a.run_case((), origin)

    def test_frozen_gate_remains_closed(self):
        a.guard('ANALYTIC_FIXTURE')

    def test_factory_failure_refused(self):
        f = a.mutate_fixture(())
        with patch(
            'trust_robot.analytic_preintegrated_fusion.make_factors',
            return_value=({}, {}, {})
        ):
            with self.assertRaises(a.BridgeViolation):
                a.verify_frontend(f)

    def test_serialization_is_deterministic(self):
        self.assertEqual(
            a.canonical({'z': 3, 'a': 1}),
            a.canonical({'a': 1, 'z': 3})
        )

    def test_noncorrupt_synthetic_baseline(self):
        f = a.mutate_fixture(())
        self.assertEqual(f['available'], [True] * 9)

class PublishedFrontendEndToEndTests(unittest.TestCase):

    def test_middle_dropout_frontend_and_shadow(self):
        case = a.run_case((4,))
        self.assertEqual(
            case['expected']['lidar_factor_count'], 3
        )
        self.assertEqual(
            case['actual_hold_windows'], [2, 3]
        )
        self.assertEqual(
            case['estimator'], 'SOLVED_SYNTHETIC'
        )
        self.assertEqual(
            case['real_factor_admission'], 'DENIED'
        )

    def test_two_distant_missing_scans_frontend(self):
        case = a.run_case((2, 6))
        self.assertEqual(
            case['expected']['lidar_factor_count'], 2
        )
        self.assertEqual(
            case['actual_hold_windows'], [1, 2, 3, 4]
        )
        self.assertEqual(
            case['shadow'], 'HOLD_SYNTHETIC_SHADOW'
        )

    def test_zero_lidar_still_solved_but_shadow_held(self):
        case = a.run_case((0, 2, 4, 6, 8))
        self.assertEqual(
            case['expected']['lidar_factor_count'], 0
        )
        self.assertEqual(
            case['estimator'], 'SOLVED_SYNTHETIC'
        )
        self.assertEqual(
            case['estimator_state_count'], 5
        )
        self.assertEqual(
            case['actual_hold_windows'], [1, 2, 3, 4]
        )
        self.assertEqual(
            case['shadow'], 'HOLD_SYNTHETIC_SHADOW'
        )
        self.assertEqual(
            case['real_factor_admission'], 'DENIED'
        )
