import copy
import json
from pathlib import Path
import unittest

from trust_robot.resource_evaluation import (
    Phase13Lifecycle,
    ResourceEvaluationContractError,
    assert_resource_claim_authorized,
    assert_resource_measurement_authorized,
    cost_views,
    required_measurement_metadata,
    resource_evidence_families,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase13_resource_evaluation_contract_candidate_v1.json"
)


class TestResourceEvaluationContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload["schema"],
            "TRUST_ROBOT_PHASE13_RESOURCE_EVALUATION_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload["lifecycle_status"],
            Phase13Lifecycle
            .CONTRACT_IMPLEMENTED_MEASUREMENT_POLICY_UNSELECTED
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "phase"
            ],
            13,
        )

    def test_04_scope(self):
        self.assertEqual(
            self.payload[
                "phase_scope"
            ][
                "name"
            ],
            "resource_evaluation",
        )

    def test_05_resource_family_separate(self):
        boundary = self.payload[
            "evaluation_family_boundary"
        ]

        self.assertTrue(
            boundary[
                "resource_evidence_is_separate_evaluation_family"
            ]
        )

        self.assertFalse(
            boundary[
                "may_be_collapsed_into_undocumented_aggregate_score"
            ]
        )

    def test_06_two_cost_views(self):
        self.assertEqual(
            cost_views(),
            (
                "complete_system_cost",
                "incremental_trust_layer_overhead",
            ),
        )

    def test_07_cost_view_count(self):
        self.assertEqual(
            self.payload[
                "cost_views"
            ][
                "required_count"
            ],
            2,
        )

    def test_08_cost_measurements_unavailable(self):
        views = self.payload[
            "cost_views"
        ]

        self.assertFalse(
            views[
                "complete_system_cost_measurement_available"
            ]
        )

        self.assertFalse(
            views[
                "incremental_trust_layer_overhead_measurement_available"
            ]
        )

    def test_09_ten_resource_evidence_families(self):
        self.assertEqual(
            len(
                resource_evidence_families()
            ),
            10,
        )

    def test_10_resource_evidence_exact(self):
        self.assertEqual(
            resource_evidence_families(),
            (
                "mean_latency",
                "p95_latency",
                "deadline_misses",
                "throughput",
                "processor_utilization_where_measurable",
                "peak_memory",
                "storage",
                "average_power",
                "peak_power",
                "energy_per_update_or_trajectory",
            ),
        )

    def test_11_evidence_names_are_not_measurements(self):
        schema = self.payload[
            "resource_evidence_schema"
        ]

        self.assertFalse(
            schema[
                "families_are_measurement_results"
            ]
        )

        self.assertTrue(
            schema[
                "families_define_required_future_evidence"
            ]
        )

    def test_12_processor_utilization_conditional(self):
        self.assertTrue(
            self.payload[
                "resource_evidence_schema"
            ][
                "processor_utilization_is_conditional_where_measurable"
            ]
        )

    def test_13_seven_metadata_fields(self):
        self.assertEqual(
            len(
                required_measurement_metadata()
            ),
            7,
        )

    def test_14_metadata_exact(self):
        self.assertEqual(
            required_measurement_metadata(),
            (
                "hardware_versions",
                "software_versions",
                "power_clock_mode",
                "sensor_rates",
                "estimator_window_size",
                "warmup_policy",
                "measurement_method",
            ),
        )

    def test_15_metadata_values_not_frozen(self):
        self.assertFalse(
            self.payload[
                "measurement_metadata_schema"
            ][
                "values_currently_frozen"
            ]
        )

    def test_16_latency_definition_unselected(self):
        boundary = self.payload[
            "measurement_policy_boundary"
        ]

        self.assertIsNone(
            boundary[
                "exact_latency_definition"
            ]
        )

        self.assertFalse(
            boundary[
                "exact_latency_definition_selected"
            ]
        )

    def test_17_clock_unselected(self):
        boundary = self.payload[
            "measurement_policy_boundary"
        ]

        self.assertIsNone(
            boundary[
                "timing_clock_source"
            ]
        )

        self.assertFalse(
            boundary[
                "timing_clock_source_selected"
            ]
        )

    def test_18_deadline_unselected(self):
        boundary = self.payload[
            "measurement_policy_boundary"
        ]

        self.assertIsNone(
            boundary[
                "deadline_definition"
            ]
        )

        self.assertFalse(
            boundary[
                "deadline_definition_selected"
            ]
        )

    def test_19_throughput_unselected(self):
        boundary = self.payload[
            "measurement_policy_boundary"
        ]

        self.assertIsNone(
            boundary[
                "throughput_definition"
            ]
        )

        self.assertFalse(
            boundary[
                "throughput_definition_selected"
            ]
        )

    def test_20_processor_metric_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "processor_utilization_measurement_selected"
            ]
        )

    def test_21_memory_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "peak_memory_measurement_selected"
            ]
        )

    def test_22_storage_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "storage_scope_selected"
            ]
        )

    def test_23_power_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "power_measurement_method_selected"
            ]
        )

    def test_24_energy_unselected(self):
        boundary = self.payload[
            "measurement_policy_boundary"
        ]

        self.assertFalse(
            boundary[
                "energy_measurement_method_selected"
            ]
        )

        self.assertFalse(
            boundary[
                "energy_unit_scope_update_vs_trajectory_selected"
            ]
        )

    def test_25_warmup_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "warmup_policy_selected"
            ]
        )

    def test_26_repetition_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "repetition_policy_selected"
            ]
        )

    def test_27_aggregation_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "aggregation_policy_selected"
            ]
        )

    def test_28_cpu_gpu_specific_metrics_unselected(self):
        boundary = self.payload[
            "measurement_policy_boundary"
        ]

        self.assertFalse(
            boundary[
                "cpu_specific_metric_selected"
            ]
        )

        self.assertFalse(
            boundary[
                "gpu_specific_metric_selected"
            ]
        )

    def test_29_realtime_threshold_unselected(self):
        self.assertFalse(
            self.payload[
                "measurement_policy_boundary"
            ][
                "real_time_acceptance_threshold_selected"
            ]
        )

    def test_30_environment_unfrozen(self):
        boundary = self.payload[
            "measurement_environment_boundary"
        ]

        for key, value in boundary.items():
            if key.endswith(
                "_frozen"
            ):
                self.assertFalse(
                    value
                )
            else:
                self.assertIsNone(
                    value
                )

    def test_31_historical_protocol_not_phase13(self):
        boundary = self.payload[
            "historical_resource_reuse_boundary"
        ]

        self.assertTrue(
            boundary[
                "historical_protocol_exists"
            ]
        )

        self.assertFalse(
            boundary[
                "historical_protocol_is_TRUST_ROBOT_phase13_protocol"
            ]
        )

    def test_32_historical_numeric_policy_not_adopted(self):
        boundary = self.payload[
            "historical_resource_reuse_boundary"
        ]

        for key in (
            "historical_numeric_latency_targets_adopted",
            "historical_warmup_iteration_count_adopted",
            "historical_repetition_count_adopted",
            "historical_latency_clock_method_adopted",
            "historical_median_primary_statistic_adopted",
            "historical_rss_method_adopted",
            "historical_tracemalloc_method_adopted",
            "historical_project_latency_targets_adopted",
        ):
            self.assertFalse(
                boundary[
                    key
                ]
            )

    def test_33_historical_results_not_adopted(self):
        boundary = self.payload[
            "historical_resource_reuse_boundary"
        ]

        self.assertFalse(
            boundary[
                "historical_reference_host_results_adopted"
            ]
        )

        self.assertFalse(
            boundary[
                "historical_stm32_claims_adopted"
            ]
        )

        self.assertFalse(
            boundary[
                "legacy_IMU_HAR_resource_semantics_adopted"
            ]
        )

    def test_34_legacy_instrumentation_requires_explicit_binding(self):
        self.assertTrue(
            self.payload[
                "historical_resource_reuse_boundary"
            ][
                "legacy_instrumentation_may_inform_future_engineering_implementation_only_after_explicit_phase13_binding"
            ]
        )

    def test_35_host_not_target_evidence(self):
        boundary = self.payload[
            "platform_claim_boundary"
        ]

        self.assertFalse(
            boundary[
                "reference_host_measurement_equals_onboard_robot_measurement"
            ]
        )

        self.assertFalse(
            boundary[
                "reference_host_measurement_equals_stm32_measurement"
            ]
        )

        self.assertFalse(
            boundary[
                "host_python_or_native_measurement_may_be_relabelled_as_stm32"
            ]
        )

    def test_36_target_claim_requires_target_measurement(self):
        boundary = self.payload[
            "platform_claim_boundary"
        ]

        self.assertTrue(
            boundary[
                "target_specific_resource_claim_requires_target_specific_measurement"
            ]
        )

        self.assertTrue(
            boundary[
                "onboard_robot_resource_claim_requires_onboard_robot_measurement"
            ]
        )

    def test_37_rq4_resource_unanswered(self):
        boundary = self.payload[
            "rq4_boundary"
        ]

        self.assertTrue(
            boundary[
                "resource_component_in_phase13"
            ]
        )

        self.assertTrue(
            boundary[
                "closed_loop_safety_component_deferred_to_phase14"
            ]
        )

        self.assertFalse(
            boundary[
                "resource_answer_available"
            ]
        )

    def test_38_measurement_guard_raises(self):
        with self.assertRaises(
            ResourceEvaluationContractError
        ):
            assert_resource_measurement_authorized()

    def test_39_claim_guard_raises(self):
        with self.assertRaises(
            ResourceEvaluationContractError
        ):
            assert_resource_claim_authorized()

    def test_40_manifest_validates_and_mutation_rejected(self):
        validate_contract_manifest(
            self.payload
        )

        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "measurement_policy_boundary"
        ][
            "timing_clock_source"
        ] = "time.perf_counter_ns"

        modified[
            "measurement_policy_boundary"
        ][
            "timing_clock_source_selected"
        ] = True

        with self.assertRaises(
            ResourceEvaluationContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
