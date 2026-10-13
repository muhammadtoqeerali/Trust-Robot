"""Offline camera pixel-motion characterization for preserved V15 frames."""
from __future__ import annotations

import argparse

from trust_robot.v15_visual_motion_review import review_v15
from trust_robot.visual_pixel_motion import canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recording", required=True)
    parser.add_argument("--compact-evidence", required=True)
    args = parser.parse_args()

    result = review_v15(
        args.recording, args.compact_evidence
    )

    print(canonical(result).decode(), end="")


if __name__ == "__main__":
    main()
