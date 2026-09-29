from pathlib import Path
from tempfile import TemporaryDirectory
import inspect
import json
import unittest

import trust_robot.portable_physical_lidar_capture_bundle as module

from trust_robot.portable_physical_lidar_capture_bundle import (
    BUNDLE_SCHEMA,
    EXPECTED_MODEL,
    EXPECTED_VENDOR,
    REQUIRED_RUNTIME_FIELDS,
    PhysicalLidarInventoryDeclaration,
    PortablePhysicalLidarCaptureBundleError,
    build_bound_bundle,
    build_inventory_only_bundle,
    build_phase5_plan_argv,
    build_runtime_input_template,
    content_sha256,
    operator_checklist_text,
    validate_portable_bundle,
    write_portable_bundle_directory,
)

from trust_robot.se4_real_train_runtime_input_binding_v2 import (
    validate_runtime_binding_candidate_v2,
)


def inventory(
    *,
    vendor="Velodyne",
    model="VLP-32C",
):
    return PhysicalLidarInventoryDeclaration(
        acquisition_session_id=
            "KIOS_BENCH_001",

        acquisition_host_id=
            "KIOS_ACQUISITION_HOST",

        sensor_vendor=
            vendor,

        sensor_model=
            model,

        sensor_serial=
            "DECLARED_SERIAL_001",

        connection_path=
            "sensor_ethernet_to_acquisition_host",

        declared_condition=
            "DECLARED_NOMINAL_BENCH_CONDITION",
    )


def bound():
    return build_bound_bundle(
        inventory=
            inventory(),

        split=
            "TRAIN",

        capture_interface=
            "example0",

        bind_ipv4=
            "192.0.2.10",

        measurement_udp_port=
            25000,

        position_udp_port=
            25001,

        sensor_ipv4=
            "192.0.2.20",

        capture_duration_seconds=
            5,

        absolute_output_root=
            "/tmp/TRUST_ROBOT_SYNTHETIC_CAPTURE_ROOT",

        http_port=
            8080,

        http_connect_timeout_seconds=
            1,

        http_total_timeout_seconds=
            2,

        vlp32c_destination_ipv4=
            "192.0.2.10",

        vlp32c_measurement_destination_udp_port=
            25000,

        vlp32c_position_destination_udp_port=
            25001,

        vlp32c_destination_configuration_verified=
            True,

        declared_before_execution=
            True,
    )


class PortablePhysicalLidarCaptureBundleTests(
    unittest.TestCase
):
    def test_01_schema(self):
        self.assertEqual(
            BUNDLE_SCHEMA,
            "TRUST_ROBOT_PORTABLE_PHYSICAL_LIDAR_CAPTURE_BUNDLE_V1",
        )

    def test_02_expected_vendor(self):
        self.assertEqual(
            EXPECTED_VENDOR,
            "Velodyne",
        )

    def test_03_expected_model(self):
        self.assertEqual(
            EXPECTED_MODEL,
            "VLP-32C",
        )

    def test_04_runtime_field_count(self):
        self.assertEqual(
            len(
                REQUIRED_RUNTIME_FIELDS
            ),
            16,
        )

    def test_05_inventory_vlp32c_compatible(self):
        self.assertTrue(
            inventory()
            .frozen_vlp32c_path_compatible
        )

    def test_06_other_hardware_inventory_allowed(self):
        item = inventory(
            vendor="OtherVendor",
            model="OtherModel",
        )

        self.assertFalse(
            item.frozen_vlp32c_path_compatible
        )

    def test_07_empty_host_rejected(self):
        with self.assertRaises(
            PortablePhysicalLidarCaptureBundleError
        ):
            PhysicalLidarInventoryDeclaration(
                acquisition_session_id=
                    "S",

                acquisition_host_id=
                    "",

                sensor_vendor=
                    "Velodyne",

                sensor_model=
                    "VLP-32C",

                sensor_serial=
                    "X",

                connection_path=
                    "ethernet",
            )

    def test_08_unsafe_session_rejected(self):
        with self.assertRaises(
            PortablePhysicalLidarCaptureBundleError
        ):
            PhysicalLidarInventoryDeclaration(
                acquisition_session_id=
                    "../bad",

                acquisition_host_id=
                    "host",

                sensor_vendor=
                    "Velodyne",

                sensor_model=
                    "VLP-32C",

                sensor_serial=
                    "X",

                connection_path=
                    "ethernet",
            )

    def test_09_runtime_template_all_no_defaults(self):
        template = (
            build_runtime_input_template()
        )

        self.assertTrue(
            all(
                item[
                    "value"
                ]
                is None
                and item[
                    "physical_default_selected"
                ]
                is False
                for item
                in template[
                    "required_fields"
                ].values()
            )
        )

    def test_10_runtime_template_exact_fields(self):
        template = (
            build_runtime_input_template()
        )

        self.assertEqual(
            tuple(
                template[
                    "required_fields"
                ].keys()
            ),
            REQUIRED_RUNTIME_FIELDS,
        )

    def test_11_inventory_bundle_unbound(self):
        payload = (
            build_inventory_only_bundle(
                inventory()
            )
        )

        self.assertEqual(
            payload[
                "state"
            ],
            "INVENTORY_DECLARED_RUNTIME_UNBOUND",
        )

        self.assertIsNone(
            payload[
                "runtime_binding_candidate"
            ]
        )

    def test_12_inventory_bundle_not_authorized(self):
        payload = (
            build_inventory_only_bundle(
                inventory()
            )
        )

        self.assertFalse(
            payload[
                "execution_authorization"
            ][
                "generated"
            ]
        )

    def test_13_bound_bundle_state(self):
        self.assertEqual(
            bound()[
                "state"
            ],
            "RUNTIME_BOUND_NOT_AUTHORIZED",
        )

    def test_14_bound_bundle_v2_binding_valid(self):
        payload = bound()

        validate_runtime_binding_candidate_v2(
            payload[
                "runtime_binding_candidate"
            ]
        )

    def test_15_bound_bundle_execution_unauthorized(self):
        self.assertFalse(
            bound()[
                "execution_authorization"
            ][
                "authorized_for_real_sensor_execution"
            ]
        )

    def test_16_non_train_rejected(self):
        kwargs = dict(
            inventory=
                inventory(),

            split=
                "VALIDATION",

            capture_interface=
                "example0",

            bind_ipv4=
                "192.0.2.10",

            measurement_udp_port=
                25000,

            position_udp_port=
                25001,

            sensor_ipv4=
                "192.0.2.20",

            capture_duration_seconds=
                5,

            absolute_output_root=
                "/tmp/x",

            http_port=
                8080,

            http_connect_timeout_seconds=
                1,

            http_total_timeout_seconds=
                2,

            vlp32c_destination_ipv4=
                "192.0.2.10",

            vlp32c_measurement_destination_udp_port=
                25000,

            vlp32c_position_destination_udp_port=
                25001,

            vlp32c_destination_configuration_verified=
                True,

            declared_before_execution=
                True,
        )

        with self.assertRaises(
            PortablePhysicalLidarCaptureBundleError
        ):
            build_bound_bundle(
                **kwargs
            )

    def test_17_incompatible_model_rejected_for_binding(self):
        kwargs = dict(
            inventory=
                inventory(
                    vendor="OtherVendor",
                    model="OtherModel",
                ),

            split=
                "TRAIN",

            capture_interface=
                "example0",

            bind_ipv4=
                "192.0.2.10",

            measurement_udp_port=
                25000,

            position_udp_port=
                25001,

            sensor_ipv4=
                "192.0.2.20",

            capture_duration_seconds=
                5,

            absolute_output_root=
                "/tmp/x",

            http_port=
                8080,

            http_connect_timeout_seconds=
                1,

            http_total_timeout_seconds=
                2,

            vlp32c_destination_ipv4=
                "192.0.2.10",

            vlp32c_measurement_destination_udp_port=
                25000,

            vlp32c_position_destination_udp_port=
                25001,

            vlp32c_destination_configuration_verified=
                True,

            declared_before_execution=
                True,
        )

        with self.assertRaises(
            PortablePhysicalLidarCaptureBundleError
        ):
            build_bound_bundle(
                **kwargs
            )

    def test_18_destination_verification_required(self):
        payload = bound()

        binding = payload[
            "runtime_binding_candidate"
        ]

        self.assertTrue(
            binding[
                "sensor_binding"
            ][
                "vlp32c_destination_configuration_verified"
            ]
        )

    def test_19_phase5_argv_is_list(self):
        plan = bound()[
            "phase5_plan_argv"
        ]

        self.assertIsInstance(
            plan[
                "argv"
            ],
            list,
        )

    def test_20_phase5_argv_contains_explicit_interface(self):
        argv = bound()[
            "phase5_plan_argv"
        ][
            "argv"
        ]

        index = argv.index(
            "--capture-interface"
        )

        self.assertEqual(
            argv[
                index + 1
            ],
            "example0",
        )

    def test_21_phase5_argv_contains_explicit_ports(self):
        argv = bound()[
            "phase5_plan_argv"
        ][
            "argv"
        ]

        self.assertIn(
            "25000",
            argv,
        )

        self.assertIn(
            "25001",
            argv,
        )

    def test_22_plan_not_executed(self):
        plan = bound()[
            "phase5_plan_argv"
        ]

        self.assertFalse(
            plan[
                "execution"
            ][
                "executed"
            ]
        )

    def test_23_real_health_truth_false(self):
        self.assertFalse(
            bound()[
                "scientific_boundary"
            ][
                "real_physical_health_truth"
            ]
        )

    def test_24_validation_closed(self):
        self.assertFalse(
            bound()[
                "scientific_boundary"
            ][
                "VALIDATION_open"
            ]
        )

    def test_25_confirmation_closed(self):
        self.assertFalse(
            bound()[
                "scientific_boundary"
            ][
                "CONFIRMATION_open"
            ]
        )

    def test_26_module_has_no_socket_or_subprocess_import(self):
        source = inspect.getsource(
            module
        )

        self.assertNotIn(
            "import socket",
            source,
        )

        self.assertNotIn(
            "import subprocess",
            source,
        )

    def test_27_no_verona_interface_hardcoded(self):
        source = inspect.getsource(
            module
        )

        self.assertNotIn(
            "157.27.31.126",
            source,
        )

        self.assertEqual(
            source.count(
                "eno1"
            ),
            1,
        )

        self.assertIn(
            "Do not assume eno1.",
            source,
        )

        checklist_source = inspect.getsource(
            module.operator_checklist_text
        )

        self.assertIn(
            "Do not assume eno1.",
            checklist_source,
        )

        production_without_warning = source.replace(
            "Do not assume eno1.",
            "",
        )

        self.assertNotIn(
            "eno1",
            production_without_warning,
        )

    def test_28_inventory_bundle_directory_written(self):
        payload = (
            build_inventory_only_bundle(
                inventory()
            )
        )

        with TemporaryDirectory() as temp:
            root = (
                Path(temp)
                / "bundle"
            )

            receipt = (
                write_portable_bundle_directory(
                    bundle_directory=
                        root,

                    payload=
                        payload,
                )
            )

            self.assertTrue(
                (
                    root
                    / "hardware_inventory.json"
                ).is_file()
            )

            self.assertTrue(
                (
                    root
                    / "runtime_input_template.json"
                ).is_file()
            )

            self.assertFalse(
                (
                    root
                    / "runtime_binding_candidate_v2.json"
                ).exists()
            )

            self.assertFalse(
                receipt[
                    "execution_authorization_generated"
                ]
            )

    def test_29_bound_bundle_directory_written(self):
        with TemporaryDirectory() as temp:
            root = (
                Path(temp)
                / "bundle"
            )

            write_portable_bundle_directory(
                bundle_directory=
                    root,

                payload=
                    bound(),
            )

            self.assertTrue(
                (
                    root
                    / "runtime_binding_candidate_v2.json"
                ).is_file()
            )

            self.assertTrue(
                (
                    root
                    / "phase5_plan_argv.json"
                ).is_file()
            )

    def test_30_bundle_directory_collision_rejected(self):
        with TemporaryDirectory() as temp:
            root = (
                Path(temp)
                / "bundle"
            )

            root.mkdir()

            with self.assertRaises(
                PortablePhysicalLidarCaptureBundleError
            ):
                write_portable_bundle_directory(
                    bundle_directory=
                        root,

                    payload=
                        build_inventory_only_bundle(
                            inventory()
                        ),
                )

    def test_31_bundle_content_digest_validates(self):
        payload = bound()

        self.assertEqual(
            payload[
                "content_sha256"
            ],
            content_sha256(
                payload
            ),
        )

        validate_portable_bundle(
            payload
        )

    def test_32_checklist_preserves_nominal_nonclaim(self):
        text = operator_checklist_text(
            bound()
        )

        self.assertIn(
            "NOT proven healthy",
            text,
        )

        self.assertIn(
            "creates no health label",
            text,
        )


if __name__ == "__main__":
    unittest.main()
