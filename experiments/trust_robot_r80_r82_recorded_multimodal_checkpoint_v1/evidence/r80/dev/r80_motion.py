"""R80: recorded LiDAR SE(3) diagnostics, not executable estimator factors.

Reads only already-published, frozen TRAIN diagnostic JSON.
The eight pairs are noncontiguous across pairs and may not be chained
into a continuous 8-increment trajectory.
"""
import hashlib
import json
import math
import pathlib
import sys

SCHEMA = "TRUST_ROBOT_R80_RECORDED_LIDAR_MOTION_BRIDGE_V1"

class MotionError(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise MotionError(message)

def digest(path):
    return hashlib.sha256(
        pathlib.Path(path).read_bytes()
    ).hexdigest()

def load(path):
    return json.loads(
        pathlib.Path(path).read_text(encoding="utf-8")
    )

def finite(x):
    return type(x) in (int, float) and math.isfinite(x)

def transpose(R):
    return [
        [R[j][i] for j in range(3)]
        for i in range(3)
    ]

def mv(R, v):
    return [
        sum(R[i][j]*v[j] for j in range(3))
        for i in range(3)
    ]

def det(R):
    return (
        R[0][0]*(R[1][1]*R[2][2]-R[1][2]*R[2][1])
        - R[0][1]*(R[1][0]*R[2][2]-R[1][2]*R[2][0])
        + R[0][2]*(R[1][0]*R[2][1]-R[1][1]*R[2][0])
    )

def validate_se3(reg):
    R = reg.get("rotation_previous_from_current")
    t = reg.get("translation_previous_from_current_m")

    need(
        type(R) is list and len(R) == 3
        and all(
            type(row) is list
            and len(row) == 3
            and all(finite(v) for v in row)
            for row in R
        ),
        "ROTATION_MATRIX_SHAPE"
    )

    need(
        type(t) is list and len(t) == 3
        and all(finite(x) for x in t),
        "TRANSLATION_SHAPE"
    )

    Rt = transpose(R)

    errors = [
        abs(
            sum(Rt[i][k]*R[k][j] for k in range(3))
            - (1.0 if i == j else 0.0)
        )
        for i in range(3)
        for j in range(3)
    ]

    determinant = det(R)

    # Algebraic consistency tolerance; NOT a registration quality
    # threshold, outlier filter, covariance or pose admission rule.
    need(max(errors) <= 1e-8, "SO3_ORTHOGONALITY")
    need(abs(determinant-1.0) <= 1e-8, "SO3_DETERMINANT")
    need(
        abs(determinant-reg["determinant"]) <= 1e-8,
        "REPORTED_DETERMINANT"
    )

    inv_t = [-v for v in mv(Rt, t)]
    closure = mv(R, inv_t)
    closure = [a+b for a,b in zip(closure,t)]

    need(
        max(abs(x) for x in closure) <= 1e-9,
        "INVERSE_TRANSLATION_CLOSURE"
    )

    trace = R[0][0]+R[1][1]+R[2][2]
    cosine = min(1.0,max(-1.0,(trace-1.0)/2.0))
    angle = math.acos(cosine)

    return {
        "previous_T_current": {
            "rotation_3x3": R,
            "translation_m": t,
        },
        "current_T_previous": {
            "rotation_3x3": Rt,
            "translation_m": inv_t,
        },
        "rotation_angle_rad": angle,
        "translation_norm_m": math.sqrt(
            sum(x*x for x in t)
        ),
        "so3_max_orthogonality_error": max(errors),
        "inverse_translation_closure_error_m": max(
            abs(x) for x in closure
        ),
    }

def build(r27, r29, freeze, pins):
    need(
        r27.get("schema") ==
        "TRUST_ROBOT_R27_TRAIN_LIDAR_SINGLE_PAIR_REGISTRATION_DIAGNOSTIC_V1",
        "R27_SCHEMA"
    )

    need(
        r29.get("schema") ==
        "TRUST_ROBOT_R29_TRAIN_LIDAR_ADJACENT_PAIR_DIAGNOSTICS_V1",
        "R29_SCHEMA"
    )

    for src in (r27,r29):
        need(
            src.get("trajectory_id") == "room_02"
            and src.get("split") == "train",
            "RECORDED_TRAIN_SCOPE"
        )

    need(
        r29.get("pair_count") == 8
        and len(r29.get("pairs",[])) == 8,
        "RECORDED_PAIR_COUNT"
    )

    need(
        r29["pair_order"] ==
        "previous_lidar_T_current_lidar_diagnostic_only",
        "FRAME_DIRECTION"
    )

    need(
        r29["per_scan_selected_points"] == 512
        and r29["fixed_registration_iterations"] == 10,
        "HISTORICAL_ALGORITHM"
    )

    need(
        r29["authenticated_bag_sha256"] ==
        r27["bag_sha256"],
        "RECORDING_PROVENANCE"
    )

    # R27 and R29 are separate frozen report schemas.
    # Do not assume a synchronization field exists in R29.
    need(
        r27.get("cross_modal_synchronization_verified") is False
        and r27.get("full_extrinsics_verified") is False,
        "R27_SCIENCE_BOUNDARY"
    )

    need(
        r29.get("cross_modal_alignment_performed") is False
        and r29.get("full_extrinsics_verified") is False,
        "R29_SCIENCE_BOUNDARY"
    )

    for field in (
        "physical_capture_time_verified",
        "pose_accuracy_established",
        "real_sensor_factor_execution_authorized",
        "independent_ground_truth_scored",
        "m2dgr_scoring_authorized",
        "cross_modal_alignment_performed",
    ):
        need(r29[field] is False, "R29_BOUNDARY_"+field)

    need(
        r29["real_pose_factors_generated"] == 0
        and r29["health_labels_generated"] == 0,
        "R29_FACTORS_OR_LABELS"
    )

    need(
        freeze["execution_evidence"]["total_increment_count"]
        == 90992,
        "PHASE2_FROZEN_BASELINE"
    )

    need(
        freeze["baseline_identity"]["transform_convention"]
        == "prev_body_T_current_body",
        "PHASE2_DIRECTION"
    )

    need(
        r29["pairs"][0]["registration"]
        == r27["registration_diagnostic"],
        "R27_FIRST_PAIR_AGREEMENT"
    )

    rows = []
    last_sequence = None
    last_timestamp = None

    for index,p in enumerate(r29["pairs"]):
        need(
            type(p["pair_index"]) is int
            and p["pair_index"] == index,
            "PAIR_IDENTITY"
        )

        scans = p["scans"]
        need(
            type(scans) is list and len(scans) == 2,
            "PAIR_SCAN_COUNT"
        )

        a,b = scans

        need(
            a["frame_id"] == b["frame_id"] == "velodyne",
            "SENSOR_FRAME"
        )

        need(
            type(a["sequence"]) is int
            and type(b["sequence"]) is int
            and b["sequence"] == a["sequence"]+1,
            "CONSECUTIVE_SCAN_PAIR"
        )

        ta,tb = a["header_stamp_ns"],b["header_stamp_ns"]

        need(
            type(ta) is int
            and type(tb) is int
            and tb > ta
            and tb-ta == p["observed_header_gap_ns"],
            "SCAN_HEADER_ORDER"
        )

        if last_sequence is not None:
            need(
                a["sequence"] > last_sequence+1
                and ta > last_timestamp,
                "CROSS_PAIR_SEPARATION"
            )

        last_sequence = b["sequence"]
        last_timestamp = tb

        reg = p["registration"]

        need(
            reg["candidate_registered_as_factor"] is False
            and reg["independent_pose_accuracy_claimed"] is False
            and reg["physical_scan_time_qualified"] is False
            and reg["convergence_claimed"] is False,
            "REGISTRATION_SCIENCE_BOUNDARY"
        )

        need(
            reg["fixed_iterations"] == 10
            and reg["deterministic_points_per_scan"] == 512,
            "FROZEN_REGISTRATION"
        )

        for key in (
            "identity_nearest_neighbor_rmse_m",
            "candidate_nearest_neighbor_rmse_m",
            "candidate_median_nn_distance_m",
            "candidate_max_nn_distance_m",
        ):
            need(
                finite(reg[key]) and reg[key] >= 0.0,
                "INVALID_DIAGNOSTIC:"+key
            )

        geometry = validate_se3(reg)

        rows.append({
            "pair_index": index,
            "previous_scan_sequence": a["sequence"],
            "current_scan_sequence": b["sequence"],
            "previous_header_stamp_ns": ta,
            "current_header_stamp_ns": tb,
            "observed_header_gap_ns": tb-ta,
            "body_frame": "velodyne",
            "transform_convention": "previous_lidar_T_current_lidar",
            "motion": geometry,
            "identity_rmse_m":
                reg["identity_nearest_neighbor_rmse_m"],
            "registered_rmse_m":
                reg["candidate_nearest_neighbor_rmse_m"],
            "gt_used": False,
            "factor_executable": False,
            "pair_not_chained_across_unobserved_scans": True,
        })

    need(len(rows) == 8, "EXPECTED_EIGHT_PAIRS")

    return {
        "schema": SCHEMA,
        "trajectory": "room_02",
        "split": "train",
        "source_sha256": pins,
        "source": "FROZEN_M2DGR_RECORDED_LIDAR_DIAGNOSTICS",
        "records": rows,
        "pair_count": 8,
        "separate_disjoint_scan_segments": 8,
        "full_frozen_train_increments_previously_completed": 90992,
        "continuous_trajectory_reconstructed_from_eight_pairs": False,
        "physical_timestamp_semantics_verified": False,
        "sensor_frame_to_robot_base_verified": False,
        "real_pose_factors_authorized": False,
        "reference_scoring_performed": False,
        "ate_rpe_authorized": False,
        "health_training_authorized": False,
        "confirmation_test_accessed": False,
        "raw_rosbag_or_gt_opened": False,
        "scientific_gates_closed": 11,
    }

def write(result,path):
    path.write_text(
        json.dumps(
            result,sort_keys=True,indent=2,allow_nan=False
        )+"\n",
        encoding="utf-8"
    )

if __name__ == "__main__":
    repo=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2])

    rels={
        "r27":
            "experiments/trust_robot_r27_r31_recorded_motion_checkpoint_v1/r27/r27_lidar_diagnostic_registration_v1.json",
        "r29":
            "experiments/trust_robot_r27_r31_recorded_motion_checkpoint_v1/r29/r29_lidar_multipair_diagnostics_v1.json",
        "phase2":
            "manifests/trust_robot_phase2_clean_lidar_baseline_freeze_v1.json",
    }

    objects={k:load(repo/v) for k,v in rels.items()}
    pins={k:digest(repo/v) for k,v in rels.items()}

    result=build(
        objects["r27"],objects["r29"],
        objects["phase2"],pins
    )

    target=out/"r80_recorded_lidar_motion_bridge_v1.json"
    write(result,target)

    print("R80_RECORDED_TRAIN_SCAN_PAIRS=8_VERIFIED")
    print("R80_SE3_AND_INVERSE_GEOMETRY=PASS")
    print("R80_DISJOINT_SEGMENTS=8_NOT_FALSELY_CHAINED")
    print("R80_REAL_FACTOR_ADMISSION=DENIED")
