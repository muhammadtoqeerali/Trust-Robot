import copy
from pathlib import Path

import pytest

from s4_requirements import (
    GATES,
    S4Error,
    build_rows,
    check_rows,
    require_factor_execution,
)

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "github_checkout_v15"

S3 = (
    ROOT
    / "experiments"
    / "trust_robot_s3_train_factor_input_result_v1"
    / "s3_four_stream_metadata_v1.json"
)


@pytest.fixture(scope="module")
def rows():
    result, _ = build_rows(REPO, S3)
    return result


def test_four_distinct_sources(rows):
    assert len(rows) == 4

    assert len({
        x["stream_id"]
        for x in rows
    }) == 4


def test_imu_sources_not_conflated(rows):
    imu = [
        x for x in rows
        if x["modality"] == "imu"
    ]

    assert len(imu) == 2
    assert imu[0]["stream_id"] != imu[1]["stream_id"]
    assert imu[0]["frame_id"] != imu[1]["frame_id"]
    assert imu[0]["clock_domain"] != imu[1]["clock_domain"]


def test_integrity_is_not_calibration(rows):
    for item in rows:
        assert item["bag_integrity_verified"] is True
        assert item["bag_integrity_proves_calibration"] is False
        assert item["physical_body_T_sensor"] is None


def test_partial_rotation_is_not_full_extrinsic(rows):
    supported = [
        x for x in rows
        if x["d435i_relative_rotation_content_supported"]
    ]

    assert len(supported) == 1
    assert supported[0]["stream_id"] == "/camera/imu"
    assert supported[0]["partial_rotation_proves_full_extrinsic"] is False


def test_all_requirements_closed(rows):
    for item in rows:
        assert list(item["requirement_gates"]) == list(GATES)
        assert all(
            value is False
            for value in item["requirement_gates"].values()
        )


@pytest.mark.parametrize("stream_index", range(4))
@pytest.mark.parametrize("gate", GATES)
def test_false_gate_promotion_denied(
    rows, stream_index, gate
):
    changed = copy.deepcopy(rows)

    changed[stream_index][
        "requirement_gates"
    ][gate] = True

    with pytest.raises(S4Error):
        check_rows(REPO, S3, changed)


@pytest.mark.parametrize(
    "field,forgery",
    (
        ("frame_id", "FORGED"),
        ("clock_domain", "TRUSTED_CLOCK"),
        ("stream_id", "/unregistered"),
        ("bag_integrity_sha256", "0" * 64),
        ("bag_integrity_proves_calibration", True),
        ("sensor_sync_status", "verified"),
        ("physical_body_T_sensor", [1, 0, 0]),
        ("relative_pose_factor", "FORGED_POSE"),
        ("factor_covariance", [1.0]),
        ("header_stamp_authenticated", True),
        ("actual_header_observed", True),
        ("disposition", "APPROVED"),
    ),
)
def test_false_metadata_denied(rows, field, forgery):
    changed = copy.deepcopy(rows)

    changed[0][field] = forgery

    with pytest.raises(S4Error):
        check_rows(REPO, S3, changed)


def test_invented_offset_denied(rows):
    changed = copy.deepcopy(rows)
    changed[0]["fixed_offset_seconds"] = 0.0

    with pytest.raises(S4Error):
        check_rows(REPO, S3, changed)


def test_transport_time_not_promoted(rows):
    changed = copy.deepcopy(rows)

    changed[0]["header_timestamp_basis"] = (
        "bag_record_time"
    )

    with pytest.raises(S4Error):
        check_rows(REPO, S3, changed)


def test_full_extrinsic_not_promoted(rows):
    changed = copy.deepcopy(rows)

    changed[1][
        "partial_rotation_proves_full_extrinsic"
    ] = True

    with pytest.raises(S4Error):
        check_rows(REPO, S3, changed)


def test_missing_stream_denied(rows):
    with pytest.raises(S4Error):
        check_rows(REPO, S3, rows[:3])


def test_duplicate_stream_denied(rows):
    changed = copy.deepcopy(rows)
    changed[1] = copy.deepcopy(changed[0])

    with pytest.raises(S4Error):
        check_rows(REPO, S3, changed)


def test_factor_execution_always_denied(rows):
    with pytest.raises(S4Error):
        require_factor_execution(rows)

    promoted = copy.deepcopy(rows)

    for item in promoted:
        item["requirement_gates"][
            "recorded_factor_execution_authorized"
        ] = True

    with pytest.raises(S4Error):
        require_factor_execution(promoted)
