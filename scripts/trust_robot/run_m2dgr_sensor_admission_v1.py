"""Read-only M2DGR admission and optional frozen feature-batch inspection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from trust_robot.m2dgr_sensor_admission import (
    audit_feature_records,
    inventory,
    load_frozen_snapshot,
    require_real_factor_execution,
    SensorAdmissionError,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--feature-jsonl", type=Path)
    parser.add_argument("--trajectory")
    parser.add_argument("--stream")
    args = parser.parse_args()

    repo = args.repo.resolve(strict=True)
    snapshot = load_frozen_snapshot(repo)

    result = {"inventory": inventory(snapshot)}

    if args.feature_jsonl is not None:
        if not args.trajectory or not args.stream:
            parser.error(
                "Feature inspection requires --trajectory and --stream"
            )

        # Only dedicated project-local recordings are accepted.
        workspace = repo.parent.resolve(strict=True)
        path = args.feature_jsonl

        if not path.is_file() or path.is_symlink():
            raise SensorAdmissionError(
                "Unsafe or missing feature recording"
            )

        resolved = path.resolve(strict=True)

        if not resolved.is_relative_to(workspace):
            raise SensorAdmissionError(
                "Feature recording outside dedicated workspace"
            )

        if resolved.stat().st_size > 64*1024*1024:
            raise SensorAdmissionError(
                "Feature recording exceeds bounded input size"
            )

        def rows():
            with resolved.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        yield json.loads(line)

        result["feature_audit"] = audit_feature_records(
            snapshot,
            args.trajectory,
            args.stream,
            rows(),
        )

    print(json.dumps(
        result,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ))


if __name__ == "__main__":
    main()
