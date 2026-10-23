import unittest

from r126_single_authority import (
    AuthorityError,
    TerminalAuthority,
    STAGES,
    POSTPUBLICATION,
)

from r126_d2_fault_matrix import (
    ACTIONS,
    fault_case,
    normal_case,
)


class AdditionalAuthorityTests(unittest.TestCase):

    def setUp(self):
        self.a, self.lease, self.owner = TerminalAuthority.create()

    def test_documented_surface_has_no_raw_backend(self):
        for name in (
            "published", "backend", "registry",
            "pool", "session", "submit", "open",
        ):
            self.assertFalse(hasattr(self.a, name), name)

    def test_python_introspection_can_access_backend(self):
        raw = getattr(
            self.a, "_TerminalAuthority__published"
        )
        self.assertEqual(
            raw.observe_session(
                self.lease, self.owner
            )["phase"], "ACTIVE",
        )

    def test_private_backend_direct_cancel_bypass(self):
        raw = getattr(
            self.a, "_TerminalAuthority__published"
        )
        raw.terminal_cancel(
            self.lease, self.owner, version=0
        )
        self.assertEqual(self.a.inspect()["phase"], "CANCELLED")

    def test_private_pointer_rebinding_possible(self):
        raw = getattr(
            self.a, "_TerminalAuthority__published"
        )
        self.a.terminal_cancel(
            self.lease, self.owner, version=0
        )
        self.assertEqual(self.a.inspect()["phase"], "CANCELLED")

        setattr(
            self.a, "_TerminalAuthority__published", raw
        )

        self.assertEqual(self.a.inspect()["phase"], "ACTIVE")

    def test_invalid_lease_preserves_observation(self):
        before = self.a.inspect()
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_LEASE_DENIED$"
        ):
            self.a.terminal_cancel(
                object(), self.owner, version=0
            )
        self.assertEqual(self.a.inspect(), before)

    def test_invalid_owner_preserves_observation(self):
        before = self.a.inspect()
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_OWNER_DENIED$"
        ):
            self.a.terminal_cancel(
                self.lease, object(), version=0
            )
        self.assertEqual(self.a.inspect(), before)

    def test_boolean_version_denied(self):
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_VERSION_TYPE$"
        ):
            self.a.terminal_cancel(
                self.lease, self.owner, version=True
            )
        self.assertEqual(self.a.inspect()["phase"], "ACTIVE")

    def test_stale_version_denied(self):
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_STALE_VERSION$"
        ):
            self.a.terminal_cancel(
                self.lease, self.owner, version=99
            )
        self.assertEqual(self.a.inspect()["phase"], "ACTIVE")

    def test_unknown_fault_stage_denied(self):
        before = self.a.inspect()
        with self.assertRaisesRegex(
            AuthorityError, "^UNKNOWN_DIAGNOSTIC_STAGE$"
        ):
            self.a._diagnostic_fault(
                "cancel", self.lease, self.owner,
                version=0, stage="unknown_stage"
            )
        self.assertEqual(self.a.inspect(), before)

    def test_retire_before_cancel_denied(self):
        before = self.a.inspect()
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_RETIRE_PHASE_DENIED$"
        ):
            self.a.terminal_retire(
                self.lease, self.owner
            )
        self.assertEqual(self.a.inspect(), before)

    def test_duplicate_terminal_operations_denied(self):
        self.a.terminal_cancel(
            self.lease, self.owner, version=0
        )
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_CANCEL_PHASE_DENIED$"
        ):
            self.a.terminal_cancel(
                self.lease, self.owner, version=0
            )

        self.a.terminal_retire(
            self.lease, self.owner
        )
        after = self.a.inspect()

        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_RETIRE_PHASE_DENIED$"
        ):
            self.a.terminal_retire(
                self.lease, self.owner
            )

        self.assertEqual(self.a.inspect(), after)

    def test_detached_view_mutation_does_not_publish(self):
        self.a.terminal_cancel(
            self.lease, self.owner, version=0
        )
        before = self.a.inspect()
        view = self.a.inspect()
        view["observation"]["terminal"]["receipts"][0][
            "event"
        ] = "mutated_detached_view"
        self.assertEqual(self.a.inspect(), before)


class FullFaultMatrix(unittest.TestCase):
    pass


def create_fault_test(action, stage):
    def test(self):
        row = fault_case(action, stage)
        post = stage in POSTPUBLICATION

        self.assertTrue(row["exception_observed"])
        self.assertFalse(row["caller_acknowledged_at_fault"])
        self.assertIs(
            row["published_before_exception"], post
        )
        self.assertIs(
            row["published_observation_unchanged_at_fault"],
            not post,
        )
        self.assertIs(
            row["pointer_unchanged_at_fault"],
            not post,
        )
        self.assertEqual(
            row["recovery"],
            "duplicate_denied" if post
            else "safe_retry_succeeded",
        )
        self.assertEqual(
            row["terminal_count"],
            1 if action == "cancel" else 2,
        )
    return test


for action in ACTIONS:
    for stage in STAGES:
        setattr(
            FullFaultMatrix,
            "test_" + action + "_" + stage,
            create_fault_test(action, stage),
        )

assert sum(
    name.startswith("test_")
    for name in vars(AdditionalAuthorityTests)
) == 12

assert sum(
    name.startswith("test_")
    for name in vars(FullFaultMatrix)
) == 22


if __name__ == "__main__":
    unittest.main()
