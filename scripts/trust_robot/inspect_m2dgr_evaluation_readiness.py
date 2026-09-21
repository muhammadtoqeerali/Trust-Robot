#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import argparse

from trust_robot.m2dgr_evaluation_plan import (
    build_nonexecut_m2dgr_evaluation_plan,
)
from trust_robot.m2dgr_evaluation_request import (
    EvaluationInspectionRequest,
    inspect_nonexecut_m2dgr_evaluation_request,
    render_evaluation_inspection_report,
)


REFERENCE_FAMILIES = (
    "rtk_ins",
    "leica",
    "mocap",
)

METRICS = (
    "absolute_rotation_trajectory_error",
    "absolute_translation_trajectory_error",
    "relative_rotation_pose_error",
    "relative_translation_pose_error",
)


def repo_root() -> Path:
    return Path(
        __file__
    ).resolve().parents[2]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the fail-closed M2DGR evaluation state. "
            "This tool accepts metadata names only and never loads trajectories."
        )
    )

    parser.add_argument(
        "--reference-family",
        required=True,
        choices=REFERENCE_FAMILIES,
    )

    parser.add_argument(
        "--metric",
        required=True,
        choices=METRICS,
    )

    parser.add_argument(
        "--present-provenance-field",
        action="append",
        default=[],
        help=(
            "Declare that a required provenance FIELD NAME is present. "
            "No provenance value is accepted."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    root = repo_root()

    plan = build_nonexecut_m2dgr_evaluation_plan(
        repo_root=root,

        protocol_path=(
            root
            / "configs/trust_robot/"
              "m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json"
        ),

        boundary_path=(
            root
            / "manifests/"
              "m2dgr_reference_family_protocol_boundary_evidence_v1.json"
        ),

        split_manifest_path=(
            root
            / "manifests/"
              "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
        ),

        split_evidence_path=(
            root
            / "manifests/"
              "m2dgr_split_freeze_evidence_v1.json"
        ),

        evaluator_gate_path=(
            root
            / "src/trust_robot/"
              "m2dgr_evaluator_gate.py"
        ),
    )

    report = inspect_nonexecut_m2dgr_evaluation_request(
        plan.to_payload(),

        EvaluationInspectionRequest(
            reference_family=args.reference_family,
            metric_name=args.metric,
            present_provenance_fields=tuple(
                args.present_provenance_field
            ),
        ),
    )

    print(
        render_evaluation_inspection_report(
            report
        ),
        end="",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
