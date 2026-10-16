import copy
import json
from pathlib import Path

import pytest

from trust_robot.m2dgr_sensor_admission import (
    CAMERA,
    CAMERA_IMU,
    BODY_IMU,
    LIDAR,
    load_frozen_snapshot,
)

from s3_contract import (
    FIELDS,
    S3ContractError,
    build_envelope,
    canonical,
    parse_envelope,
    require_real_factor,
)

REPO = Path(__file__).resolve().parents[2] / "github_checkout_v15"

# The S3 DEV directory is:
# experiments/trust_robot_s3_train_factor_input_dev_v1
REPO = Path(__file__).resolve().parents[2] / "github_checkout_v15"


@pytest.fixture(scope="module")
def snapshot():
    return load_frozen_snapshot(REPO)


@pytest.fixture
def base(snapshot):
    return build_envelope(
        snapshot,
        "gate_01",
        CAMERA,
        100,
    )


@pytest.mark.parametrize(
    "stream",
    (CAMERA, CAMERA_IMU, BODY_IMU, LIDAR),
)
def test_four_train_streams(snapshot, stream):
    value = build_envelope(
        snapshot,
        "gate_01",
        stream,
        100,
    )

    assert parse_envelope(
        snapshot,
        canonical(value),
    ) == value

    assert value["real_sensor_factor_execution_authorized"] is False
    assert value["relative_pose"] is None
    assert value["factor_covariance"] is None


def test_separate_imu_frames(snapshot):
    a = build_envelope(
        snapshot,
        "gate_01",
        CAMERA_IMU,
        100,
    )

    b = build_envelope(
        snapshot,
        "gate_01",
        BODY_IMU,
        100,
    )

    assert a["stream_id"] != b["stream_id"]
    assert a["frame_id"] != b["frame_id"]
    assert a["clock_domain"] != b["clock_domain"]


def test_heldout_never_admitted(snapshot):
    with pytest.raises(S3ContractError):
        build_envelope(
            snapshot,
            "room_01",
            CAMERA,
            100,
        )


def test_absent_camera_never_admitted(snapshot):
    with pytest.raises(S3ContractError):
        build_envelope(
            snapshot,
            "street_09",
            CAMERA,
            100,
        )


@pytest.mark.parametrize(
    "bad_stamp",
    (True, None, -1, 1.5, "100", 2**63),
)
def test_invalid_claimed_timestamps(snapshot, bad_stamp):
    with pytest.raises(S3ContractError):
        build_envelope(
            snapshot,
            "gate_01",
            CAMERA,
            bad_stamp,
        )


def test_unknown_stream_denied(snapshot):
    with pytest.raises(S3ContractError):
        build_envelope(
            snapshot,
            "gate_01",
            "/unregistered/stream",
            100,
        )


def test_noncanonical_bytes_denied(snapshot, base):
    altered_format = json.dumps(
        base,
        indent=2,
    ).encode()

    with pytest.raises(S3ContractError):
        parse_envelope(
            snapshot,
            altered_format,
        )


def test_duplicate_json_field_denied(snapshot, base):
    data = canonical(base)

    duplicate = (
        b'{"schema":"FORGED",'
        + data[1:]
    )

    with pytest.raises(S3ContractError):
        parse_envelope(
            snapshot,
            duplicate,
        )


@pytest.mark.parametrize(
    "field",
    tuple(
        field
        for field in FIELDS
        if field != "claimed_header_stamp_ns"
    ),
)
def test_every_metadata_field_promotion_denied(
    snapshot, base, field
):
    changed = copy.deepcopy(base)
    old = changed[field]

    if old is False:
        changed[field] = True
    elif old is None:
        changed[field] = "FORGED"
    elif type(old) is str:
        changed[field] = old + "_FORGED"
    else:
        changed[field] = 1

    with pytest.raises(S3ContractError):
        parse_envelope(
            snapshot,
            canonical(changed),
        )


def test_claimed_header_is_not_authentication(snapshot):
    first = build_envelope(
        snapshot,
        "gate_01",
        CAMERA,
        100,
    )

    second = build_envelope(
        snapshot,
        "gate_01",
        CAMERA,
        101,
    )

    assert first != second

    assert parse_envelope(
        snapshot,
        canonical(second),
    ) == second

    assert second[
        "header_stamp_origin"
    ] == "CALLER_ASSERTION_NOT_OBSERVED"

    assert second[
        "real_sensor_factor_execution_authorized"
    ] is False


def test_factor_conversion_always_blocked(base):
    with pytest.raises(S3ContractError):
        require_real_factor(base)

    forged = copy.deepcopy(base)
    forged["real_sensor_factor_execution_authorized"] = True

    with pytest.raises(S3ContractError):
        require_real_factor(forged)
