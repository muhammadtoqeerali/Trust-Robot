from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json


SCHEMA = (
    "TRUST_ROBOT_M2DGR_REFERENCE_TEMPORAL_"
    "ASSOCIATION_EVIDENCE_V1"
)

SCHEMA_VERSION = 1


EXPECTED_POLICY = {
    "characterization_only": True,
    "raw_data_modified": False,
    "source_manifest_modified": False,
    "successor_manifest_created": False,
    "reference_interpolation_authorized": False,
    "nearest_neighbor_pose_association_authorized": False,
    "lag_search_authorized": False,
    "fixed_offset_estimated": False,
    "fixed_offset_applied": False,
    "association_tolerance_frozen": False,
    "automatic_sample_exclusion_rule_created": False,
    "evaluation_interval_created": False,
    "reference_to_estimator_temporal_association_verified": False,
    "synchronization_verified": False,
    "evaluation_ready": False,
}


class M2DGRReferenceTemporalAssociationEvidenceError(
    ValueError
):
    pass


def reference_temporal_association_evidence_content_sha256(
    payload: dict,
) -> str:
    copy = deepcopy(
        payload
    )

    copy.pop(
        "content_sha256",
        None,
    )

    raw = json.dumps(
        copy,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode(
        "utf-8"
    )

    return sha256(
        raw
    ).hexdigest()


def validate_m2dgr_reference_temporal_association_evidence(
    payload: dict,
) -> None:
    if not isinstance(
        payload,
        dict,
    ):
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "evidence root must be a mapping"
        )

    expected_keys = {
        "schema",
        "schema_version",
        "dataset_id",
        "source_artifacts",
        "source_manifest",
        "observations",
        "manifest_semantics",
        "remaining_blockers",
        "policy",
        "content_sha256",
    }

    if set(
        payload
    ) != expected_keys:
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "unexpected evidence root keys"
        )

    if payload[
        "schema"
    ] != SCHEMA:
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "unexpected evidence schema"
        )

    if payload[
        "schema_version"
    ] != SCHEMA_VERSION:
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "unexpected schema version"
        )

    if payload[
        "dataset_id"
    ] != "M2DGR":
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "unexpected dataset"
        )

    if payload[
        "policy"
    ] != EXPECTED_POLICY:
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "unexpected Phase-3E policy"
        )

    if (
        payload[
            "content_sha256"
        ]
        != reference_temporal_association_evidence_content_sha256(
            payload
        )
    ):
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "evidence content SHA mismatch"
        )

    semantics = payload[
        "manifest_semantics"
    ]

    if (
        semantics[
            "trajectory_manifest_modified"
        ]
        is not False
        or semantics[
            "successor_manifest_created"
        ]
        is not False
    ):
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "Phase-3E must not modify the trajectory manifest"
        )

    interpretation = payload[
        "observations"
    ][
        "interpretation"
    ]

    forbidden_true = (
        "reference_to_estimator_temporal_association_verified",
        "single_global_reference_timing_policy_supported",
        "fixed_reference_to_estimator_offset_supported",
        "association_tolerance_supported",
        "reference_interpolation_authorized",
        "nearest_neighbor_pose_association_authorized",
        "evaluation_interval_authorized",
        "mocap_lag_scan_supported",
        "translation_lag_scan_supported",
    )

    for key in forbidden_true:
        if interpretation[
            key
        ] is not False:
            raise M2DGRReferenceTemporalAssociationEvidenceError(
                f"unsafe Phase-3E interpretation: {key}"
            )

    rotation = payload[
        "observations"
    ][
        "rotation_content_association"
    ]

    if (
        rotation[
            "rtk_ins"
        ][
            "trajectory_count"
        ]
        != 16
        or rotation[
            "mocap"
        ][
            "trajectory_count"
        ]
        != 9
    ):
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "unexpected rotation cohort counts"
        )

    rtk = payload[
        "observations"
    ][
        "rtk_receiver_utc_coordinate"
    ]

    if (
        rtk[
            "trajectory_count"
        ]
        != 16
        or rtk[
            "numeric_coordinate_range_overlap_count"
        ]
        != 16
        or rtk[
            "all_fix_headers_exactly_present_in_reference_coordinate_count"
        ]
        != 0
    ):
        raise M2DGRReferenceTemporalAssociationEvidenceError(
            "unexpected RTK/GNSS coordinate evidence"
        )
