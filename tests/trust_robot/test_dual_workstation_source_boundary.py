import copy
import json
import unittest
from pathlib import Path

from trust_robot.dual_workstation_source_boundary import (
    SourceBoundaryError,
    review_source_boundary,
    require_physical_factor_authorization,
    require_health_training_authorization,
    canonical,
)


ROOT = Path(__file__).resolve().parents[2]

FILES = (
    "configs/trust_robot/phase5_camera_imu_train_ingestion_candidate_v1.json",
    "manifests/trust_robot_phase5_camera_imu_train_source_evidence_v1.json",
    "manifests/trust_robot_se3_multimodal_feature_pipeline_freeze_v1.json",
    "manifests/trust_robot_se2_health_supervision_protocol_freeze_v1.json",
    "manifests/trust_robot_se4_health_model_training_blocked_frontier_freeze_v1.json",
    "manifests/m2dgr_calibration_evidence_v1.json",
    "experiments/isaacsim_v15/compact_evidence_v15.json",
)


def inputs():
    return [
        json.loads((ROOT / path).read_text())
        for path in FILES
    ]


def review(rows=None):
    return review_source_boundary(
        *(inputs() if rows is None else rows)
    )


class DualWorkstationSourceBoundaryTests(unittest.TestCase):

    def test_published_sources_admitted_as_metadata(self):
        self.assertEqual(
            review()["status"],
            "TWO_SOURCE_PROVENANCE_BOUND",
        )

    def test_real_and_simulation_sources_distinct(self):
        result = review()
        self.assertNotEqual(
            result["real_train_source"]["source_class"],
            result["simulation_source"]["source_class"],
        )

    def test_no_health_label_inference(self):
        result = review()
        self.assertFalse(
            result["authorization"][
                "automatic_health_label_generation"
            ]
        )

    def test_no_metric_physical_fusion(self):
        result = review()
        self.assertFalse(
            result["authorization"][
                "physical_camera_factor_fusion"
            ]
        )

    def test_modified_train_partition_rejected(self):
        rows = inputs()
        rows[0]["train_trajectories"].pop()
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_modified_se3_feature_count_rejected(self):
        rows = inputs()
        rows[2]["empirical_train_validation"][
            "total_feature_records"
        ] = 1
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_broken_train_source_lineage_rejected(self):
        rows = inputs()
        rows[1]["content_sha256"] = "0"*64
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_synthetic_source_relabel_rejected(self):
        rows = inputs()
        rows[6]["data_origin"] = "REAL"
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_modified_simulation_population_rejected(self):
        rows = inputs()
        rows[6]["camera_frames"] = 7
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_unsupported_health_supervision_promotion(self):
        rows = inputs()
        rows[3]["current_empirical_readiness"][
            "real_health_label_count"
        ] = 100
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_unsupported_model_training_promotion(self):
        rows = inputs()
        rows[4]["model_state"][
            "classifier_training_authorized"
        ] = True
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_unsupported_camera_calibration_promotion(self):
        rows = inputs()
        rows[5]["interpretation"][
            "camera_intrinsics_verified"
        ] = True
        with self.assertRaises(SourceBoundaryError):
            review(rows)

    def test_execution_authorization_guards(self):
        result = review()
        with self.assertRaises(SourceBoundaryError):
            require_physical_factor_authorization(result)
        with self.assertRaises(SourceBoundaryError):
            require_health_training_authorization(result)

    def test_deterministic_snapshot(self):
        self.assertEqual(
            canonical(review()),
            canonical(review()),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
