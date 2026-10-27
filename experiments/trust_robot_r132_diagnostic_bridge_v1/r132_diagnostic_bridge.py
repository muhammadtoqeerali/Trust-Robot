"""R132 diagnostic-only, aggregate-only R129 evidence boundary.
No health labels, factor measurements, pose, timing calibration or real admission.
"""
import hashlib, json

REPORT_PIN = "acdc86114f31e52990a14b74e0787db1fa2d1887dbbd9becd869c02596c838cb"
SCHEMA = "TRUST_ROBOT_R129_B1_AGGREGATE_DIAGNOSTICS_V1"
FEATURES = {
    **{f"/alphasense/cam{i}/image_raw": ("camera", f"cam{i}_sensor_frame",
        frozenset(("pixel_mean", "pixel_std", "zero_fraction", "max_fraction", "spatial_gradient"))) for i in range(5)},
    "/alphasense/imu": ("imu", "imu_sensor_frame", frozenset(("acceleration_norm", "angular_rate_norm", "acceleration_delta_norm", "angular_velocity_delta_norm"))),
    "/hesai/pandar": ("lidar", "PandarXT-32", frozenset(("point_count", "finite_xyz_fraction", "range_median", "range_p95"))),
}
CLOSED = ("groundtruth_accessed", "physical_clock_sync_proven", "independent_6dof_reference_proven",
          "dataset_partition_frozen", "training_performed", "health_labels_constructed",
          "metric_scoring_authorized", "real_factors_authorized", "m2dgr_confirmation_test_accessed")

class DiagnosticBoundaryError(RuntimeError):
    pass

def require(ok, reason):
    if not ok:
        raise DiagnosticBoundaryError("R132_DIAGNOSTIC_DENIED:" + reason)

def _structure(d):
    require(type(d) is dict and d.get("schema") == SCHEMA, "SCHEMA")
    require(d.get("dataset") == "Hilti-Oxford 2022" and d.get("recording") == "exp14_basement_2", "RECORDING")
    require(d.get("feature_scope") == "DESCRIPTIVE_AGGREGATES_ONLY", "EVIDENCE_ROLE")
    require(d.get("source_bag_sha256") == "18eea013076b8263ababf4f36eb68d331564a0a493262b006dc0dddc2aa85b82", "BAG_ID")
    require(d.get("decoded_messages") == 448 and d.get("sample_limit_per_topic") == 64, "BOUNDED_SAMPLE")
    s=d.get("scientific_boundary")
    require(type(s) is dict and all(s.get(k) is False for k in CLOSED), "CLOSED_SCIENCE")
    require(type(s.get("m2dgr_scientific_gates_closed")) is int and s["m2dgr_scientific_gates_closed"] == 11, "ELEVEN_GATES")
    rows=d.get("topics")
    require(type(rows) is dict and set(rows) == set(FEATURES), "TOPICS")
    for topic, (kind, frame, feature_keys) in FEATURES.items():
        row=rows[topic]
        require(type(row) is dict and row.get("modality") == kind and row.get("frame_ids") == [frame], "FRAME_OR_KIND")
        require(type(row.get("sample_count")) is int and row["sample_count"] == 64, "SAMPLE_COUNT")
        require(type(row.get("feature_statistics")) is dict and set(row["feature_statistics"]) == feature_keys, "FEATURE_SET")
    return True

def diagnostic_inventory(raw):
    require(type(raw) is bytes and hashlib.sha256(raw).hexdigest() == REPORT_PIN, "REPORT_INTEGRITY")
    d=json.loads(raw.decode("utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    _structure(d)
    return tuple((topic, FEATURES[topic][0], tuple(sorted(FEATURES[topic][2]))) for topic in sorted(FEATURES))

def require_real_factor(*args, **kwargs):
    raise DiagnosticBoundaryError("R132_DIAGNOSTIC_DENIED:REAL_FACTOR_ALWAYS_BLOCKED")

def require_health_label(*args, **kwargs):
    raise DiagnosticBoundaryError("R132_DIAGNOSTIC_DENIED:HEALTH_LABEL_ALWAYS_BLOCKED")
