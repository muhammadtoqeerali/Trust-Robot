from __future__ import annotations

import ctypes
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

import torch

from imu_reliability.integrity import (
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
    assess_evidence,
)
from imu_reliability.runtime import (
    TrustState,
    decide_from_logits,
)


ROOT = Path(
    __file__
).resolve().parents[1]

HEADER = (
    ROOT
    / "embedded/reference_runtime/include/"
      "imu_reliability_runtime.h"
)

SOURCE = (
    ROOT
    / "embedded/reference_runtime/src/"
      "imu_reliability_runtime.c"
)

CONTRACT = (
    ROOT
    / "configs/embedded/"
      "portable_c_runtime_semantic_contract_v1.json"
)


IR_STATUS_OK = 0
IR_STATUS_NULL_OUTPUT = 1
IR_STATUS_NONFINITE_LOGIT = 2
IR_STATUS_UNSUPPORTED_HARD_CAUSE = 3

IR_TRUST_VALID = 0
IR_TRUST_OOD_UNKNOWN = 1
IR_TRUST_INTEGRITY_ALERT = 2

IR_CAUSE_NONE = 0
IR_CAUSE_FRAME_GAP = 1


class CDecision(
    ctypes.Structure
):
    _fields_ = [
        (
            "task_prediction",
            ctypes.c_uint8,
        ),
        (
            "trust_state",
            ctypes.c_uint8,
        ),
        (
            "integrity_cause_mask",
            ctypes.c_uint32,
        ),
        (
            "suspect_mask",
            ctypes.c_uint32,
        ),
        (
            "ood_margin",
            ctypes.c_float,
        ),
        (
            "ood_threshold",
            ctypes.c_float,
        ),
    ]


def f32_from_bits(
    bits: int,
) -> float:
    return struct.unpack(
        "<f",
        struct.pack(
            "<I",
            bits,
        ),
    )[0]


def f32_bits(
    value: float,
) -> int:
    return struct.unpack(
        "<I",
        struct.pack(
            "<f",
            value,
        ),
    )[0]


def empty_assessment():
    return assess_evidence(
        []
    )


def frame_gap_assessment():
    return assess_evidence(
        [
            IntegrityEvidence(
                indicator="FRAME_COUNTER_GAP",
                status=EvidenceStatus.HARD_QUALIFIED,
                candidate_cause=IntegrityCause.FRAME_GAP,
                source="portable_c_parity_qualified_frame_gap",
            ),
        ]
    )


class PortableCRuntimeParityV1Tests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        cc = (
            os.environ.get(
                "CC"
            )
            or "/usr/bin/cc"
        )

        if not Path(
            cc
        ).is_file():
            raise RuntimeError(
                f"Host C compiler unavailable: {cc}"
            )

        cls._tmp = (
            tempfile.TemporaryDirectory(
                prefix="imu_reliability_c_parity_"
            )
        )

        cls.library_path = (
            Path(
                cls._tmp.name
            )
            / "libimu_reliability_runtime.so"
        )

        subprocess.run(
            [
                cc,
                "-std=c11",
                "-O2",
                "-fno-fast-math",
                "-fPIC",
                "-shared",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                "-I",
                str(
                    HEADER.parent
                ),
                str(
                    SOURCE
                ),
                "-o",
                str(
                    cls.library_path
                ),
                "-lm",
            ],
            check=True,
            cwd=ROOT,
        )

        cls.lib = ctypes.CDLL(
            str(
                cls.library_path
            )
        )

        cls.fn = (
            cls.lib
            .ir_decide_from_logits
        )

        cls.fn.argtypes = [
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(
                CDecision
            ),
        ]

        cls.fn.restype = (
            ctypes.c_uint8
        )

    @classmethod
    def tearDownClass(
        cls,
    ):
        cls._tmp.cleanup()

    def call_c(
        self,
        activity: float,
        falling: float,
        hard_mask: int = 0,
        suspect_mask: int = 0,
    ):
        out = CDecision()

        status = int(
            self.fn(
                ctypes.c_float(
                    activity
                ),
                ctypes.c_float(
                    falling
                ),
                ctypes.c_uint32(
                    hard_mask
                ),
                ctypes.c_uint32(
                    suspect_mask
                ),
                ctypes.byref(
                    out
                ),
            )
        )

        return (
            status,
            out,
        )

    def python_decision(
        self,
        activity: float,
        falling: float,
        hard_mask: int,
    ):
        logits = torch.tensor(
            [
                [
                    activity,
                    falling,
                ],
            ],
            dtype=torch.float32,
        )

        if hard_mask == 0:
            assessment = (
                empty_assessment()
            )
        elif hard_mask == 1:
            assessment = (
                frame_gap_assessment()
            )
        else:
            raise ValueError(
                "Python parity helper supports only 0/1 hard masks"
            )

        return decide_from_logits(
            logits,
            assessment,
        )

    def assert_parity(
        self,
        activity: float,
        falling: float,
        hard_mask: int,
    ):
        status, c_out = (
            self.call_c(
                activity,
                falling,
                hard_mask,
            )
        )

        self.assertEqual(
            status,
            IR_STATUS_OK,
        )

        py_out = (
            self.python_decision(
                activity,
                falling,
                hard_mask,
            )
        )

        expected_trust = {
            TrustState.VALID:
                IR_TRUST_VALID,

            TrustState.OOD_UNKNOWN:
                IR_TRUST_OOD_UNKNOWN,

            TrustState.INTEGRITY_ALERT:
                IR_TRUST_INTEGRITY_ALERT,
        }[
            py_out.trust_state
        ]

        self.assertEqual(
            c_out.task_prediction,
            py_out.task_prediction,
        )

        self.assertEqual(
            c_out.trust_state,
            expected_trust,
        )

        self.assertEqual(
            c_out.integrity_cause_mask,
            int(
                py_out.integrity_cause_mask
            ),
        )

        self.assertEqual(
            f32_bits(
                c_out.ood_margin
            ),
            f32_bits(
                py_out.ood_margin
            ),
        )

        self.assertEqual(
            f32_bits(
                c_out.ood_threshold
            ),
            0x3C15D520,
        )

    def test_exact_constant_bits(
        self,
    ):
        self.assertEqual(
            f32_bits(
                0.00914505124092102
            ),
            0x3C15D520,
        )

        self.assertEqual(
            f32_bits(
                0.9
            ),
            0x3F666666,
        )

    def test_contract_predeclared_cases_match_python(
        self,
    ):
        cases = [
            (
                1.0,
                0.0,
                0,
            ),
            (
                0.0,
                0.0,
                0,
            ),
            (
                0.0,
                2.0,
                0,
            ),
            (
                0.0,
                3.0,
                0,
            ),
            (
                0.0,
                f32_from_bits(
                    0x3C15D520
                ),
                0,
            ),
            (
                0.0,
                0.0,
                1,
            ),
        ]

        for case in cases:
            with self.subTest(
                case=case
            ):
                self.assert_parity(
                    *case
                )

    def test_threshold_below_equal_above_parity(
        self,
    ):
        below = f32_from_bits(
            0x3C15D51F
        )

        equal = f32_from_bits(
            0x3C15D520
        )

        above = f32_from_bits(
            0x3C15D521
        )

        expected = [
            (
                below,
                IR_TRUST_OOD_UNKNOWN,
            ),
            (
                equal,
                IR_TRUST_VALID,
            ),
            (
                above,
                IR_TRUST_VALID,
            ),
        ]

        for margin, trust in expected:
            status, out = (
                self.call_c(
                    0.0,
                    margin,
                    0,
                )
            )

            self.assertEqual(
                status,
                IR_STATUS_OK,
            )

            self.assertEqual(
                out.trust_state,
                trust,
            )

            self.assertEqual(
                f32_bits(
                    out.ood_margin
                ),
                f32_bits(
                    margin
                ),
            )

            self.assert_parity(
                0.0,
                margin,
                0,
            )

    def test_historical_non_argmax_case(
        self,
    ):
        status, out = (
            self.call_c(
                0.0,
                2.0,
                0,
            )
        )

        self.assertEqual(
            status,
            IR_STATUS_OK,
        )

        self.assertEqual(
            out.task_prediction,
            0,
        )

        self.assertEqual(
            int(
                torch.argmax(
                    torch.tensor(
                        [
                            [
                                0.0,
                                2.0,
                            ],
                        ],
                        dtype=torch.float32,
                    ),
                    dim=1,
                )[
                    0
                ]
            ),
            1,
        )

        self.assert_parity(
            0.0,
            2.0,
            0,
        )

    def test_deterministic_float32_grid_parity(
        self,
    ):
        values = [
            -5.0,
            -3.0,
            -2.0,
            -1.0,
            0.0,
            1.0,
            2.0,
            3.0,
            5.0,
        ]

        checked = 0

        for activity in values:
            for falling in values:
                for hard_mask in (
                    0,
                    1,
                ):
                    self.assert_parity(
                        activity,
                        falling,
                        hard_mask,
                    )

                    checked += 1

        self.assertEqual(
            checked,
            162,
        )

    def test_integrity_precedence_and_task_survival(
        self,
    ):
        status, out = (
            self.call_c(
                0.0,
                3.0,
                IR_CAUSE_FRAME_GAP,
            )
        )

        self.assertEqual(
            status,
            IR_STATUS_OK,
        )

        self.assertEqual(
            out.task_prediction,
            1,
        )

        self.assertEqual(
            out.trust_state,
            IR_TRUST_INTEGRITY_ALERT,
        )

        self.assertEqual(
            out.integrity_cause_mask,
            IR_CAUSE_FRAME_GAP,
        )

        self.assert_parity(
            0.0,
            3.0,
            1,
        )

    def test_suspect_passthrough_does_not_change_state(
        self,
    ):
        suspect = 0xA5A55A5A

        status, out = (
            self.call_c(
                1.0,
                0.0,
                0,
                suspect,
            )
        )

        self.assertEqual(
            status,
            IR_STATUS_OK,
        )

        self.assertEqual(
            out.suspect_mask,
            suspect,
        )

        self.assertEqual(
            out.trust_state,
            IR_TRUST_VALID,
        )

    def test_errors_leave_output_unmodified(
        self,
    ):
        sentinel = CDecision(
            77,
            88,
            0x11223344,
            0x55667788,
            123.25,
            -456.5,
        )

        before = bytes(
            ctypes.string_at(
                ctypes.byref(
                    sentinel
                ),
                ctypes.sizeof(
                    sentinel
                ),
            )
        )

        status = int(
            self.fn(
                ctypes.c_float(
                    1.0
                ),
                ctypes.c_float(
                    0.0
                ),
                ctypes.c_uint32(
                    2
                ),
                ctypes.c_uint32(
                    0
                ),
                ctypes.byref(
                    sentinel
                ),
            )
        )

        self.assertEqual(
            status,
            IR_STATUS_UNSUPPORTED_HARD_CAUSE,
        )

        after = bytes(
            ctypes.string_at(
                ctypes.byref(
                    sentinel
                ),
                ctypes.sizeof(
                    sentinel
                ),
            )
        )

        self.assertEqual(
            before,
            after,
        )

        status = int(
            self.fn(
                ctypes.c_float(
                    float("nan")
                ),
                ctypes.c_float(
                    0.0
                ),
                ctypes.c_uint32(
                    0
                ),
                ctypes.c_uint32(
                    0
                ),
                ctypes.byref(
                    sentinel
                ),
            )
        )

        self.assertEqual(
            status,
            IR_STATUS_NONFINITE_LOGIT,
        )

        after_nan = bytes(
            ctypes.string_at(
                ctypes.byref(
                    sentinel
                ),
                ctypes.sizeof(
                    sentinel
                ),
            )
        )

        self.assertEqual(
            before,
            after_nan,
        )

    def test_null_output_status(
        self,
    ):
        status = int(
            self.fn(
                ctypes.c_float(
                    0.0
                ),
                ctypes.c_float(
                    0.0
                ),
                ctypes.c_uint32(
                    0
                ),
                ctypes.c_uint32(
                    0
                ),
                None,
            )
        )

        self.assertEqual(
            status,
            IR_STATUS_NULL_OUTPUT,
        )


if __name__ == "__main__":
    unittest.main()
