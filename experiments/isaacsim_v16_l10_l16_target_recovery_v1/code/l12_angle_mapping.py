"""L12: GMO azimuth convention and endpoint-return timeline.

Synthetic engineering diagnostics only. Elevation-based association
does not constitute verified physical emitter identity.
"""

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

SCENE_SHA = (
    "08d7f96b249e56cf53a53593b4f7e09cfe3c5e37b08b06a6361403438888c4b0"
)

L10_SHA = (
    "f1f20e7ad8cb2d93bc91437bb4e94800ae706603824712362d8d7259774086bb"
)

L11_SHA = (
    "3cd034389160c80f1ce1d57d499cecb3b8c3d20117ec2366d5d0550b20dcbaa2"
)

SELECTED = (51, 61, 71, 81, 91, 101)
WINDOW = tuple(range(88, 111))


def sha(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    sha(path)
    return json.loads(path.read_text())


def canon(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def parse_angles(path):
    assert sha(path) == SCENE_SHA

    text = path.read_text()
    fields = []

    for key in ("azimuthDeg", "elevationDeg"):
        match = re.search(
            r"emitterState:s001:"
            + key
            + r"\s*=\s*\[([^]]+)\]",
            text,
        )

        assert match is not None

        values = np.array([
            float(v)
            for v in match.group(1).split(",")
        ])

        assert values.shape == (16,)
        assert np.isfinite(values).all()

        fields.append(values)

    assert len(set(fields[1])) == 16

    assert (
        "omni:sensor:Core:nearRangeM = 0.2"
        in text
    )

    assert (
        "omni:sensor:Core:farRangeM = 10"
        in text
    )

    return fields


def parse_log(path):
    sweeps = {}
    snapshots = {}

    with path.open(errors="replace") as stream:
        for line in stream:
            for marker, destination in (
                ("GMO_SWEEP_ROW ", sweeps),
                ("PRE_GMO_SNAPSHOT ", snapshots),
            ):
                if marker not in line:
                    continue

                row = json.loads(
                    line.split(marker, 1)[1].strip()
                )

                step = int(row["step"])

                assert step not in destination

                destination[step] = row

    assert sorted(sweeps) == list(
        range(1, 131)
    )

    assert all(
        step in snapshots
        for step in SELECTED
    )

    return sweeps, snapshots


def raw_angles(
    run,
    step,
    l10_row,
    l11_rows,
    az,
    el,
    sensor_x,
):
    filename = (
        run / "pre_gmo_samples_v1"
        / f"gmo_pre_step_{step:03d}.npz"
    )

    assert sha(filename) == l10_row[
        "pre_gmo_file_sha256"
    ]

    with np.load(
        filename,
        allow_pickle=False,
    ) as raw:
        a = np.asarray(raw["x"], dtype=float)
        e = np.asarray(raw["y"], dtype=float)
        dist = np.asarray(raw["z"], dtype=float)

    assert (
        len(a)
        == len(e)
        == len(dist)
        == l10_row["gmo_raw_elements"]
    )

    assert len(l11_rows) == len(a)

    for array in (a, e, dist):
        assert np.isfinite(array).all()

    assert np.all(dist > 0)

    selected = []

    for i, (aa, ee, rr) in enumerate(
        zip(a, e, dist)
    ):
        assert float(aa) == l11_rows[i][
            "reported_azimuth_deg"
        ]

        assert float(ee) == l11_rows[i][
            "reported_elevation_deg"
        ]

        assert float(rr) == l11_rows[i][
            "reported_range_m"
        ]

        # Associate by unique configured elevation.
        # This is a geometric hypothesis, not a
        # verified physical emitter identifier.

        idx = int(
            np.argmin(np.abs(el - ee))
        )

        el_err = float(
            abs(el[idx] - ee)
        )

        flipped_err = float(
            abs(-az[idx] - aa)
        )

        direct_err = float(
            abs(az[idx] - aa)
        )

        assert el_err < 0.05
        assert flipped_err < 0.05

        forward = float(
            rr
            * math.cos(math.radians(ee))
            * math.cos(math.radians(aa))
        )

        selected.append({
            "record_index": i,

            "associated_configured_index_not_verified_emitter_id":
                idx,

            "observed_azimuth_deg":
                float(aa),

            "configured_azimuth_deg":
                float(az[idx]),

            "inverted_azimuth_residual_deg":
                flipped_err,

            "direct_azimuth_residual_deg":
                direct_err,

            "elevation_residual_deg":
                el_err,

            "range_m":
                float(rr),

            "observed_sensor_forward_m":
                forward,

            "forward_residual_from_scripted_front_face_m":
                forward - (1.25 - sensor_x),
        })

    indices = [
        row[
            "associated_configured_index_not_verified_emitter_id"
        ]
        for row in selected
    ]

    assert len(set(indices)) == len(indices)

    if step == 91:
        assert indices == list(range(16))

    if step == 101:
        assert indices == [0, 15]

    return {
        "step": step,

        "association_inferred_not_verified":
            True,

        "azimuth_sign_inversion_supported":
            True,

        "associated_indices":
            indices,

        "maximum_inverted_azimuth_residual_deg":
            max(
                x["inverted_azimuth_residual_deg"]
                for x in selected
            ),

        "maximum_elevation_residual_deg":
            max(
                x["elevation_residual_deg"]
                for x in selected
            ),

        "returns":
            selected,
    }


def derive(run, logfile, l10, l11):
    az, el = parse_angles(
        run / "multimodal_scene_v5.usda"
    )

    sweeps, snapshots = parse_log(logfile)

    assert l11[
        "upstream_l10_sha256"
    ] == L10_SHA

    assert l11[
        "upstream_runtime_log_sha256"
    ] == sha(logfile)

    assert l10[
        "candidate_log_sha256"
    ] == sha(logfile)

    assert len(
        l11["per_step_gmo_sweep"]
    ) == 130

    for i, stored in enumerate(
        l11["per_step_gmo_sweep"], 1
    ):
        actual = sweeps[i]

        assert stored["step"] == i

        assert stored["state"] == actual["state"]

        assert stored[
            "raw_element_count"
        ] == actual.get("num_elements")

        assert stored[
            "frame_id"
        ] == actual.get("frame_id")

        assert stored[
            "gmo_timestamp_ns_unqualified"
        ] == actual.get("timestamp_ns")

    poses_path = (
        run / "multimodal_probe_results_v15"
        / "base_pose_series_v15.jsonl"
    )

    sha(poses_path)

    poses = [
        json.loads(line)
        for line in poses_path.read_text().splitlines()
        if line.strip()
    ]

    assert len(poses) == 130

    assert [
        row["step"] for row in poses
    ] == list(range(1, 131))

    assert len(
        l11["selected_capture_crosscheck"]
    ) == 6

    timeline = []

    for step in WINDOW:
        row = sweeps[step]

        pose = np.asarray(
            poses[step - 1][
                "lidar_usd_world_position_m"
            ],
            dtype=float,
        )

        assert pose.shape == (3,)
        assert np.isfinite(pose).all()

        assert abs(pose[1]) < 1e-5
        assert abs(pose[2] - 0.525) < 1e-5

        front_dx = (
            1.25 - float(pose[0])
        )

        # Analytic front-cube plane geometry,
        # NOT per-beam RTX return evidence.

        ray_distances = [
            front_dx / (
                math.cos(math.radians(float(e)))
                * math.cos(math.radians(float(a)))
            )
            for a, e in zip(az, el)
        ]

        assert all(
            0.2 <= distance <= 10.0
            for distance in ray_distances
        )

        for a, e in zip(az, el):
            y = (
                pose[1]
                + front_dx
                * math.tan(math.radians(float(a)))
            )

            z = (
                pose[2]
                + front_dx
                * math.tan(math.radians(float(e)))
                / math.cos(math.radians(float(a)))
            )

            assert -0.75 <= y <= 0.75
            assert 0 <= z <= 1.5

        previous = sweeps.get(
            step - 1, {}
        )

        current_stamp = row.get(
            "timestamp_ns"
        )

        previous_stamp = previous.get(
            "timestamp_ns"
        )

        current_frame = row.get(
            "frame_id"
        )

        previous_frame = previous.get(
            "frame_id"
        )

        timeline.append({
            "step": step,

            "gmo_state":
                row["state"],

            "gmo_element_count":
                row.get("num_elements"),

            "gmo_frame_id":
                current_frame,

            "gmo_timestamp_ns_unqualified":
                current_stamp,

            "same_frame_id_as_previous":
                (
                    current_frame == previous_frame
                    if (
                        current_frame is not None
                        and previous_frame is not None
                    )
                    else None
                ),

            "gmo_timestamp_delta_from_previous_s":
                (
                    (current_stamp - previous_stamp)
                    * 1e-9
                    if (
                        current_stamp is not None
                        and previous_stamp is not None
                    )
                    else None
                ),

            "scripted_sensor_world_x_m":
                float(pose[0]),

            "analytic_front_face_distance_m":
                front_dx,

            "analytic_intersections":
                16,

            "analytic_min_range_m":
                float(min(ray_distances)),

            "analytic_max_range_m":
                float(max(ray_distances)),

            "analytic_near_range_margin_m":
                float(min(ray_distances) - 0.2),
        })

    expected_counts = [
        16, 0, 16, 14, 11, 10, 7,
        6, 5, 4, 2, 0, 2, 0
    ]

    assert [
        sweeps[step].get("num_elements")
        for step in range(91, 105)
    ] == expected_counts

    mapping = {}

    lookup = {
        row["step"]: row
        for row in l10["candidate_raw_gmo"]
    }

    for step in (91, 101):
        row = lookup[step]

        assert snapshots[step][
            "num_elements"
        ] == row["gmo_raw_elements"]

        assert snapshots[step][
            "valid_elements"
        ] == row["gmo_valid_elements"]

        assert sweeps[step][
            "num_elements"
        ] == row["gmo_raw_elements"]

        mapping[str(step)] = raw_angles(
            run,
            step,
            row,
            l11[
                "spherical_raw_return_details_step_91_and_101"
            ][str(step)],
            az,
            el,
            float(
                poses[step - 1][
                    "lidar_usd_world_position_m"
                ][0]
            ),
        )

    return {
        "timeline_steps_88_to_110":
            timeline,

        "azimuth_mapping_steps_91_and_101":
            mapping,

        "last_frame_associated_indices":
            mapping["101"]["associated_indices"],

        "last_frame_raw_returns":
            2,

        "last_frame_analytic_intersections":
            16,
    }


def main():
    assert len(sys.argv) == 6

    run, logfile, l10path, l11path, out = map(
        Path, sys.argv[1:]
    )

    assert out.is_dir() and not out.is_symlink()

    assert sha(l10path) == L10_SHA
    assert sha(l11path) == L11_SHA

    l10 = read_json(l10path)
    l11 = read_json(l11path)

    assert l10["pose_factors_authorized"] == 0
    assert l11["pose_factors_authorized"] == 0

    first = derive(
        run, logfile, l10, l11
    )

    second = derive(
        run, logfile, l10, l11
    )

    assert canon(first) == canon(second)

    report = {
        "schema":
            "TRUST_ROBOT_L12_GMO_AZIMUTH_MAPPING_AND_TIMELINE_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "l10_sha256":
            sha(l10path),

        "l11_sha256":
            sha(l11path),

        "runtime_log_sha256":
            sha(logfile),

        "deterministic_repeat_identical":
            True,

        "analytic_geometry_is_not_rtx_measurement":
            True,

        "associated_indices_are_not_verified_emitter_ids":
            True,

        "zero_count_frame_not_assumed_invalid":
            True,

        "definitive_missing_return_cause_identified":
            False,

        "physical_time_calibration_verified":
            False,

        "independent_ground_truth_verified":
            False,

        "health_labels_generated": 0,
        "pose_factors_authorized": 0,

        **first,
    }

    target = (
        out / "l12_azimuth_mapping_and_return_timeline_v1.json"
    )

    with target.open("x") as stream:
        json.dump(
            report,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        stream.write("\n")

    for row in first["timeline_steps_88_to_110"]:
        print(
            "L12_TIMELINE=",
            json.dumps({
                key: row[key]
                for key in (
                    "step",
                    "gmo_state",
                    "gmo_element_count",
                    "gmo_frame_id",
                    "same_frame_id_as_previous",
                    "gmo_timestamp_delta_from_previous_s",
                    "analytic_near_range_margin_m",
                    "analytic_intersections",
                )
            }, sort_keys=True),
            flush=True,
        )

    for step in (91, 101):
        mapping = first[
            "azimuth_mapping_steps_91_and_101"
        ][str(step)]

        print(
            "L12_AZIMUTH_MAPPING=",
            json.dumps({
                "step": step,
                "associated_indices":
                    mapping["associated_indices"],

                "max_inverted_azimuth_residual_deg":
                    mapping[
                        "maximum_inverted_azimuth_residual_deg"
                    ],

                "max_elevation_residual_deg":
                    mapping[
                        "maximum_elevation_residual_deg"
                    ],
            }, sort_keys=True),
            flush=True,
        )

    print("L12_LAST_FRAME_ASSOCIATED_INDICES=[0,15]")
    print("L12_MISSING_RETURN_CAUSE=UNRESOLVED")
    print("L12_DETERMINISTIC_REDERIVATION=PASS")
    print("L12_OFFLINE_AUDIT=PASS")

    print(
        "L12_REPORT_SHA256=",
        sha(target),
    )


if __name__ == "__main__":
    main()
