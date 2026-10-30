"""R135-A27-6: static nominal URDF frame-transform algebra.

Transforms use T_target_source: a column vector expressed
in source coordinates is mapped into target coordinates.

URDF fixed-joint origins use T_parent_child. RPY follows
Rz(yaw) @ Ry(pitch) @ Rx(roll).

Dynamic joint motion, physical calibration, clock alignment,
and BMI088 frame aliasing are deliberately unsupported.
"""

from __future__ import annotations

import math

SCHEMA = "TRUST_ROBOT_R135_A27_6_NOMINAL_FRAME_GRAPH_V1"

JOINT_TYPES = frozenset({
    "fixed", "revolute", "continuous",
    "prismatic", "planar", "floating",
})


class FrameGraphError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise FrameGraphError(message)


def _vector(value):
    require(
        type(value) in (tuple, list)
        and len(value) == 3
        and all(
            type(x) in (int, float) and math.isfinite(x)
            for x in value
        ),
        "Invalid finite XYZ/RPY vector",
    )
    return tuple(float(x) for x in value)


def _identity():
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _matmul(a, b):
    return [
        [
            sum(a[i][k] * b[k][j] for k in range(4))
            for j in range(4)
        ]
        for i in range(4)
    ]


def _inverse_rigid(t):
    result = _identity()

    for i in range(3):
        for j in range(3):
            result[i][j] = t[j][i]

    for i in range(3):
        result[i][3] = -sum(
            result[i][j] * t[j][3] for j in range(3)
        )

    return result


def _origin_matrix(xyz, rpy):
    x, y, z = _vector(xyz)
    roll, pitch, yaw = _vector(rpy)

    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    m = _identity()

    m[0][:3] = [
        cy * cp,
        cy * sp * sr - sy * cr,
        cy * sp * cr + sy * sr,
    ]
    m[1][:3] = [
        sy * cp,
        sy * sp * sr + cy * cr,
        sy * sp * cr - cy * sr,
    ]
    m[2][:3] = [
        -sp,
        cp * sr,
        cp * cr,
    ]

    m[0][3], m[1][3], m[2][3] = x, y, z

    return m


def validate_graph(document):
    """Reject malformed, disconnected or cyclic URDF graphs."""
    require(type(document) is dict, "Invalid graph document")

    links = document.get("links")
    joints = document.get("joints")

    require(
        type(links) is list
        and 1 <= len(links) <= 512
        and all(
            type(x) is str and 0 < len(x) <= 256
            for x in links
        )
        and len(set(links)) == len(links),
        "Invalid link inventory",
    )

    require(
        type(joints) is list
        and len(joints) == len(links) - 1,
        "Invalid joint count",
    )

    link_set = set(links)
    by_child = {}
    names = set()

    for joint in joints:
        require(
            type(joint) is dict
            and set(joint) == {
                "name", "type", "parent",
                "child", "xyz", "rpy",
            },
            "Invalid joint fields",
        )

        name = joint["name"]
        parent = joint["parent"]
        child = joint["child"]

        require(
            type(name) is str
            and bool(name)
            and name not in names,
            "Duplicate or invalid joint name",
        )
        names.add(name)

        require(
            type(parent) is str
            and type(child) is str
            and parent in link_set
            and child in link_set
            and parent != child
            and child not in by_child,
            "Invalid parent-child relationship",
        )

        require(
            joint["type"] in JOINT_TYPES,
            "Unsupported URDF joint type",
        )

        _vector(joint["xyz"])
        _vector(joint["rpy"])

        by_child[child] = joint

    roots = link_set - set(by_child)

    require(len(roots) == 1, "Expected one URDF root")
    root = next(iter(roots))

    for link in links:
        seen = set()
        current = link

        while current in by_child:
            require(
                current not in seen,
                "URDF joint graph cycle",
            )
            seen.add(current)
            current = by_child[current]["parent"]

        require(
            current == root,
            "Disconnected URDF graph",
        )

    return root, by_child


def relative_transform(document, source, target):
    """Return T_target_source for entirely fixed-joint chains.

    The result is nominal source configuration, not a verified
    physical sensor extrinsic.
    """
    root, by_child = validate_graph(document)
    link_set = set(document["links"])

    require(
        type(source) is str and source in link_set
        and type(target) is str and target in link_set,
        "Unknown or unqualified URDF frame",
    )

    def root_transform(frame):
        chain = []
        current = frame

        while current != root:
            joint = by_child[current]

            require(
                joint["type"] == "fixed",
                "Dynamic joint transform is unavailable",
            )

            chain.append(joint)
            current = joint["parent"]

        t = _identity()

        for joint in reversed(chain):
            t = _matmul(
                t,
                _origin_matrix(
                    joint["xyz"],
                    joint["rpy"],
                ),
            )

        return t

    t_root_source = root_transform(source)
    t_root_target = root_transform(target)

    return _matmul(
        _inverse_rigid(t_root_target),
        t_root_source,
    )


def nominal_inventory(document, selected_frames):
    """Generate private structural diagnostics, never calibration."""
    root, by_child = validate_graph(document)

    require(
        type(selected_frames) is list
        and len(selected_frames) <= 64
        and len(set(selected_frames)) == len(selected_frames),
        "Invalid frame selection",
    )

    results = {}

    for frame in selected_frames:
        require(
            type(frame) is str and frame in document["links"],
            "Unknown frame selection",
        )

        try:
            matrix = relative_transform(
                document, frame, root
            )
            results[frame] = {
                "status": "NOMINAL_STATIC_ONLY",
                "T_root_frame": [
                    [round(v, 12) for v in row]
                    for row in matrix
                ],
                "physically_validated": False,
            }
        except FrameGraphError:
            results[frame] = {
                "status": "UNAVAILABLE_DYNAMIC_PATH",
                "T_root_frame": None,
                "physically_validated": False,
            }

    return {
        "schema": SCHEMA,
        "status": "NOMINAL_URDF_GEOMETRY_ONLY",
        "root_frame": root,
        "link_count": len(document["links"]),
        "joint_count": len(by_child),
        "fixed_joint_count": sum(
            j["type"] == "fixed"
            for j in document["joints"]
        ),
        "dynamic_joint_count": sum(
            j["type"] != "fixed"
            for j in document["joints"]
        ),
        "selected_frames": results,
        "bmi088_frame_alias_assumed": False,
        "metric_extrinsic_accuracy": "UNVERIFIED",
        "transform_uncertainty": "UNVERIFIED",
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def qualify_physical_transform(*args, **kwargs):
    raise FrameGraphError(
        "Nominal URDF geometry cannot qualify physical transforms"
    )
