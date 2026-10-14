"""Offline synthetic V16 scene enrichment.

Preserves the verified V15 scene and adds deterministic
high-contrast markers for future camera observability tests.

No simulator, sensor, GPU, network or robot is accessed.
"""

from __future__ import annotations

from pathlib import Path


SCHEMA = "TRUST_ROBOT_V16_SCENE_CANDIDATE_V1"

ANCHOR = '    def Xform "CalibrationTargets"'

MARKER_ROWS = 8
MARKER_COLUMNS = 10


class V16SceneError(ValueError):
    pass


def build_v16_scene(original: str):
    if not original.startswith("#usda 1.0"):
        raise V16SceneError("Invalid USDA source header")

    if original.count(ANCHOR) != 1:
        raise V16SceneError(
            "Missing or ambiguous original scene anchor"
        )

    if '"V16FeatureTargets"' in original:
        raise V16SceneError(
            "V16 scene has already been modified"
        )

    lines = [
        '    def Xform "V16FeatureTargets"',
        "    {",
    ]

    for row in range(MARKER_ROWS):
        for col in range(MARKER_COLUMNS):
            name = f"Marker_{row:02d}_{col:02d}"

            # Multiple depths are intentional for future
            # visibility and geometric-observability checks.
            depth_index = (row + 2 * col) % 3

            x = 1.18 - 0.03 * depth_index
            y = -0.675 + 0.15 * col
            z = 0.31 + 0.12 * row

            material = (
                "Light" if (row + col) % 2 == 0
                else "Dark"
            )

            lines += [
                f'        def Cube "{name}" (',
                '            prepend apiSchemas = '
                '["MaterialBindingAPI"]',
                '        )',
                '        {',
                '            rel material:binding = '
                f'</World/V16FeatureTargets/Materials/{material}>',
                '            double size = 1',
                '            float3 xformOp:scale = '
                '(0.020, 0.130, 0.105)',
                '            double3 xformOp:translate = '
                f'({x:.4f}, {y:.4f}, {z:.4f})',
                '            uniform token[] xformOpOrder = '
                '["xformOp:translate", "xformOp:scale"]',
                '        }',
            ]

    lines += [
        '        def Xform "Materials"',
        '        {',
    ]

    for name, color in (
        ("Light", "(0.95, 0.95, 0.95)"),
        ("Dark", "(0.025, 0.025, 0.025)"),
    ):
        target = (
            "/World/V16FeatureTargets/Materials/"
            f"{name}/Surface.outputs:surface"
        )

        lines += [
            f'            def Material "{name}"',
            '            {',
            '                token outputs:surface.connect = '
            f'<{target}>',
            '                def Shader "Surface"',
            '                {',
            '                    uniform token info:id = '
            '"UsdPreviewSurface"',
            '                    color3f inputs:diffuseColor = '
            f'{color}',
            '                    color3f inputs:emissiveColor = '
            f'{color}',
            '                    float inputs:roughness = 0.8',
            '                    token outputs:surface',
            '                }',
            '            }',
        ]

    lines += [
        '        }',
        '    }',
        '',
    ]

    insertion = "\n".join(lines)

    modified = original.replace(
        ANCHOR,
        insertion + ANCHOR,
        1,
    )

    if modified.count('def Cube "Marker_') != 80:
        raise V16SceneError(
            "Incorrect generated marker count"
        )

    return modified


def validate_output_destination(
    workspace: Path,
    destination: Path,
):
    """Fail closed on shared-host output paths."""

    workspace = Path(workspace)
    destination = Path(destination)

    expected = Path("/home/kios/TRUST_ROBOT_ALI")

    if workspace != expected:
        raise V16SceneError(
            "Workspace is not the dedicated KIOS directory"
        )

    if (
        workspace.is_symlink()
        or not workspace.is_dir()
    ):
        raise V16SceneError(
            "Unsafe project workspace"
        )

    parent = workspace / "experiments"

    if parent.is_symlink() or not parent.is_dir():
        raise V16SceneError(
            "Unsafe experiment parent directory"
        )

    if not destination.is_absolute():
        raise V16SceneError(
            "Destination must be absolute"
        )

    if destination.parent != parent:
        raise V16SceneError(
            "Destination must be directly inside "
            "the dedicated experiments directory"
        )

    if not destination.name.startswith(
        "isaacsim_v16_"
    ):
        raise V16SceneError(
            "Destination must be a V16-specific directory"
        )

    if (
        destination.exists()
        or destination.is_symlink()
    ):
        raise V16SceneError(
            "Existing experiment output cannot be overwritten"
        )

    return destination
