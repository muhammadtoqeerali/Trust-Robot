import inspect

import numpy as np
import pytest

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_preintegrated_fusion import (
    make_factors,
)
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    SyntheticPoseFactor,
)

from s6_joint_fusion import (
    CAMERA_STD,
    LIDAR_STD,
    JointFactor,
    assemble_joint,
    diag_cov,
    estimate_joint,
    validate_factors,
    whitened_pose_residual,
)


@pytest.fixture(scope="module")
def synthetic():
    return make_fixture("clean")


@pytest.fixture
def measured(synthetic):
    fixture, truth = synthetic

    return manufactured_camera_packets(
        truth,
        seed=13,
    )


def test_same_edge_factors_retained(synthetic, measured):
    fixture, _ = synthetic
    _, lidar, _ = make_factors(fixture)

    factors = assemble_joint(lidar, measured)

    assert len(lidar) == 7
    assert len(factors) == 9

    both = [
        f
        for f in factors
        if f.packet.edge == (0, 1)
    ]

    assert len(both) == 2
    assert {f.packet.modality for f in both} == {
        "camera", "lidar"
    }

    assert both[0].key != both[1].key


def test_assumed_covariances_are_different(
    synthetic, measured
):
    fixture, _ = synthetic
    _, lidar, _ = make_factors(fixture)

    factors = assemble_joint(lidar, measured)

    camera = next(
        f for f in factors
        if f.packet.modality == "camera"
    )
    scan = next(
        f for f in factors
        if f.packet.modality == "lidar"
    )

    assert not np.array_equal(
        np.asarray(camera.covariance),
        np.asarray(scan.covariance),
    )

    assert np.all(np.diag(camera.covariance) > 0)
    assert np.all(np.diag(scan.covariance) > 0)


def test_full_spd_whitening(synthetic, measured):
    packet = measured[0]

    base = diag_cov(CAMERA_STD)

    full = base.copy()
    full[0, 1] = full[1, 0] = 0.0002

    factor = JointFactor(packet, full)

    fixture, _ = synthetic
    _, lidar, _ = make_factors(fixture)

    assert np.linalg.eigvalsh(
        np.asarray(factor.covariance)
    ).min() > 0


@pytest.mark.parametrize(
    "covariance",
    (
        np.zeros((6, 6)),
        np.eye(5),
        np.diag([1, 1, 1, 1, 1, -1]),
        np.diag([1, 1, 1, 1, 1, np.nan]),
        np.diag([1, 1, 1, 1, 1, np.inf]),
        np.diag([1e-16, 1, 1, 1, 1, 1]),
    ),
)
def test_invalid_covariances_denied(
    measured, covariance
):
    with pytest.raises(ValueError):
        JointFactor(
            measured[0],
            covariance,
        )


def test_nonsymmetric_covariance_denied(measured):
    bad = np.eye(6)
    bad[0, 1] = 0.25

    with pytest.raises(ValueError):
        JointFactor(
            measured[0],
            bad,
        )


def test_repeated_measurement_identity_denied(
    synthetic, measured
):
    fixture, _ = synthetic
    _, lidar, _ = make_factors(fixture)

    with pytest.raises(ValueError):
        assemble_joint(
            lidar,
            (measured[0], measured[0]),
        )


def test_cross_origin_packet_denied():
    with pytest.raises(ValueError):
        SyntheticPoseFactor(
            modality="camera",
            edge=(0, 1),
            measurement_id="recorded-origin",
            source_id=CAMERA_SOURCE,
            frame_id=ANALYTIC_FRAME,
            measurement=PoseSE3.identity(),
            origin="M2DGR",
        )


def test_invalid_synthetic_source_denied():
    with pytest.raises(ValueError):
        SyntheticPoseFactor(
            modality="camera",
            edge=(0, 1),
            measurement_id="wrong-source",
            source_id="M2DGR_CAMERA",
            frame_id=ANALYTIC_FRAME,
            measurement=PoseSE3.identity(),
        )


def test_solver_api_excludes_truth():
    signature = inspect.signature(
        estimate_joint
    )

    assert list(signature.parameters) == [
        "fixture",
        "camera_packets",
    ]

    assert "truth" not in signature.parameters
    assert "reference" not in signature.parameters


@pytest.mark.parametrize(
    "condition",
    ("clean", "lidar_dropout"),
)
@pytest.mark.parametrize(
    "camera_enabled",
    (False, True),
)
def test_actual_joint_schur_solver(
    condition, camera_enabled
):
    fixture, truth = make_fixture(
        condition
    )

    packets = (
        manufactured_camera_packets(
            truth,
            seed=13,
        )
        if camera_enabled else ()
    )

    states, audit = estimate_joint(
        fixture,
        packets,
    )

    assert len(states) == 5
    assert audit["accepted_window_count"] == 4
    assert audit["schur_elimination_count"] == 3

    assert audit["camera_factor_count"] == (
        2 if camera_enabled else 0
    )

    assert audit["unaccounted_factor_count"] == 0
    assert audit["factor_reuse_after_marginalization"] is False

    ids = [
        f["measurement_id"]
        for f in audit["factor_ledger"]
    ]

    assert len(ids) == len(set(ids))

    assert set(ids) == (
        set(audit["consumed_pose_ids"])
        | set(audit["remaining_pose_ids"])
    )

    assert not (
        set(audit["consumed_pose_ids"])
        & set(audit["remaining_pose_ids"])
    )

    for state in states:
        for key in (
            "position_m",
            "rotation_vector_rad",
            "velocity_m_s",
            "gyro_bias",
            "accel_bias",
        ):
            assert np.isfinite(state[key]).all()


def test_no_camera_no_camera_factor(synthetic):
    fixture, _ = synthetic

    _, audit = estimate_joint(
        fixture,
        (),
    )

    assert audit["camera_factor_count"] == 0
    assert audit["lidar_factor_count"] == 7
    assert audit["same_edge_camera_lidar_count"] == 0


def test_duplicate_modality_edge_denied(measured):
    identical = JointFactor(
        measured[0],
        diag_cov(CAMERA_STD),
    )

    with pytest.raises(ValueError):
        validate_factors(
            (identical, identical),
        )


def test_covariance_immutable_copy(measured):
    cov = diag_cov(CAMERA_STD)
    value = JointFactor(measured[0], cov)

    saved = value.covariance
    cov[0, 0] = 1000.0

    assert value.covariance == saved


def test_unauthorized_factor_type_denied():
    with pytest.raises(ValueError):
        validate_factors(
            ({"source": "M2DGR"},)
        )


def test_distinct_lidar_camera_same_edge_residual(
    synthetic, measured
):
    fixture, _ = synthetic
    _, lidar, _ = make_factors(fixture)

    pairs = [
        f for f in assemble_joint(lidar, measured)
        if f.packet.edge == (0, 1)
    ]

    x = np.zeros(15)
    y = x.copy()
    y[0] = 0.02

    residuals = [
        whitened_pose_residual(x, y, f)
        for f in pairs
    ]

    assert len(residuals) == 2
    assert all(
        r.shape == (6,)
        and np.isfinite(r).all()
        for r in residuals
    )
