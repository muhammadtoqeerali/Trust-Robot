import dataclasses
import inspect

import numpy as np
import pytest

from trust_robot.clean_backbone import PoseSE3
from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_preintegrated_fusion import make_factors
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_FRAME,
    CAMERA_SOURCE,
    SyntheticPoseFactor,
)

from s6_joint_fusion import (
    JointFactor,
    assemble_joint,
    diag_cov,
    estimate_joint,
    whitened_pose_residual,
)

from s7_factor_support import (
    PERTURBATION_M,
    camera_lidar_pair,
    comparison_states,
    information_experiment,
    jacobian_on_edge,
    nonlinear_perturbation_experiment,
    perturb_camera,
)


def test_shared_edge_retains_two_measurements():
    _, _, pair, _ = camera_lidar_pair()

    assert set(pair) == {"camera", "lidar"}
    assert pair["camera"].key != pair["lidar"].key


def test_distinct_modality_covariances():
    _, _, pair, _ = camera_lidar_pair()

    assert not np.array_equal(
        pair["camera"].covariance,
        pair["lidar"].covariance,
    )


def test_both_pose_jacobians_rank_six():
    fixture, _, pair, _ = camera_lidar_pair()
    xi, xj = comparison_states(fixture)

    for factor in pair.values():
        j = jacobian_on_edge(xi, xj, factor)

        assert j.shape == (6, 6)
        assert np.linalg.matrix_rank(j) == 6


def test_joint_information_contains_both_modalities():
    result = information_experiment()

    cam = np.asarray(
        result["camera_information_matrix"]
    )
    lidar = np.asarray(
        result["lidar_information_matrix"]
    )
    joint = np.asarray(
        result["joint_information_matrix"]
    )

    assert np.allclose(joint, cam + lidar)
    assert np.linalg.eigvalsh(cam).min() > 0
    assert np.linalg.eigvalsh(lidar).min() > 0
    assert np.linalg.eigvalsh(joint).min() > 0

    assert np.trace(joint) > np.trace(cam)
    assert np.trace(joint) > np.trace(lidar)


def test_information_does_not_claim_independent_noise():
    result = information_experiment()

    assert result[
        "assumed_residual_independence_for_additive_information"
    ] is True

    assert result[
        "empirical_cross_modality_noise_independence_verified"
    ] is False

    assert result[
        "physically_supported_information_matrix"
    ] is False


def test_assumed_covariance_changes_residual_scale():
    result = information_experiment()

    baseline = result[
        "camera_baseline_whitened_norm"
    ]

    relaxed = result[
        "camera_inflated_whitened_norm"
    ]

    assert np.isclose(
        relaxed,
        baseline / 5.0,
        atol=1e-10,
        rtol=1e-9,
    )


def test_camera_corruption_visible_in_residual():
    result = information_experiment()

    assert result[
        "camera_corrupted_whitened_norm"
    ] > result[
        "camera_baseline_whitened_norm"
    ]


def test_perturbation_preserves_source_identity():
    _, _, pair, _ = camera_lidar_pair()

    original = pair["camera"].packet

    modified = perturb_camera(original)

    assert modified.measurement_id == original.measurement_id
    assert modified.source_id == original.source_id
    assert modified.frame_id == original.frame_id
    assert modified.origin == original.origin
    assert modified.measurement != original.measurement


@pytest.mark.parametrize(
    "bad_displacement",
    (
        -1.0,
        0.0,
        0.5,
        float("nan"),
        float("inf"),
    ),
)
def test_invalid_perturbation_denied(bad_displacement):
    _, _, pair, _ = camera_lidar_pair()

    with pytest.raises(ValueError):
        perturb_camera(
            pair["camera"].packet,
            bad_displacement,
        )


def test_recorded_origin_still_rejected():
    with pytest.raises(ValueError):
        SyntheticPoseFactor(
            modality="camera",
            edge=(0, 1),
            measurement_id="recorded-source-forgery",
            source_id=CAMERA_SOURCE,
            frame_id=ANALYTIC_FRAME,
            measurement=PoseSE3.identity(),
            origin="M2DGR",
        )


def test_correlated_six_by_six_covariance_supported():
    _, _, pair, _ = camera_lidar_pair()

    cov = np.asarray(
        pair["camera"].covariance
    ).copy()

    cov[0, 1] = cov[1, 0] = 0.0002

    factor = JointFactor(
        pair["camera"].packet,
        cov,
    )

    assert np.linalg.eigvalsh(
        factor.covariance
    ).min() > 0


def test_non_spd_covariance_denied():
    _, _, pair, _ = camera_lidar_pair()

    with pytest.raises(ValueError):
        JointFactor(
            pair["camera"].packet,
            np.zeros((6, 6)),
        )


def test_actual_nonlinear_perturbation_response():
    result = nonlinear_perturbation_experiment()

    assert result[
        "max_trajectory_position_change_m"
    ] > 1e-6

    assert result["shared_edges_preserved"] is True
    assert result["measurement_id_set_preserved"] is True
    assert result["factor_reuse_after_marginalization"] is False

    assert result[
        "state_response_is_physical_accuracy_metric"
    ] is False


def test_non_linear_estimator_excludes_truth_argument():
    signature = inspect.signature(estimate_joint)

    assert "truth" not in signature.parameters
    assert "reference" not in signature.parameters


@pytest.mark.parametrize(
    "condition,camera_enabled",
    (
        ("clean", False),
        ("clean", True),
        ("lidar_dropout", False),
        ("lidar_dropout", True),
    ),
)
def test_factor_chronology_under_ablation(
    condition, camera_enabled
):
    fixture, truth = make_fixture(condition)

    packets = (
        manufactured_camera_packets(
            truth,
            seed=13,
        )
        if camera_enabled else ()
    )

    _, audit = estimate_joint(
        fixture,
        packets,
    )

    assert audit["accepted_window_count"] == 4
    assert audit["schur_elimination_count"] == 3
    assert audit["unaccounted_factor_count"] == 0
    assert audit["factor_reuse_after_marginalization"] is False

    assert audit["camera_factor_count"] == (
        2 if camera_enabled else 0
    )
