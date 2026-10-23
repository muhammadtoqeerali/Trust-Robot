import unittest

from r126_single_authority import (
    TerminalAuthority,
    AuthorityError,
    InjectedAuthorityFault,
)


class AuthorityTests(unittest.TestCase):

    def setUp(self):
        self.a, self.lease, self.owner = TerminalAuthority.create()

    def test_initial_saturated_state(self):
        s = self.a.inspect()
        self.assertEqual(s["phase"], "ACTIVE")
        self.assertEqual(
            s["observation"]["ordinary_audit"]["denials"][
                "receipt_count"
            ], 1
        )

    def test_sequential_cancel_and_retire(self):
        cancel = self.a.terminal_cancel(
            self.lease, self.owner, version=0
        )
        self.assertTrue(cancel["acknowledged"])
        self.assertEqual(self.a.inspect()["phase"], "CANCELLED")

        retire = self.a.terminal_retire(
            self.lease, self.owner
        )
        self.assertTrue(retire["acknowledged"])
        self.assertEqual(self.a.inspect()["phase"], "RETIRED")

    def test_wrong_lease(self):
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_LEASE_DENIED$"
        ):
            self.a.terminal_cancel(
                object(), self.owner, version=0
            )

    def test_wrong_owner(self):
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_OWNER_DENIED$"
        ):
            self.a.terminal_cancel(
                self.lease, object(), version=0
            )

    def test_stale_version(self):
        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_STALE_VERSION$"
        ):
            self.a.terminal_cancel(
                self.lease, self.owner, version=1
            )

    def test_prepublication_registry_post_fault(self):
        before = self.a.inspect()

        with self.assertRaises(InjectedAuthorityFault):
            self.a._diagnostic_fault(
                "cancel", self.lease, self.owner,
                version=0, stage="registry_post"
            )

        self.assertEqual(self.a.inspect(), before)

        self.a.terminal_cancel(
            self.lease, self.owner, version=0
        )
        self.assertEqual(self.a.inspect()["phase"], "CANCELLED")

    def test_prepublication_receipt_post_fault(self):
        before = self.a.inspect()

        with self.assertRaises(InjectedAuthorityFault):
            self.a._diagnostic_fault(
                "cancel", self.lease, self.owner,
                version=0, stage="receipt_post"
            )

        self.assertEqual(self.a.inspect(), before)

    def test_cancel_acknowledgement_ambiguity(self):
        with self.assertRaises(InjectedAuthorityFault):
            self.a._diagnostic_fault(
                "cancel", self.lease, self.owner,
                version=0, stage="publication_post"
            )

        self.assertEqual(self.a.inspect()["phase"], "CANCELLED")

        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_CANCEL_PHASE_DENIED$"
        ):
            self.a.terminal_cancel(
                self.lease, self.owner, version=0
            )

    def test_retire_acknowledgement_ambiguity(self):
        self.a.terminal_cancel(
            self.lease, self.owner, version=0
        )

        with self.assertRaises(InjectedAuthorityFault):
            self.a._diagnostic_fault(
                "retire", self.lease, self.owner,
                stage="ack_pre"
            )

        self.assertEqual(self.a.inspect()["phase"], "RETIRED")

        with self.assertRaisesRegex(
            AuthorityError, "^AUTHORITY_RETIRE_PHASE_DENIED$"
        ):
            self.a.terminal_retire(
                self.lease, self.owner
            )

    def test_detached_observation(self):
        self.a.terminal_cancel(
            self.lease, self.owner, version=0
        )
        s = self.a.inspect()
        s["observation"]["terminal"]["receipts"][0][
            "event"
        ] = "bad_view"

        self.assertEqual(
            self.a.inspect()["observation"]["terminal"][
                "receipts"
            ][0]["event"],
            "terminal_cancel",
        )

    def test_public_interface_does_not_return_backend(self):
        for name in (
            "published", "original", "registry",
            "pool", "backend", "submit", "open", "finish",
        ):
            self.assertFalse(hasattr(self.a, name), name)

        self.assertFalse(hasattr(self.a, "__dict__"))

        view = self.a.inspect()
        self.assertIsInstance(view, dict)
        self.assertIs(type(self.lease), object)
        self.assertIs(type(self.owner), object)


if __name__ == "__main__":
    unittest.main()
