import copy
import pathlib
import sys
import unittest

import r92_gap as g

REPO = pathlib.Path(sys.argv[1])
sys.argv[:] = [sys.argv[0]]

class GapAnalysisTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sources, cls.pins = g.load(REPO)

    def evaluate(self, changes=None):
        d = copy.deepcopy(self.sources)
        if changes:
            changes(d)
        return g.analyze(d, self.pins)

    def reject(self, changes):
        with self.assertRaises(g.EvidenceError):
            self.evaluate(changes)

    def test_positive(self):
        self.assertEqual(
            self.evaluate()['status'],
            'PASS_EXISTING_EVIDENCE_GAP_ANALYSIS_ONLY'
        )

    def test_exact_gate_names(self):
        self.assertEqual(
            set(self.evaluate()['gate_matrix']),
            g.GATE_NAMES
        )

    def test_five_clock_streams(self):
        self.assertEqual(
            set(self.evaluate()['timing_receipt_matrix']),
            g.TIMING_NAMES
        )

    def test_local_gt_distinction(self):
        x = self.evaluate()['reference_recovery']
        self.assertTrue(x['raw_gt_bytes_recovered_locally'])
        self.assertFalse(x['reference_physically_qualified'])

    def test_invalid_rotation_count(self):
        self.assertEqual(
            self.evaluate()['reference_recovery']['invalid_rotation_records'],
            90
        )

    def test_all_actions_cover_gates(self):
        x = self.evaluate()
        self.assertEqual(
            {q for a in x['priority_actions'] for q in a['gate_dependencies']},
            g.GATE_NAMES
        )

    def test_new_r43_claim_denied(self):
        self.reject(lambda d:
            d['r43']['gate_receipts']['real_sensor_factors_authorized']
            .update(physical_qualification_authorized=True))

    def test_missing_r43_gate_denied(self):
        self.reject(lambda d:
            d['r43']['gate_receipts'].pop(
                'camera_intrinsics_physically_verified'
            ))

    def test_new_r53_claim_denied(self):
        self.reject(lambda d:
            d['r53']['receipts']['camera_imu']
            .update(physical_measurement_qualified=True))

    def test_timing_receipt_spoof_denied(self):
        self.reject(lambda d:
            d['r53']['receipts']['velodyne_lidar']['fields']
            .update(source_sha256='fake'))

    def test_false_gt_recovery_denied(self):
        self.reject(lambda d:
            d['r68'].update(dataset_bytes_recovered_and_verified=False))

    def test_false_quality_claim_denied(self):
        self.reject(lambda d:
            d['r68'].update(invalid_rotation_count=0))

    def test_r74_physical_upgrade_denied(self):
        self.reject(lambda d:
            d['r74']['physical_qualification']
            .update(mocap_body_origin_verified=True))

    def test_r76_new_source_upgrade_denied(self):
        self.reject(lambda d:
            d['r76'].update(independent_new_sources_qualified=1))

    def test_r77_factor_gate_change_denied(self):
        self.reject(lambda d:
            d['r77'].update(multimodal_recorded_factor_gate_rejected=False))

    def test_r78_runtime_change_denied(self):
        self.reject(lambda d:
            d['r78'].update(runtime_authorizations=1))

    def test_r91_gate_change_denied(self):
        self.reject(lambda d:
            d['r91_manifest'].update(scientific_gates_closed=10))

    def test_repeat_identical(self):
        a = self.evaluate()
        b = self.evaluate()
        self.assertEqual(g.canonical(a), g.canonical(b))

if __name__ == '__main__':
    unittest.main(verbosity=2)
