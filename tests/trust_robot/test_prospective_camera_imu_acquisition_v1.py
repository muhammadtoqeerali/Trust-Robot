import copy
import unittest

from trust_robot.prospective_camera_imu_acquisition_v1 import (
    SCHEMA, STATUS, ROLE_PROOF, AcquisitionDesignError, build_design,
    validate_design, build_empty_intake_packet,
    validate_empty_intake_packet, build_both_draft_packets, content_sha256,
)

class ProspectiveCameraImuAcquisitionTests(unittest.TestCase):
    def test_camera_draft(self):
        p=build_design('camera'); self.assertEqual(p['modality'],'camera')
        self.assertIn('vision',p['measurement_role'])
    def test_imu_draft(self):
        p=build_design('imu'); self.assertIn('inertial',p['measurement_role'])
    def test_bad_modality(self):
        for val in ('lidar','gnss','',None,True,0,[],{}):
            with self.subTest(val=val),self.assertRaises(AcquisitionDesignError):build_design(val)
    def test_role_names_exact(self):
        self.assertEqual(len(ROLE_PROOF),4)
        self.assertEqual(set(ROLE_PROOF),set(build_design('imu')['generic_independent_artifact_roles']))
    def test_camera_interval_requirement(self):
        p=build_design('camera'); self.assertEqual(len(p['interval_association_requirements']),3)
    def test_imu_interval_requirement(self):
        p=build_design('imu'); self.assertEqual(len(p['interval_association_requirements']),3)
    def test_sensor_specific_instrumentation(self):
        self.assertNotEqual(build_design('camera')['instrumentation_candidates'],build_design('imu')['instrumentation_candidates'])
    def test_camera_no_brightness_label(self):
        self.assertTrue(any('brightness' in x for x in build_design('camera')['cannot_assume']))
    def test_imu_no_magnitude_label(self):
        self.assertTrue(any('magnitude' in x for x in build_design('imu')['cannot_assume']))
    def test_intake_packet_unaccepted(self):
        p=build_empty_intake_packet('camera');self.assertFalse(p['independent_source_accepted'])
        self.assertFalse(p['shape_review']['health_supervision_source_accepted'])
    def test_intake_four_missing(self):
        for mod in ('camera','imu'):
            self.assertEqual(len(build_empty_intake_packet(mod)['shape_review']['evidence_roles_missing']),4)
    def test_intake_packet_canonical(self):
        p=build_empty_intake_packet('imu');self.assertEqual(p,validate_empty_intake_packet(p))
    def test_design_canonical(self):
        for mod in ('camera','imu'):
            p=build_design(mod);self.assertEqual(p,validate_design(p))
    def test_hash_integrity(self):
        p=build_design('camera');self.assertEqual(p['content_sha256'],content_sha256(p))
    def test_packet_hash_integrity(self):
        p=build_empty_intake_packet('camera');self.assertEqual(p['content_sha256'],content_sha256(p))
    def test_both_coverage(self):
        p=build_both_draft_packets();self.assertEqual([x['design']['modality'] for x in p['packets']],['camera','imu'])
    def test_both_readiness(self):
        p=build_both_draft_packets();self.assertEqual(p['real_health_training'],'BLOCKED');self.assertEqual(p['real_health_labels'],0)
    def test_both_lidar_untouched(self):
        self.assertTrue(build_both_draft_packets()['lidar_source_protocol_untouched'])
    def test_both_digest(self):
        p=build_both_draft_packets();self.assertEqual(p['content_sha256'],content_sha256(p))
    def test_no_physical_intervention_auth(self):
        p=build_design('camera');self.assertFalse(p['physical_intervention_authorized'])
    def test_no_validation_confirmation_reference(self):
        p=build_design('imu');self.assertFalse(p['validation_access']);self.assertFalse(p['confirmation_access']);self.assertFalse(p['reference_trajectory_access'])
    def test_tampered_status_rejected(self):
        p=build_design('camera');p['status']='ACCEPTED';p['content_sha256']=content_sha256(p)
        with self.assertRaises(AcquisitionDesignError):validate_design(p)
    def test_tampered_train_rejected(self):
        p=build_design('camera');p['split_role']='confirmation_test';p['content_sha256']=content_sha256(p)
        with self.assertRaises(AcquisitionDesignError):validate_design(p)
    def test_fabricated_label_rejected(self):
        p=build_design('imu');p['real_health_label_count']=1;p['content_sha256']=content_sha256(p)
        with self.assertRaises(AcquisitionDesignError):validate_design(p)
    def test_fabricated_training_rejected(self):
        p=build_design('imu');p['health_model_training_authorized']=True;p['content_sha256']=content_sha256(p)
        with self.assertRaises(AcquisitionDesignError):validate_design(p)
    def test_fabricated_robot_authority_rejected(self):
        p=build_design('camera');p['robot_action_authorized']=True;p['content_sha256']=content_sha256(p)
        with self.assertRaises(AcquisitionDesignError):validate_design(p)
    def test_injected_packet_artifact_rejected(self):
        p=build_empty_intake_packet('camera');p['source_candidate']['independent_artifact_sha256_by_role']['prospective_source_declaration_sha256']='a'*64
        p['content_sha256']=content_sha256(p)
        with self.assertRaises(AcquisitionDesignError):validate_empty_intake_packet(p)
    def test_input_not_mutated(self):
        p=build_design('imu');orig=copy.deepcopy(p);validate_design(p);self.assertEqual(p,orig)
    def test_no_nonfinite_or_extra_fields(self):
        p=build_design('camera');p['fake_threshold']=0.5;p['content_sha256']=content_sha256(p)
        with self.assertRaises(AcquisitionDesignError):validate_design(p)

if __name__=='__main__':unittest.main()
