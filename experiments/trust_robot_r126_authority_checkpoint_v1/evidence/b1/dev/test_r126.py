import copy
import unittest

import r122_terminal as terminal
from r126_identity_shadow import (
    ACTIONS, STAGES, PRE, POST,
    ShadowAdapter, clone_preserving_local_identity,
    fault_case, normal_case, snapshot,
)


class Tests(unittest.TestCase):

    def test_identity_tokens_preserved(self):
        h = ShadowAdapter("cancel")
        c = clone_preserving_local_identity(
            h.published, h.lease, h.owner
        )
        self.assertIs(
            c._registry._active[h.lease]["owner"], h.owner
        )

    def test_candidate_nested_objects_distinct(self):
        h = ShadowAdapter("cancel")
        c = clone_preserving_local_identity(
            h.published, h.lease, h.owner
        )
        self.assertIsNot(c._registry, h.original._registry)
        self.assertIsNot(
            c._registry._pool, h.original._registry._pool
        )
        self.assertIsNot(c._terminal, h.original._terminal)

    def test_shallow_copy_is_unsafe(self):
        h = ShadowAdapter("cancel")
        c = copy.copy(h.original)
        self.assertIs(c._registry, h.original._registry)
        self.assertIs(c._terminal, h.original._terminal)

    def test_normal_cancel(self):
        row = normal_case("cancel")
        self.assertEqual(row["terminal_receipt_count"], 1)
        self.assertEqual(row["registry_active_count"], 1)

    def test_normal_retire(self):
        row = normal_case("retire")
        self.assertEqual(row["terminal_receipt_count"], 2)
        self.assertEqual(row["registry_retired_count"], 1)

    def test_original_reference_unchanged(self):
        h = ShadowAdapter("cancel")
        old = snapshot(h.original, h.lease)
        h.transact()
        self.assertEqual(
            snapshot(h.original, h.lease), old
        )

    def test_old_reference_remains_accessible(self):
        h = ShadowAdapter("cancel")
        h.transact()
        self.assertEqual(
            h.original.observe_session(
                h.lease, h.owner
            )["phase"], "ACTIVE"
        )
        self.assertEqual(
            h.published.observe_session(
                h.lease, h.owner
            )["phase"], "CANCELLED"
        )

    def test_wrong_owner_denied(self):
        h = ShadowAdapter("cancel")
        with self.assertRaises(terminal.TerminalPathError):
            h.published.terminal_cancel(
                h.lease, object(), version=0
            )


class FaultTests(unittest.TestCase):
    pass


def make_test(action, stage):
    def test(self):
        result = fault_case(action, stage)
        post = stage in POST

        self.assertEqual(result["action"], action)
        self.assertEqual(result["stage"], stage)
        self.assertEqual(
            result["published_before_exception"], post
        )
        self.assertFalse(result["caller_acknowledged"])
        self.assertTrue(result["old_reference_unchanged"])
        self.assertEqual(
            result["visible_state_unchanged_at_fault"],
            not post,
        )
        self.assertEqual(
            result["recovery"],
            "duplicate_denied" if post
            else "safe_retry_succeeded",
        )
    return test


for action in ACTIONS:
    for stage in STAGES:
        setattr(
            FaultTests,
            "test_" + action + "_" + stage,
            make_test(action, stage),
        )


assert sum(
    name.startswith("test_")
    for name in vars(Tests)
) == 8

assert sum(
    name.startswith("test_")
    for name in vars(FaultTests)
) == 10


if __name__ == "__main__":
    unittest.main()
