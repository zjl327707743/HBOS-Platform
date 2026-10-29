from __future__ import annotations

import hashlib
import sys
import types
import unittest
from datetime import datetime, timedelta

# The contract tests run without a Site or a real Frappe installation, like the
# other Portal backend gates. Only pure state-machine helpers are exercised here;
# real transaction/HTTP behaviour is recorded on the synthetic Site separately.
sys.modules.setdefault("frappe", types.SimpleNamespace())

from hbos_portal.auth import write_receipts as receipts


SECRET = "synthetic-site-encryption-key-for-tests"
NOW = datetime(2026, 10, 28, 12, 0, 0)
REQUEST_ID = "11111111-2222-4333-8444-555555555555"
OTHER_ID = "99999999-8888-4777-8666-555555555555"


def row(**overrides):
    base = {
        "name": "receipt-1",
        "request_key": "k" * 64,
        "channel": "session",
        "request_id": REQUEST_ID,
        "site_name": "pr61-synth.localhost",
        "actor": "r6-hr@hbos.test",
        "subject": "r6-hr@hbos.test",
        "action": "password",
        "state": receipts.COMMITTED,
        "intent_digest": "i" * 64,
        "claimed_at": NOW - timedelta(seconds=5),
        "committed_at": NOW - timedelta(seconds=4),
        "failed_at": None,
        "sealed_at": None,
        "sealed_by": None,
        "failure_code": None,
        "attempt_count": 1,
        "outcome_json": "{}",
    }
    base.update(overrides)
    return base


class RequestIdentifierTest(unittest.TestCase):
    def test_only_canonical_uuid_is_a_request_identifier(self):
        self.assertTrue(receipts.request_id_valid(REQUEST_ID))
        for invalid in (None, "", "not-a-uuid", REQUEST_ID + "\n", 42, REQUEST_ID.replace("-", "")):
            self.assertFalse(receipts.request_id_valid(invalid))

    def test_session_namespace_binds_actor_site_and_identifier(self):
        first = receipts.session_request_key(SECRET, site="site-a", actor="a@test", request_id=REQUEST_ID)
        self.assertEqual(first, receipts.session_request_key(SECRET, site="site-a", actor="a@test", request_id=REQUEST_ID))
        self.assertNotEqual(first, receipts.session_request_key(SECRET, site="site-a", actor="b@test", request_id=REQUEST_ID))
        self.assertNotEqual(first, receipts.session_request_key(SECRET, site="site-b", actor="a@test", request_id=REQUEST_ID))
        self.assertNotEqual(first, receipts.session_request_key(SECRET, site="site-a", actor="a@test", request_id=OTHER_ID))
        self.assertNotEqual(first, receipts.session_request_key("other-secret", site="site-a", actor="a@test", request_id=REQUEST_ID))

    def test_guest_namespace_requires_the_same_recovery_context(self):
        handle_a = receipts.guest_request_key(SECRET, site="site-a", request_id=REQUEST_ID, context="ctx-a-0123456789abcdef")
        handle_b = receipts.guest_request_key(SECRET, site="site-a", request_id=REQUEST_ID, context="ctx-b-0123456789abcdef")
        self.assertEqual(handle_a, receipts.guest_request_key(SECRET, site="site-a", request_id=REQUEST_ID, context="ctx-a-0123456789abcdef"))
        self.assertNotEqual(handle_a, handle_b)
        self.assertNotEqual(handle_a, receipts.session_request_key(SECRET, site="site-a", actor="a@test", request_id=REQUEST_ID))
        with self.assertRaises(Exception):
            receipts.context_handle(SECRET, "short")

    def test_legacy_cache_key_stays_compatible_with_shipped_frontend(self):
        self.assertEqual(
            receipts.legacy_cache_key("a@test", REQUEST_ID),
            "hbos:account:write-result:" + hashlib.sha256(("a@test:" + REQUEST_ID).encode()).hexdigest(),
        )


class IntentBindingTest(unittest.TestCase):
    def test_intent_digest_is_keyed_and_binds_payload(self):
        base = dict(secret=SECRET, site="site-a", actor="a@test", subject="a@test", action="password")
        one = receipts.intent_digest(payload_digest=receipts.password_payload_digest("first-password"), **base)
        same = receipts.intent_digest(payload_digest=receipts.password_payload_digest("first-password"), **base)
        other_password = receipts.intent_digest(payload_digest=receipts.password_payload_digest("second-password"), **base)
        other_action = receipts.intent_digest(payload_digest=receipts.password_payload_digest("first-password"), **dict(base, action="unlink"))
        other_subject = receipts.intent_digest(payload_digest=receipts.password_payload_digest("first-password"), **dict(base, subject="b@test"))
        other_secret = receipts.intent_digest(secret="another-secret", payload_digest=receipts.password_payload_digest("first-password"), site="site-a", actor="a@test", subject="a@test", action="password")
        self.assertEqual(one, same)
        self.assertNotEqual(one, other_password)
        self.assertNotEqual(one, other_action)
        self.assertNotEqual(one, other_subject)
        self.assertNotEqual(one, other_secret)
        self.assertNotEqual(
            receipts.password_payload_digest("first-password"),
            receipts.password_payload_digest("second-password"),
        )

    def test_password_fingerprint_does_not_contain_the_password(self):
        payload = receipts.password_payload_digest("plain-secret-123")
        self.assertNotIn("plain-secret-123", payload)
        self.assertEqual(64, len(payload))

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(Exception):
            receipts.intent_digest(SECRET, site="site-a", actor="a@test", subject="a@test", action="drop-table")


class ClaimDecisionTest(unittest.TestCase):
    def decide(self, stored, *, action="password", subject="r6-hr@hbos.test", intent="i" * 64, now=NOW):
        return receipts.evaluate_claim(stored, action=action, subject=subject, intent=intent, now=now)

    def test_missing_row_means_new_claim(self):
        self.assertEqual({"status": "new"}, self.decide(None))

    def test_committed_row_replays_only_for_the_same_intent(self):
        committed = row(state=receipts.COMMITTED)
        self.assertEqual("replayed", self.decide(committed)["status"])
        self.assertEqual("conflict", self.decide(committed, action="unlink")["status"])
        self.assertEqual("conflict", self.decide(committed, subject="other@test")["status"])
        self.assertEqual("conflict", self.decide(committed, intent="j" * 64)["status"])

    def test_pending_claim_is_processing_only_inside_the_lease(self):
        fresh = row(state=receipts.PENDING, claimed_at=NOW - timedelta(seconds=5))
        stale = row(state=receipts.PENDING, claimed_at=NOW - timedelta(seconds=receipts.CLAIM_LEASE_SECONDS + 1))
        self.assertEqual("processing", self.decide(fresh)["status"])
        self.assertEqual("unknown", self.decide(stale)["status"])

    def test_aborted_and_sealed_states_never_execute(self):
        self.assertEqual("retry", self.decide(row(state=receipts.ABORTED, committed_at=None))["status"])
        self.assertEqual("sealed", self.decide(row(state=receipts.SEALED, committed_at=None))["status"])
        self.assertEqual("conflict", self.decide(row(state=receipts.SEALED, committed_at=None), action="unlink")["status"])

    def test_corrupt_state_is_unknown_not_success(self):
        self.assertEqual("unknown", self.decide(row(state="BROKEN"))["status"])


class PublicStateTest(unittest.TestCase):
    def test_committed_public_state_claims_success_only_when_committed(self):
        state = receipts.public_state(row(state=receipts.COMMITTED), now=NOW)
        self.assertTrue(state["completed"])
        self.assertEqual(receipts.COMMITTED, state["state"])
        self.assertFalse(state["processing"])
        self.assertFalse(state["sealed"])
        self.assertIn("committed_at", state)

    def test_pending_public_state_distinguishes_processing_and_stale_unknown(self):
        fresh = receipts.public_state(row(state=receipts.PENDING, claimed_at=NOW - timedelta(seconds=1)), now=NOW)
        stale = receipts.public_state(row(state=receipts.PENDING, claimed_at=NOW - timedelta(seconds=receipts.CLAIM_LEASE_SECONDS + 5)), now=NOW)
        self.assertTrue(fresh["processing"])
        self.assertFalse(fresh["unknown"])
        self.assertFalse(stale["processing"])
        self.assertTrue(stale["unknown"])
        for state in (fresh, stale):
            self.assertFalse(state["completed"])

    def test_aborted_public_state_is_explicitly_retryable(self):
        state = receipts.public_state(row(state=receipts.ABORTED, committed_at=None), now=NOW)
        self.assertTrue(state["retryable"])
        self.assertFalse(state["completed"])

    def test_sealed_public_state_is_unknown_never_success(self):
        state = receipts.public_state(row(state=receipts.SEALED, committed_at=None), now=NOW)
        self.assertTrue(state["sealed"])
        self.assertTrue(state["unknown"])
        self.assertFalse(state["completed"])

    def test_unknown_state_public_shape(self):
        self.assertIsNone(receipts.public_state(None, now=NOW))
        state = receipts.public_state(row(state="BROKEN"), now=NOW)
        self.assertEqual("UNKNOWN", state["state"])
        self.assertFalse(state["completed"])


class CacheCompatibilityTest(unittest.TestCase):
    def test_version_one_cache_is_read_as_legacy_committed(self):
        parsed = receipts.parse_cache_payload({"completed": True, "action": "password"})
        self.assertTrue(parsed["completed"])
        self.assertTrue(parsed["legacy"])
        self.assertEqual(receipts.COMMITTED, parsed["state"])

    def test_version_two_cache_round_trips_without_secrets(self):
        payload = receipts.cache_payload(row(state=receipts.COMMITTED))
        serialised = str(payload)
        for secret in ("new_password", "recovery_url", "proof", "cookie", "password_hash"):
            self.assertNotIn(secret, serialised)
        parsed = receipts.parse_cache_payload(payload)
        self.assertTrue(parsed["completed"])
        self.assertEqual(receipts.COMMITTED, parsed["state"])
        self.assertFalse(parsed["legacy"])

    def test_corrupt_or_expired_payload_is_not_committed(self):
        for payload in (None, {}, {"completed": False, "action": "password"}, {"version": 2, "state": "PENDING", "completed": False}, "gone"):
            parsed = receipts.parse_cache_payload(payload)
            self.assertTrue(parsed is None or parsed.get("completed") is False)

    def test_stale_cache_cannot_claim_success_for_a_pending_row(self):
        # Parse alone preserves a pending/aborted/sealed payload; the database
        # row always takes precedence in read_receipt(), so cache cannot turn a
        # non-committed database state into success.
        parsed = receipts.parse_cache_payload({"version": 2, "state": "ABORTED", "completed": False, "action": "password"})
        self.assertFalse(parsed["completed"])
        self.assertEqual("ABORTED", parsed["state"])


class DocumentedBoundaryTest(unittest.TestCase):
    def test_receipt_states_and_actions_match_the_approved_contract(self):
        self.assertEqual(("PENDING", "COMMITTED", "ABORTED", "SEALED"), receipts.STATES)
        self.assertEqual(("password", "unlink", "recovery_issue", "recovery"), receipts.ACTIONS)
        self.assertEqual(("session", "guest_recovery"), receipts.CHANNELS)
        self.assertGreaterEqual(receipts.CLAIM_LEASE_SECONDS, 60)

    def test_receipt_contract_does_not_reuse_the_password_link_ttl(self):
        self.assertFalse(hasattr(receipts, "RECOVERY_TTL"))
        self.assertIn("no automatic purge", receipts.RECEIPT_DURABLE_RETENTION)
