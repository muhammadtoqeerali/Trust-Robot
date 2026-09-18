from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import unittest

from trust_robot.m2dgr_evaluation_protocol import (
    M2DGREvaluationProtocolError,
    evaluation_protocol_content_sha256,
    validate_m2dgr_evaluation_protocol,
)


ROOT = Path(__file__).resolve().parents[2]

PROTOCOL = (
    ROOT
    / "configs"
    / "trust_robot"
    / "m2dgr_trajectory_association_evaluation_protocol_candidate_v1.json"
)


def file_sha256(
    path: Path,
) -> str:
    digest = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


class M2DGREvaluationProtocolTests(
    unittest.TestCase
):
    def load(self):
        return json.loads(
            PROTOCOL.read_text(
                encoding="utf-8"
            )
        )

    def rehash(self, payload):
        payload[
            "content_sha256"
        ] = (
            evaluation_protocol_content_sha256(
                payload
            )
        )

    def test_candidate_validates(self):
        validate_m2dgr_evaluation_protocol(
            self.load()
        )

    def test_scoring_cannot_be_enabled(self):
        payload = deepcopy(
            self.load()
        )

        payload[
            "authorization"
        ][
            "estimator_scoring_authorized"
        ] = True

        self.rehash(
            payload
        )

        with self.assertRaises(
            M2DGREvaluationProtocolError
        ):
            validate_m2dgr_evaluation_protocol(
                payload
            )

    def test_nearest_neighbor_cannot_be_selected(self):
        payload = deepcopy(
            self.load()
        )

        payload[
            "temporal_association"
        ][
            "selected_method"
        ] = "nearest_neighbor"

        self.rehash(
            payload
        )

        with self.assertRaises(
            M2DGREvaluationProtocolError
        ):
            validate_m2dgr_evaluation_protocol(
                payload
            )

    def test_association_tolerance_cannot_be_invented(self):
        payload = deepcopy(
            self.load()
        )

        payload[
            "temporal_association"
        ][
            "association_tolerance_seconds"
        ] = 0.01

        self.rehash(
            payload
        )

        with self.assertRaises(
            M2DGREvaluationProtocolError
        ):
            validate_m2dgr_evaluation_protocol(
                payload
            )

    def test_alignment_cannot_be_selected(self):
        payload = deepcopy(
            self.load()
        )

        payload[
            "frame_alignment"
        ][
            "selected_mode"
        ] = "se3_rigid"

        self.rehash(
            payload
        )

        with self.assertRaises(
            M2DGREvaluationProtocolError
        ):
            validate_m2dgr_evaluation_protocol(
                payload
            )

    def test_source_files_are_bound(self):
        payload = self.load()

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
                file_sha256(
                    path
                ),
                source[
                    "file_sha256"
                ],
            )


if __name__ == "__main__":
    unittest.main()
