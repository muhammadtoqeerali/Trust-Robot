from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping
import json

from .diagnostics import (
    extract_lidar_registration_diagnostics,
)
from .lidar_frontend import (
    LidarRegistrationDiagnostics,
)


PAIRED_DIAGNOSTIC_SCHEMA = (
    "TRUST_ROBOT_PHASE4_LIDAR_PAIRED_DIAGNOSTIC_ARTIFACT_V1"
)

EXPECTED_PHASE3_RECEIPT_SCHEMA = (
    "TRUST_ROBOT_PHASE3_LIDAR_PAIRED_ESTIMATOR_REGISTRATION_RECEIPT_V1"
)

EXPECTED_PHASE3_EXECUTION_SCHEMA = (
    "TRUST_ROBOT_PHASE3_PAIRED_FROZEN_LIDAR_REGISTRATION_V1"
)

EXPECTED_PHASE3_PATH_SCHEMA = (
    "TRUST_ROBOT_PHASE3_FROZEN_LIDAR_REGISTRATION_PATH_V1"
)

EXPECTED_DIAGNOSTIC_INTERPRETATION = (
    "execution_diagnostic_only_not_accuracy_score"
)

DIAGNOSTIC_FIELDS = (
    "source_point_count",
    "target_point_count",
    "fixed_point_iterations",
    "final_correspondence_count",
    "final_nearest_neighbor_rmse_m",
    "convergence_rule",
    "correspondence_rejection_used",
    "voxel_downsampling_used",
)


class PairedDiagnosticArtifactError(ValueError):
    """Raised when frozen paired diagnostic provenance is inconsistent."""


def _canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _content_sha256(
    payload: Mapping[str, Any],
) -> str:
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _mapping_sha256(
    payload: Mapping[str, Any],
) -> str:
    return sha256(
        _canonical_json(
            dict(
                payload
            )
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _exact_int(
    value,
    *,
    name,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise PairedDiagnosticArtifactError(
            f"{name} must be an exact integer"
        )

    return value


def _validate_phase3_receipt(
    receipt: Mapping[str, Any],
) -> None:
    if receipt.get(
        "schema"
    ) != EXPECTED_PHASE3_RECEIPT_SCHEMA:
        raise PairedDiagnosticArtifactError(
            "unexpected Phase-3 paired receipt schema"
        )

    if receipt.get(
        "status"
    ) != "completed":
        raise PairedDiagnosticArtifactError(
            "Phase-3 paired receipt is not completed"
        )

    stored = receipt.get(
        "content_sha256"
    )

    if (
        not isinstance(
            stored,
            str,
        )
        or stored
        != _content_sha256(
            receipt
        )
    ):
        raise PairedDiagnosticArtifactError(
            "Phase-3 paired receipt content digest mismatch"
        )

    scope = receipt.get(
        "scientific_scope"
    )

    if not isinstance(
        scope,
        Mapping,
    ):
        raise PairedDiagnosticArtifactError(
            "Phase-3 paired receipt scientific_scope missing"
        )

    forbidden_true = (
        "reference_data_used",
        "confirmation_test_data_used",
        "ground_truth_association_performed",
        "alignment_performed",
        "ate_computed",
        "rpe_computed",
        "trajectory_scoring_performed",
        "estimator_scoring_performed",
        "accuracy_comparison_performed",
        "severity_selection_performed",
        "phase3_exit_evidence_satisfied",
    )

    for key in forbidden_true:
        if scope.get(
            key
        ) is not False:
            raise PairedDiagnosticArtifactError(
                f"forbidden Phase-3 scope value: {key}"
            )

    interpretation = receipt.get(
        "interpretation"
    )

    if not isinstance(
        interpretation,
        Mapping,
    ):
        raise PairedDiagnosticArtifactError(
            "Phase-3 paired receipt interpretation missing"
        )

    if interpretation.get(
        "localization_accuracy_comparison"
    ) is not False:
        raise PairedDiagnosticArtifactError(
            "source receipt performed localization accuracy comparison"
        )

    if interpretation.get(
        "clean_corrupt_error_metric"
    ) is not None:
        raise PairedDiagnosticArtifactError(
            "source receipt contains clean/corrupt error metric"
        )


def _extract_registration_record(
    *,
    branch: str,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    if branch not in {
        "clean",
        "corrupt",
    }:
        raise PairedDiagnosticArtifactError(
            "branch must be clean or corrupt"
        )

    pair_index = _exact_int(
        record.get(
            "pair_index"
        ),
        name="pair_index",
    )

    previous_origin = _exact_int(
        record.get(
            "previous_clean_origin_index"
        ),
        name="previous_clean_origin_index",
    )

    current_origin = _exact_int(
        record.get(
            "current_clean_origin_index"
        ),
        name="current_clean_origin_index",
    )

    previous_timestamp = _exact_int(
        record.get(
            "previous_timestamp_ns"
        ),
        name="previous_timestamp_ns",
    )

    current_timestamp = _exact_int(
        record.get(
            "current_timestamp_ns"
        ),
        name="current_timestamp_ns",
    )

    if previous_origin >= current_origin:
        raise PairedDiagnosticArtifactError(
            "clean-origin registration pair must be strictly increasing"
        )

    if previous_timestamp >= current_timestamp:
        raise PairedDiagnosticArtifactError(
            "registration timestamps must be strictly increasing"
        )

    source_diagnostics = record.get(
        "diagnostics"
    )

    if not isinstance(
        source_diagnostics,
        Mapping,
    ):
        raise PairedDiagnosticArtifactError(
            "registration diagnostic mapping missing"
        )

    if source_diagnostics.get(
        "interpretation"
    ) != EXPECTED_DIAGNOSTIC_INTERPRETATION:
        raise PairedDiagnosticArtifactError(
            "registration diagnostic interpretation is not nonscoring"
        )

    missing = [
        key
        for key
        in DIAGNOSTIC_FIELDS
        if key not in source_diagnostics
    ]

    if missing:
        raise PairedDiagnosticArtifactError(
            "registration diagnostic fields missing: "
            + ", ".join(
                missing
            )
        )

    diagnostic_payload = {
        key:
            source_diagnostics[
                key
            ]
        for key
        in DIAGNOSTIC_FIELDS
    }

    diagnostics = LidarRegistrationDiagnostics(
        **diagnostic_payload
    )

    feature_record = extract_lidar_registration_diagnostics(
        diagnostics
    )

    return {
        "branch":
            branch,

        "pair_index":
            pair_index,

        "previous_clean_origin_index":
            previous_origin,

        "current_clean_origin_index":
            current_origin,

        "previous_timestamp_ns":
            previous_timestamp,

        "current_timestamp_ns":
            current_timestamp,

        "source_diagnostic_content_sha256":
            _mapping_sha256(
                diagnostic_payload
            ),

        "feature_record_fingerprint_sha256":
            feature_record.fingerprint_sha256,

        "feature_record":
            feature_record.to_dict(),
    }


def build_phase3_paired_diagnostic_artifact(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_phase3_receipt(
        receipt
    )

    corruption = receipt.get(
        "corruption"
    )

    if not isinstance(
        corruption,
        Mapping,
    ):
        raise PairedDiagnosticArtifactError(
            "Phase-3 corruption mapping missing"
        )

    if corruption.get(
        "family"
    ) != "EVENT_GAP":
        raise PairedDiagnosticArtifactError(
            "expected frozen EVENT_GAP paired receipt"
        )

    spec_id = corruption.get(
        "spec_id"
    )

    injection_id = corruption.get(
        "injection_id"
    )

    if not isinstance(
        spec_id,
        str,
    ) or not spec_id:
        raise PairedDiagnosticArtifactError(
            "missing corruption spec_id"
        )

    if not isinstance(
        injection_id,
        str,
    ) or not injection_id:
        raise PairedDiagnosticArtifactError(
            "missing corruption injection_id"
        )

    execution = receipt.get(
        "registration_execution"
    )

    if not isinstance(
        execution,
        Mapping,
    ):
        raise PairedDiagnosticArtifactError(
            "registration_execution missing"
        )

    if execution.get(
        "schema"
    ) != EXPECTED_PHASE3_EXECUTION_SCHEMA:
        raise PairedDiagnosticArtifactError(
            "unexpected Phase-3 execution schema"
        )

    if execution.get(
        "corruption_spec_ids"
    ) != [
        spec_id
    ]:
        raise PairedDiagnosticArtifactError(
            "execution corruption spec linkage mismatch"
        )

    if execution.get(
        "corruption_injection_ids"
    ) != [
        injection_id
    ]:
        raise PairedDiagnosticArtifactError(
            "execution corruption injection linkage mismatch"
        )

    topology = execution.get(
        "path_topology"
    )

    if not isinstance(
        topology,
        Mapping,
    ):
        raise PairedDiagnosticArtifactError(
            "registration path_topology missing"
        )

    branch_payloads = {}

    for branch in (
        "clean",
        "corrupt",
    ):
        source_path = execution.get(
            branch
        )

        if not isinstance(
            source_path,
            Mapping,
        ):
            raise PairedDiagnosticArtifactError(
                f"{branch} registration path missing"
            )

        if source_path.get(
            "schema"
        ) != EXPECTED_PHASE3_PATH_SCHEMA:
            raise PairedDiagnosticArtifactError(
                f"unexpected {branch} registration path schema"
            )

        records = source_path.get(
            "records"
        )

        if not isinstance(
            records,
            list,
        ):
            raise PairedDiagnosticArtifactError(
                f"{branch} registration records missing"
            )

        extracted = [
            _extract_registration_record(
                branch=branch,
                record=record,
            )
            for record
            in records
        ]

        if source_path.get(
            "increment_count"
        ) != len(
            extracted
        ):
            raise PairedDiagnosticArtifactError(
                f"{branch} increment_count mismatch"
            )

        derived_origin_pairs = [
            [
                record[
                    "previous_clean_origin_index"
                ],
                record[
                    "current_clean_origin_index"
                ],
            ]
            for record
            in extracted
        ]

        if source_path.get(
            "origin_pairs"
        ) != derived_origin_pairs:
            raise PairedDiagnosticArtifactError(
                f"{branch} source origin-pair mismatch"
            )

        topology_key = (
            f"{branch}_origin_pairs"
        )

        if topology.get(
            topology_key
        ) != derived_origin_pairs:
            raise PairedDiagnosticArtifactError(
                f"{branch} topology linkage mismatch"
            )

        branch_payloads[
            branch
        ] = {
            "registration_count":
                len(
                    extracted
                ),

            "origin_pairs":
                derived_origin_pairs,

            "feature_record_fingerprints_sha256": [
                record[
                    "feature_record_fingerprint_sha256"
                ]
                for record
                in extracted
            ],

            "records":
                extracted,
        }

    payload: dict[str, Any] = {
        "schema":
            PAIRED_DIAGNOSTIC_SCHEMA,

        "source": {
            "phase3_receipt_content_sha256":
                receipt[
                    "content_sha256"
                ],

            "dataset_id":
                receipt[
                    "source"
                ][
                    "dataset_id"
                ],

            "split":
                receipt[
                    "source"
                ][
                    "split"
                ],

            "trajectory":
                receipt[
                    "source"
                ][
                    "trajectory"
                ],

            "topic":
                receipt[
                    "source"
                ][
                    "topic"
                ],
        },

        "corruption": {
            "family":
                "EVENT_GAP",

            "spec_id":
                spec_id,

            "injection_id":
                injection_id,
        },

        "clean":
            branch_payloads[
                "clean"
            ],

        "corrupt":
            branch_payloads[
                "corrupt"
            ],

        "interpretation": {
            "same_extractor_used_for_clean_and_corrupt":
                True,

            "clean_corrupt_numeric_difference_computed":
                False,

            "descriptive_statistics_computed":
                False,

            "source_registration_outputs_are_nonscoring":
                True,

            "diagnostic_features_are_accuracy_scores":
                False,

            "diagnostic_features_are_health_labels":
                False,
        },

        "scientific_scope": {
            "existing_phase3_receipt_only":
                True,

            "ros_bag_opened":
                False,

            "pointcloud_decoded":
                False,

            "registration_rerun":
                False,

            "corruption_rerun":
                False,

            "normalization_applied":
                False,

            "window_aggregation_applied":
                False,

            "threshold_applied":
                False,

            "health_label_emitted":
                False,

            "fault_label_emitted":
                False,

            "reliability_score_emitted":
                False,

            "accuracy_score_emitted":
                False,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "estimator_scoring_performed":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = _content_sha256(
        payload
    )

    return payload
