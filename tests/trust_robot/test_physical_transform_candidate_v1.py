import copy
import unittest

from trust_robot.physical_transform_candidate_v1 import (
    TransformCandidateError,
    review_transform_candidate,
    admit_physical_transform,
)


def fixture():
    return {
        "source_frame": "camera",
        "target_frame": "base_link",
        "direction_convention": "T_target_source",
        "T_target_source": [
            [1, 0, 0, 1],
            [0, 1, 0, 2],
            [0, 0, 1, 3],
            [0, 0, 0, 1],
        ],
        "covariance_6x6": None,
        "evidence_request_id": "B01",
        "candidate_origin": "NOMINAL_URDF",
        "source_artifact_sha256": None,
        "physical_qualification_claim": False,
    }


class TransformTests(unittest.TestCase):

    def check_bad(self, change):
        candidate = fixture()
        change(candidate)
        with self.assertRaises(TransformCandidateError):
            review_transform_candidate(
                candidate, ["base_link", "camera"]
            )

    def test_01_nominal_candidate(self):
        result = review_transform_candidate(
            fixture(), ["base_link", "camera"]
        )
        self.assertTrue(result["proper_rotation_checked"])
        self.assertFalse(
            result["physical_extrinsics_qualified"]
        )

    def test_02_determinism(self):
        self.assertEqual(
            review_transform_candidate(
                fixture(), ["base_link", "camera"]
            ),
            review_transform_candidate(
                copy.deepcopy(fixture()),
                ["base_link", "camera"],
            ),
        )

    def test_03_unknown_bmi088_not_assumed(self):
        candidate = fixture()
        candidate["source_frame"] = "bmi088_frame"
        result = review_transform_candidate(
            candidate, ["base_link", "camera"]
        )
        self.assertFalse(
            result["source_in_nominal_urdf"]
        )
        self.assertFalse(
            result["physical_frame_equivalence_verified"]
        )

    def test_04_reverse_convention_rejected(self):
        self.check_bad(lambda x: x.update(
            direction_convention="T_source_target"
        ))

    def test_05_reflection_rejected(self):
        self.check_bad(lambda x: x[
            "T_target_source"
        ][0].__setitem__(0, -1))

    def test_06_scaling_rejected(self):
        self.check_bad(lambda x: x[
            "T_target_source"
        ][0].__setitem__(0, 2))

    def test_07_bad_homogeneous_row(self):
        self.check_bad(lambda x: x[
            "T_target_source"
        ][3].__setitem__(0, 1))

    def test_08_nonfinite(self):
        self.check_bad(lambda x: x[
            "T_target_source"
        ][0].__setitem__(3, float("nan")))

    def test_09_boolean_matrix(self):
        self.check_bad(lambda x: x[
            "T_target_source"
        ][0].__setitem__(0, True))

    def test_10_fake_qualification(self):
        self.check_bad(lambda x: x.update(
            physical_qualification_claim=True
        ))

    def test_11_extra_field(self):
        self.check_bad(lambda x: x.update(
            factor_weight=1.0
        ))

    def test_12_bad_request(self):
        self.check_bad(lambda x: x.update(
            evidence_request_id="D02"
        ))

    def test_13_valid_covariance(self):
        x = fixture()
        x["covariance_6x6"] = [
            [1.0 if i == j else 0.0 for j in range(6)]
            for i in range(6)
        ]
        result = review_transform_candidate(
            x, ["base_link", "camera"]
        )
        self.assertTrue(
            result["covariance_structurally_checked"]
        )
        self.assertFalse(
            result["covariance_independently_verified"]
        )

    def test_14_negative_covariance(self):
        self.check_bad(lambda x: x.update(
            covariance_6x6=[
                [-1.0 if i == j == 0 else
                 1.0 if i == j else 0.0
                 for j in range(6)]
                for i in range(6)
            ]
        ))

    def test_15_asymmetric_covariance(self):
        c = [
            [1.0 if i == j else 0.0 for j in range(6)]
            for i in range(6)
        ]
        c[0][1] = 0.5
        self.check_bad(lambda x: x.update(
            covariance_6x6=c
        ))

    def test_16_wrong_sha(self):
        self.check_bad(lambda x: x.update(
            source_artifact_sha256="invalid"
        ))

    def test_17_same_frames(self):
        self.check_bad(lambda x: x.update(
            source_frame="base_link"
        ))

    def test_18_admission_always_denied(self):
        with self.assertRaises(TransformCandidateError):
            admit_physical_transform(fixture())


if __name__ == "__main__":
    unittest.main()
