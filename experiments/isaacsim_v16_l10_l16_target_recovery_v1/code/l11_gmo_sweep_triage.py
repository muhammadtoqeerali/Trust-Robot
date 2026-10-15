"""L11: inspect existing GMO per-step sweep and spherical returns.

Offline engineering audit only. No qualified exposure timing,
calibrated sensor uncertainty, health labels or pose factors.
"""

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

STEPS = [51, 61, 71, 81, 91, 101]
EXPECTED = [16, 16, 16, 16, 16, 2]

SCENE_SHA = (
    "08d7f96b249e56cf53a53593b4f7e09cfe3c5e37b08b06a6361403438888c4b0"
)

L10_SHA = (
    "f1f20e7ad8cb2d93bc91437bb4e94800ae706603824712362d8d7259774086bb"
)


def sha(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    sha(path)
    return json.loads(path.read_text())


def log_rows(path, marker):
    rows = {}

    with path.open(errors="replace") as stream:
        for line in stream:
            token = marker + " "

            if token not in line:
                continue

            row = json.loads(
                line.split(token, 1)[1].strip()
            )

            step = int(row["step"])

            assert 1 <= step <= 130
            assert step not in rows

            rows[step] = row

    return rows


def configured_angles(scene):
    assert sha(scene) == SCENE_SHA

    text = scene.read_text()
    values = []

    for field in ("azimuthDeg", "elevationDeg"):
        match = re.search(
            r"emitterState:s001:"
            + field
            + r"\s*=\s*\[([^]]+)\]",
            text,
        )

        assert match is not None

        array = np.array([
            float(value)
            for value in match.group(1).split(",")
        ])

        assert len(array) == 16
        assert np.isfinite(array).all()

        values.append(array)

    return np.stack(values, axis=1)


def inspect_spherical(run, expected, beam_angles):
    step = expected["step"]

    path = (
        run / "pre_gmo_samples_v1"
        / f"gmo_pre_step_{step:03d}.npz"
    )

    assert sha(path) == expected[
        "pre_gmo_file_sha256"
    ]

    with np.load(
        path,
        allow_pickle=False,
    ) as raw:
        azimuth = np.asarray(
            raw["x"], dtype=np.float64
        )

        elevation = np.asarray(
            raw["y"], dtype=np.float64
        )

        distance = np.asarray(
            raw["z"], dtype=np.float64
        )

        frame_id = int(raw["frame_id"][0])
        timestamp = int(raw["timestamp_ns"][0])

    assert (
        len(azimuth)
        == len(elevation)
        == len(distance)
        == expected["gmo_raw_elements"]
    )

    assert frame_id == expected["frame_id"]
    assert timestamp == expected["timestamp_ns"]

    assert np.isfinite(azimuth).all()
    assert np.isfinite(elevation).all()
    assert np.isfinite(distance).all()

    assert np.all(distance > 0)

    returns = []

    for az, el, length in zip(
        azimuth,
        elevation,
        distance,
    ):
        differences = np.linalg.norm(
            beam_angles - np.array([az, el]),
            axis=1,
        )

        closest = int(
            np.argmin(differences)
        )

        returns.append({
            "reported_azimuth_deg": float(az),
            "reported_elevation_deg": float(el),
            "reported_range_m": float(length),

            "nearest_configured_beam_index_not_verified_emitter_id":
                closest,

            "angular_discrepancy_deg":
                float(differences[closest]),

            "sensor_forward_component_m":
                float(
                    length
                    * math.cos(math.radians(el))
                    * math.cos(math.radians(az))
                ),
        })

    return returns


def derive(run, logpath, l10):
    sweep = log_rows(
        logpath,
        "GMO_SWEEP_ROW",
    )

    snapshots = log_rows(
        logpath,
        "PRE_GMO_SNAPSHOT",
    )

    assert sorted(sweep) == list(
        range(1, 131)
    )

    assert all(
        step in snapshots
        for step in STEPS
    )

    assert [
        x["step"]
        for x in l10["candidate_raw_gmo"]
    ] == STEPS

    assert [
        x["step"]
        for x in l10["candidate"]
    ] == STEPS

    beam_angles = configured_angles(
        run / "multimodal_scene_v5.usda"
    )

    timeline = []
    transitions = []

    previous = None

    for step in range(1, 131):
        row = sweep[step]

        count = (
            int(row["num_elements"])
            if row["num_elements"] is not None
            else None
        )

        entry = {
            "step": step,
            "state": row["state"],
            "raw_element_count": count,

            "frame_id": (
                int(row["frame_id"])
                if row.get("frame_id") is not None
                else None
            ),

            "gmo_timestamp_ns_unqualified": (
                int(row["timestamp_ns"])
                if row.get("timestamp_ns") is not None
                else None
            ),
        }

        timeline.append(entry)

        if (
            previous is not None
            and previous["raw_element_count"] != count
        ):
            transitions.append({
                "step": step,

                "prior_count":
                    previous["raw_element_count"],

                "new_count": count,
            })

        previous = entry

    selected = []

    for row, capture in zip(
        l10["candidate_raw_gmo"],
        l10["candidate"],
    ):
        step = row["step"]
        saved = snapshots[step]

        assert int(
            saved["num_elements"]
        ) == row["gmo_raw_elements"]

        assert int(
            saved["valid_elements"]
        ) == row["gmo_valid_elements"]

        assert int(
            saved["frame_id"]
        ) == capture["frame_id"]

        assert int(
            saved["timestamp_ns"]
        ) == capture["timestamp_ns"]

        assert capture[
            "front_cube_ray_intersections_predicted"
        ] == 16

        current = timeline[step - 1]

        selected.append({
            "step": step,

            "pre_gmo_raw_count":
                int(saved["num_elements"]),

            "pre_gmo_valid_count":
                int(saved["valid_elements"]),

            "sweep_state":
                current["state"],

            "sweep_raw_count":
                current["raw_element_count"],

            "sweep_agrees_with_pre_snapshot":
                current["raw_element_count"]
                == int(saved["num_elements"]),

            "front_cube_analytic_ray_hits":
                16,

            "analytic_min_target_distance_m":
                capture[
                    "minimum_predicted_distance_m"
                ],

            "analytic_max_target_distance_m":
                capture[
                    "maximum_predicted_distance_m"
                ],
        })

    assert [
        row["pre_gmo_raw_count"]
        for row in selected
    ] == EXPECTED

    saved_lookup = {
        row["step"]: row
        for row in l10["candidate_raw_gmo"]
    }

    details = {}

    for step in (91, 101):
        row = saved_lookup[step]

        capture = l10["candidate"][
            STEPS.index(step)
        ]

        expected = {
            "step": step,

            "pre_gmo_file_sha256":
                row["pre_gmo_file_sha256"],

            "gmo_raw_elements":
                row["gmo_raw_elements"],

            "frame_id":
                capture["frame_id"],

            "timestamp_ns":
                capture["timestamp_ns"],
        }

        details[str(step)] = inspect_spherical(
            run,
            expected,
            beam_angles,
        )

    first_drop = next(
        (
            event
            for event in transitions
            if (
                event["step"] > 91
                and event["new_count"] is not None
                and event["new_count"] < 16
            )
        ),
        None,
    )

    return {
        "per_step_gmo_sweep": timeline,
        "raw_count_change_events": transitions,

        "selected_capture_crosscheck":
            selected,

        "spherical_raw_return_details_step_91_and_101":
            details,

        "first_logged_raw_drop_after_step_91":
            first_drop,
    }


def main():
    assert len(sys.argv) == 5

    run, logfile, l10path, out = map(
        Path, sys.argv[1:]
    )

    assert run.is_dir() and not run.is_symlink()
    assert out.is_dir() and not out.is_symlink()

    assert sha(l10path) == L10_SHA

    l10 = load(l10path)

    assert sha(logfile) == l10[
        "candidate_log_sha256"
    ]

    assert l10[
        "candidate_last_frame_raw_element_count"
    ] == 2

    assert l10[
        "candidate_last_frame_valid_element_count"
    ] == 2

    assert l10[
        "candidate_last_frame_model_ray_hits"
    ] == 16

    assert l10[
        "missing_return_cause_conclusively_identified"
    ] is False

    first = derive(
        run, logfile, l10
    )

    second = derive(
        run, logfile, l10
    )

    assert json.dumps(
        first,
        sort_keys=True,
        allow_nan=False,
    ) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )

    report = {
        "schema":
            "TRUST_ROBOT_L11_EXISTING_GMO_SWEEP_TRIAGE_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_l10_sha256":
            sha(l10path),

        "upstream_runtime_log_sha256":
            sha(logfile),

        "repeated_derivation_identical": True,

        "offline_existing_recordings_only": True,

        "physical_sensor_timing_verified": False,

        "actual_per_emitter_identity_verified": False,

        "analytic_geometry_is_not_RTX_measurement":
            True,

        "missing_return_cause_conclusively_identified":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    target = (
        out / "l11_existing_gmo_sweep_triage_v1.json"
    )

    with target.open("x") as stream:
        json.dump(
            report,
            stream,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        stream.write("\n")

    for row in report[
        "selected_capture_crosscheck"
    ]:
        print(
            "L11_SELECTED=",
            json.dumps(row, sort_keys=True),
            flush=True,
        )

    for event in report[
        "raw_count_change_events"
    ]:
        if event["step"] >= 86:
            print(
                "L11_COUNT_TRANSITION=",
                json.dumps(event, sort_keys=True),
                flush=True,
            )

    for step in (91, 101):
        print(
            f"L11_RETURN_ANGLES_STEP_{step}=",
            json.dumps(
                report[
                    "spherical_raw_return_details_step_91_and_101"
                ][str(step)],
                sort_keys=True,
            ),
            flush=True,
        )

    print("L11_LAST_FRAME_RAW_COUNT=2")
    print("L11_LAST_FRAME_INVALID_FILTERED=0")
    print("L11_ANALYTIC_FRONT_CUBE_HITS=16")

    print(
        "L11_FIRST_LOGGED_DROP_AFTER_91=",
        report[
            "first_logged_raw_drop_after_step_91"
        ],
    )

    print("L11_REDERIVATION=PASS")
    print("L11_OFFLINE_SWEEP_TRIAGE=PASS")

    print(
        "L11_REPORT_SHA256=",
        sha(target),
    )


if __name__ == "__main__":
    main()
