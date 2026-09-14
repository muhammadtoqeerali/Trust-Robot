from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]

BUILDER = (
    ROOT
    / "experiments/06_paper/"
      "build_paper_evidence_claim_matrix_v1.py"
)

MATRIX = (
    ROOT
    / "configs/paper/"
      "paper_evidence_claim_matrix_v1.json"
)


SPEC = importlib.util.spec_from_file_location(
    "build_paper_evidence_claim_matrix_v1",
    BUILDER,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "Unable to import paper claim-matrix builder"
    )

MOD = importlib.util.module_from_spec(
    SPEC
)

sys.modules[
    SPEC.name
] = MOD

SPEC.loader.exec_module(
    MOD
)


class PaperEvidenceClaimMatrixV1Tests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        cls.m = json.loads(
            MATRIX.read_text()
        )

        cls.by_id = {
            row[
                "claim_id"
            ]:
                row
            for row in cls.m[
                "claims"
            ]
        }

    def test_git_anchors(
        self,
    ):
        MOD.verify_git_anchors()

    def test_convergence_ledger(
        self,
    ):
        MOD.verify_convergence_ledger()

    def test_content_hash(
        self,
    ):
        payload = deepcopy(
            self.m
        )

        stored = payload.pop(
            "content_sha256"
        )

        normalized = json.loads(
            json.dumps(
                payload,
                separators=(",", ":"),
                allow_nan=False,
            )
        )

        computed = sha256(
            json.dumps(
                normalized,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        self.assertEqual(
            stored,
            computed,
        )

    def test_claim_count(
        self,
    ):
        self.assertEqual(
            len(
                self.m[
                    "claims"
                ]
            ),
            18,
        )

    def test_claim_ids_unique(
        self,
    ):
        ids = [
            row[
                "claim_id"
            ]
            for row in self.m[
                "claims"
            ]
        ]

        self.assertEqual(
            len(
                ids
            ),
            len(
                set(
                    ids
                )
            ),
        )

    def test_integrity_numeric_claims(
        self,
    ):
        wording = self.by_id[
            "INTEGRITY_FINAL_KFALL"
        ][
            "approved_wording"
        ]

        self.assertIn(
            "932/932",
            wording,
        )

        self.assertIn(
            "zero-window",
            wording,
        )

    def test_clean_integrity_claim(
        self,
    ):
        wording = self.by_id[
            "INTEGRITY_CLEAN_ALERTS"
        ][
            "approved_wording"
        ]

        self.assertIn(
            "1.97178 h",
            wording,
        )

        self.assertIn(
            "0.726253 h",
            wording,
        )

    def test_ood_final_claim_is_qualified(
        self,
    ):
        row = self.by_id[
            "OOD_FINAL_COUNTS"
        ]

        self.assertEqual(
            row[
                "status"
            ],
            "SUPPORTED_WITH_QUALIFICATION",
        )

        self.assertIn(
            "366,507",
            row[
                "approved_wording"
            ],
        )

        self.assertIn(
            "4 windows",
            row[
                "approved_wording"
            ],
        )

        self.assertIn(
            "OOD recall",
            row[
                "prohibited_interpretations"
            ],
        )

    def test_ood_not_sensor_failure(
        self,
    ):
        prohibited = set(
            self.by_id[
                "OOD_FINAL_COUNTS"
            ][
                "prohibited_interpretations"
            ]
        )

        self.assertIn(
            "sensor-failure recall",
            prohibited,
        )

    def test_host_resource_scope(
        self,
    ):
        row = self.by_id[
            "HOST_RUNTIME_OVERHEAD"
        ]

        self.assertEqual(
            row[
                "status"
            ],
            "SUPPORTED_WITH_QUALIFICATION",
        )

        self.assertIn(
            "128.520 us",
            row[
                "approved_wording"
            ],
        )

        self.assertIn(
            "149.388 us",
            row[
                "approved_wording"
            ],
        )

        self.assertIn(
            "STM32 latency",
            row[
                "prohibited_interpretations"
            ],
        )

    def test_portable_c_claim(
        self,
    ):
        wording = self.by_id[
            "PORTABLE_C_PARITY"
        ][
            "approved_wording"
        ]

        self.assertIn(
            "13 native C tests",
            wording,
        )

        self.assertIn(
            "9 Python-to-C parity tests",
            wording,
        )

        self.assertIn(
            "162-case",
            wording,
        )

    def test_onnx_claim_is_not_validation_claim(
        self,
    ):
        prohibited = set(
            self.by_id[
                "ONNX_STATUS"
            ][
                "prohibited_interpretations"
            ]
        )

        self.assertIn(
            "ONNX export validated",
            prohibited,
        )

    def test_no_stm32_resource_measurement_claim(
        self,
    ):
        wording = self.by_id[
            "STM32_RESOURCE_STATUS"
        ][
            "approved_wording"
        ]

        for term in (
            "flash",
            "RAM",
            "cycle",
            "latency",
            "energy",
        ):
            self.assertIn(
                term,
                wording,
            )

    def test_global_prohibited_claims(
        self,
    ):
        prohibited = set(
            self.m[
                "global_prohibited_wording"
            ]
        )

        for phrase in (
            "exact deployed firmware",
            "STM32 flash usage measured",
            "STM32 RAM usage measured",
            "OOD recall",
            "sensor-failure detection rate",
        ):
            self.assertIn(
                phrase,
                prohibited,
            )

    def test_no_recompute_list(
        self,
    ):
        locked = set(
            self.m[
                "results_that_must_not_be_recomputed"
            ]
        )

        self.assertIn(
            "integrity final-test result V1",
            locked,
        )

        self.assertIn(
            "OOD final-test result V1",
            locked,
        )

        self.assertIn(
            "runtime resource-overhead benchmark V1",
            locked,
        )

    def test_section_map_complete(
        self,
    ):
        sections = set(
            self.m[
                "manuscript_section_map"
            ]
        )

        self.assertEqual(
            sections,
            {
                "Introduction",
                "Methods",
                "Results",
                "Embedded feasibility",
                "Limitations",
            },
        )

    def test_freeze_boundary_has_no_side_effects(
        self,
    ):
        for value in self.m[
            "freeze_boundary"
        ].values():
            self.assertFalse(
                value
            )


if __name__ == "__main__":
    unittest.main()
