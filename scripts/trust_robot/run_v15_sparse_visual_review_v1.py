"""Hash-verified review of preserved synthetic V15 camera imagery."""
from __future__ import annotations

import argparse

from trust_robot.v15_sparse_visual_review import (
    review_v15_sparse,
)
from trust_robot.visual_sparse_correspondence import (
    canonical,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recording", required=True)
    parser.add_argument("--compact-evidence", required=True)
    args = parser.parse_args()

    row = review_v15_sparse(
        args.recording,
        args.compact_evidence,
    )

    print(canonical(row).decode(), end="")


if __name__ == "__main__":
    main()
