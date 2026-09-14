from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

from .types import P0Pair


def build_pair_manifest(
    pair: P0Pair,
) -> dict:

    payload = {
        "schema":
            "P0_PAIRED_CORRUPTION_V1",

        "clean": {
            "source_id":
                pair.clean.source_id,
            "n_samples":
                pair.clean.n_samples,
            "n_channels":
                pair.clean.n_channels,
            "fingerprint":
                pair.clean.fingerprint(),
        },

        "corrupt": {
            "source_id":
                pair.corrupt.source_id,
            "n_samples":
                pair.corrupt.n_samples,
            "n_channels":
                pair.corrupt.n_channels,
            "fingerprint":
                pair.corrupt.fingerprint(),
        },

        "truths": [
            truth.manifest_dict()
            for truth in pair.truths
        ],
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    payload[
        "manifest_content_sha256"
    ] = sha256(
        canonical
    ).hexdigest()

    return payload


def manifest_json(
    pair: P0Pair,
) -> str:

    return json.dumps(
        build_pair_manifest(pair),
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def write_immutable_manifest(
    path,
    pair: P0Pair,
) -> Path:
    """
    Write once.

    Re-writing identical content is permitted and is a no-op.
    Attempting to replace the path with different content raises.
    """

    path = Path(path)

    content = manifest_json(
        pair
    )

    if path.exists():

        existing = path.read_text(
            encoding="utf-8"
        )

        if existing != content:
            raise FileExistsError(
                "Immutable manifest already exists with "
                f"different content: {path}"
            )

        return path

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp.write_text(
        content,
        encoding="utf-8",
    )

    temp.replace(
        path
    )

    return path
