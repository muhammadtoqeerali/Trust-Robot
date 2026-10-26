"""Portable R129-B3 sanitized handoff verifier. Stdlib only."""

import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BAG_SHA = "18eea013076b8263ababf4f36eb68d331564a0a493262b006dc0dddc2aa85b82"
B1_REPORT_SHA = "acdc86114f31e52990a14b74e0787db1fa2d1887dbbd9becd869c02596c838cb"
B1_MANIFEST_SHA = "1aa2789b33b99f94bfd5f7d494c33f27db2ccf00d9578ae39e6e61220d53ac5d"
B11_MAN_SHA = "3e2a701bbb685848b8237ab09001e07c82186d1d894abe70d12de5dd243c0ce7"

FILES = {
    "r129_b1_diagnostics.py",
    "r129_b1_aggregate_diagnostics_v1.json",
    "r129_b1_manifest_v1.json",
    "r129_b2_operator_result_record_v1.json",
    "SCIENTIFIC_SCOPE.md",
    "verify_handoff.py",
}

TOPICS = {
    **{
        f"/alphasense/cam{i}/image_raw": (
            "camera",
            {
                "pixel_mean", "pixel_std",
                "zero_fraction", "max_fraction",
                "spatial_gradient",
            },
        )
        for i in range(5)
    },
    "/alphasense/imu": (
        "imu",
        {
            "acceleration_norm", "angular_rate_norm",
            "acceleration_delta_norm",
            "angular_velocity_delta_norm",
        },
    ),
    "/hesai/pandar": (
        "lidar",
        {
            "point_count", "finite_xyz_fraction",
            "range_median", "range_p95",
        },
    ),
}


def need(ok, reason):
    if not ok:
        raise RuntimeError("R129_B3_DENIED:" + reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    path = ROOT / name
    need(
        path.is_file()
        and not path.is_symlink()
        and 0 < path.stat().st_size < 250000,
        "FILE:" + name,
    )
    return path.read_bytes()


def report_ok(d):
    if not isinstance(d, dict):
        return False

    scope = d.get("scientific_boundary", {})

    if not isinstance(scope, dict):
        return False

    if not (
        d.get("schema")
            == "TRUST_ROBOT_R129_B1_AGGREGATE_DIAGNOSTICS_V1"
        and d.get("source_bag_sha256") == BAG_SHA
        and d.get("source_b11_manifest_sha256") == B11_MAN_SHA
        and d.get("decoded_messages") == 448
        and d.get("sample_limit_per_topic") == 64
        and d.get("messages_examined") == 3831
        and d.get("decoded_raw_bytes") == 284093312
        and d.get("feature_scope") == "DESCRIPTIVE_AGGREGATES_ONLY"
        and d.get("synthetic_negative_controls_passed") == 6
        and isinstance(d.get("topics"), dict)
        and set(d["topics"]) == set(TOPICS)
        and all(
            scope.get(k) is False
            for k in (
                "groundtruth_accessed",
                "physical_clock_sync_proven",
                "independent_6dof_reference_proven",
                "dataset_partition_frozen",
                "training_performed",
                "health_labels_constructed",
                "metric_scoring_authorized",
                "real_factors_authorized",
                "m2dgr_confirmation_test_accessed",
            )
        )
        and scope.get("m2dgr_scientific_gates_closed") == 11
    ):
        return False

    for topic, (kind, keys) in TOPICS.items():
        row = d["topics"][topic]

        if not isinstance(row, dict):
            return False

        values = row.get("feature_statistics")

        if not (
            row.get("modality") == kind
            and row.get("sample_count") == 64
            and row.get("header_equals_bag_count") == 64
            and isinstance(row.get("frame_ids"), list)
            and len(row["frame_ids"]) == 1
            and isinstance(row["frame_ids"][0], str)
            and bool(row["frame_ids"][0])
            and isinstance(
                row.get("message_fingerprint_sha256"), str
            )
            and re.fullmatch(
                r"[0-9a-f]{64}",
                row["message_fingerprint_sha256"],
            )
            and row.get("median_interval_ns", 0) > 0
            and isinstance(values, dict)
            and set(values) == keys
        ):
            return False

        for name, item in values.items():
            if not isinstance(item, dict):
                return False

            if set(item) != {
                "finite_count", "min", "median", "max"
            }:
                return False

            max_count = (
                63
                if name in (
                    "acceleration_delta_norm",
                    "angular_velocity_delta_norm",
                )
                else 64
            )

            count = item["finite_count"]

            if (
                type(count) is not int
                or not 0 <= count <= max_count
            ):
                return False

            extrema = [item[k] for k in ("min", "median", "max")]

            if count == 0:
                if any(x is not None for x in extrema):
                    return False
            else:
                if not all(
                    type(x) in (int, float)
                    and x == x
                    and abs(x) != float("inf")
                    for x in extrema
                ):
                    return False

                if not extrema[0] <= extrema[1] <= extrema[2]:
                    return False

    return True


def witness_ok(d):
    return isinstance(d, dict) and (
        d.get("schema")
            == "TRUST_ROBOT_R129_B2_OPERATOR_OUTPUT_RECORD_V1"
        and d.get("evidence_basis")
            == "USER_POSTED_TERMINAL_OUTPUT_NOT_CRYPTOGRAPHICALLY_SEALED"
        and d.get("independent_replay_source_archived") is False
        and d.get("b1_report_sha256") == B1_REPORT_SHA
        and d.get("b1_manifest_sha256") == B1_MANIFEST_SHA
        and d.get("independently_decoded_messages") == 448
        and d.get("sensor_topics") == 7
        and d.get("message_fingerprints_matched") == 7
        and d.get("feature_families_reproduced") == 33
        and d.get("negative_controls_rejected") == 6
        and d.get("messages_examined") == 3831
        and d.get("decoded_raw_bytes") == 284093312
        and d.get("scoring_authorized") is False
        and d.get("m2dgr_gates_closed") == 11
    )


need(
    {p.name for p in ROOT.iterdir()}
    == FILES | {"manifest_v1.json"},
    "EXACT_FILE_SET",
)

m = json.loads(read("manifest_v1.json"))

need(
    m.get("schema")
    == "TRUST_ROBOT_R129_B3_SANITIZED_HANDOFF_MANIFEST_V1",
    "MANIFEST_SCHEMA",
)

need(
    m.get("source_bag_sha256") == BAG_SHA
    and m.get("b11_manifest_sha256") == B11_MAN_SHA
    and m.get("b1_report_sha256") == B1_REPORT_SHA
    and m.get("b1_manifest_sha256") == B1_MANIFEST_SHA,
    "SOURCE_LINEAGE",
)

need(
    m.get("raw_data_included") is False
    and m.get("groundtruth_included") is False
    and m.get("scoring_authorized") is False
    and m.get("m2dgr_gates_closed") == 11,
    "SCIENTIFIC_BOUNDARY",
)

need(
    isinstance(m.get("file_sha256"), dict)
    and set(m["file_sha256"]) == FILES,
    "MANIFEST_FILE_SET",
)

for name, expected in m["file_sha256"].items():
    need(
        isinstance(expected, str)
        and re.fullmatch(r"[0-9a-f]{64}", expected),
        "HASH_FORMAT:" + name,
    )
    need(sha(read(name)) == expected, "FILE_HASH:" + name)

need(
    sha(read("r129_b1_aggregate_diagnostics_v1.json"))
    == B1_REPORT_SHA,
    "B1_REPORT_HASH",
)
need(
    sha(read("r129_b1_manifest_v1.json"))
    == B1_MANIFEST_SHA,
    "B1_MANIFEST_HASH",
)

b1 = json.loads(
    read("r129_b1_aggregate_diagnostics_v1.json")
)
b1m = json.loads(read("r129_b1_manifest_v1.json"))
w = json.loads(
    read("r129_b2_operator_result_record_v1.json")
)

need(report_ok(b1), "B1_REPORT_STRUCTURE")
need(witness_ok(w), "B2_RESULT_RECORD")

need(
    sha(read("r129_b1_diagnostics.py"))
    == b1m["extractor_sha256"],
    "B1_EXTRACTOR_HASH",
)

need(
    b1m["report_sha256"] == B1_REPORT_SHA
    and b1m["source_b11_manifest_sha256"] == B11_MAN_SHA
    and b1m["source_bag_sha256"] == BAG_SHA,
    "B1_MANIFEST_LINEAGE",
)

need(
    b1m["report_negative_controls_passed"] == 3
    and b1m["synthetic_negative_controls_passed"] == 6
    and b1m["per_message_data_exported"] is False
    and b1m["groundtruth_included"] is False
    and b1m["scoring_authorized"] is False
    and b1m["m2dgr_scientific_gates_closed"] == 11,
    "B1_SCIENTIFIC_AND_TEST_SCOPE",
)

scope = read("SCIENTIFIC_SCOPE.md").decode("utf-8")
need(
    "not independently" in scope and "CLOSED" in scope,
    "SCOPE_DOCUMENT",
)

negatives = []

bad = copy.deepcopy(b1)
bad["source_bag_sha256"] = "0" * 64
negatives.append(not report_ok(bad))

bad = copy.deepcopy(b1)
del bad["topics"]["/hesai/pandar"]
negatives.append(not report_ok(bad))

bad = copy.deepcopy(b1)
bad["scientific_boundary"]["metric_scoring_authorized"] = True
negatives.append(not report_ok(bad))

bad = copy.deepcopy(b1)
bad["topics"]["/alphasense/imu"]["sample_count"] = 63
negatives.append(not report_ok(bad))

bad = copy.deepcopy(w)
bad["feature_families_reproduced"] = 32
negatives.append(not witness_ok(bad))

bad = copy.deepcopy(w)
bad["evidence_basis"] = "INDEPENDENTLY_SIGNED"
negatives.append(not witness_ok(bad))

need(
    len(negatives) == 6 and all(negatives),
    "NEGATIVE_CONTROLS",
)

print("R129_B3_VERIFY_SIX_FILE_HASHES=PASS")
print("R129_B3_VERIFY_B1_SOURCE_REPORT_MANIFEST=PASS")
print("R129_B3_VERIFY_B2_REPORTED_WITNESS_SCOPE=PASS")
print("R129_B3_VERIFY_NEGATIVE_CONTROLS=6_PASS")
print("R129_B3_VERIFY_SENSOR_TOPICS=7_PASS")
print("R129_B3_VERIFY_448_AGGREGATED_SAMPLES=PASS")
print("R129_B3_VERIFY_M2DGR_GATES=11_CLOSED")
print("R129_B3_STANDALONE_VERIFIER=PASS")
