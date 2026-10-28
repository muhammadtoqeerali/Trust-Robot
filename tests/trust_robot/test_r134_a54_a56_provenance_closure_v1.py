"""R134-A54-A56 provenance closure transcription checks.

These tests verify reported aggregate values and retain
scientific denies. They do not authenticate or reproduce
the original UNIVER observations.
"""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REPORT = ROOT / (
    'experiments/'
    'trust_robot_r134_a54_a56_provenance_closure_v1/'
    'aggregate_v1.json'
)

PINS = {
    'src/trust_robot/camera_imu_shadow_rotation_v1.py':
        '048abce9b63a13176dab1ccb36208195c40baaee4ba61f91eb793bccd9a04462',
    'experiments/trust_robot_r134_a44_real_shadow_checkpoint_v1/aggregate_report_v1.json':
        'cf612c945a3890e2f8313a7c22a001e0ff71c50f406dd6c146a2e2f27fdfadc6',
    'experiments/trust_robot_r134_a48_source_consistency_v1/aggregate_v1.json':
        '7e15631cc25f0171270264fd11b0f27ff8ea58f71110607ae6d08f4622a36bd4',
    'experiments/trust_robot_r134_a51_frame_clock_v1/aggregate_v1.json':
        '04f11ad6652349ffad7feb168ff6919afcbc816c0608affd66a64e5e5559dd31'
}

MANIFEST_SHA = {
    'HILTI_OXFORD_2022/r128_b8_evidence/manifest_v1.json':
        'dd0d117694608036fb895f651e80e579f6dba127eb7957c2244e7c968d5ae5c2',
    'HILTI_OXFORD_2022_RUNTIME_R128_B10/manifest_v1.json':
        '46937f40df9da2467375072a835a4d7105f2fbb5c189355fda7c68a83678ac66',
    'HILTI_OXFORD_2022_RUNTIME_R128_B7/manifest_v1.json':
        '63019a62f6354ffe4eec684f23ab2ef9b9a084e22d7c260ef636cca68c9eda8e',
    'HILTI_OXFORD_2022_RUNTIME_R128_B9/manifest_v1.json':
        '616c4df272aadd7f514a2fd760d5472259c7c7ec574494dfefa1ed6f249138e4',
    'HILTI_OXFORD_2022_RUNTIME_R129_B1/r129_b1_manifest_v1.json':
        '1aa2789b33b99f94bfd5f7d494c33f27db2ccf00d9578ae39e6e61220d53ac5d',
    'HILTI_OXFORD_2022_RUNTIME_R130_B1/manifest_v1.json':
        'ffd88df49b95f4f0caf44a472236761085d74802e680b759c2546a54ad4daed3'
}

class ProvenanceClosureTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REPORT.read_text())

    def test_identity_and_evidence_quality(self):
        d = self.data
        self.assertEqual(
            d['schema'],
            'TRUST_ROBOT_R134_A54_A56_PROVENANCE_CLOSURE_V1'
        )
        self.assertEqual(
            d['status'],
            'LOCAL_PROVENANCE_INVESTIGATION_BLOCKED'
        )
        self.assertEqual(
            d['evidence_role'],
            'UNTRUSTED_AGGREGATE_METADATA_ONLY'
        )
        self.assertEqual(len(d['source_logs']),3)
        self.assertIs(
            d['source_logs_cryptographically_attested'],
            False
        )

    def test_a54_bag_metadata(self):
        a = self.data['a54_bag_metadata']

        self.assertEqual(a['topics'],8)
        self.assertEqual(a['connections'],8)
        self.assertEqual(a['duration_seconds'],74.013)
        self.assertEqual(
            a['configuration_diagnostic_topic_candidates'],0
        )
        self.assertEqual(
            a['alphasense_connections_without_callerid'],6
        )
        self.assertEqual(a['ros_messages_deserialized'],0)
        self.assertEqual(a['ground_truth_messages_read'],0)

        for key in (
            'camera_publisher_id_recorded',
            'imu_publisher_id_recorded',
            'original_driver_settings_found',
            'original_ptp_lock_evidence_found'
        ):
            self.assertIs(a[key],False)

    def test_a55_scoped_inventory(self):
        a = self.data['a55_scoped_file_inventory']

        self.assertEqual(len(a['search_roots']),6)
        self.assertEqual(a['directories_visited'],9)
        self.assertEqual(a['entries_inspected'],33)
        self.assertEqual(a['candidate_files'],14)
        self.assertEqual(a['search_depth_limit'],3)
        self.assertEqual(
            a['scope_coverage'],'SCOPED_DEPTH_COMPLETE'
        )
        self.assertIs(a['candidate_contents_read'],False)
        self.assertIs(
            a['original_capture_configuration_identified'],
            False
        )
        self.assertIs(
            a['global_filesystem_absence_proven'],False
        )

    def test_a56_manifest_provenance(self):
        a = self.data['a56_prior_project_manifests']

        self.assertEqual(a['files'],MANIFEST_SHA)
        self.assertEqual(a['manifests_checked'],6)
        self.assertEqual(
            a['relevant_metadata_key_occurrences'],29
        )
        self.assertEqual(
            a['whitelisted_value_occurrences'],0
        )
        self.assertEqual(
            a['r130_manifest_relevant_key_count'],22
        )
        self.assertEqual(a['original_driver_logs_inspected'],0)
        self.assertEqual(a['original_ptp_logs_inspected'],0)
        self.assertIs(
            a['primary_hardware_attestation_obtained'],
            False
        )

    def test_scientific_gates_and_existing_evidence(self):
        s = self.data['scientific_decision']

        self.assertEqual(
            s['local_recording_provenance_workstream'],
            'STOP_UNTIL_PRIMARY_EVIDENCE'
        )
        self.assertEqual(
            s['m2dgr_scientific_gates_closed'],11
        )
        self.assertEqual(
            s['next_workstream'],
            'SYNTHETIC_ESTIMATOR_AND_SENSOR_HEALTH_ENGINEERING'
        )

        for key in (
            'failure_or_sensor_fault_inferred',
            'calibration_changed',
            'clock_offset_fitted',
            'ground_truth_accessed',
            'metric_pose_estimated',
            'real_factor_admission_authorized',
            'health_label_authorized',
            'm2dgr_confirmation_test_accessed'
        ):
            self.assertIs(s[key],False)

        for path,expected in PINS.items():
            self.assertEqual(
                hashlib.sha256(
                    (ROOT/path).read_bytes()
                ).hexdigest(),
                expected
            )

if __name__ == '__main__':
    unittest.main(verbosity=2)
