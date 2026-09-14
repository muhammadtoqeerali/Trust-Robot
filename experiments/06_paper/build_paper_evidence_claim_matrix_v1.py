from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]


PRE_MATRIX_HEAD = (
    "9e53db33f64dede8db34e6fcd5a96421557b4a98"
)

CONVERGENCE_COMMIT = (
    "9e53db33f64dede8db34e6fcd5a96421557b4a98"
)

INTEGRITY_FINAL_COMMIT = (
    "b1aaa28a5cd2222bd3acc7d5d86289ba9fd71c74"
)

OOD_FINAL_COMMIT = (
    "7d7db3d1efec177830239597803410384c154f07"
)

OOD_OPERATING_POINT_COMMIT = (
    "fea9316d8510a5841baba48d273973e0267e4b28"
)

INTEGRITY_OPERATING_POINT_COMMIT = (
    "9ac878ea6a40e8c01a60e42e602a1fa9fc688d3b"
)

HOST_RESOURCE_COMMIT = (
    "d97403737804eeaeeecd009b4407949b52fe6d48"
)

REFERENCE_RUNTIME_COMMIT = (
    "4755a74fe558021576934674e338865a36df5b55"
)

PORTABLE_C_COMMIT = (
    "3f0db77158cc59e4273f75b076fef53aa6b1f413"
)

TOOLCHAIN_BLOCKER_COMMIT = (
    "2d858320ba0122f483f759a50755a711c2c9ea78"
)

ONNX_BLOCKER_COMMIT = (
    "ea2653fe08a6b684ad652e0a0ad8ff8191e2632b"
)

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)


LEDGER = (
    ROOT
    / "configs/embedded/"
      "embedded_evidence_convergence_ledger_v1.json"
)

OUTPUT = (
    ROOT
    / "configs/paper/"
      "paper_evidence_claim_matrix_v1.json"
)


LEDGER_RAW_SHA256 = (
    "d58f375362fe0936bb8f153ad4a82693"
    "980b9ca2c6894ab2e91117ee021987a7"
)

LEDGER_CONTENT_SHA256 = (
    "a687c6bc71ad3d7672be3dfd388ab2ee"
    "0b56285fe4553c670a53a571175e095b"
)


def raw_hash(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_digest(
    payload,
) -> str:
    normalized = json.loads(
        json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        )
    )

    return sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def canonical_existing(
    path: Path,
) -> str:
    data = json.loads(
        path.read_text()
    )

    payload = deepcopy(
        data
    )

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            f"Canonical hash mismatch: {path}"
        )

    return stored


def git(
    *args: str,
) -> str:
    return subprocess.check_output(
        [
            "/usr/bin/git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_git_anchors() -> None:
    if git(
        "rev-parse",
        "HEAD",
    ) != PRE_MATRIX_HEAD:
        raise RuntimeError(
            "HEAD changed before paper evidence matrix freeze"
        )

    expected = {
        "embedded-evidence-convergence-ledger-v1^{commit}":
            CONVERGENCE_COMMIT,

        "integrity-final-test-result-v1^{commit}":
            INTEGRITY_FINAL_COMMIT,

        "ood-final-test-result-v1^{commit}":
            OOD_FINAL_COMMIT,

        "ood-operating-point-v1^{commit}":
            OOD_OPERATING_POINT_COMMIT,

        "integrity-operating-point-v1^{commit}":
            INTEGRITY_OPERATING_POINT_COMMIT,

        "runtime-resource-overhead-result-v1^{commit}":
            HOST_RESOURCE_COMMIT,

        "runtime-reference-implementation-v1^{commit}":
            REFERENCE_RUNTIME_COMMIT,

        "portable-c-runtime-implementation-v1^{commit}":
            PORTABLE_C_COMMIT,

        "prospective-embedded-build-toolchain-blocker-v1^{commit}":
            TOOLCHAIN_BLOCKER_COMMIT,

        "prospective-model-export-execution-environment-contract-v1^{commit}":
            ONNX_BLOCKER_COMMIT,

        "baseline-date2025-cnn400-v1^{commit}":
            BASELINE_COMMIT,
    }

    for ref, expected_commit in expected.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected_commit:
            raise RuntimeError(
                f"Frozen evidence tag moved: {ref}"
            )


def verify_convergence_ledger() -> dict:
    if raw_hash(
        LEDGER
    ) != LEDGER_RAW_SHA256:
        raise RuntimeError(
            "Convergence ledger raw bytes changed"
        )

    if (
        canonical_existing(
            LEDGER
        )
        != LEDGER_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Convergence ledger content changed"
        )

    ledger = json.loads(
        LEDGER.read_text()
    )

    if (
        ledger[
            "next_decision_boundary"
        ][
            "workstation_only_embedded_engineering_exhausted"
        ]
        is not True
    ):
        raise RuntimeError(
            "Workstation convergence boundary changed"
        )

    return ledger


def claim(
    claim_id: str,
    section: str,
    status: str,
    wording: str,
    evidence,
    *,
    qualification: str | None = None,
    prohibited_interpretations=None,
) -> dict:
    return {
        "claim_id":
            claim_id,

        "manuscript_section":
            section,

        "status":
            status,

        "approved_wording":
            wording,

        "qualification":
            qualification,

        "evidence":
            evidence,

        "prohibited_interpretations":
            list(
                prohibited_interpretations
                or []
            ),
    }


def build_matrix() -> dict:
    ledger = (
        verify_convergence_ledger()
    )

    verify_git_anchors()

    claims = [
        claim(
            "BASELINE_SURVIVING_CHECKPOINT",
            "Methods / Historical baseline",
            "SUPPORTED_WITH_QUALIFICATION",
            (
                "The study uses the exact surviving historical DATE-2025 "
                "400 ms CNN checkpoint as the protected task model."
            ),
            [
                {
                    "tag":
                        "baseline-date2025-cnn400-v1",

                    "commit":
                        BASELINE_COMMIT,

                    "checkpoint_sha256":
                        "ee7c0079bfb8555bff45c3077cc24eaa"
                        "4373c57729045d92a831a1d7a3ea9bb1",
                }
            ],
            qualification=(
                "Training/model lineage is high-confidence reconstructed; "
                "the historical deployed STM32 firmware/export was not recovered."
            ),
            prohibited_interpretations=[
                "exact deployed STM32 firmware recovered",
                "exact historical embedded export recovered",
            ],
        ),

        claim(
            "RUNTIME_TASK_DECISION",
            "Methods / Runtime semantics",
            "SUPPORTED",
            (
                "The protected historical task rule returns Falling only "
                "when P(Falling) is strictly greater than 0.9; otherwise "
                "it returns Activity."
            ),
            [
                {
                    "tag":
                        "runtime-reference-implementation-v1",

                    "commit":
                        REFERENCE_RUNTIME_COMMIT,
                }
            ],
            prohibited_interpretations=[
                "plain argmax task decision",
                "classifier bypass",
            ],
        ),

        claim(
            "INTEGRITY_SELECTED_CAUSE",
            "Methods / Integrity gate",
            "SUPPORTED",
            (
                "The selected V1 integrity operating point promotes only "
                "qualified FRAME_GAP evidence to the hard integrity-alert state."
            ),
            [
                {
                    "tag":
                        "integrity-operating-point-v1",

                    "commit":
                        INTEGRITY_OPERATING_POINT_COMMIT,
                }
            ],
            prohibited_interpretations=[
                "repeated vectors prove frame repetition",
                "duplicate timestamps prove buffer stall",
                "synthetic rail thresholds prove physical saturation",
                "timing observations are hard causes in selected V1",
            ],
        ),

        claim(
            "INTEGRITY_FINAL_KFALL",
            "Results / Integrity",
            "SUPPORTED",
            (
                "On the frozen KFall final integrity evaluation, "
                "FRAME_GAP detection achieved 932/932 event recall "
                "with zero-window detection latency."
            ),
            [
                {
                    "tag":
                        "integrity-final-test-result-v1",

                    "commit":
                        INTEGRITY_FINAL_COMMIT,
                }
            ],
        ),

        claim(
            "INTEGRITY_CLEAN_ALERTS",
            "Results / Integrity",
            "SUPPORTED",
            (
                "The frozen clean integrity evaluation produced zero hard "
                "alerts across 932 clean KFall trials (1.97178 h) and "
                "176 clean UniVR trials (0.726253 h)."
            ),
            [
                {
                    "tag":
                        "integrity-final-test-result-v1",

                    "commit":
                        INTEGRITY_FINAL_COMMIT,
                }
            ],
        ),

        claim(
            "INTEGRITY_UNIVR_BOUNDARY",
            "Results / Integrity",
            "SUPPORTED_WITH_QUALIFICATION",
            (
                "UniVR produced 0/176 qualified FRAME_GAP detections under "
                "the selected policy because its derived counter does not "
                "constitute qualified hardware frame-counter evidence."
            ),
            [
                {
                    "tag":
                        "integrity-final-test-result-v1",

                    "commit":
                        INTEGRITY_FINAL_COMMIT,
                }
            ],
            qualification=(
                "This is a provenance/evidence boundary, not evidence that "
                "UniVR contains no acquisition faults."
            ),
        ),

        claim(
            "OOD_METHOD",
            "Methods / OOD gate",
            "SUPPORTED",
            (
                "OOD_UNKNOWN is assigned when the absolute top-two binary "
                "logit margin is strictly below the frozen threshold "
                "0.00914505124092102."
            ),
            [
                {
                    "tag":
                        "ood-operating-point-v1",

                    "commit":
                        OOD_OPERATING_POINT_COMMIT,
                }
            ],
        ),

        claim(
            "OOD_FINAL_COUNTS",
            "Results / OOD",
            "SUPPORTED_WITH_QUALIFICATION",
            (
                "Across 366,507 frozen final-test windows, the selected "
                "OOD gate marked 4 windows OOD_UNKNOWN and accepted "
                "366,503 windows, corresponding to an acceptance rate of "
                "0.9999890861566082."
            ),
            [
                {
                    "tag":
                        "ood-final-test-result-v1",

                    "commit":
                        OOD_FINAL_COMMIT,
                }
            ],
            qualification=(
                "The four OOD_UNKNOWN windows are descriptive residual "
                "unfamiliarity events, not labeled true-OOD detections."
            ),
            prohibited_interpretations=[
                "OOD recall",
                "novelty-detection sensitivity",
                "sensor-failure recall",
                "four true anomalies detected",
            ],
        ),

        claim(
            "OOD_DATASET_BREAKDOWN",
            "Results / OOD",
            "SUPPORTED_WITH_QUALIFICATION",
            (
                "The four OOD_UNKNOWN windows were distributed as "
                "2 KFall, 2 OnField, and 0 UniVR windows."
            ),
            [
                {
                    "tag":
                        "ood-final-test-result-v1",

                    "commit":
                        OOD_FINAL_COMMIT,
                }
            ],
            qualification=(
                "Dataset membership does not provide ground-truth OOD labels."
            ),
        ),

        claim(
            "TRUST_PRECEDENCE",
            "Methods / Runtime integration",
            "SUPPORTED",
            (
                "The frozen primary-state precedence is "
                "INTEGRITY_ALERT, then OOD_UNKNOWN, then VALID, "
                "while the task prediction is always returned."
            ),
            [
                {
                    "tag":
                        "runtime-reference-implementation-v1",

                    "commit":
                        REFERENCE_RUNTIME_COMMIT,
                }
            ],
        ),

        claim(
            "ONE_FORWARD",
            "Methods / Runtime integration",
            "SUPPORTED",
            (
                "Reliability assessment reuses logits from exactly one full "
                "task-model forward per window and does not perform a second "
                "task forward for OOD scoring."
            ),
            [
                {
                    "tag":
                        "runtime-reference-implementation-v1",

                    "commit":
                        REFERENCE_RUNTIME_COMMIT,
                }
            ],
        ),

        claim(
            "HOST_RUNTIME_OVERHEAD",
            "Results / Computational evidence",
            "SUPPORTED_WITH_QUALIFICATION",
            (
                "On the frozen x86-64 reference host benchmark, median "
                "task-only latency was 128.520 us and median integrated "
                "latency was 149.388 us, an incremental 20.868 us "
                "(16.237161531279177%)."
            ),
            [
                {
                    "tag":
                        "runtime-resource-overhead-result-v1",

                    "commit":
                        HOST_RESOURCE_COMMIT,
                }
            ],
            qualification=(
                "These measurements are reference-host observations only."
            ),
            prohibited_interpretations=[
                "STM32 latency",
                "STM32 cycle count",
                "embedded deadline proof",
            ],
        ),

        claim(
            "HOST_POST_LOGIT_COST",
            "Results / Computational evidence",
            "SUPPORTED_WITH_QUALIFICATION",
            (
                "Reference-host post-logit median times were 19.406 us "
                "for VALID, 19.436 us for OOD_UNKNOWN, and 20.358 us "
                "for INTEGRITY_ALERT."
            ),
            [
                {
                    "tag":
                        "runtime-resource-overhead-result-v1",

                    "commit":
                        HOST_RESOURCE_COMMIT,
                }
            ],
            qualification=(
                "These values are Python/reference-host measurements and "
                "must not be relabeled as embedded timing."
            ),
        ),

        claim(
            "PORTABLE_C_PARITY",
            "Results / Embedded reference implementation",
            "SUPPORTED",
            (
                "The prospective portable-C post-logit reliability core "
                "passed 13 native C tests and 9 Python-to-C parity tests, "
                "including a deterministic 162-case float32 grid."
            ),
            [
                {
                    "tag":
                        "portable-c-runtime-implementation-v1",

                    "commit":
                        PORTABLE_C_COMMIT,
                }
            ],
        ),

        claim(
            "PORTABLE_C_LINEAGE",
            "Methods / Embedded reference implementation",
            "SUPPORTED_WITH_QUALIFICATION",
            (
                "The C implementation is a prospective embedded reference "
                "implementation of the frozen post-logit reliability semantics."
            ),
            [
                {
                    "tag":
                        "portable-c-runtime-implementation-v1",

                    "commit":
                        PORTABLE_C_COMMIT,
                }
            ],
            qualification=(
                "It is not evidence of recovered historical STM32 firmware."
            ),
        ),

        claim(
            "ONNX_STATUS",
            "Limitations / Target realization",
            "SUPPORTED",
            (
                "A prospective float32 ONNX export protocol and exporter "
                "were frozen, but execution remains blocked because no "
                "qualified single environment with Torch, ONNX, and "
                "ONNX Runtime was recovered."
            ),
            [
                {
                    "tag":
                        "prospective-model-export-execution-environment-contract-v1",

                    "commit":
                        ONNX_BLOCKER_COMMIT,
                }
            ],
            prohibited_interpretations=[
                "ONNX export validated",
                "STM32 model importability validated",
            ],
        ),

        claim(
            "TOOLCHAIN_STATUS",
            "Limitations / Target realization",
            "SUPPORTED",
            (
                "STM32F722 target compilation remains blocked because no "
                "qualified ARM GNU bare-metal toolchain or STM32 SDK was "
                "recovered from the searched workstation evidence."
            ),
            [
                {
                    "tag":
                        "prospective-embedded-build-toolchain-blocker-v1",

                    "commit":
                        TOOLCHAIN_BLOCKER_COMMIT,
                }
            ],
            qualification=(
                "The absence claim is limited to searched/available "
                "workstation evidence."
            ),
        ),

        claim(
            "STM32_RESOURCE_STATUS",
            "Limitations / Target realization",
            "SUPPORTED",
            (
                "No STM32F722 flash, RAM, cycle, latency, or energy "
                "measurement is claimed."
            ),
            [
                {
                    "tag":
                        "embedded-evidence-convergence-ledger-v1",

                    "commit":
                        CONVERGENCE_COMMIT,
                }
            ],
        ),
    ]

    payload = {
        "matrix_id":
            "PAPER_EVIDENCE_CLAIM_MATRIX_V1",

        "status":
            "frozen_claim_scope_for_manuscript_synthesis",

        "source_convergence_ledger": {
            "tag":
                "embedded-evidence-convergence-ledger-v1",

            "commit":
                CONVERGENCE_COMMIT,

            "raw_sha256":
                LEDGER_RAW_SHA256,

            "content_sha256":
                LEDGER_CONTENT_SHA256,
        },

        "paper_positioning": {
            "core_contribution":
                (
                    "Evidence-gated reliability semantics that preserve the "
                    "protected task classifier while exposing distinct "
                    "integrity-alert and residual-unfamiliarity trust states."
                ),

            "embedded_positioning":
                (
                    "Host-validated prospective portable-C post-logit "
                    "reference implementation with explicit target-infrastructure "
                    "limitations."
                ),

            "not_positioned_as":
                [
                    "new fall classifier",
                    "STM32 deployment benchmark",
                    "sensor-fault diagnostic classifier",
                    "general-purpose OOD detector with labeled-OOD recall",
                ],
        },

        "claims":
            claims,

        "global_prohibited_wording": [
            "exact deployed firmware",
            "exact historical STM32 export",
            "deployed STM32 latency",
            "STM32 flash usage measured",
            "STM32 RAM usage measured",
            "STM32 cycle count measured",
            "STM32 energy measured",
            "OOD recall",
            "sensor-failure detection rate",
            "four true OOD events detected",
            "timing anomaly proves sensor failure",
            "duplicate timestamp proves buffer stall",
            "repeated vector proves frame repetition",
        ],

        "results_that_must_not_be_recomputed": [
            "integrity final-test result V1",
            "OOD calibration result V1",
            "OOD final-test result V1",
            "runtime resource-overhead benchmark V1",
        ],

        "manuscript_section_map": {
            "Introduction":
                [
                    "motivation for reliability/trust state separation",
                    "preserving protected task behavior",
                    "evidence-qualified integrity causes",
                ],

            "Methods":
                [
                    "historical classifier decision rule",
                    "integrity evidence contract",
                    "OOD logit-margin contract",
                    "trust-state precedence",
                    "one-forward runtime integration",
                    "portable-C prospective reference",
                ],

            "Results":
                [
                    "integrity final evaluation",
                    "OOD final descriptive results",
                    "reference-host overhead",
                    "portable-C host semantic parity",
                ],

            "Embedded feasibility":
                [
                    "prospective portable-C implementation",
                    "reference-host-only computational evidence",
                    "ONNX execution blocker",
                    "ARM/STM32 toolchain blocker",
                ],

            "Limitations":
                [
                    "no exact historical deployed firmware recovered",
                    "UniVR counter evidence limitation",
                    "no labeled true-OOD detection claim",
                    "no STM32 resource/latency measurements",
                    "remaining external infrastructure gates",
                ],
        },

        "freeze_boundary": {
            "scientific_result_recomputed":
                False,

            "protected_dataset_opened":
                False,

            "checkpoint_deserialized":
                False,

            "model_forward_executed":
                False,

            "exporter_executed":
                False,

            "cross_compiler_executed":
                False,

            "resource_benchmark_rerun":
                False,

            "final_test_reopened":
                False,

            "scientific_threshold_modified":
                False,
        },
    }

    if (
        ledger[
            "next_decision_boundary"
        ][
            "workstation_only_embedded_engineering_exhausted"
        ]
        is not True
    ):
        raise RuntimeError(
            "Paper synthesis started before workstation convergence"
        )

    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )

    return payload


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(
            "Refusing to overwrite paper evidence claim matrix"
        )

    matrix = build_matrix()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            matrix,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    status_counts = {}

    for row in matrix[
        "claims"
    ]:
        status_counts[
            row[
                "status"
            ]
        ] = (
            status_counts.get(
                row[
                    "status"
                ],
                0,
            )
            + 1
        )

    print(
        "PAPER_EVIDENCE_CLAIM_MATRIX_V1_WRITTEN = True"
    )

    print(
        "MATRIX_CONTENT_SHA256 =",
        matrix[
            "content_sha256"
        ],
    )

    print(
        "CLAIM_COUNT =",
        len(
            matrix[
                "claims"
            ]
        ),
    )

    print(
        "CLAIM_STATUS_COUNTS =",
        status_counts,
    )

    print(
        "GLOBAL_PROHIBITED_WORDING_COUNT =",
        len(
            matrix[
                "global_prohibited_wording"
            ]
        ),
    )

    print(
        "SCIENTIFIC_RESULT_RECOMPUTED = False"
    )

    print(
        "PROTECTED_DATASET_OPENED = False"
    )

    print(
        "CHECKPOINT_DESERIALIZED = False"
    )

    print(
        "MODEL_FORWARD_EXECUTED = False"
    )


if __name__ == "__main__":
    main()
