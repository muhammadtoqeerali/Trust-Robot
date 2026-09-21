from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json
import os
import re
import tempfile

from .m2dgr_evaluation_protocol_v2 import (
    validate_m2dgr_evaluation_protocol_v2,
)
from .m2dgr_evaluator_gate import (
    M2DGRFailClosedEvaluationGate,
    validate_m2dgr_reference_family_protocol_boundary,
)


PLAN_SCHEMA = "TRUST_ROBOT_M2DGR_NONEXECUTABLE_EVALUATION_PLAN_V1"
PLAN_SCHEMA_VERSION = 1

REFERENCE_FAMILIES = (
    "rtk_ins",
    "leica",
    "mocap",
)

HEX64 = re.compile(r"^[0-9a-f]{64}$")


class M2DGREvaluationPlanError(ValueError):
    """Raised when a non-executable evaluation plan violates its contract."""


@dataclass(frozen=True)
class ArtifactBinding:
    role: str
    relative_path: str
    file_sha256: str
    content_sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "relative_path": self.relative_path,
            "file_sha256": self.file_sha256,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ProvenanceRecord:
    artifact_bindings: tuple[ArtifactBinding, ...]
    required_per_evaluation_fields: tuple[str, ...]
    per_trajectory_values_populated: bool
    estimator_trajectory_bound: bool
    reference_trajectory_bound: bool
    confirmation_test_raw_data_accessed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_bindings": [
                item.to_dict()
                for item in self.artifact_bindings
            ],
            "required_per_evaluation_fields":
                list(self.required_per_evaluation_fields),
            "per_trajectory_values_populated":
                self.per_trajectory_values_populated,
            "estimator_trajectory_bound":
                self.estimator_trajectory_bound,
            "reference_trajectory_bound":
                self.reference_trajectory_bound,
            "confirmation_test_raw_data_accessed":
                self.confirmation_test_raw_data_accessed,
        }


@dataclass(frozen=True)
class PlannedMetric:
    reference_family: str
    metric_name: str
    short_name: str
    required_dimensions: tuple[str, ...]
    definition_authorized: bool
    structural_dimensions_supported: bool
    metric_enabled: bool
    execution_authorized: bool
    scoring_authorized: bool
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "reference_family":
                self.reference_family,
            "metric_name":
                self.metric_name,
            "short_name":
                self.short_name,
            "required_dimensions":
                list(self.required_dimensions),
            "definition_authorized":
                self.definition_authorized,
            "structural_dimensions_supported":
                self.structural_dimensions_supported,
            "metric_enabled":
                self.metric_enabled,
            "execution_authorized":
                self.execution_authorized,
            "scoring_authorized":
                self.scoring_authorized,
            "blockers":
                list(self.blockers),
        }


@dataclass(frozen=True)
class RequirementGroup:
    name: str
    requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "requirements": list(self.requirements),
        }


@dataclass(frozen=True)
class NonExecutableEvaluationPlan:
    dataset_id: str
    status: str
    provenance: ProvenanceRecord
    metrics: tuple[PlannedMetric, ...]
    requirement_groups: tuple[RequirementGroup, ...]
    remaining_blockers: tuple[str, ...]

    association_method: str
    association_tolerance_seconds: float | None
    fixed_reference_to_estimator_offset_seconds: float | None
    interpolation_method: str
    evaluation_interval_policy: str
    alignment_mode: str

    confirmation_test_partition_closed: bool
    confirmation_test_used_for_selection: bool

    association_execution_authorized: bool
    evaluation_interval_authorized: bool
    alignment_execution_authorized: bool
    metric_computation_authorized: bool
    trajectory_scoring_authorized: bool
    estimator_scoring_authorized: bool
    evaluation_ready: bool

    raw_trajectory_data_loaded: bool
    estimator_output_loaded: bool
    parameter_selection_performed: bool
    metric_values_computed: bool

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": PLAN_SCHEMA,
            "schema_version": PLAN_SCHEMA_VERSION,
            "dataset_id": self.dataset_id,
            "status": self.status,

            "provenance": self.provenance.to_dict(),

            "execution_contract": {
                "association_method":
                    self.association_method,

                "association_tolerance_seconds":
                    self.association_tolerance_seconds,

                "fixed_reference_to_estimator_offset_seconds":
                    self.fixed_reference_to_estimator_offset_seconds,

                "interpolation_method":
                    self.interpolation_method,

                "evaluation_interval_policy":
                    self.evaluation_interval_policy,

                "alignment_mode":
                    self.alignment_mode,
            },

            "confirmation_test_policy": {
                "partition_closed_to_selection":
                    self.confirmation_test_partition_closed,

                "used_for_selection":
                    self.confirmation_test_used_for_selection,

                "raw_data_accessed":
                    self.provenance.confirmation_test_raw_data_accessed,
            },

            "execution_authorization": {
                "association_execution_authorized":
                    self.association_execution_authorized,

                "evaluation_interval_authorized":
                    self.evaluation_interval_authorized,

                "alignment_execution_authorized":
                    self.alignment_execution_authorized,

                "metric_computation_authorized":
                    self.metric_computation_authorized,

                "trajectory_scoring_authorized":
                    self.trajectory_scoring_authorized,

                "estimator_scoring_authorized":
                    self.estimator_scoring_authorized,

                "evaluation_ready":
                    self.evaluation_ready,
            },

            "scope": {
                "raw_trajectory_data_loaded":
                    self.raw_trajectory_data_loaded,

                "estimator_output_loaded":
                    self.estimator_output_loaded,

                "parameter_selection_performed":
                    self.parameter_selection_performed,

                "metric_values_computed":
                    self.metric_values_computed,

                "non_executable_plan":
                    True,
            },

            "metrics": [
                item.to_dict()
                for item in self.metrics
            ],

            "remaining_blockers":
                list(self.remaining_blockers),

            "next_evidence_or_design_requirements": [
                item.to_dict()
                for item in self.requirement_groups
            ],
        }

        payload["content_sha256"] = (
            evaluation_plan_content_sha256(
                payload
            )
        )

        return payload


def _canonical_payload(
    payload: Mapping[str, object],
) -> bytes:
    value = deepcopy(dict(payload))
    value.pop("content_sha256", None)

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def evaluation_plan_content_sha256(
    payload: Mapping[str, object],
) -> str:
    return sha256(
        _canonical_payload(payload)
    ).hexdigest()


def _file_sha256(
    path: Path,
) -> str:
    h = sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def _repo_relative_path(
    repo_root: Path,
    path: Path,
) -> str:
    root = repo_root.resolve()
    target = path.resolve()

    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise M2DGREvaluationPlanError(
            f"artifact outside repository root: {path}"
        ) from exc

    return relative.as_posix()


def _binding(
    *,
    repo_root: Path,
    role: str,
    path: Path,
    content_sha256: str | None = None,
) -> ArtifactBinding:
    file_sha = _file_sha256(path)

    if HEX64.fullmatch(file_sha) is None:
        raise M2DGREvaluationPlanError(
            f"invalid SHA256 for {role}"
        )

    if (
        content_sha256 is not None
        and HEX64.fullmatch(content_sha256) is None
    ):
        raise M2DGREvaluationPlanError(
            f"invalid content SHA256 for {role}"
        )

    return ArtifactBinding(
        role=role,
        relative_path=_repo_relative_path(
            repo_root,
            path,
        ),
        file_sha256=file_sha,
        content_sha256=content_sha256,
    )


def _require_file_binding(
    *,
    actual_sha256: str,
    expected_block: Mapping[str, object],
    label: str,
) -> None:
    expected = expected_block.get(
        "file_sha256"
    )

    if actual_sha256 != expected:
        raise M2DGREvaluationPlanError(
            f"{label} file SHA256 does not match frozen provenance"
        )


def build_nonexecut_m2dgr_evaluation_plan(
    *,
    repo_root: Path,
    protocol_path: Path,
    boundary_path: Path,
    split_manifest_path: Path,
    split_evidence_path: Path,
    evaluator_gate_path: Path,
) -> NonExecutableEvaluationPlan:
    protocol = json.loads(
        protocol_path.read_text(
            encoding="utf-8"
        )
    )

    boundary = json.loads(
        boundary_path.read_text(
            encoding="utf-8"
        )
    )

    validate_m2dgr_evaluation_protocol_v2(
        protocol
    )

    validate_m2dgr_reference_family_protocol_boundary(
        boundary
    )

    gate = M2DGRFailClosedEvaluationGate(
        protocol=protocol,
        boundary=boundary,
    )

    if protocol.get("dataset_id") != "M2DGR":
        raise M2DGREvaluationPlanError(
            "unexpected protocol dataset"
        )

    if boundary.get("dataset_id") != "M2DGR":
        raise M2DGREvaluationPlanError(
            "unexpected boundary dataset"
        )

    if (
        protocol.get("status")
        != "blocked_pending_physical_evidence"
    ):
        raise M2DGREvaluationPlanError(
            "protocol must remain blocked"
        )

    if (
        boundary.get("status")
        != "blocked_pending_physical_evidence"
    ):
        raise M2DGREvaluationPlanError(
            "boundary must remain blocked"
        )

    protocol_sha = _file_sha256(
        protocol_path
    )

    boundary_sha = _file_sha256(
        boundary_path
    )

    split_sha = _file_sha256(
        split_manifest_path
    )

    split_evidence_sha = _file_sha256(
        split_evidence_path
    )

    gate_sha = _file_sha256(
        evaluator_gate_path
    )

    boundary_sources = boundary[
        "source_artifacts"
    ]

    _require_file_binding(
        actual_sha256=protocol_sha,
        expected_block=boundary_sources[
            "protocol_v2"
        ],
        label="protocol_v2",
    )

    _require_file_binding(
        actual_sha256=split_sha,
        expected_block=boundary_sources[
            "split_manifest_v1"
        ],
        label="split_manifest_v1",
    )

    _require_file_binding(
        actual_sha256=split_evidence_sha,
        expected_block=boundary_sources[
            "split_evidence_v1"
        ],
        label="split_evidence_v1",
    )

    protocol_sources = protocol[
        "source_artifacts"
    ]

    _require_file_binding(
        actual_sha256=split_sha,
        expected_block=protocol_sources[
            "frozen_split_manifest"
        ],
        label="protocol frozen split",
    )

    _require_file_binding(
        actual_sha256=split_evidence_sha,
        expected_block=protocol_sources[
            "split_freeze_evidence"
        ],
        label="protocol split-freeze evidence",
    )

    authorization = protocol[
        "authorization"
    ]

    for key in (
        "provenance_requirement_definition_authorized",
        "metric_family_definition_authorized",
        "dimension_gating_definition_authorized",
        "protocol_schema_definition_authorized",
        "confirmation_test_partition_closed",
    ):
        if authorization.get(key) is not True:
            raise M2DGREvaluationPlanError(
                f"{key} must remain true for definition-only plan construction"
            )

    for key in (
        "association_execution_authorized",
        "evaluation_interval_authorized",
        "alignment_execution_authorized",
        "metric_computation_authorized",
        "trajectory_scoring_authorized",
        "estimator_scoring_authorized",
        "dataset_calibration_verified",
        "synchronization_verified",
        "evaluation_ready",
    ):
        if authorization.get(key) is not False:
            raise M2DGREvaluationPlanError(
                f"{key} must remain false"
            )

    provenance_fields = tuple(
        sorted(
            key
            for key, required
            in protocol[
                "required_provenance"
            ].items()
            if required is True
        )
    )

    bindings = (
        _binding(
            repo_root=repo_root,
            role="protocol_v2",
            path=protocol_path,
            content_sha256=protocol[
                "content_sha256"
            ],
        ),

        _binding(
            repo_root=repo_root,
            role="reference_family_boundary_v1",
            path=boundary_path,
            content_sha256=boundary[
                "content_sha256"
            ],
        ),

        _binding(
            repo_root=repo_root,
            role="frozen_split_manifest_v1",
            path=split_manifest_path,
            content_sha256=protocol_sources[
                "frozen_split_manifest"
            ][
                "content_sha256"
            ],
        ),

        _binding(
            repo_root=repo_root,
            role="split_freeze_evidence_v1",
            path=split_evidence_path,
            content_sha256=protocol_sources[
                "split_freeze_evidence"
            ][
                "content_sha256"
            ],
        ),

        _binding(
            repo_root=repo_root,
            role="fail_closed_evaluator_gate_v1",
            path=evaluator_gate_path,
            content_sha256=None,
        ),
    )

    if bindings[0].file_sha256 != protocol_sha:
        raise M2DGREvaluationPlanError(
            "internal protocol binding mismatch"
        )

    if bindings[1].file_sha256 != boundary_sha:
        raise M2DGREvaluationPlanError(
            "internal boundary binding mismatch"
        )

    if bindings[4].file_sha256 != gate_sha:
        raise M2DGREvaluationPlanError(
            "internal evaluator-gate binding mismatch"
        )

    planned_metrics = []

    for family in REFERENCE_FAMILIES:
        for definition in gate.metric_definitions:
            metric_gate = gate.metric_gate(
                family,
                definition.name,
            )

            if metric_gate.execution_authorized:
                raise M2DGREvaluationPlanError(
                    "current metric unexpectedly executable"
                )

            if metric_gate.scoring_authorized:
                raise M2DGREvaluationPlanError(
                    "current metric unexpectedly scoreable"
                )

            planned_metrics.append(
                PlannedMetric(
                    reference_family=family,
                    metric_name=definition.name,
                    short_name=definition.short_name,
                    required_dimensions=definition.required_dimensions,
                    definition_authorized=
                        metric_gate.definition_authorized,
                    structural_dimensions_supported=
                        metric_gate.structural_dimensions_supported,
                    metric_enabled=
                        metric_gate.metric_enabled,
                    execution_authorized=
                        metric_gate.execution_authorized,
                    scoring_authorized=
                        metric_gate.scoring_authorized,
                    blockers=
                        metric_gate.blockers,
                )
            )

    requirement_groups = tuple(
        RequirementGroup(
            name=name,
            requirements=tuple(values),
        )
        for name, values
        in sorted(
            boundary[
                "next_evidence_or_design_requirements"
            ].items()
        )
    )

    plan = NonExecutableEvaluationPlan(
        dataset_id="M2DGR",
        status="blocked_pending_physical_evidence",

        provenance=ProvenanceRecord(
            artifact_bindings=bindings,
            required_per_evaluation_fields=
                provenance_fields,
            per_trajectory_values_populated=False,
            estimator_trajectory_bound=False,
            reference_trajectory_bound=False,
            confirmation_test_raw_data_accessed=False,
        ),

        metrics=tuple(
            planned_metrics
        ),

        requirement_groups=requirement_groups,

        remaining_blockers=tuple(
            protocol[
                "remaining_blockers"
            ]
        ),

        association_method=protocol[
            "temporal_association"
        ][
            "selected_method"
        ],

        association_tolerance_seconds=protocol[
            "temporal_association"
        ][
            "association_tolerance_seconds"
        ],

        fixed_reference_to_estimator_offset_seconds=protocol[
            "temporal_association"
        ][
            "fixed_reference_to_estimator_offset_seconds"
        ],

        interpolation_method=protocol[
            "temporal_association"
        ][
            "interpolation_method"
        ],

        evaluation_interval_policy=protocol[
            "evaluation_interval"
        ][
            "selected_policy"
        ],

        alignment_mode=protocol[
            "frame_alignment"
        ][
            "selected_mode"
        ],

        confirmation_test_partition_closed=protocol[
            "selection_policy"
        ][
            "confirmation_test_closed_to_future_selection"
        ],

        confirmation_test_used_for_selection=False,

        association_execution_authorized=authorization[
            "association_execution_authorized"
        ],

        evaluation_interval_authorized=authorization[
            "evaluation_interval_authorized"
        ],

        alignment_execution_authorized=authorization[
            "alignment_execution_authorized"
        ],

        metric_computation_authorized=authorization[
            "metric_computation_authorized"
        ],

        trajectory_scoring_authorized=authorization[
            "trajectory_scoring_authorized"
        ],

        estimator_scoring_authorized=authorization[
            "estimator_scoring_authorized"
        ],

        evaluation_ready=authorization[
            "evaluation_ready"
        ],

        raw_trajectory_data_loaded=False,
        estimator_output_loaded=False,
        parameter_selection_performed=False,
        metric_values_computed=False,
    )

    validate_nonexecut_m2dgr_evaluation_plan(
        plan.to_payload()
    )

    return plan


def validate_nonexecut_m2dgr_evaluation_plan(
    payload: Mapping[str, object],
) -> None:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise M2DGREvaluationPlanError(
            "plan root must be a mapping"
        )

    required_root = {
        "schema",
        "schema_version",
        "dataset_id",
        "status",
        "provenance",
        "execution_contract",
        "confirmation_test_policy",
        "execution_authorization",
        "scope",
        "metrics",
        "remaining_blockers",
        "next_evidence_or_design_requirements",
        "content_sha256",
    }

    if set(payload) != required_root:
        raise M2DGREvaluationPlanError(
            "plan root keys mismatch"
        )

    if payload["schema"] != PLAN_SCHEMA:
        raise M2DGREvaluationPlanError(
            "unexpected plan schema"
        )

    if payload["schema_version"] != PLAN_SCHEMA_VERSION:
        raise M2DGREvaluationPlanError(
            "unexpected plan schema version"
        )

    if payload["dataset_id"] != "M2DGR":
        raise M2DGREvaluationPlanError(
            "unexpected plan dataset"
        )

    if (
        payload["status"]
        != "blocked_pending_physical_evidence"
    ):
        raise M2DGREvaluationPlanError(
            "plan must remain blocked"
        )

    stored_sha = payload["content_sha256"]

    if (
        not isinstance(stored_sha, str)
        or HEX64.fullmatch(stored_sha) is None
    ):
        raise M2DGREvaluationPlanError(
            "invalid plan content SHA256"
        )

    if stored_sha != evaluation_plan_content_sha256(
        payload
    ):
        raise M2DGREvaluationPlanError(
            "plan content SHA256 mismatch"
        )

    provenance = payload["provenance"]

    if not isinstance(
        provenance,
        Mapping,
    ):
        raise M2DGREvaluationPlanError(
            "provenance must be a mapping"
        )

    expected_provenance_keys = {
        "artifact_bindings",
        "required_per_evaluation_fields",
        "per_trajectory_values_populated",
        "estimator_trajectory_bound",
        "reference_trajectory_bound",
        "confirmation_test_raw_data_accessed",
    }

    if set(provenance) != expected_provenance_keys:
        raise M2DGREvaluationPlanError(
            "provenance keys mismatch"
        )

    for key in (
        "per_trajectory_values_populated",
        "estimator_trajectory_bound",
        "reference_trajectory_bound",
        "confirmation_test_raw_data_accessed",
    ):
        if provenance[key] is not False:
            raise M2DGREvaluationPlanError(
                f"provenance.{key} must remain false"
            )

    bindings = provenance[
        "artifact_bindings"
    ]

    if not isinstance(
        bindings,
        list,
    ):
        raise M2DGREvaluationPlanError(
            "artifact_bindings must be a list"
        )

    expected_roles = {
        "protocol_v2",
        "reference_family_boundary_v1",
        "frozen_split_manifest_v1",
        "split_freeze_evidence_v1",
        "fail_closed_evaluator_gate_v1",
    }

    actual_roles = set()

    for binding in bindings:
        if not isinstance(
            binding,
            Mapping,
        ):
            raise M2DGREvaluationPlanError(
                "artifact binding must be a mapping"
            )

        if set(binding) != {
            "role",
            "relative_path",
            "file_sha256",
            "content_sha256",
        }:
            raise M2DGREvaluationPlanError(
                "artifact binding keys mismatch"
            )

        role = binding["role"]
        path = binding["relative_path"]
        file_sha = binding["file_sha256"]
        content_sha = binding["content_sha256"]

        if not isinstance(role, str):
            raise M2DGREvaluationPlanError(
                "artifact role must be a string"
            )

        actual_roles.add(role)

        if (
            not isinstance(path, str)
            or not path
            or Path(path).is_absolute()
        ):
            raise M2DGREvaluationPlanError(
                f"{role}: invalid relative path"
            )

        if (
            not isinstance(file_sha, str)
            or HEX64.fullmatch(file_sha) is None
        ):
            raise M2DGREvaluationPlanError(
                f"{role}: invalid file SHA256"
            )

        if (
            content_sha is not None
            and (
                not isinstance(content_sha, str)
                or HEX64.fullmatch(content_sha) is None
            )
        ):
            raise M2DGREvaluationPlanError(
                f"{role}: invalid content SHA256"
            )

    if actual_roles != expected_roles:
        raise M2DGREvaluationPlanError(
            "artifact binding roles changed"
        )

    provenance_fields = provenance[
        "required_per_evaluation_fields"
    ]

    if (
        not isinstance(
            provenance_fields,
            list,
        )
        or not provenance_fields
        or any(
            not isinstance(item, str)
            for item in provenance_fields
        )
    ):
        raise M2DGREvaluationPlanError(
            "required provenance fields invalid"
        )

    execution = payload[
        "execution_contract"
    ]

    if execution != {
        "association_method": "unselected",
        "association_tolerance_seconds": None,
        "fixed_reference_to_estimator_offset_seconds": None,
        "interpolation_method": "unselected",
        "evaluation_interval_policy": "unselected",
        "alignment_mode": "unselected",
    }:
        raise M2DGREvaluationPlanError(
            "execution contract must remain unselected"
        )

    confirmation = payload[
        "confirmation_test_policy"
    ]

    if confirmation != {
        "partition_closed_to_selection": True,
        "used_for_selection": False,
        "raw_data_accessed": False,
    }:
        raise M2DGREvaluationPlanError(
            "confirmation-test policy changed"
        )

    execution_auth = payload[
        "execution_authorization"
    ]

    expected_auth_keys = {
        "association_execution_authorized",
        "evaluation_interval_authorized",
        "alignment_execution_authorized",
        "metric_computation_authorized",
        "trajectory_scoring_authorized",
        "estimator_scoring_authorized",
        "evaluation_ready",
    }

    if set(execution_auth) != expected_auth_keys:
        raise M2DGREvaluationPlanError(
            "execution authorization keys changed"
        )

    for key in expected_auth_keys:
        if execution_auth[key] is not False:
            raise M2DGREvaluationPlanError(
                f"{key} must remain false"
            )

    scope = payload["scope"]

    if scope != {
        "raw_trajectory_data_loaded": False,
        "estimator_output_loaded": False,
        "parameter_selection_performed": False,
        "metric_values_computed": False,
        "non_executable_plan": True,
    }:
        raise M2DGREvaluationPlanError(
            "non-executable scope changed"
        )

    metrics = payload["metrics"]

    if (
        not isinstance(metrics, list)
        or len(metrics) != 12
    ):
        raise M2DGREvaluationPlanError(
            "expected exactly 12 family/metric plan entries"
        )

    seen = set()

    for metric in metrics:
        if not isinstance(
            metric,
            Mapping,
        ):
            raise M2DGREvaluationPlanError(
                "planned metric must be a mapping"
            )

        family = metric.get(
            "reference_family"
        )

        metric_name = metric.get(
            "metric_name"
        )

        if family not in REFERENCE_FAMILIES:
            raise M2DGREvaluationPlanError(
                "unknown planned reference family"
            )

        if not isinstance(
            metric_name,
            str,
        ):
            raise M2DGREvaluationPlanError(
                "invalid planned metric name"
            )

        key = (
            family,
            metric_name,
        )

        if key in seen:
            raise M2DGREvaluationPlanError(
                "duplicate family/metric plan entry"
            )

        seen.add(key)

        if metric.get(
            "definition_authorized"
        ) is not True:
            raise M2DGREvaluationPlanError(
                "metric definition must remain authorized"
            )

        if metric.get(
            "metric_enabled"
        ) is not False:
            raise M2DGREvaluationPlanError(
                "planned metric must remain disabled"
            )

        if metric.get(
            "execution_authorized"
        ) is not False:
            raise M2DGREvaluationPlanError(
                "planned metric execution must remain blocked"
            )

        if metric.get(
            "scoring_authorized"
        ) is not False:
            raise M2DGREvaluationPlanError(
                "planned metric scoring must remain blocked"
            )

        if (
            family == "leica"
            and metric.get("short_name")
            in {
                "ATE_rotation",
                "RPE_rotation",
            }
        ):
            if metric.get(
                "structural_dimensions_supported"
            ) is not False:
                raise M2DGREvaluationPlanError(
                    "Leica rotation must remain structurally unsupported"
                )

    blockers = payload[
        "remaining_blockers"
    ]

    if (
        not isinstance(blockers, list)
        or not blockers
        or any(
            not isinstance(item, str)
            for item in blockers
        )
    ):
        raise M2DGREvaluationPlanError(
            "remaining blockers invalid"
        )

    requirements = payload[
        "next_evidence_or_design_requirements"
    ]

    if (
        not isinstance(requirements, list)
        or not requirements
    ):
        raise M2DGREvaluationPlanError(
            "requirement groups missing"
        )

    for group in requirements:
        if (
            not isinstance(group, Mapping)
            or set(group) != {
                "name",
                "requirements",
            }
            or not isinstance(
                group["name"],
                str,
            )
            or not isinstance(
                group["requirements"],
                list,
            )
            or not group["requirements"]
            or any(
                not isinstance(item, str)
                for item in group["requirements"]
            )
        ):
            raise M2DGREvaluationPlanError(
                "requirement group invalid"
            )
def write_immutable_nonexecut_m2dgr_evaluation_plan(
    path: Path,
    payload: Mapping[str, object],
) -> str:
    """Persist a validated plan without allowing content-changing overwrite."""

    validate_nonexecut_m2dgr_evaluation_plan(
        payload
    )

    target = Path(path)

    serialized = (
        json.dumps(
            dict(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    digest = sha256(
        serialized
    ).hexdigest()

    if target.exists():
        existing = target.read_bytes()

        if existing != serialized:
            raise M2DGREvaluationPlanError(
                "refusing to overwrite non-executable evaluation plan "
                "with different content"
            )

        return digest

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                serialized
            )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            target,
        )

    finally:
        if temporary.exists():
            temporary.unlink()

    return digest


def load_nonexecut_m2dgr_evaluation_plan(
    path: Path,
) -> dict[str, object]:
    """Load and validate a persisted non-executable evaluation plan."""

    target = Path(path)

    payload = json.loads(
        target.read_text(
            encoding="utf-8"
        )
    )

    validate_nonexecut_m2dgr_evaluation_plan(
        payload
    )

    return payload
