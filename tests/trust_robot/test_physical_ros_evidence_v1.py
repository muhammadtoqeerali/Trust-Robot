"""Synthetic, standard-library-only checks; never imports physical data."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from trust_robot.physical_ros_evidence_v1 import (
    EvidenceValidationError, review_evidence,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PhysicalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.samples = {}
        for key in ('imu', 'left', 'right', 'left_info', 'right_info', 'lidar'):
            self.samples[key] = [[1000000000, 2000000000, 3000000000],
                                 [1100000000, 2100000000, 3100000000]]
        self.samples['correlation'] = [{
            'arrival_monotonic_ns': 2000000000,
            'fields': {k: '1234' for k in
                       ('phc_val', 'phc2_val', 'sys_val', 'tsc_val', 'phc_latency')}
        }]
        summaries = {
            k: {'count': 2, 'recorded': 2, 'header_nonincreasing': 0,
                'first_header_ns': 1000000000, 'last_header_ns': 1100000000,
                'header_p50_ms': 100.0}
            for k in self.samples if k != 'correlation'
        }
        summaries['correlation'] = {'count': 1}
        self.metadata = {
            'phase': 'R135-A25E-3',
            'qualification': 'Diagnostic only; no real factors admitted; 11 M2DGR gates closed',
            'shutdown': {'launch_group_gone': True, 'ros_graph_clear': True,
                         'remaining_driver_processes': []},
            'correlation_node_names': [['correlated_timestamp_driver', '/']],
            'image_exact_header_pairs': 2,
            'image_distinct_left_stamps': 2,
            'image_distinct_right_stamps': 2,
            'samples': self.samples, 'summaries': summaries,
        }
        (self.root / 'launch.log').write_text('synthetic log')
        (self.root / 'three_sensors.launch.py').write_text('synthetic source')
        self.refresh()

    def refresh(self):
        self.metadata['launch_file_sha256'] = digest(
            self.root / 'three_sensors.launch.py')
        (self.root / 'metadata.json').write_text(json.dumps(self.metadata))
        self.meta_hash = digest(self.root / 'metadata.json')
        files = {
            name: {'sha256': digest(self.root / name),
                   'bytes': (self.root / name).stat().st_size}
            for name in ('metadata.json', 'launch.log', 'three_sensors.launch.py')
        }
        self.manifest = {
            'phase': 'R135-A25F-1R', 'source_phase': 'R135-A25E-3',
            'original_metadata_sha256': self.meta_hash,
            'original_launch_log_sha256': digest(self.root / 'launch.log'),
            'real_factor_admission': 'DENIED', 'm2dgr_gates': '11_CLOSED',
            'raw_images_saved': False, 'raw_pointclouds_saved': False,
            'verified_files': files,
        }
        (self.root / 'TRANSFER_MANIFEST.json').write_text(json.dumps(self.manifest))
        self.manifest_hash = digest(self.root / 'TRANSFER_MANIFEST.json')

    def review(self):
        return review_evidence(self.root, self.meta_hash, self.manifest_hash)

    def test_valid_synthetic_evidence_never_admitted(self):
        result = self.review()
        self.assertEqual(result['real_factor_admission'], 'DENIED')
        self.assertEqual(result['m2dgr_gates'], '11_CLOSED')
        self.assertEqual(result['exact_stereo_timestamp_pairs'], 2)
        self.assertEqual(result['physical_clock_accuracy'], 'UNVERIFIED')

    def test_metadata_mutation_rejected(self):
        (self.root / 'metadata.json').write_text('{}')
        with self.assertRaises(EvidenceValidationError):
            self.review()

    def test_manifest_mutation_rejected(self):
        (self.root / 'TRANSFER_MANIFEST.json').write_text('{}')
        with self.assertRaises(EvidenceValidationError):
            self.review()

    def test_nonmonotonic_header_rejected_even_after_rehash(self):
        self.samples['imu'][1][0] = 999999999
        self.refresh()
        with self.assertRaises(EvidenceValidationError):
            self.review()

    def test_fabricated_stereo_count_rejected_even_after_rehash(self):
        self.metadata['image_exact_header_pairs'] = 5
        self.refresh()
        with self.assertRaises(EvidenceValidationError):
            self.review()

    def test_admission_claim_rejected_even_after_rehash(self):
        self.refresh()
        self.manifest['real_factor_admission'] = 'ADMITTED'
        (self.root / 'TRANSFER_MANIFEST.json').write_text(json.dumps(self.manifest))
        self.manifest_hash = digest(self.root / 'TRANSFER_MANIFEST.json')
        with self.assertRaises(EvidenceValidationError):
            self.review()

    def test_extra_untracked_file_rejected(self):
        (self.root / 'untracked.txt').write_text('unexpected')
        with self.assertRaises(EvidenceValidationError):
            self.review()

    def test_symlink_rejected(self):
        (self.root / 'link').symlink_to(self.root / 'metadata.json')
        with self.assertRaises(EvidenceValidationError):
            self.review()

    def test_modified_log_rejected(self):
        (self.root / 'launch.log').write_text('mutated log')
        with self.assertRaises(EvidenceValidationError):
            self.review()


if __name__ == '__main__':
    unittest.main()
