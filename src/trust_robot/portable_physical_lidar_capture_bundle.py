"""Portable physical-LiDAR capture preparation for TRUST-ROBOT.

This layer is intentionally non-executing.

It packages explicit operator declarations and, only when every required
physical/runtime value has been supplied, constructs a hash-addressed V2
runtime-binding candidate using the already-frozen SE4 API.

It does not:

* inspect host network interfaces;
* execute subprocesses;
* open sockets;
* contact a sensor;
* issue HTTP requests;
* capture UDP packets;
* configure a sensor;
* generate real-execution authorization;
* accept baseline nominality;
* create health labels;
* open VALIDATION or CONFIRMATION.

The current frozen physical acquisition path supports Velodyne VLP-32C.
Other hardware may be inventoried, but cannot be bound through that frozen
VLP-32C execution path.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
import json
import re

from .se4_real_train_runtime_input_binding_v2 import (
    build_runtime_binding_candidate_v2,
    validate_runtime_binding_candidate_v2,
)


BUNDLE_SCHEMA = (
    "TRUST_ROBOT_PORTABLE_PHYSICAL_LIDAR_CAPTURE_BUNDLE_V1"
)

INVENTORY_SCHEMA = (
    "TRUST_ROBOT_PHYSICAL_LIDAR_HARDWARE_INVENTORY_DECLARATION_V1"
)

RUNTIME_TEMPLATE_SCHEMA = (
    "TRUST_ROBOT_PHYSICAL_LIDAR_RUNTIME_INPUT_TEMPLATE_V1"
)

PHASE5_PLAN_ARGV_SCHEMA = (
    "TRUST_ROBOT_PHASE5_VLP32C_PLAN_ARGV_V1"
)

EXPECTED_VENDOR = "Velodyne"
EXPECTED_MODEL = "VLP-32C"

_SESSION_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)

REQUIRED_RUNTIME_FIELDS = (
    "acquisition_session_id",
    "split",
    "bind_ipv4",
    "measurement_udp_port",
    "position_udp_port",
    "sensor_ipv4",
    "capture_duration_seconds",
    "absolute_output_root",
    "http_port",
    "http_connect_timeout_seconds",
    "http_total_timeout_seconds",
    "vlp32c_destination_ipv4",
    "vlp32c_measurement_destination_udp_port",
    "vlp32c_position_destination_udp_port",
    "vlp32c_destination_configuration_verified",
    "declared_before_execution",
)

BUNDLE_ARTIFACT_NAMES = {
    "hardware_inventory":
        "hardware_inventory.json",

    "runtime_input_template":
        "runtime_input_template.json",

    "runtime_binding_candidate":
        "runtime_binding_candidate_v2.json",

    "phase5_plan_argv":
        "phase5_plan_argv.json",

    "operator_checklist":
        "KIOS_OPERATOR_CHECKLIST.txt",

    "bundle_manifest":
        "portable_bundle_manifest.json",
}


class PortablePhysicalLidarCaptureBundleError(
    ValueError
):
    """Raised when the portable capture-preparation contract is violated."""


def canonical_json_bytes(
    value: object,
) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )


def content_sha256(
    payload: Mapping[str, Any],
) -> str:
    body = dict(
        payload
    )

    body.pop(
        "content_sha256",
        None,
    )

    return sha256(
        canonical_json_bytes(
            body
        )
    ).hexdigest()


def _text(
    value: object,
    *,
    name: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise PortablePhysicalLidarCaptureBundleError(
            name
            + " must be a non-empty string"
        )

    return value.strip()


def _session_id(
    value: object,
) -> str:
    result = _text(
        value,
        name=
            "acquisition_session_id",
    )

    if _SESSION_ID_RE.fullmatch(
        result
    ) is None:
        raise PortablePhysicalLidarCaptureBundleError(
            "acquisition_session_id must be a safe single path component"
        )

    return result


@dataclass(
    frozen=True
)
class PhysicalLidarInventoryDeclaration:
    acquisition_session_id: str

    acquisition_host_id: str

    sensor_vendor: str

    sensor_model: str

    sensor_serial: str

    connection_path: str

    declared_condition: str = (
        "DECLARED_NOMINAL_BENCH_CONDITION"
    )

    def __post_init__(
        self,
    ) -> None:
        _session_id(
            self.acquisition_session_id
        )

        for name in (
            "acquisition_host_id",
            "sensor_vendor",
            "sensor_model",
            "sensor_serial",
            "connection_path",
            "declared_condition",
        ):
            _text(
                getattr(
                    self,
                    name,
                ),
                name=name,
            )

    @property
    def frozen_vlp32c_path_compatible(
        self,
    ) -> bool:
        return (
            self.sensor_vendor
            == EXPECTED_VENDOR
            and self.sensor_model
            == EXPECTED_MODEL
        )

    def to_payload(
        self,
    ) -> dict[str, object]:
        payload: dict[
            str,
            object,
        ] = {
            "schema":
                INVENTORY_SCHEMA,

            "schema_version":
                1,

            "acquisition_session_id":
                self.acquisition_session_id,

            "acquisition_host_id":
                self.acquisition_host_id,

            "sensor_vendor":
                self.sensor_vendor,

            "sensor_model":
                self.sensor_model,

            "sensor_serial":
                self.sensor_serial,

            "connection_path":
                self.connection_path,

            "declared_condition":
                self.declared_condition,

            "frozen_vlp32c_path_compatible":
                self.frozen_vlp32c_path_compatible,

            "scientific_boundary": {
                "inventory_is_sensor_contact":
                    False,

                "declared_nominal_means_proven_healthy":
                    False,

                "real_health_label_created":
                    False,
            },
        }

        payload[
            "content_sha256"
        ] = content_sha256(
            payload
        )

        return payload


def build_runtime_input_template(
) -> dict[str, object]:
    payload: dict[
        str,
        object,
    ] = {
        "schema":
            RUNTIME_TEMPLATE_SCHEMA,

        "schema_version":
            1,

        "required_field_count":
            len(
                REQUIRED_RUNTIME_FIELDS
            ),

        "required_fields":
            {
                name: {
                    "required":
                        True,

                    "value":
                        None,

                    "physical_default_selected":
                        False,
                }
                for name
                in REQUIRED_RUNTIME_FIELDS
            },

        "additional_portable_fact": {
            "capture_interface": {
                "required":
                    True,

                "value":
                    None,

                "physical_default_selected":
                    False,
            },
        },

        "binding_policy": {
            "split_must_be_TRAIN":
                True,

            "all_values_operator_supplied_or_physically_discovered":
                True,

            "destination_configuration_must_be_explicitly_verified":
                True,

            "binding_candidate_is_execution_authorization":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def build_phase5_plan_argv(
    *,
    acquisition_session_id: str,
    split: str,
    sensor_ipv4: str,
    capture_interface: str,
    measurement_udp_port: int,
    position_udp_port: int,
    capture_duration_seconds: int,
    absolute_output_root: str,
) -> dict[str, object]:
    if split != "TRAIN":
        raise PortablePhysicalLidarCaptureBundleError(
            "portable physical acquisition preparation is TRAIN-only"
        )

    interface = _text(
        capture_interface,
        name=
            "capture_interface",
    )

    argv = [
        "python3",
        "scripts/trust_robot/plan_phase5_vlp32c_live_acquisition.py",
        "--session-id",
        _session_id(
            acquisition_session_id
        ),
        "--split",
        "TRAIN",
        "--sensor-ipv4",
        _text(
            sensor_ipv4,
            name=
                "sensor_ipv4",
        ),
        "--capture-interface",
        interface,
        "--data-port",
        str(
            measurement_udp_port
        ),
        "--telemetry-port",
        str(
            position_udp_port
        ),
        "--duration-seconds",
        str(
            capture_duration_seconds
        ),
        "--output-directory",
        _text(
            absolute_output_root,
            name=
                "absolute_output_root",
        ),
    ]

    payload: dict[
        str,
        object,
    ] = {
        "schema":
            PHASE5_PLAN_ARGV_SCHEMA,

        "schema_version":
            1,

        "argv":
            argv,

        "execution": {
            "executed":
                False,

            "subprocess_created":
                False,

            "network_IO":
                False,

            "sensor_contact":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def build_inventory_only_bundle(
    inventory: PhysicalLidarInventoryDeclaration,
) -> dict[str, object]:
    payload: dict[
        str,
        object,
    ] = {
        "schema":
            BUNDLE_SCHEMA,

        "schema_version":
            1,

        "state":
            "INVENTORY_DECLARED_RUNTIME_UNBOUND",

        "hardware_inventory":
            inventory.to_payload(),

        "runtime_input_template":
            build_runtime_input_template(),

        "runtime_binding_candidate":
            None,

        "phase5_plan_argv":
            None,

        "physical_configuration": {
            "discovery_completed":
                False,

            "sensor_destination_configuration_verified":
                False,

            "capture_interface_verified_on_acquisition_host":
                False,

            "packet_presence_verified":
                False,
        },

        "execution_authorization": {
            "generated":
                False,

            "authorized_for_real_sensor_execution":
                False,
        },

        "scientific_boundary":
            _scientific_boundary(),
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def build_bound_bundle(
    *,
    inventory: PhysicalLidarInventoryDeclaration,
    split: str,
    capture_interface: str,
    bind_ipv4: str,
    measurement_udp_port: int,
    position_udp_port: int,
    sensor_ipv4: str,
    capture_duration_seconds: int,
    absolute_output_root: str,
    http_port: int,
    http_connect_timeout_seconds: int,
    http_total_timeout_seconds: int,
    vlp32c_destination_ipv4: str,
    vlp32c_measurement_destination_udp_port: int,
    vlp32c_position_destination_udp_port: int,
    vlp32c_destination_configuration_verified: bool,
    declared_before_execution: bool,
) -> dict[str, object]:
    if not inventory.frozen_vlp32c_path_compatible:
        raise PortablePhysicalLidarCaptureBundleError(
            "declared hardware is not compatible with the frozen "
            "Velodyne VLP-32C acquisition path"
        )

    if split != "TRAIN":
        raise PortablePhysicalLidarCaptureBundleError(
            "real physical acquisition preparation must remain TRAIN-only"
        )

    interface = _text(
        capture_interface,
        name=
            "capture_interface",
    )

    if (
        vlp32c_destination_configuration_verified
        is not True
    ):
        raise PortablePhysicalLidarCaptureBundleError(
            "VLP-32C destination configuration must be explicitly verified"
        )

    if declared_before_execution is not True:
        raise PortablePhysicalLidarCaptureBundleError(
            "runtime values must be declared before execution"
        )

    binding = (
        build_runtime_binding_candidate_v2(
            acquisition_session_id=
                inventory.acquisition_session_id,

            split=
                split,

            bind_ipv4=
                bind_ipv4,

            measurement_udp_port=
                measurement_udp_port,

            position_udp_port=
                position_udp_port,

            sensor_ipv4=
                sensor_ipv4,

            capture_duration_seconds=
                capture_duration_seconds,

            absolute_output_root=
                absolute_output_root,

            http_port=
                http_port,

            http_connect_timeout_seconds=
                http_connect_timeout_seconds,

            http_total_timeout_seconds=
                http_total_timeout_seconds,

            vlp32c_destination_ipv4=
                vlp32c_destination_ipv4,

            vlp32c_measurement_destination_udp_port=
                vlp32c_measurement_destination_udp_port,

            vlp32c_position_destination_udp_port=
                vlp32c_position_destination_udp_port,

            vlp32c_destination_configuration_verified=
                vlp32c_destination_configuration_verified,

            declared_before_execution=
                declared_before_execution,
        )
    )

    validate_runtime_binding_candidate_v2(
        binding
    )

    plan = build_phase5_plan_argv(
        acquisition_session_id=
            inventory.acquisition_session_id,

        split=
            split,

        sensor_ipv4=
            sensor_ipv4,

        capture_interface=
            interface,

        measurement_udp_port=
            measurement_udp_port,

        position_udp_port=
            position_udp_port,

        capture_duration_seconds=
            capture_duration_seconds,

        absolute_output_root=
            absolute_output_root,
    )

    payload: dict[
        str,
        object,
    ] = {
        "schema":
            BUNDLE_SCHEMA,

        "schema_version":
            1,

        "state":
            "RUNTIME_BOUND_NOT_AUTHORIZED",

        "hardware_inventory":
            inventory.to_payload(),

        "runtime_input_template":
            build_runtime_input_template(),

        "capture_interface":
            interface,

        "runtime_binding_candidate":
            binding,

        "phase5_plan_argv":
            plan,

        "physical_configuration": {
            "discovery_completed":
                True,

            "sensor_destination_configuration_verified":
                True,

            "capture_interface_verified_on_acquisition_host":
                True,

            "packet_presence_verified":
                False,
        },

        "execution_authorization": {
            "generated":
                False,

            "authorized_for_real_sensor_execution":
                False,
        },

        "scientific_boundary":
            _scientific_boundary(),
    }

    payload[
        "content_sha256"
    ] = content_sha256(
        payload
    )

    return payload


def _scientific_boundary(
) -> dict[str, bool | int]:
    return {
        "network_IO_executed":
            False,

        "sensor_contact_executed":
            False,

        "packet_capture_executed":
            False,

        "raw_real_sensor_capture_artifact_count":
            0,

        "real_health_label_count":
            0,

        "real_physical_health_truth":
            False,

        "baseline_nominality_accepted":
            False,

        "health_supervision_source_accepted":
            False,

        "model_fit_executed":
            False,

        "VALIDATION_open":
            False,

        "CONFIRMATION_open":
            False,

        "SE4_physical_completion":
            False,

        "SE5_physical_progression_authorized":
            False,
    }


def validate_portable_bundle(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise PortablePhysicalLidarCaptureBundleError(
            "portable bundle must be a mapping"
        )

    if payload.get(
        "schema"
    ) != BUNDLE_SCHEMA:
        raise PortablePhysicalLidarCaptureBundleError(
            "portable bundle schema mismatch"
        )

    if payload.get(
        "schema_version"
    ) != 1:
        raise PortablePhysicalLidarCaptureBundleError(
            "portable bundle version mismatch"
        )

    if payload.get(
        "content_sha256"
    ) != content_sha256(
        payload
    ):
        raise PortablePhysicalLidarCaptureBundleError(
            "portable bundle digest mismatch"
        )

    state = payload.get(
        "state"
    )

    if state not in (
        "INVENTORY_DECLARED_RUNTIME_UNBOUND",
        "RUNTIME_BOUND_NOT_AUTHORIZED",
    ):
        raise PortablePhysicalLidarCaptureBundleError(
            "portable bundle state invalid"
        )

    boundary = payload.get(
        "scientific_boundary"
    )

    if not isinstance(
        boundary,
        Mapping,
    ):
        raise PortablePhysicalLidarCaptureBundleError(
            "scientific boundary missing"
        )

    false_fields = (
        "network_IO_executed",
        "sensor_contact_executed",
        "packet_capture_executed",
        "real_physical_health_truth",
        "baseline_nominality_accepted",
        "health_supervision_source_accepted",
        "model_fit_executed",
        "VALIDATION_open",
        "CONFIRMATION_open",
        "SE4_physical_completion",
        "SE5_physical_progression_authorized",
    )

    for name in false_fields:
        if boundary.get(
            name
        ) is not False:
            raise PortablePhysicalLidarCaptureBundleError(
                name
                + " must remain false"
            )

    if boundary.get(
        "real_health_label_count"
    ) != 0:
        raise PortablePhysicalLidarCaptureBundleError(
            "real health labels must remain zero"
        )

    authorization = payload.get(
        "execution_authorization"
    )

    if (
        not isinstance(
            authorization,
            Mapping,
        )
        or authorization.get(
            "generated"
        ) is not False
        or authorization.get(
            "authorized_for_real_sensor_execution"
        ) is not False
    ):
        raise PortablePhysicalLidarCaptureBundleError(
            "portable bundle may not generate execution authorization"
        )

    if state == "RUNTIME_BOUND_NOT_AUTHORIZED":
        binding = payload.get(
            "runtime_binding_candidate"
        )

        if not isinstance(
            binding,
            Mapping,
        ):
            raise PortablePhysicalLidarCaptureBundleError(
                "bound bundle requires runtime binding candidate"
            )

        validate_runtime_binding_candidate_v2(
            binding
        )

    return payload


def operator_checklist_text(
    payload: Mapping[str, Any],
) -> str:
    validate_portable_bundle(
        payload
    )

    return """TRUST-ROBOT PORTABLE KIOS PHYSICAL LIDAR CAPTURE CHECKLIST V1

THIS BUNDLE DOES NOT AUTHORIZE OR EXECUTE REAL SENSOR I/O.

Before any real capture, on the KIOS acquisition machine:

1. Confirm the physical sensor vendor/model/serial from the actual hardware.
2. Confirm cabling and the acquisition host connection path.
3. Record the host network-interface inventory using read-only OS commands.
4. Identify the actual sensor-facing interface. Do not assume eno1.
5. Confirm the actual host IPv4 address on that interface.
6. Confirm the actual sensor IPv4 address.
7. Confirm the VLP-32C destination IPv4 and both destination UDP ports.
8. Confirm the HTTP port actually exposed by the sensor.
9. Confirm measurement and position packets are directed to the acquisition host.
10. Only after those facts are verified, generate a bound runtime candidate.
11. A runtime binding candidate is NOT execution authorization.
12. Separate grounded authorization is still required before real network I/O.
13. The first bench capture condition is a declared nominal experimental condition.
14. A declared nominal capture is NOT proven healthy and creates no health label.
15. Preserve raw capture evidence, receipts, hashes, and host-side provenance.
16. Keep VALIDATION and CONFIRMATION closed.

Read-only host commands that may be useful:
    ip -brief link
    ip -brief -4 address
    ip route

Do not automatically change interface addresses, routes, sensor configuration,
or firewall state from this preparation layer.

Dog-robot integration is not required for the first bench capture.
"""


def _write_json(
    path: Path,
    payload: object,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_portable_bundle_directory(
    *,
    bundle_directory: str | Path,
    payload: Mapping[str, Any],
) -> dict[str, object]:
    validate_portable_bundle(
        payload
    )

    root = Path(
        bundle_directory
    )

    if not root.is_absolute():
        raise PortablePhysicalLidarCaptureBundleError(
            "bundle_directory must be absolute"
        )

    if root.exists():
        raise PortablePhysicalLidarCaptureBundleError(
            "bundle_directory must be fresh"
        )

    if not root.parent.is_dir():
        raise PortablePhysicalLidarCaptureBundleError(
            "bundle_directory parent must already exist"
        )

    root.mkdir(
        mode=0o750,
        parents=False,
        exist_ok=False,
    )

    inventory_path = (
        root
        / BUNDLE_ARTIFACT_NAMES[
            "hardware_inventory"
        ]
    )

    template_path = (
        root
        / BUNDLE_ARTIFACT_NAMES[
            "runtime_input_template"
        ]
    )

    checklist_path = (
        root
        / BUNDLE_ARTIFACT_NAMES[
            "operator_checklist"
        ]
    )

    manifest_path = (
        root
        / BUNDLE_ARTIFACT_NAMES[
            "bundle_manifest"
        ]
    )

    _write_json(
        inventory_path,
        payload[
            "hardware_inventory"
        ],
    )

    _write_json(
        template_path,
        payload[
            "runtime_input_template"
        ],
    )

    checklist_path.write_text(
        operator_checklist_text(
            payload
        ),
        encoding="utf-8",
    )

    emitted = {
        "hardware_inventory":
            inventory_path,

        "runtime_input_template":
            template_path,

        "operator_checklist":
            checklist_path,
    }

    if payload[
        "runtime_binding_candidate"
    ] is not None:
        binding_path = (
            root
            / BUNDLE_ARTIFACT_NAMES[
                "runtime_binding_candidate"
            ]
        )

        plan_path = (
            root
            / BUNDLE_ARTIFACT_NAMES[
                "phase5_plan_argv"
            ]
        )

        _write_json(
            binding_path,
            payload[
                "runtime_binding_candidate"
            ],
        )

        _write_json(
            plan_path,
            payload[
                "phase5_plan_argv"
            ],
        )

        emitted[
            "runtime_binding_candidate"
        ] = binding_path

        emitted[
            "phase5_plan_argv"
        ] = plan_path

    publication = {
        name: {
            "file":
                path.name,

            "bytes":
                path.stat().st_size,

            "sha256":
                sha256(
                    path.read_bytes()
                ).hexdigest(),
        }
        for name, path
        in emitted.items()
    }

    published_manifest = dict(
        payload
    )

    published_manifest[
        "published_artifacts"
    ] = publication

    published_manifest[
        "content_sha256"
    ] = content_sha256(
        published_manifest
    )

    _write_json(
        manifest_path,
        published_manifest,
    )

    publication[
        "bundle_manifest"
    ] = {
        "file":
            manifest_path.name,

        "bytes":
            manifest_path.stat().st_size,

        "sha256":
            sha256(
                manifest_path.read_bytes()
            ).hexdigest(),
    }

    return {
        "bundle_directory":
            str(root),

        "state":
            payload[
                "state"
            ],

        "published_artifacts":
            publication,

        "execution_authorization_generated":
            False,

        "network_IO_executed":
            False,

        "sensor_contact_executed":
            False,
    }
