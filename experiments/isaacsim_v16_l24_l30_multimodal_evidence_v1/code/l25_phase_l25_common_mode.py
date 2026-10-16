"""L25: anchored provenance and scripted-motion cross-witness challenge.

All replay/geometry substitutions are in memory. Scripted USD motion
and pinned history are not independent physical ground truth.
"""

import argparse
import copy
import hashlib
import io
import json
import math
import runpy

from pathlib import Path

import numpy as np

PAIRS = ((3, 4), (4, 5))
THRESHOLDS_M = (0.010, 0.020, 0.040)
STEPS = (51, 61, 71, 81, 91, 101)


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    sha(path)
    return json.loads(path.read_text())


def stable(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def npy_sha(xyz):
    data = io.BytesIO()

    np.save(
        data,
        np.asarray(xyz, dtype=np.float32),
        allow_pickle=False,
    )

    return hashlib.sha256(
        data.getvalue()
    ).hexdigest()


def pointset_sha(xyz):
    xyz = np.asarray(
        xyz,
        dtype=np.float32,
    )

    assert xyz.shape == (16, 3)

    order = np.lexsort((
        xyz[:, 2],
        xyz[:, 1],
        xyz[:, 0],
    ))

    data = np.ascontiguousarray(
        xyz[order]
    ).tobytes()

    return hashlib.sha256(data).hexdigest()


def beam_sha(xyz, order):
    arr = np.asarray(
        xyz,
        dtype=np.float32,
    )[order]

    assert arr.shape == (16, 3)

    return hashlib.sha256(
        np.ascontiguousarray(arr).tobytes()
    ).hexdigest()


def motion_pair(xyz, i, j, api, pose_rows, old):
    transform, rmse, _, err = api["register"](
        xyz[i],
        xyz[j],
    )

    previous_position = np.asarray(
        pose_rows[STEPS[i] - 1][
            "lidar_usd_world_position_m"
        ],
        dtype=float,
    )

    current_position = np.asarray(
        pose_rows[STEPS[j] - 1][
            "lidar_usd_world_position_m"
        ],
        dtype=float,
    )

    expected = float(np.linalg.norm(
        current_position - previous_position
    ))

    baseline_pose = api["matrix"](
        old["pose"]
    )

    baseline_m = float(np.linalg.norm(
        baseline_pose[:3, 3]
    ))

    baseline_abs = abs(
        baseline_m - expected
    )

    record = {
        "steps": [STEPS[i], STEPS[j]],

        "scripted_usd_translation_norm_m":
            expected,

        "frozen_baseline_translation_norm_m":
            baseline_m,

        "baseline_abs_norm_residual_m":
            baseline_abs,

        "scripted_usd_is_physical_ground_truth":
            False,
    }

    if transform is None:
        record.update(
            status="NOT_EVALUABLE",
            error=err,
            new_translation_norm_m=None,
            new_abs_norm_residual_m=None,
            excess_over_baseline_m=None,
            rotation_change_vs_frozen_baseline_deg=None,
        )

        return record

    difference = api["discrepancy"](
        baseline_pose,
        transform,
    )

    actual_m = float(np.linalg.norm(
        transform[:3, 3]
    ))

    actual_abs = abs(
        actual_m - expected
    )

    record.update(
        status="DIAGNOSTIC_AVAILABLE",
        error=None,
        new_translation_norm_m=actual_m,
        new_abs_norm_residual_m=actual_abs,
        excess_over_baseline_m=float(
            actual_abs - baseline_abs
        ),
        rotation_change_vs_frozen_baseline_deg=(
            difference["rotation_deg"]
        ),
        nearest_neighbor_rmse_m=rmse,
    )

    return record


def derive(
    original,
    orders,
    packets,
    pose_rows,
    l15,
    l23,
    api17,
    api23,
    api24,
):
    assert len(original) == len(orders) == len(packets) == 6

    baseline = {}

    for i, j in PAIRS:
        result = motion_pair(
            original,
            i,
            j,
            api17,
            pose_rows,
            l15["forward"][i],
        )

        assert result["status"] == (
            "DIAGNOSTIC_AVAILABLE"
        )

        assert abs(
            result["new_translation_norm_m"]
            - result["frozen_baseline_translation_norm_m"]
        ) < 1e-8

        baseline[(i, j)] = result

    prior = {
        x["scenario"]: x
        for x in l23["scenario_summaries"]
    }

    assert len(prior) == len(
        api23["SCENARIOS"]
    ) == 11

    scenarios = []

    for spec in api23["SCENARIOS"]:
        clouds, associations, description = (
            api23["build_case"](
                original,
                orders,
                spec,
            )
        )

        name = description["scenario"]

        assert (
            description["altered_clouds_sha256"]
            == prior[name]["altered_clouds_sha256"]
        )

        affected_step = int(
            description["affected_recorded_step"]
        )

        k = STEPS.index(affected_step)

        assert all(
            np.array_equal(original[n], clouds[n])
            for n in range(6)
            if n != k
        )

        assert not np.array_equal(
            original[k],
            clouds[k],
        )

        live = copy.deepcopy(packets)

        if name == "stale_scan_101_from_91":
            payload = packets[k - 1][
                "lidar_payload_sha256"
            ]
        else:
            payload = npy_sha(clouds[k])

        assert payload != packets[k][
            "lidar_payload_sha256"
        ]

        live[k]["lidar_payload_sha256"] = payload
        live[k]["lidar_claimed_sha256"] = payload

        pinned = api24["check"](
            live,
            packets,
            pinned=True,
        )

        sequence = api24["check"](
            live,
            packets,
            pinned=False,
        )

        assert pinned["decision"] == (
            "REVIEW_REQUIRED"
        )

        identical_pointset = (
            pointset_sha(clouds[k])
            == pointset_sha(original[k])
        )

        identical_beam = (
            beam_sha(clouds[k], associations[k])
            == beam_sha(original[k], orders[k])
        )

        if name == "point_order_changed_mapping_corrected":
            assert identical_pointset
            assert identical_beam

        if name == "point_order_changed_mapping_stale":
            assert identical_pointset
            assert not identical_beam

        if name == "stale_scan_101_from_91":
            assert sequence["decision"] == (
                "REVIEW_REQUIRED"
            )

        evidence = []

        for i, j in PAIRS:
            if k in (i, j):
                row = motion_pair(
                    clouds,
                    i,
                    j,
                    api17,
                    pose_rows,
                    l15["forward"][i],
                )

                evidence.append(row)

        assert evidence

        threshold_screen = {}

        for threshold in THRESHOLDS_M:
            threshold_screen[str(threshold)] = any(
                x["status"] == "NOT_EVALUABLE"
                or (
                    x["excess_over_baseline_m"] is not None
                    and x["excess_over_baseline_m"] > threshold
                )
                for x in evidence
            )

        scenarios.append({
            "scenario": name,
            "affected_step": affected_step,

            "l23_decision_changes":
                prior[name]["decision_changes"],

            "l23_not_flagged_count":
                prior[name]["not_flagged"],

            "pinned_recording_review":
                pinned["decision"] == "REVIEW_REQUIRED",

            "pinned_trigger_codes":
                pinned["trigger_codes"],

            "incoming_sequence_review":
                sequence["decision"] == "REVIEW_REQUIRED",

            "incoming_sequence_trigger_codes":
                sequence["trigger_codes"],

            "geometry_fingerprint_changed_from_archived_capture":
                not identical_pointset,

            "emitter_ordered_fingerprint_changed":
                not identical_beam,

            "scripted_usd_motion_comparisons":
                evidence,

            "scripted_motion_excess_threshold_reviews":
                threshold_screen,

            "frozen_reference_is_not_live_trust_anchor":
                True,

            "pose_factor_authorized":
                False,
        })

    assert len(scenarios) == 11

    camera_attack = api24["mutate"](
        "camera_payload_replay",
        packets,
        original[-1],
    )

    camera_baseline_duplicate = (
        packets[-1]["camera_payload_sha256"]
        == packets[-2]["camera_payload_sha256"]
    )

    camera_new_duplicate = (
        camera_attack[-1]["camera_payload_sha256"]
        == camera_attack[-2]["camera_payload_sha256"]
    )

    assert camera_new_duplicate

    camera_old_check = api24["check"](
        camera_attack,
        packets,
        pinned=False,
    )

    assert camera_old_check["decision"] == (
        "NOT_FLAGGED_DIAGNOSTIC_ONLY"
    )

    camera_summary = {
        "baseline_consecutive_identical_camera_content":
            camera_baseline_duplicate,

        "replay_consecutive_identical_camera_content":
            camera_new_duplicate,

        "new_exact_duplicate_camera_content_review":
            (
                not camera_baseline_duplicate
                and camera_new_duplicate
            ),

        "existing_l24_sequence_review":
            False,

        "duplicate_camera_content_is_proof_of_fault":
            False,
    }

    return {
        "scenario_summaries": scenarios,

        "camera_replay_content_control":
            camera_summary,

        "scenario_count": 11,

        "pinned_review_count": sum(
            x["pinned_recording_review"]
            for x in scenarios
        ),

        "incoming_sequence_review_count": sum(
            x["incoming_sequence_review"]
            for x in scenarios
        ),

        "geometry_fingerprint_changed_count": sum(
            x[
                "geometry_fingerprint_changed_from_archived_capture"
            ]
            for x in scenarios
        ),

        "emitter_ordered_fingerprint_changed_count": sum(
            x["emitter_ordered_fingerprint_changed"]
            for x in scenarios
        ),

        "scripted_motion_review_counts_by_threshold_m": {
            str(t): sum(
                x[
                    "scripted_motion_excess_threshold_reviews"
                ][str(t)]
                for x in scenarios
            )
            for t in THRESHOLDS_M
        },

        "all_transforms_in_memory": True,

        "all_frozen_report_pose_factors_unauthorized":
            True,
    }


def main():
    parser = argparse.ArgumentParser()

    for key in (
        "run", "l14", "l15", "l19",
        "l23", "l24", "s17", "s22",
        "s23", "s24", "out",
    ):
        parser.add_argument(
            "--" + key,
            required=True,
            type=Path,
        )

    a = parser.parse_args()

    assert a.run.is_dir() and not a.run.is_symlink()
    assert a.out.is_dir() and not a.out.is_symlink()

    l14, l15, l19, l23, l24 = [
        read_json(x)
        for x in (
            a.l14, a.l15, a.l19,
            a.l23, a.l24,
        )
    ]

    assert l15["upstream_l14_sha256"] == sha(a.l14)
    assert l23["upstream_sha256"]["l19"] == sha(a.l19)
    assert l24["l15_report_sha256"] == sha(a.l15)
    assert l24["l14_report_sha256"] == sha(a.l14)

    assert l24["implementation_sha256"] == sha(a.s24)
    assert l23["implementation_sha256"] == sha(a.s23)

    assert l23["reused_source_sha256"]["l22"] == sha(a.s22)
    assert l23["reused_source_sha256"]["l17"] == sha(a.s17)

    assert l24["challenge_count"] == 11
    assert l24["pinned_review_count"] == 11

    assert l23["total_pair_trials"] == 110
    assert l23["decision_changes"] == 5

    assert all(
        x["pose_factors_authorized"] == 0
        for x in (l14, l15, l19, l23, l24)
    )

    api17, api22, api23, api24 = [
        runpy.run_path(str(s))
        for s in (
            a.s17, a.s22, a.s23, a.s24,
        )
    ]

    original, orders, provenance = (
        api22["load_scans"](
            a.run,
            l15,
            l19,
        )
    )

    baseline_packets, context = (
        api24["recording"](
            a.run,
            l15,
            l14,
        )
    )

    assert api24["check"](
        baseline_packets,
        baseline_packets,
        pinned=True,
    )["trigger_codes"] == []

    poses = api24["jsonl"](
        a.run
        / "multimodal_probe_results_v15"
        / "base_pose_series_v15.jsonl"
    )

    assert len(poses) == 130

    first = derive(
        original,
        orders,
        baseline_packets,
        poses,
        l15,
        l23,
        api17,
        api23,
        api24,
    )

    second = derive(
        original,
        orders,
        baseline_packets,
        poses,
        l15,
        l23,
        api17,
        api23,
        api24,
    )

    assert stable(first) == stable(second)

    report = {
        "schema":
            "TRUST_ROBOT_L25_COMMON_MODE_CROSS_WITNESS_DIAGNOSTIC_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_report_sha256": {
            "l14": sha(a.l14),
            "l15": sha(a.l15),
            "l19": sha(a.l19),
            "l23": sha(a.l23),
            "l24": sha(a.l24),
        },

        "reused_source_sha256": {
            "l17": sha(a.s17),
            "l22": sha(a.s22),
            "l23": sha(a.s23),
            "l24": sha(a.s24),
        },

        "source_scan_provenance":
            provenance,

        "recording_context":
            context,

        "scripted_usd_motion_is_not_independent_ground_truth":
            True,

        "camera_content_repeat_is_not_proof_of_fault":
            True,

        "stored_capture_hash_is_not_live_sensor_authenticity":
            True,

        "motion_deviation_thresholds_exploratory_m":
            list(THRESHOLDS_M),

        "two_derivations_identical":
            True,

        "original_recordings_modified":
            False,

        "physical_exposure_sync_verified":
            False,

        "sensor_failure_detection_validated":
            False,

        "false_positive_rate_estimated":
            False,

        "false_negative_rate_estimated":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    output = (
        a.out
        / "l25_common_mode_cross_witness_diagnostic_v1.json"
    )

    with output.open("x") as file:
        json.dump(
            report,
            file,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )

        file.write("\n")

    for row in first["scenario_summaries"]:
        print(
            "L25_SCENARIO=",
            json.dumps({
                "scenario": row["scenario"],

                "pinned_review":
                    row["pinned_recording_review"],

                "sequence_review":
                    row["incoming_sequence_review"],

                "pointset_changed":
                    row[
                        "geometry_fingerprint_changed_from_archived_capture"
                    ],

                "emitter_ordered_changed":
                    row[
                        "emitter_ordered_fingerprint_changed"
                    ],

                "scripted_motion_threshold_flags":
                    row[
                        "scripted_motion_excess_threshold_reviews"
                    ],

                "l23_decision_changes":
                    row["l23_decision_changes"],
            }, sort_keys=True),
            flush=True,
        )

    print(
        "L25_CAMERA_REPLAY_CONTROL=",
        json.dumps(
            first["camera_replay_content_control"],
            sort_keys=True,
        ),
        flush=True,
    )

    print(
        "L25_MOTION_THRESHOLD_COUNTS=",
        json.dumps(
            first[
                "scripted_motion_review_counts_by_threshold_m"
            ],
            sort_keys=True,
        ),
        flush=True,
    )

    print(
        "L25_PINNED_REVIEW_COUNT=",
        first["pinned_review_count"],
    )

    print(
        "L25_SEQUENCE_REVIEW_COUNT=",
        first["incoming_sequence_review_count"],
    )

    print("L25_DETERMINISTIC_REDERIVATION=PASS")
    print("L25_COMMON_MODE_AUDIT=PASS")
    print("QUALIFIED_POSE_FACTORS=0")
    print("L25_REPORT_SHA256=", sha(output))


if __name__ == "__main__":
    main()
