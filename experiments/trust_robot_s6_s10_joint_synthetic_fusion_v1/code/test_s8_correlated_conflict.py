import numpy as np
import pytest

from trust_robot.clean_backbone import PoseSE3
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    SyntheticPoseFactor,
)

from s6_joint_fusion import JointFactor

from s7_factor_support import (
    camera_lidar_pair,
    information_experiment,
    perturb_camera,
)

from s8_correlated_conflict import (
    DISPLACEMENT_M,
    paired_covariance,
    disagreement_diagnostic,
    information_diagnostic,
    conflict_scenarios,
    nonlinear_factor_retention,
    require_runtime_conflict_action,
    comparison_states,
)


@pytest.fixture(scope="module")
def pair():
    fixture, packets, factors, _ = camera_lidar_pair()

    return fixture, packets, factors


def test_distinct_shared_edge_owners(pair):
    _, _, factors = pair

    assert factors["camera"].packet.edge == (0, 1)
    assert factors["lidar"].packet.edge == (0, 1)
    assert factors["camera"].key != factors["lidar"].key


@pytest.mark.parametrize("rho", (0.0, 0.35, -0.25))
def test_manufactured_covariance_is_spd(pair, rho):
    _, _, factors = pair

    matrix, cross = paired_covariance(
        factors["camera"],
        factors["lidar"],
        rho,
    )

    assert matrix.shape == (12, 12)
    assert cross.shape == (6, 6)
    assert np.allclose(matrix, matrix.T)
    assert np.linalg.eigvalsh(matrix).min() > 0


def test_zero_cross_covariance_is_block_diagonal(pair):
    _, _, factors = pair

    matrix, cross = paired_covariance(
        factors["camera"],
        factors["lidar"],
        0.0,
    )

    assert np.array_equal(
        cross,
        np.zeros((6, 6)),
    )

    assert np.array_equal(
        matrix[:6, 6:],
        np.zeros((6, 6)),
    )


@pytest.mark.parametrize(
    "invalid",
    (
        True,
        None,
        "0.35",
        float("nan"),
        float("inf"),
        0.76,
        -0.76,
        1.0,
        -1.0,
    ),
)
def test_unqualified_correlation_denied(pair, invalid):
    _, _, factors = pair

    with pytest.raises(ValueError):
        paired_covariance(
            factors["camera"],
            factors["lidar"],
            invalid,
        )


@pytest.mark.parametrize("rho", (0.0, 0.35, -0.25))
def test_synthetic_conflict_detection(pair, rho):
    _, _, factors = pair

    camera = factors["camera"]
    lidar = factors["lidar"]

    altered = JointFactor(
        perturb_camera(
            camera.packet,
            DISPLACEMENT_M,
        ),
        camera.covariance,
    )

    ordinary = disagreement_diagnostic(
        camera, lidar, rho
    )

    disturbed = disagreement_diagnostic(
        altered, lidar, rho
    )

    assert ordinary[
        "flagged_synthetic_disagreement"
    ] is False

    assert disturbed[
        "flagged_synthetic_disagreement"
    ] is True

    assert disturbed[
        "squared_normalized_disagreement"
    ] > ordinary[
        "squared_normalized_disagreement"
    ]

    assert ordinary["handling"] == disturbed["handling"]
    assert ordinary[
        "sensor_auto_suppression_executed"
    ] is False
    assert disturbed[
        "health_state_inferred"
    ] is False


def test_information_zero_correlation_matches_s7(pair):
    fixture, _, factors = pair

    xi, xj = comparison_states(
        fixture
    )

    result = information_diagnostic(
        factors["camera"],
        factors["lidar"],
        0.0,
        xi,
        xj,
    )

    prior = information_experiment()

    assert np.allclose(
        result["correlated_information_matrix"],
        prior["joint_information_matrix"],
        rtol=1e-8,
        atol=1e-7,
    )


def test_assumed_correlation_changes_information(pair):
    fixture, _, factors = pair
    xi, xj = comparison_states(fixture)

    a = information_diagnostic(
        factors["camera"],
        factors["lidar"],
        0.0,
        xi, xj,
    )

    b = information_diagnostic(
        factors["camera"],
        factors["lidar"],
        0.35,
        xi, xj,
    )

    assert not np.allclose(
        a["correlated_information_matrix"],
        b["correlated_information_matrix"],
        rtol=1e-5,
    )

    assert b[
        "cross_modal_noise_empirically_verified"
    ] is False


def test_no_physical_conflict_threshold_claim(pair):
    _, _, factors = pair

    diagnostic = disagreement_diagnostic(
        factors["camera"],
        factors["lidar"],
        0.35,
    )

    assert diagnostic[
        "physical_false_alarm_probability_established"
    ] is False

    assert diagnostic[
        "health_state_inferred"
    ] is False


@pytest.mark.parametrize(
    "claim",
    (
        {},
        {"authorization": True},
        {"sensor_health": "unusable"},
        {"drop_camera": True},
    ),
)
def test_runtime_sensor_action_remains_denied(claim):
    with pytest.raises(ValueError):
        require_runtime_conflict_action(
            **claim
        )


def test_recorded_pose_origin_remains_denied():
    with pytest.raises(ValueError):
        SyntheticPoseFactor(
            modality="camera",
            edge=(0, 1),
            measurement_id="M2DGR-fake",
            source_id=CAMERA_SOURCE,
            frame_id=ANALYTIC_FRAME,
            measurement=PoseSE3.identity(),
            origin="M2DGR",
        )


def test_three_correlation_scenarios():
    rows, packets = conflict_scenarios()

    assert len(rows) == 3
    assert len(packets) == 2
    assert [row["rho"] for row in rows] == [
        0.0, 0.35, -0.25
    ]

    assert all(
        row["baseline"][
            "flagged_synthetic_disagreement"
        ] is False
        and row["corrupted"][
            "flagged_synthetic_disagreement"
        ] is True
        for row in rows
    )


def test_nonlinear_schur_keeps_both_modalities(pair):
    _, packets, _ = pair

    result = nonlinear_factor_retention(
        packets
    )

    assert result["baseline_factor_count"] == 9
    assert result["disturbed_factor_count"] == 9
    assert result["shared_edge_factor_pairs"] == 2
    assert result["accepted_window_solves"] == 8

    assert result["factor_ids_preserved"] is True
    assert result[
        "automatic_sensor_suppression_executed"
    ] is False

    assert result[
        "real_factor_execution_authorized"
    ] is False
