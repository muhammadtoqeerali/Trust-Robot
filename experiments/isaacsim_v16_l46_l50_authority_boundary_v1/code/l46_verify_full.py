"""L46 separate-process reproduction of synthetic authority tests.

Uses the same prototype implementation with fresh ephemeral keys.
This is not independently administered source attestation.
"""

import argparse
import hashlib
import json
from pathlib import Path

from l46_engine_full import exercise


def need(ok, reason):
    if not ok:
        raise AssertionError(reason)


def digest(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def main():
    parser = argparse.ArgumentParser()

    for name in (
        "engine",
        "l41",
        "l45",
        "contract",
        "report",
        "validation",
    ):
        parser.add_argument(
            "--" + name,
            required=True,
        )

    a = parser.parse_args()

    c = json.loads(
        Path(a.contract).read_text()
    )

    r = json.loads(
        Path(a.report).read_text()
    )

    need(
        c["schema"]
        == "TRUST_ROBOT_L46_AUTHORITY_TRUST_BOUNDARY_CONTRACT_V1",
        "CONTRACT_SCHEMA",
    )

    need(
        r["schema"]
        == "TRUST_ROBOT_L46_SYNTHETIC_AUTHORITY_FALSIFICATION_V1",
        "REPORT_SCHEMA",
    )

    need(
        c["simulation_source_sha256"]
        == r["source_sha256"]
        == digest(a.engine),
        "SOURCE_HASH",
    )

    need(
        c["l41_sha256"] == digest(a.l41)
        and c["l45_sha256"] == digest(a.l45),
        "EVIDENCE_HASH",
    )

    need(
        r["contract_sha256"] == digest(a.contract),
        "CONTRACT_HASH",
    )

    # New ephemeral keys; fresh test execution.
    fresh = exercise()

    need(
        fresh == r["test_results"],
        "FRESH_TEST_RESULT_MISMATCH",
    )

    need(
        fresh["negative_controls_denied"] == 35
        and len(set(
            fresh["negative_control_names"]
        )) == 35,
        "CONTROL_COUNTS",
    )

    need(
        fresh[
            "coherent_software_forgery_internally_accepted"
        ] is True
        and fresh[
            "coherent_software_forgery_trusted"
        ] is False,
        "FORGERY_INTERPRETATION",
    )

    need(
        fresh[
            "independent_registry_clone_double_acceptance"
        ] is True,
        "SPLIT_REGISTRY",
    )

    for field in (
        "key_material_persisted",
        "independent_physical_trust_established",
        "live_simulator_launch_authorized",
    ):
        need(
            c[field] is False,
            "CONTRACT_" + field,
        )

    for field in (
        "ephemeral_key_material_archived",
        "physical_source_authenticity_verified",
        "hardware_attestation_verified",
        "trusted_clock_verified",
        "multi_host_replay_protection_verified",
        "real_power_loss_durability_verified",
        "simulator_launch_authorized",
    ):
        need(
            r[field] is False,
            "REPORT_" + field,
        )

    for field in (
        "new_sensor_acquisitions",
        "pose_factors_authorized",
        "health_labels_generated",
    ):
        need(
            r[field] == 0,
            "SCIENCE_" + field,
        )

    data = {
        "schema":
            "TRUST_ROBOT_L46_SEPARATE_PROCESS_VALIDATION_V1",
        "engine_sha256": digest(a.engine),
        "verifier_sha256": digest(__file__),
        "contract_sha256": digest(a.contract),
        "report_sha256": digest(a.report),
        "fresh_negative_controls_reproduced": 35,
        "coherent_software_forgery_trusted": False,
        "shared_registry_qualified": False,
        "independent_physical_witness_qualified": False,
        "simulator_launch_authorized": False,
        "new_sensor_acquisitions": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    with Path(a.validation).open(
        "x",
        encoding="utf-8",
    ) as f:
        f.write(
            json.dumps(
                data,
                indent=2,
                sort_keys=True,
            ) + "\n"
        )

    print(
        "L46_FRESH_SEPARATE_PROCESS_NEGATIVE_CONTROLS="
        "35_REPRODUCED"
    )
    print("L46_INDEPENDENT_REPORT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
