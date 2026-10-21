import copy
import pathlib
import sys
import unittest

import r80_motion as m

REPO=pathlib.Path(sys.argv[1])
P27=REPO/"experiments/trust_robot_r27_r31_recorded_motion_checkpoint_v1/r27/r27_lidar_diagnostic_registration_v1.json"
P29=REPO/"experiments/trust_robot_r27_r31_recorded_motion_checkpoint_v1/r29/r29_lidar_multipair_diagnostics_v1.json"
P2=REPO/"manifests/trust_robot_phase2_clean_lidar_baseline_freeze_v1.json"

class MotionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r27=m.load(P27)
        cls.r29=m.load(P29)
        cls.p2=m.load(P2)
        cls.pins={
            "r27":m.digest(P27),
            "r29":m.digest(P29),
            "phase2":m.digest(P2)
        }

    def build(self,changed=None):
        src=copy.deepcopy(self.r29)
        if changed:
            changed(src)
        return m.build(
            self.r27,src,self.p2,self.pins
        )

    def test_recorded_eight_pairs(self):
        result=self.build()
        self.assertEqual(len(result["records"]),8)
        self.assertFalse(
            result["real_pose_factors_authorized"]
        )
        self.assertFalse(
            result["continuous_trajectory_reconstructed_from_eight_pairs"]
        )

    def test_inverse_translation_closure(self):
        for row in self.build()["records"]:
            self.assertLess(
                row["motion"][
                    "inverse_translation_closure_error_m"
                ],1e-9
            )

    def test_repeat_determinism(self):
        self.assertEqual(self.build(),self.build())

    def reject(self,change):
        with self.assertRaises(
            (m.MotionError,KeyError,TypeError,ValueError)
        ):
            self.build(change)

    def test_wrong_split(self):
        self.reject(lambda x:x.update(split="confirmation_test"))

    def test_mocap_claim(self):
        self.reject(
            lambda x:x.update(full_extrinsics_verified=True)
        )

    def test_unqualified_factor(self):
        self.reject(
            lambda x:x.update(real_pose_factors_generated=1)
        )

    def test_fake_timestamp_gap(self):
        self.reject(
            lambda x:x["pairs"][0].update(
                observed_header_gap_ns=1
            )
        )

    def test_nonconsecutive_scans(self):
        self.reject(
            lambda x:x["pairs"][0]["scans"][1].update(
                sequence=999999
            )
        )

    def test_reflected_rotation(self):
        self.reject(
            lambda x:x["pairs"][1]["registration"][
                "rotation_previous_from_current"
            ].__setitem__(0,[-1.0,0.0,0.0])
        )

    def test_malformed_matrix(self):
        self.reject(
            lambda x:x["pairs"][1]["registration"].update(
                rotation_previous_from_current=[[1.0]]
            )
        )

    def test_broken_pair_order(self):
        self.reject(
            lambda x:x["pairs"][1].update(pair_index=0)
        )

    def test_claimed_factor_on_registration(self):
        self.reject(
            lambda x:x["pairs"][0]["registration"].update(
                candidate_registered_as_factor=True
            )
        )

    def test_fabricated_implied_continuity(self):
        self.reject(
            lambda x:x["pairs"][1]["scans"][0].update(
                sequence=x["pairs"][0]["scans"][1]["sequence"]+1
            )
        )

if __name__=="__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
