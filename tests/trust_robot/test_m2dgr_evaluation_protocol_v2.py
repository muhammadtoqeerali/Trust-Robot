from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import unittest

from trust_robot.m2dgr_evaluation_protocol_v2 import (
    M2DGREvaluationProtocolV2Error,
    evaluation_protocol_v2_content_sha256,
    validate_m2dgr_evaluation_protocol_v2,
)


ROOT = Path(__file__).resolve().parents[2]

PROTOCOL = (
    ROOT
    / "configs"
    / "trust_robot"
    / "m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json"
)


def load():
    return json.loads(
        PROTOCOL.read_text(
            encoding="utf-8"
        )
    )


def rehash(payload):
    payload[
        "content_sha256"
    ] = (
        evaluation_protocol_v2_content_sha256(
            payload
        )
    )


class M2DGREvaluationProtocolV2Tests(
    unittest.TestCase
):
    def test_candidate_validates(self):
        validate_m2dgr_evaluation_protocol_v2(
            load()
        )

    def test_frozen_split_is_recognized(self):
        payload = load()

        self.assertEqual(
            payload[
                "observed_dataset_state"
            ][
                "split_counts"
            ],
            {
                "train": 22,
                "validation_calibration": 7,
                "confirmation_test": 7,
            },
        )

    def test_validation_partition_does_not_authorize_association(self):
        payload = deepcopy(
            load()
        )

        payload[
            "temporal_association"
        ][
            "selection_authorized_now"
        ] = True

        rehash(payload)

        with self.assertRaises(
            M2DGREvaluationProtocolV2Error
        ):
            validate_m2dgr_evaluation_protocol_v2(
                payload
            )

    def test_confirmation_cannot_select_association(self):
        payload = deepcopy(
            load()
        )

        payload[
            "temporal_association"
        ][
            "confirmation_test_may_select_association_parameters"
        ] = True

        rehash(payload)

        with self.assertRaises(
            M2DGREvaluationProtocolV2Error
        ):
            validate_m2dgr_evaluation_protocol_v2(
                payload
            )

    def test_association_tolerance_stays_null(self):
        payload = deepcopy(
            load()
        )

        payload[
            "temporal_association"
        ][
            "association_tolerance_seconds"
        ] = 0.01

        rehash(payload)

        with self.assertRaises(
            M2DGREvaluationProtocolV2Error
        ):
            validate_m2dgr_evaluation_protocol_v2(
                payload
            )

    def test_alignment_stays_unselected(self):
        payload = deepcopy(
            load()
        )

        payload[
            "frame_alignment"
        ][
            "selected_mode"
        ] = "se3_rigid"

        rehash(payload)

        with self.assertRaises(
            M2DGREvaluationProtocolV2Error
        ):
            validate_m2dgr_evaluation_protocol_v2(
                payload
            )

    def test_split_does_not_enable_scoring(self):
        payload = deepcopy(
            load()
        )

        payload[
            "authorization"
        ][
            "estimator_scoring_authorized"
        ] = True

        rehash(payload)

        with self.assertRaises(
            M2DGREvaluationProtocolV2Error
        ):
            validate_m2dgr_evaluation_protocol_v2(
                payload
            )

    def test_bound_source_files_match_sha256(self):
        payload = load()

        for source in payload[
            "source_artifacts"
        ].values():
            path = (
                ROOT
                / source[
                    "relative_path"
                ]
            )

            self.assertTrue(
                path.is_file()
            )

            self.assertEqual(
                sha256(
                    path.read_bytes()
                ).hexdigest(),
                source[
                    "file_sha256"
                ],
            )


if __name__ == "__main__":
    unittest.main()
