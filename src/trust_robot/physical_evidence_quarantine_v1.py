"""R135-A32-2: read-only preflight of quarantined artifact bytes.

An explicitly supplied private directory is trusted by caller.
Only one direct-child regular file can be inspected.

A SHA match and valid candidate format do not establish
artifact authenticity, independent witnessing, physical
calibration, event accuracy or scientific admissibility.
"""

import os
import re
import stat
from pathlib import Path

from trust_robot.independent_evidence_intake_v1 import (
    preflight_candidate,
)

SCHEMA = "TRUST_ROBOT_R135_A32_2_QUARANTINE_PREFLIGHT_V1"
MAX_BYTES = 2_000_000


class EvidenceQuarantineError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise EvidenceQuarantineError(message)


def review_quarantined_candidate(root, filename, candidate):
    """Read a direct-child artifact without following final symlinks.

    No file is created, changed, copied, uploaded or qualified.
    """
    require(
        type(root) is str
        and bool(root)
        and os.path.isabs(root),
        "Expected an explicit absolute quarantine root",
    )

    require(
        type(filename) is str
        and bool(re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}",
            filename,
        ))
        and filename not in (".", ".."),
        "Unsafe artifact filename",
    )

    directory = Path(root)

    require(
        directory.is_dir()
        and not directory.is_symlink(),
        "Quarantine root unavailable or linked",
    )

    dir_fd = None
    file_fd = None

    try:
        dir_fd = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )

        file_fd = os.open(
            filename,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=dir_fd,
        )

        before = os.fstat(file_fd)

        require(
            stat.S_ISREG(before.st_mode)
            and 0 < before.st_size <= MAX_BYTES,
            "Candidate is not a bounded regular file",
        )

        with os.fdopen(os.dup(file_fd), "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)

        after = os.fstat(file_fd)

        require(
            0 < len(raw) <= MAX_BYTES
            and len(raw) == before.st_size
            and before.st_ino == after.st_ino
            and before.st_dev == after.st_dev
            and before.st_size == after.st_size
            and before.st_mtime_ns == after.st_mtime_ns
            and before.st_ctime_ns == after.st_ctime_ns,
            "Candidate changed during byte inspection",
        )

        try:
            review = preflight_candidate(candidate, raw)
        except (ValueError, TypeError, KeyError) as exc:
            raise EvidenceQuarantineError(
                "A23 candidate preflight rejected artifact"
            ) from exc

    except OSError as exc:
        raise EvidenceQuarantineError(
            "Unsafe or unreadable candidate path"
        ) from exc

    finally:
        if file_fd is not None:
            os.close(file_fd)
        if dir_fd is not None:
            os.close(dir_fd)

    require(
        review["real_factor_count"] == 0
        and review["real_factor_admission"] == "DENIED"
        and review["qualifying_receipt_created"] is False
        and review["witness_independence_verified"] is False,
        "Candidate scientific boundary changed",
    )

    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_CANDIDATE_BYTE_PREFLIGHT_ONLY",
        "request_id": review["request_id"],
        "artifact_sha256": review["candidate_artifact_sha256"],
        "artifact_byte_count": review["candidate_artifact_bytes"],
        "artifact_authenticity_verified": False,
        "independent_witness_verified": False,
        "independent_physical_measurement_verified": False,
        "candidate_receipt_qualified": False,
        "physical_event_time_verified": False,
        "physical_calibration_verified": False,
        "real_factor_count": 0,
        "real_factor_admission": "DENIED",
        "m2dgr_gates": "11_CLOSED",
    }


def release_physical_evidence(*args, **kwargs):
    raise EvidenceQuarantineError(
        "Artifact preflight cannot release qualified evidence"
    )
