#!/usr/bin/env python3
"""Execute deterministic multimodal replay over the exact frozen M2DGR TRAIN.

This runner opens only the 22 frozen TRAIN bags. It writes aggregate replay
evidence only; it does not persist raw per-message payloads.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
import json
import os
import shutil
import sys

from trust_robot.deterministic_multimodal_dataset_replay import (
    FROZEN_SPLIT_SHA256,
    iter_anyreader_replay,
    load_train_replay_source_from_manifest_file,
    resolve_train_bag_path,
)
from trust_robot.deterministic_multimodal_dataset_replay_run import (
    RUN_ID,
    TrajectoryReplayAggregateBuilder,
    build_candidate_contract,
    build_run_manifest,
    build_success_payload,
    build_trajectory_record,
    file_sha256,
)
from trust_robot.software_evidence_completion import (
    TRAIN_TRAJECTORIES,
)


def atomic_json(
    path: Path,
    payload: Any,
) -> None:
    temporary = path.with_name(
        path.name
        + ".partial"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--split-manifest",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    dataset_root = (
        args.dataset_root.resolve()
    )

    split_manifest = (
        args.split_manifest.resolve()
    )

    output_dir = (
        args.output_dir.resolve()
    )

    if not dataset_root.is_dir():
        raise RuntimeError(
            f"dataset root does not exist: {dataset_root}"
        )

    if not split_manifest.is_file():
        raise RuntimeError(
            f"split manifest does not exist: {split_manifest}"
        )

    if file_sha256(
        split_manifest
    ) != FROZEN_SPLIT_SHA256:
        raise RuntimeError(
            "split manifest SHA-256 differs from frozen SE1 contract"
        )

    if output_dir.exists():
        raise RuntimeError(
            f"output directory already exists: {output_dir}"
        )

    staging = output_dir.with_name(
        output_dir.name
        + ".partial"
    )

    if staging.exists():
        raise RuntimeError(
            f"partial output already exists: {staging}"
        )

    staging.mkdir(
        parents=True,
        exist_ok=False,
    )

    trajectory_dir = (
        staging
        / "trajectories"
    )

    trajectory_dir.mkdir()

    try:
        candidate = (
            build_candidate_contract()
        )

        atomic_json(
            staging
            / "candidate_contract.json",
            candidate,
        )

        trajectory_records = []

        for trajectory_id in TRAIN_TRAJECTORIES:
            source = (
                load_train_replay_source_from_manifest_file(
                    split_manifest,
                    trajectory_id,
                )
            )

            bag_path = (
                resolve_train_bag_path(
                    dataset_root,
                    source,
                )
            )

            print(
                f"trajectory_start={trajectory_id} "
                f"bag_bytes={bag_path.stat().st_size}",
                flush=True,
            )

            builder = (
                TrajectoryReplayAggregateBuilder(
                    source
                )
            )

            for envelope in iter_anyreader_replay(
                source,
                bag_path,
            ):
                builder.add(
                    envelope
                )

            trajectory_payload = (
                builder.payload(
                    bag_file_size_bytes=(
                        bag_path.stat().st_size
                    ),
                )
            )

            trajectory_path = (
                trajectory_dir
                / f"{trajectory_id}.json"
            )

            atomic_json(
                trajectory_path,
                trajectory_payload,
            )

            trajectory_record = (
                build_trajectory_record(
                    trajectory_payload=trajectory_payload,
                    trajectory_file_sha256=file_sha256(
                        trajectory_path
                    ),
                )
            )

            trajectory_records.append(
                trajectory_record
            )

            print(
                f"trajectory_complete={trajectory_id} "
                f"messages={trajectory_payload['message_count']} "
                f"bytes={trajectory_payload['total_serialized_payload_bytes']}",
                flush=True,
            )

        run_manifest = (
            build_run_manifest(
                dataset_root=str(
                    dataset_root
                ),
                candidate_contract_content_sha256=(
                    candidate[
                        "content_sha256"
                    ]
                ),
                trajectory_records=trajectory_records,
            )
        )

        run_manifest_path = (
            staging
            / "run_manifest.json"
        )

        atomic_json(
            run_manifest_path,
            run_manifest,
        )

        success_payload = (
            build_success_payload(
                run_manifest_file_sha256=file_sha256(
                    run_manifest_path
                ),
                run_manifest_content_sha256=(
                    run_manifest[
                        "content_sha256"
                    ]
                ),
                total_selected_replay_messages=(
                    run_manifest[
                        "total_selected_replay_messages"
                    ]
                ),
                total_selected_serialized_payload_bytes=(
                    run_manifest[
                        "total_selected_serialized_payload_bytes"
                    ]
                ),
            )
        )

        atomic_json(
            staging
            / "SUCCESS.json",
            success_payload,
        )

        os.replace(
            staging,
            output_dir,
        )

        print(
            "SE1_DETERMINISTIC_MULTIMODAL_DATASET_REPLAY=PASS",
            flush=True,
        )

        print(
            f"run_id={RUN_ID}",
            flush=True,
        )

        print(
            f"output_dir={output_dir}",
            flush=True,
        )

        return 0

    except BaseException:
        if staging.exists():
            shutil.rmtree(
                staging
            )

        raise


if __name__ == "__main__":
    sys.exit(
        main()
    )
