import copy
import pathlib
import sys
import unittest
import r93_readiness as m

REPO=pathlib.Path(sys.argv[1])
R92=pathlib.Path(sys.argv[2])
sys.argv[:]=[sys.argv[0]]

class ReadinessTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        r,h,o=m.load_inputs(REPO,R92)
        cls.package=m.build(r,h,o)

    def sample(self):
        expected=self.package['timing_stream_requests']['camera_imu']
        return {
            'schema':m.CANDIDATE,
            'receipt_category':'timing',
            'receipt_id':'camera_imu',
            'trajectory_id':'room_02',
            'split':'train',
            'source_reference':'author-source:synthetic-test-only',
            'source_sha256':'a'*64,
            'evidence_fields':{
                k:None
                for k in expected['required_evidence_fields']
            },
            'independent_validation_sha256':None,
            'source_bytes_verified':False,
            'physical_validation_completed':False,
            'factor_execution_authorized':False,
            'confirmation_test_accessed':False
        }

    def deny(self,modify):
        row=self.sample()
        modify(row)
        with self.assertRaises(m.ReadinessError):
            m.validate_candidate(row,self.package)

    def test_package(self):
        self.assertEqual(
            self.package['status'],
            'DRAFT_READY_FOR_USER_REVIEW_NOT_SENT'
        )

    def test_gate_count(self):
        self.assertEqual(len(self.package['gate_requests']),11)

    def test_timing_count(self):
        self.assertEqual(len(self.package['timing_stream_requests']),5)

    def test_no_request_sent(self):
        self.assertFalse(self.package['request_sent'])

    def test_no_gt_redownload(self):
        self.assertFalse(self.package['raw_gt_re_download_required'])

    def test_no_real_factor_authorization(self):
        self.assertFalse(
            self.package['real_factor_execution_authorized']
        )

    def test_request_language(self):
        s=m.draft(self.package)
        self.assertIn('DRAFT — NOT SENT',s)
        self.assertIn('not requesting another GT download',s)
        self.assertIn('Vicon',s)

    def test_checklist(self):
        s=m.intake_checklist(self.package)
        self.assertIn('handsfree_imu',s)
        self.assertIn('mocap_body_to_lidar_physically_verified',s)

    def test_candidate_format_only(self):
        value=m.validate_candidate(self.sample(),self.package)
        self.assertFalse(value['physical_qualification_established'])

    def test_bad_schema(self):
        self.deny(lambda x:x.update(schema='REAL_APPROVED'))

    def test_unknown_receipt(self):
        self.deny(lambda x:x.update(receipt_id='other'))

    def test_wrong_split(self):
        self.deny(lambda x:x.update(split='confirmation_test'))

    def test_wrong_trajectory(self):
        self.deny(lambda x:x.update(trajectory_id='room_03'))

    def test_source_bytes_claim(self):
        self.deny(lambda x:x.update(source_bytes_verified=True))

    def test_physical_qualification_claim(self):
        self.deny(lambda x:x.update(physical_validation_completed=True))

    def test_real_factor_claim(self):
        self.deny(lambda x:x.update(factor_execution_authorized=True))

    def test_confirmation_claim(self):
        self.deny(lambda x:x.update(confirmation_test_accessed=True))

    def test_fake_independent_receipt(self):
        self.deny(lambda x:x.update(
            independent_validation_sha256='a'*64
        ))

    def test_invalid_source_hash(self):
        self.deny(lambda x:x.update(source_sha256='not-a-hash'))

    def test_missing_evidence_key(self):
        self.deny(lambda x:x['evidence_fields'].pop(
            next(iter(x['evidence_fields']))
        ))

    def test_extra_authorization_field(self):
        self.deny(lambda x:x.update(
            independent_truth_verified=True
        ))

    def test_private_source_reference(self):
        self.deny(lambda x:x.update(
            source_reference='author-source:/mnt/private'
        ))

    def test_repeat_determinism(self):
        self.assertEqual(
            m.canonical(self.package),
            m.canonical(copy.deepcopy(self.package))
        )

if __name__=='__main__':
    unittest.main(verbosity=2)
