import dataclasses
import numpy as np
import pytest

from trust_robot.clean_backbone import PoseSE3
from trust_robot.multimodal_factor_interface import (
    CAMERA_SOURCE, ANALYTIC_FRAME, SyntheticPoseFactor,
)
from s6_joint_fusion import JointFactor, validate_factors
from s7_factor_support import camera_lidar_pair
from s8_correlated_conflict import paired_covariance, disagreement_diagnostic
from s9_adversarial import (
    RHOS, SHIFTS, DENIALS, changed_camera, stress_grid,
    require_runtime_action, solver_stress,
)


@pytest.fixture(scope="module")
def shared():
    _, packets, pair, _ = camera_lidar_pair()
    return packets, pair


@pytest.mark.parametrize("rho", RHOS)
@pytest.mark.parametrize("shift", SHIFTS)
def test_fifteen_stress_cells_are_diagnostic_only(shared, rho, shift):
    _, pair = shared
    camera, lidar = pair["camera"], pair["lidar"]
    perturbed = JointFactor(changed_camera(camera.packet, shift), camera.covariance)
    diagnostic = disagreement_diagnostic(perturbed, lidar, rho)
    assert diagnostic["handling"] == "DIAGNOSTIC_ONLY_RETAIN_BOTH_NO_RUNTIME_ACTION"
    assert diagnostic["sensor_auto_suppression_executed"] is False
    assert diagnostic["health_state_inferred"] is False
    assert diagnostic["physical_false_alarm_probability_established"] is False
    if shift == 0:
        assert diagnostic["flagged_synthetic_disagreement"] is False
    elif abs(shift) == .2:
        assert diagnostic["flagged_synthetic_disagreement"] is True


@pytest.mark.parametrize("rho", RHOS)
def test_manufactured_paired_covariance_spd(shared, rho):
    _, pair = shared
    covariance, cross = paired_covariance(pair["camera"], pair["lidar"], rho)
    assert covariance.shape == (12, 12)
    assert cross.shape == (6, 6)
    assert np.linalg.eigvalsh(covariance)[0] > 0


@pytest.mark.parametrize("rho", (True, None, "0.2", float("nan"), .8, -.8))
def test_invalid_correlation_denied(shared, rho):
    _, pair = shared
    with pytest.raises(ValueError):
        paired_covariance(pair["camera"], pair["lidar"], rho)


@pytest.mark.parametrize("shift", (True, None, "0.2", float("nan"), float("inf"), .21, -.21))
def test_invalid_camera_manipulation_denied(shared, shift):
    _, pair = shared
    with pytest.raises(ValueError):
        changed_camera(pair["camera"].packet, shift)


@pytest.mark.parametrize("action", DENIALS)
def test_four_runtime_action_attempts_denied(action):
    assert require_runtime_action(action) == "DENIED"


def test_unknown_action_denied():
    with pytest.raises(ValueError):
        require_runtime_action("allow_scoring")


def test_recorded_camera_factor_denied():
    with pytest.raises(ValueError):
        SyntheticPoseFactor(
            modality="camera", edge=(0, 1), measurement_id="forged-m2dgr",
            source_id=CAMERA_SOURCE, frame_id=ANALYTIC_FRAME,
            measurement=PoseSE3.identity(), origin="M2DGR",
        )


def test_wrong_manufactured_source_denied():
    with pytest.raises(ValueError):
        SyntheticPoseFactor(
            modality="camera", edge=(0, 1), measurement_id="forged-src",
            source_id="M2DGR_CAMERA", frame_id=ANALYTIC_FRAME,
            measurement=PoseSE3.identity(),
        )


def test_duplicate_measurement_identity_denied(shared):
    _, pair = shared
    factor = pair["camera"]
    with pytest.raises(ValueError):
        validate_factors((factor, factor))


def test_forged_second_camera_same_edge_denied(shared):
    _, pair = shared
    factor = pair["camera"]
    second = dataclasses.replace(
        factor.packet, measurement_id="different-id-same-owner"
    )
    with pytest.raises(ValueError):
        validate_factors((factor, JointFactor(second, factor.covariance)))


def test_singular_covariance_denied(shared):
    _, pair = shared
    with pytest.raises(ValueError):
        JointFactor(pair["camera"].packet, np.zeros((6, 6)))


def test_grid_stable_ledger_and_scientific_limits():
    rows, packets = stress_grid()
    assert len(rows) == 3 and len(packets) == 2
    assert sum(len(r["disagreement_grid"]) for r in rows) == 15
    assert all(r["physical_detection_rate_claimed"] is False for r in rows)
    assert all(len({e["camera_measurement_id"] for e in r["disagreement_grid"]}) == 1 for r in rows)


def test_nonlinear_solver_stress_and_ownership():
    results = solver_stress()
    assert len(results) == 3
    assert [r["camera_shift_m"] for r in results] == [-.2, 0., .2]
    assert results[1]["state_delta_from_unperturbed_m"] == 0
    assert all(r["factor_count"] == 9 and r["accepted_window_solves"] == 4 for r in results)
    assert all(r["state_delta_from_unperturbed_m"] > 1e-6 for r in (results[0], results[2]))
    assert len({r["estimated_trajectory_sha256"] for r in results}) == 3
