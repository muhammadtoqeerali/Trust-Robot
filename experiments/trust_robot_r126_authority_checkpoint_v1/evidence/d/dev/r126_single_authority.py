"""R126-D: cooperative single-authority API over actual R122 synthetic objects.

No raw backend is returned by the supported public methods.
Python private-object inspection is NOT prevented or authenticated.
Single-threaded, in-memory and non-durable.
"""

import json
from unittest.mock import patch

import r123_terminal_faults as faults

from r126_identity_shadow import clone_preserving_local_identity


STAGES = (
    "candidate_create_pre",
    "candidate_create_post",
    "registry_pre",
    "registry_post",
    "receipt_pre",
    "receipt_post",
    "verification_pre",
    "verification_post",
    "publication_pre",
    "publication_post",
    "ack_pre",
)

PREPUBLICATION = STAGES[:9]
POSTPUBLICATION = STAGES[9:]


class AuthorityError(RuntimeError):
    pass


class InjectedAuthorityFault(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise AuthorityError(reason)


def detached(value):
    return json.loads(
        json.dumps(value, sort_keys=True, allow_nan=False)
    )


def phase_of(view):
    receipts = view["terminal"]["receipts"]
    events = [item["event"] for item in receipts]

    if events == []:
        return "ACTIVE"
    if events == ["terminal_cancel"]:
        return "CANCELLED"
    if events == ["terminal_cancel", "terminal_retire"]:
        return "RETIRED"

    raise AuthorityError("INVALID_TERMINAL_SEQUENCE")


class TerminalAuthority:
    """Supported API: create, inspect, terminal_cancel, terminal_retire.

    The diagnostic method beginning with '_' is test-only.
    Not a sandbox against Python introspection.
    """

    __slots__ = (
        "__published",
        "__lease",
        "__owner",
    )

    def __init__(self):
        raise AuthorityError("USE_CREATE")

    @classmethod
    def create(cls):
        # Raw synthetic facade is created *inside* the authority.
        # The caller receives only this wrapper and capability tokens.
        backend, lease, owner = faults.make_saturated_fixture()

        instance = object.__new__(cls)
        instance.__published = backend
        instance.__lease = lease
        instance.__owner = owner

        need(
            phase_of(backend.inspect_terminal()) == "ACTIVE",
            "INITIAL_PHASE",
        )
        need(
            backend.observe_denials()["receipt_count"] == 1,
            "INITIAL_DENIAL_SATURATION",
        )

        return instance, lease, owner

    def inspect(self):
        # R122 already returns a detached JSON-compatible observation.
        view = self.__published.inspect_terminal()

        return detached({
            "schema": "trust_robot_r126_single_authority_view_v1",
            "phase": phase_of(view),
            "observation": view,
        })

    def _authorize(self, action, lease, owner, version):
        need(
            type(lease) is object and lease is self.__lease,
            "AUTHORITY_LEASE_DENIED",
        )
        need(owner is self.__owner, "AUTHORITY_OWNER_DENIED")
        need(action in ("cancel", "retire"), "UNKNOWN_ACTION")

        view = self.inspect()
        phase = view["phase"]

        if action == "cancel":
            need(type(version) is int, "AUTHORITY_VERSION_TYPE")
            need(phase == "ACTIVE", "AUTHORITY_CANCEL_PHASE_DENIED")

            session = self.__published.observe_session(
                lease, owner
            )
            need(
                version == session["version"],
                "AUTHORITY_STALE_VERSION",
            )

        else:
            need(
                phase == "CANCELLED",
                "AUTHORITY_RETIRE_PHASE_DENIED",
            )

        return view

    @staticmethod
    def _inject(selected, stage):
        if selected == stage:
            raise InjectedAuthorityFault(stage)

    @staticmethod
    def _perform(candidate, action, lease, owner, selected):
        if action == "cancel":
            operation = lambda: candidate.terminal_cancel(
                lease, owner, version=0
            )
        else:
            operation = lambda: candidate.terminal_retire(
                lease, owner
            )

        if selected in (
            "registry_pre", "registry_post",
            "receipt_pre", "receipt_post",
        ):
            if selected.startswith("registry"):
                target = candidate._registry
                attribute = action
            else:
                target = candidate
                attribute = "_append_terminal"

            original = getattr(target, attribute)

            def injected(*args, **kwargs):
                if selected.endswith("_post"):
                    original(*args, **kwargs)
                raise InjectedAuthorityFault(selected)

            with patch.object(
                target, attribute, side_effect=injected
            ):
                return operation()

        return operation()

    @staticmethod
    def _validate_candidate(
        candidate, action, lease, owner, before
    ):
        candidate._verify()

        after = candidate.inspect_terminal()
        phase = phase_of(after)

        expected = (
            "CANCELLED" if action == "cancel" else "RETIRED"
        )
        count = 1 if action == "cancel" else 2
        retired = 0 if action == "cancel" else 1

        need(phase == expected, "CANDIDATE_PHASE")
        need(
            after["terminal"]["receipt_count"] == count,
            "CANDIDATE_TERMINAL_RECEIPTS",
        )
        need(
            after["ordinary_audit"]["registry"]["active_count"]
            == 1 - retired,
            "CANDIDATE_ACTIVE_COUNT",
        )
        need(
            after["ordinary_audit"]["registry"]["retired_count"]
            == retired,
            "CANDIDATE_RETIRED_COUNT",
        )
        need(
            len(candidate._registry._ledger) == retired,
            "CANDIDATE_REGISTRY_LEDGER",
        )

        item = after["terminal"]["receipts"][-1]
        need(
            item["event"] == (
                "terminal_cancel"
                if action == "cancel" else "terminal_retire"
            ),
            "CANDIDATE_RECEIPT_EVENT",
        )

        need(
            after["terminal"]["chain_tip"]
            == item["linked_sha256"],
            "CANDIDATE_TERMINAL_TIP",
        )

        old_session = before["session"]

        for key in (
            "attempted_work_units",
            "committed_work_units",
            "committed_digest",
        ):
            need(
                item[key] == old_session[key]
                if action == "retire"
                else item["after"][key] == old_session[key],
                "CANDIDATE_WORK_PRESERVATION:" + key,
            )

        if action == "cancel":
            session = candidate.observe_session(
                lease, owner
            )
            need(
                session["phase"] == "CANCELLED",
                "CANDIDATE_SESSION_PHASE",
            )
        else:
            need(
                candidate._state_for_known_lease(lease) is None,
                "CANDIDATE_RETIRED_LEASE_ACTIVE",
            )

        return after

    def _transact(
        self, action, lease, owner,
        *, version=None, inject=None
    ):
        need(
            inject is None or inject in STAGES,
            "UNKNOWN_DIAGNOSTIC_STAGE",
        )

        self._authorize(action, lease, owner, version)

        # The original pointer remains immutable through all
        # candidate work performed using the supported API.
        before = {
            "view": self.__published.inspect_terminal(),
            "session": self.__published.observe_session(
                lease, owner
            ),
        }

        self._inject(inject, "candidate_create_pre")

        candidate = clone_preserving_local_identity(
            self.__published, lease, owner
        )

        self._inject(inject, "candidate_create_post")

        self._perform(
            candidate, action, lease, owner, inject
        )

        self._inject(inject, "verification_pre")

        after = self._validate_candidate(
            candidate, action, lease, owner, before
        )

        self._inject(inject, "verification_post")

        self._inject(inject, "publication_pre")

        # This is the only published-backend pointer replacement.
        # It is NOT synchronized or durable.
        self.__published = candidate

        self._inject(inject, "publication_post")
        self._inject(inject, "ack_pre")

        return detached({
            "acknowledged": True,
            "phase": phase_of(after),
            "terminal_receipt_count":
                after["terminal"]["receipt_count"],
            "terminal_chain_tip":
                after["terminal"]["chain_tip"],
        })

    def terminal_cancel(self, lease, owner, *, version):
        return self._transact(
            "cancel", lease, owner, version=version
        )

    def terminal_retire(self, lease, owner):
        return self._transact(
            "retire", lease, owner
        )

    def _diagnostic_fault(
        self, action, lease, owner, *,
        version=None, stage
    ):
        """Test-only seam; not part of the supported public API."""
        return self._transact(
            action, lease, owner,
            version=version, inject=stage
        )
