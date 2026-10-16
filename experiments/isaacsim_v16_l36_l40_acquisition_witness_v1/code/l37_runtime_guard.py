"""L37 runtime hooks: preparation only, live acquisition disabled."""

from pathlib import Path

EXPECTED_ROOT = Path(
    "/home/kios/TRUST_ROBOT_ALI/experiments/"
    "isaacsim_v16_l37_witness_candidate_v1"
)

def preflight_gate(candidate_root, scene, metadata, output):
    root = Path(candidate_root)

    if root != EXPECTED_ROOT:
        raise ValueError("L37_CANDIDATE_ROOT_MISMATCH")

    if Path(scene) != root / "multimodal_scene_v5.usda":
        raise ValueError("L37_SCENE_PATH_MISMATCH")

    if Path(metadata) != root / "multimodal_probe_validation_v15.json":
        raise ValueError("L37_METADATA_PATH_MISMATCH")

    if Path(output) != root / "multimodal_probe_results_v15":
        raise ValueError("L37_OUTPUT_PATH_MISMATCH")

    # L36 is an offline design, not persistent replay protection.
    # No L37 live authorization mechanism exists.
    raise PermissionError(
        "L37_LIVE_SIMULATOR_LAUNCH_NOT_AUTHORIZED"
    )

def seal_after_capture(candidate_root, envelope):
    root = Path(candidate_root)

    if root != EXPECTED_ROOT:
        raise ValueError("L37_SEAL_ROOT_MISMATCH")

    if Path(envelope) != (
        root / "multimodal_probe_results_v15"
        / "l29_runtime_envelope_v1"
    ):
        raise ValueError("L37_SEAL_ENVELOPE_MISMATCH")

    # This interface location is intentionally prepared only.
    # A source-independent capture witness is not yet implemented.
    raise PermissionError(
        "L37_LIVE_CAPTURE_SEAL_NOT_QUALIFIED"
    )
