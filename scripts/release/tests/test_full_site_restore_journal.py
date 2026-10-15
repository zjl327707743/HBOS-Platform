"""Synthetic private journal fixtures only; no real ROOT, backup or service."""
from dataclasses import FrozenInstanceError, replace
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.release.full_site_restore import journal, landing
from scripts.release.full_site_restore.common import VOLUME_NAMES, RestoreError
from scripts.release.full_site_restore.journal import OwnedJournal, review_existing
from scripts.release.full_site_restore.lifecycle import (
    CleanupDecision, CreationIntent, IntentOutcome, LifecycleRegistry, OwnerAuthorization,
)
from scripts.release.tests.test_full_site_restore_lifecycle import BASELINE, FakeClock

SECRET = "SYNTHETIC_JOURNAL_SECRET_DO_NOT_PRINT"


class JournalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hbos-synthetic-journal-')
        self.addCleanup(temporary.cleanup)
        self.fixture = Path(temporary.name).resolve()
        self.root = self.fixture / 'owned-root'
        self.log = self.root / 'runtime/journal/events.jsonl'
        for module in (journal, landing):
            override = patch.object(module, 'ROOT', self.root)
            override.start()
            self.addCleanup(override.stop)
        self.clock = FakeClock()
        self.registry = LifecycleRegistry(
            authorization=OwnerAuthorization.from_confirmation(explicit=True, reference_sha256='a'*64),
            baseline=BASELINE, clock=self.clock)
        self.registry.note_owned_action()
        self.capability = None

    def create(self):
        if self.capability is None:
            self.capability = landing._new_landing()
            self.addCleanup(self.capability.close)
        return OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64)

    def assert_denied(self, callback, code=None):
        with self.assertRaises(RestoreError) as caught:
            callback()
        if code:
            self.assertEqual(str(caught.exception), code)
        self.assertRegex(str(caught.exception), r'^[A-Z][A-Z0-9_]{2,80}$')
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertNotIn(str(self.fixture), str(caught.exception))

    def pending_intent(self, owned):
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        receipt = owned.append_intent(intent)
        return intent, receipt

    def overwrite(self, raw):
        self.log.write_bytes(raw)
        self.log.chmod(0o600)

    def test_default_and_import_are_inert(self):
        original = dict(journal.__dict__)
        try:
            with (patch.object(os, 'open', side_effect=AssertionError('no I/O')),
                  patch.object(subprocess, 'Popen', side_effect=AssertionError('no process')),
                  patch.object(socket, 'socket', side_effect=AssertionError('no socket'))):
                importlib.reload(journal)
                owned = journal.OwnedJournal()
                self.assertEqual(owned.public_summary()['execution'], 'HARD_BLOCKED')
                self.assert_denied(owned.require_execution_ready, 'JOURNAL_RESUME_HARD_BLOCKED')
        finally:
            # Preserve issued exact types for other suites importing this
            # module before discovery; the inertness probe must not mutate API.
            journal.__dict__.clear()
            journal.__dict__.update(original)
        self.assertFalse(self.root.exists())

    def test_requires_existing_capability_and_explicit_authorization(self):
        self.assert_denied(lambda: OwnedJournal.create(None, self.registry, clock_id_sha256='b'*64),
                           'JOURNAL_LANDING_CAPABILITY_REQUIRED')
        self.assertFalse(self.root.exists())
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        registry = LifecycleRegistry(clock=self.clock)
        self.assert_denied(lambda: OwnedJournal.create(self.capability, registry, clock_id_sha256='b'*64),
                           'JOURNAL_OWNER_AUTHORIZATION_REQUIRED')
        self.assertFalse((self.root / 'runtime').exists())

    def test_first_owned_action_required_no_new_timer_is_created(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        registry = LifecycleRegistry(authorization=self.registry.authorization, baseline=BASELINE, clock=self.clock)
        self.assert_denied(lambda: OwnedJournal.create(self.capability, registry, clock_id_sha256='b'*64),
                           'JOURNAL_FIRST_ACTION_REQUIRED')
        self.assertIsNone(registry._started_at)
        self.assertFalse((self.root / 'runtime').exists())

    def test_create_private_fixed_layout_and_fsynced_header(self):
        calls = []
        real_fsync = os.fsync
        with patch.object(os, 'fsync', side_effect=lambda fd: (calls.append(fd), real_fsync(fd))[1]):
            owned = self.create()
        self.assertGreaterEqual(len(calls), 6)
        self.assertEqual(set(self.log.parent.iterdir()), {self.log})
        for path in (self.root, self.root/'runtime', self.log.parent, self.log):
            metadata = path.lstat()
            self.assertEqual(metadata.st_uid, os.geteuid())
            self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o600 if path == self.log else 0o700)
        self.assertEqual(self.log.stat().st_nlink, 1)
        self.assertTrue(self.log.read_bytes().endswith(b'\n'))
        self.capability.verify_private_tree()
        self.assertEqual(owned.public_summary()['records'], 1)
        self.assertEqual(review_existing().run_deadline_ns, 2800 * 10**9)

    def test_durable_intent_then_exact_receipt_preserves_prefix(self):
        owned = self.create()
        header = self.log.read_bytes()
        intent, receipt = self.pending_intent(owned)
        self.assertTrue(self.log.read_bytes().startswith(header))
        self.assertEqual((receipt.run_id, receipt.intent_id, receipt.sequence),
                         (self.registry.run_id, intent.intent_id, 1))
        with self.assertRaises(FrozenInstanceError):
            receipt.sequence = 7
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        owned.append_receipt(self.registry._intents[intent.intent_id])
        review = review_existing(expected_tip_sha256=owned.public_summary()['tip_sha256'])
        self.assertEqual(review.records, 3)
        self.assertFalse(review.unknown_intents)
        self.assertEqual(review.execution, 'HARD_BLOCKED')
        self.assertEqual(review.crash_outcome, 'UNKNOWN')

    def test_pending_last_intent_is_unknown_on_cross_process_review(self):
        owned = self.create()
        intent, _ = self.pending_intent(owned)
        owned.close()
        self.capability.close()
        review = review_existing()
        self.assertEqual(review.integrity, 'VALIDATED_RECORDS_ONLY')
        self.assertEqual(review.unknown_intents, (intent.intent_id,))
        self.assertEqual(review.crash_outcome, 'UNKNOWN')
        self.assertEqual(review.run_deadline_ns, 2800 * 10**9)
        self.assert_denied(owned.require_execution_ready, 'JOURNAL_RESUME_HARD_BLOCKED')

    def test_unknown_receipt_stays_unknown_and_no_error_text_is_stored(self):
        owned = self.create()
        intent, _ = self.pending_intent(owned)
        self.registry.mark_unknown(intent.intent_id, error_code=SECRET)
        owned.append_receipt(self.registry._intents[intent.intent_id])
        self.assertNotIn(SECRET.encode(), self.log.read_bytes())
        self.assertEqual(review_existing().unknown_intents, (intent.intent_id,))

    def test_unregistered_or_cross_run_intents_and_receipts_are_denied(self):
        owned = self.create()
        intent = CreationIntent('c'*64, self.registry.run_id, 'container', 'db', 100)
        self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_INTENT_INVALID')
        self.assert_denied(lambda: owned.append_intent(replace(intent, intent_id=[])), 'JOURNAL_INTENT_INVALID')
        real_intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        self.assert_denied(lambda: owned.append_intent(replace(real_intent, run_id='e'*64)), 'JOURNAL_INTENT_INVALID')
        self.assert_denied(lambda: owned.append_receipt(IntentOutcome(real_intent, 'CONFIRMED')),
                           'JOURNAL_RECEIPT_INVALID')
        self.assert_denied(lambda: owned.append_receipt(IntentOutcome(None)), 'JOURNAL_RECEIPT_INVALID')

    def test_receipt_without_durable_intent_is_denied(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        self.assert_denied(lambda: owned.append_receipt(self.registry._intents[intent.intent_id]),
                           'JOURNAL_RECEIPT_INVALID')
        self.assertEqual(len(self.log.read_bytes().splitlines()), 1)

    def test_duplicate_intent_or_receipt_cannot_overwrite_events(self):
        owned = self.create()
        intent, _ = self.pending_intent(owned)
        before = self.log.read_bytes()
        self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_INTENT_INVALID')
        self.assertEqual(self.log.read_bytes(), before)

    def test_existing_log_cannot_be_reinitialized(self):
        owned = self.create()
        old = self.log.read_bytes()
        self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64))
        self.assertEqual(self.log.read_bytes(), old)
        self.assertEqual(owned.public_summary()['run_deadline_ns'], 2800 * 10**9)

    def test_deadline_expired_create_cannot_create_runtime(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        self.clock.value = 2800
        self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64),
                           'JOURNAL_DEADLINE_EXPIRED')
        self.assertFalse((self.root/'runtime').exists())

    def test_unknown_registry_create_is_denied_before_any_journal_write(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        self.registry.mark_unknown(intent.intent_id)
        self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64),
                           'JOURNAL_RUN_CLOSED')
        self.assertFalse((self.root/'runtime').exists())

    def test_cleanup_registry_create_is_denied_before_any_journal_write(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        self.registry.cleanup_plan([])
        self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64),
                           'JOURNAL_RUN_CLOSED')
        self.assertFalse((self.root/'runtime').exists())

    def test_invalid_clock_create_is_denied_before_any_journal_write(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        self.clock.value = 99
        self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64),
                           'LIFECYCLE_CLOCK_INVALID')
        self.assertFalse((self.root/'runtime').exists())

    def test_create_post_fsync_expiry_withholds_object_and_keeps_binding(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        real_append = self.capability.journal_append_bytes
        def append(raw):
            real_append(raw)
            self.clock.value = 2800
        with patch.object(self.capability, 'journal_append_bytes', side_effect=append):
            self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64),
                               'JOURNAL_DEADLINE_EXPIRED')
        review = review_existing()
        self.assertEqual((review.records, review.execution), (1, 'HARD_BLOCKED'))
        self.assertEqual(review.run_deadline_ns, 2800 * 10**9)

    def test_create_post_fsync_invalid_clock_withholds_object_and_keeps_binding(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        real_append = self.capability.journal_append_bytes
        def append(raw):
            real_append(raw)
            self.clock.value = 99
        with patch.object(self.capability, 'journal_append_bytes', side_effect=append):
            self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64),
                               'LIFECYCLE_CLOCK_INVALID')
        self.assertEqual(review_existing().records, 1)

    def test_create_post_fsync_cleanup_withholds_object_and_keeps_binding(self):
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        real_append = self.capability.journal_append_bytes
        def append(raw):
            real_append(raw)
            self.registry.cleanup_plan([])
        with patch.object(self.capability, 'journal_append_bytes', side_effect=append):
            self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256='b'*64),
                               'JOURNAL_RUN_CLOSED')
        self.assertEqual(review_existing().records, 1)

    def test_closed_registry_refuses_new_intent_but_preserves_terminal_audit(self):
        owned = self.create()
        first, _ = self.pending_intent(owned)
        second = self.registry.create_intent('volume', VOLUME_NAMES[1])
        self.registry.mark_unknown(first.intent_id)
        old = self.log.read_bytes()
        self.assert_denied(lambda: owned.append_intent(second), 'JOURNAL_RUN_CLOSED')
        self.assertEqual(self.log.read_bytes(), old)
        self.assertEqual(owned.public_summary()['status'], 'CLOSED')
        owned.append_receipt(self.registry._intents[first.intent_id])
        decision = self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        owned.append_cleanup_result(decision)
        self.assertEqual(owned.public_summary()['status'], 'CLOSED')
        self.assertEqual(review_existing().records, 5)

    def test_cleanup_started_refuses_pending_intent_before_journal_append(self):
        owned = self.create()
        first, _ = self.pending_intent(owned)
        second = self.registry.create_intent('volume', VOLUME_NAMES[1])
        decision = self.registry.cleanup_plan([])
        old = self.log.read_bytes()
        self.assert_denied(lambda: owned.append_intent(second), 'JOURNAL_RUN_CLOSED')
        self.assertEqual(self.log.read_bytes(), old)
        self.registry.mark_not_created(first.intent_id, confirmed=True)
        owned.append_receipt(self.registry._intents[first.intent_id])
        owned.append_cleanup_started()
        owned.append_cleanup_result(decision)
        self.assertEqual((review_existing().records, owned.public_summary()['status']), (5, 'CLOSED'))

    def test_deadline_crossing_fsync_withholds_durable_intent_receipt(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        real_append = self.capability.journal_append_bytes
        def append(raw):
            real_append(raw)
            self.clock.value = 2800
        with patch.object(self.capability, 'journal_append_bytes', side_effect=append):
            self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_DEADLINE_EXPIRED')
        self.assertEqual(review_existing().unknown_intents, (intent.intent_id,))
        self.assertEqual(owned.public_summary()['status'], 'CLOSED')
        self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_RUN_CLOSED')
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        owned.append_receipt(self.registry._intents[intent.intent_id])
        decision = self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        owned.append_cleanup_result(decision)
        self.assertEqual((review_existing().records, owned.public_summary()['status']), (5, 'CLOSED'))

    def test_post_append_invalid_clock_permanently_closes_intents_not_terminal_audit(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        real_append = self.capability.journal_append_bytes
        def append(raw):
            real_append(raw)
            self.clock.value = 99
        with patch.object(self.capability, 'journal_append_bytes', side_effect=append):
            self.assert_denied(lambda: owned.append_intent(intent), 'LIFECYCLE_CLOCK_INVALID')
        self.assertEqual((owned.public_summary()['status'], review_existing().records), ('CLOSED', 2))
        old = self.log.read_bytes()
        self.clock.value = 100
        self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_RUN_CLOSED')
        self.assertEqual(self.log.read_bytes(), old)
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        owned.append_receipt(self.registry._intents[intent.intent_id])
        decision = self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        owned.append_cleanup_result(decision)
        self.assertEqual((review_existing().records, owned.public_summary()['status']), (5, 'CLOSED'))

    def test_post_append_registry_cleanup_withholds_durable_intent_receipt(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        real_append = self.capability.journal_append_bytes
        def append(raw):
            real_append(raw)
            self.registry.cleanup_plan([])
        with patch.object(self.capability, 'journal_append_bytes', side_effect=append):
            self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_RUN_CLOSED')
        self.assertEqual((owned.public_summary()['status'], review_existing().records), ('CLOSED', 2))
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        owned.append_receipt(self.registry._intents[intent.intent_id])
        owned.append_cleanup_started()
        owned.append_cleanup_result(CleanupDecision('RECORDED_CLEAN'))
        self.assertEqual(review_existing().records, 5)

    def test_pre_append_invalid_clock_closes_intents_without_writing(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        old = self.log.read_bytes()
        self.clock.value = 99
        self.assert_denied(lambda: owned.append_intent(intent), 'LIFECYCLE_CLOCK_INVALID')
        self.assertEqual(self.log.read_bytes(), old)
        self.assertEqual(owned.public_summary()['status'], 'CLOSED')
        self.clock.value = 100
        self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_RUN_CLOSED')

    def test_explicit_close_also_disables_terminal_audit(self):
        owned = self.create()
        intent, _ = self.pending_intent(owned)
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        owned.close()
        old = self.log.read_bytes()
        self.assert_denied(lambda: owned.append_receipt(self.registry._intents[intent.intent_id]), 'JOURNAL_DISABLED')
        self.assertEqual(self.log.read_bytes(), old)

    def test_cleanup_start_is_once_and_deadline_is_preserved(self):
        owned = self.create()
        decision = self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        owned.append_cleanup_result(decision)
        self.clock.value += 99
        review = review_existing()
        self.assertEqual(review.cleanup_deadline_ns, 700 * 10**9)
        self.assert_denied(owned.append_cleanup_started, 'JOURNAL_CLEANUP_INVALID')
        self.assertEqual(review_existing().cleanup_deadline_ns, 700 * 10**9)

    def test_cleanup_result_never_stores_argv_or_plain_error(self):
        owned = self.create()
        self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        decision = CleanupDecision('FAILED_CLOSED', actions=(('SYNTHETIC_UNTRUSTED_COMMAND', SECRET),),
                                   blockers=('SYNTHETIC_JOURNAL_SECRET_DO_NOT_PRINT',))
        owned.append_cleanup_result(decision)
        raw = self.log.read_bytes()
        self.assertNotIn(SECRET.encode(), raw)
        self.assertNotIn(b'SYNTHETIC_UNTRUSTED_COMMAND', raw)
        self.assertNotIn(b'actions', raw)
        self.assertEqual(review_existing().integrity, 'VALIDATED_RECORDS_ONLY')

    def test_false_clean_with_unresolved_intent_is_denied(self):
        owned = self.create()
        self.pending_intent(owned)
        self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        self.assert_denied(lambda: owned.append_cleanup_result(CleanupDecision('RECORDED_CLEAN')),
                           'JOURNAL_CLEANUP_INVALID')

    def test_truncated_tail_empty_and_missing_newline_are_unknown(self):
        self.create()
        raw = self.log.read_bytes()
        for altered in (raw[:-1], raw[:-12], b'', raw+b'{"secret":"'+SECRET.encode()):
            with self.subTest(length=len(altered)):
                self.overwrite(altered)
                review = review_existing()
                self.assertEqual((review.integrity, review.execution, review.crash_outcome),
                                 ('UNKNOWN', 'HARD_BLOCKED', 'UNKNOWN'))
                self.assertNotIn(SECRET, repr(review))

    def test_bad_hash_sequence_duplicate_key_and_extra_schema_are_unknown(self):
        self.create()
        original = self.log.read_bytes()
        envelope = json.loads(original)
        cases = []
        for key, value in (('sequence', 1), ('previous_sha256', 'c'*64),
                           ('sha256', 'd'*64), ('event', SECRET)):
            data = dict(envelope)
            data[key] = value
            cases.append(journal._canonical(data)+b'\n')
        cases.append(original[:-2]+b',"secret":"'+SECRET.encode()+b'"}\n')
        cases.append(original.replace(b'"version":1', b'"version":1,"version":1'))
        for altered in cases:
            self.overwrite(altered)
            self.assertEqual(review_existing().integrity, 'UNKNOWN')

    def test_external_header_and_tip_pins_detect_rewritten_chain(self):
        owned = self.create()
        tip = owned.public_summary()['tip_sha256']
        envelope = json.loads(self.log.read_bytes())
        envelope['data']['authorization_reference_sha256'] = 'c'*64
        content = {key: value for key, value in envelope.items() if key != 'sha256'}
        envelope['sha256'] = journal._digest(content)
        self.overwrite(journal._canonical(envelope)+b'\n')
        # A hash chain is not a signature; unpinned self-consistency cannot
        # identify arbitrary same-euid rewriting, and still cannot enable I/O.
        self.assertEqual(review_existing().execution, 'HARD_BLOCKED')
        self.assertEqual(review_existing(expected_tip_sha256=tip).reason, 'JOURNAL_PIN_MISMATCH')
        self.assertEqual(review_existing(expected_authorization_reference_sha256='a'*64).reason,
                         'JOURNAL_PIN_MISMATCH')

    def test_log_permissions_hardlink_and_directory_permissions_are_rejected(self):
        self.create()
        for path in (self.root, self.root/'runtime', self.log.parent, self.log):
            original = stat.S_IMODE(path.stat().st_mode)
            path.chmod(0o755 if path.is_dir() else 0o644)
            self.assertEqual(review_existing().integrity, 'UNKNOWN')
            path.chmod(original)
        other = self.fixture/'hardlink'
        os.link(self.log, other)
        self.assertEqual(review_existing().reason, 'JOURNAL_FILE_INVALID')

    def test_symlinked_log_and_ancestor_never_followed(self):
        self.create()
        saved = self.log.with_name('saved')
        self.log.rename(saved)
        self.log.symlink_to(saved)
        self.assertEqual(review_existing().integrity, 'UNKNOWN')
        self.log.unlink()
        saved.rename(self.log)
        original = self.root/'runtime'
        moved = self.root/'runtime-saved'
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        self.assertEqual(review_existing().integrity, 'UNKNOWN')

    def test_unregistered_child_and_oversized_log_are_rejected(self):
        self.create()
        extra = self.log.parent/'unknown'
        extra.write_text(SECRET)
        self.assertEqual(review_existing().reason, 'JOURNAL_UNREGISTERED_CHILD')
        extra.unlink()
        self.overwrite(b'x'*(journal.MAX_JOURNAL_BYTES+1))
        self.assertEqual(review_existing().reason, 'JOURNAL_FILE_INVALID')

    def test_changed_held_inode_is_rejected_before_append(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        original = self.log.read_bytes()
        self.log.unlink()
        self.overwrite(original)
        self.assert_denied(lambda: owned.append_intent(intent))
        self.assertEqual(owned.public_summary()['status'], 'CLOSED')

    def test_partial_append_failure_never_returns_receipt_or_auto_deletes(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        real_write = os.write
        count = [0]
        def write(fd, view):
            count[0] += 1
            if count[0] == 1:
                return real_write(fd, view[:7])
            raise OSError('SYNTHETIC_JOURNAL_SECRET_DO_NOT_PRINT')
        with patch.object(os, 'write', side_effect=write):
            self.assert_denied(lambda: owned.append_intent(intent))
        self.assertEqual(review_existing().integrity, 'UNKNOWN')
        self.assert_denied(self.capability.cleanup)
        self.assertTrue(self.log.exists())

    def test_fsync_failure_never_returns_durable_receipt(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        with patch.object(os, 'fsync', side_effect=OSError(SECRET)):
            self.assert_denied(lambda: owned.append_intent(intent))
        self.assertEqual(owned.public_summary()['status'], 'CLOSED')
        self.assertTrue(self.log.exists())
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        self.assert_denied(lambda: owned.append_receipt(self.registry._intents[intent.intent_id]), 'JOURNAL_DISABLED')

    def test_lock_held_by_another_open_description_is_not_waited_on(self):
        owned = self.create()
        descriptor = os.open(self.log, os.O_RDWR)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(review_existing().integrity, 'UNKNOWN')
            intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
            self.assert_denied(lambda: owned.append_intent(intent))
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def test_record_and_total_byte_quotas_refuse_before_write(self):
        owned = self.create()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        original = self.log.read_bytes()
        with patch.object(journal, 'MAX_RECORDS', 1):
            self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_RECORD_LIMIT')
        self.assertEqual(self.log.read_bytes(), original)
        self.assertEqual(review_existing().integrity, 'VALIDATED_RECORDS_ONLY')
        self.assert_denied(lambda: journal._read_chain(original+b'x'*(journal.MAX_JOURNAL_BYTES)),
                           'JOURNAL_INCOMPLETE_UNKNOWN')

    def test_cleanup_of_valid_registered_journal_removes_only_owned_fixture(self):
        owned = self.create()
        sentinel = self.fixture/'unrelated'
        sentinel.write_text(SECRET)
        owned.close()
        result = self.capability.cleanup()
        self.assertEqual(result['status'], 'LANDING_CLEANED')
        self.assertFalse(self.root.exists())
        self.assertEqual(sentinel.read_text(), SECRET)

    def test_invalid_pins_and_clock_identity_do_not_leak(self):
        self.assert_denied(lambda: review_existing(expected_run_id=SECRET), 'JOURNAL_PIN_INVALID')
        self.capability = landing._new_landing()
        self.addCleanup(self.capability.close)
        self.assert_denied(lambda: OwnedJournal.create(self.capability, self.registry, clock_id_sha256=SECRET))
        self.assertFalse((self.root/'runtime').exists())

    def test_double_slash_and_missing_root_review_cannot_create_resources(self):
        self.assertEqual(review_existing().integrity, 'UNKNOWN')
        self.assertFalse(self.root.exists())
        with patch.object(journal, 'ROOT', Path('//invalid/root')):
            self.assertEqual(review_existing().reason, 'JOURNAL_ROOT_INVALID')
        self.assertFalse(self.root.exists())

    def test_full_256_event_capacity_uses_one_registered_file_then_refuses(self):
        owned = self.create()
        decision = self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        for _ in range(journal.MAX_RECORDS - 2):
            owned.append_cleanup_result(decision)
        self.assertEqual(owned.public_summary()['records'], 256)
        self.assertEqual(len(self.capability._entries), 5)
        old = self.log.read_bytes()
        self.assert_denied(lambda: owned.append_cleanup_result(decision), 'JOURNAL_RECORD_LIMIT')
        self.assertEqual(self.log.read_bytes(), old)
        self.assertEqual(review_existing().records, 256)

    def test_total_byte_and_line_quotas_are_checked_before_append(self):
        owned = self.create()
        original = self.log.read_bytes()
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        with patch.object(journal, 'MAX_JOURNAL_BYTES', len(original)+5):
            self.assert_denied(lambda: owned.append_intent(intent), 'JOURNAL_RECORD_LIMIT')
        self.assertEqual(self.log.read_bytes(), original)
        self.assert_denied(lambda: journal._read_chain(b'\n'*(journal.MAX_RECORDS+1)), 'JOURNAL_RECORD_LIMIT')
        self.assert_denied(lambda: journal._read_chain(b'x'*(journal.MAX_RECORD_BYTES+1)+b'\n'),
                           'JOURNAL_RECORD_LIMIT')

    def test_ancestor_replaced_during_read_is_unknown(self):
        self.create()
        real_read = os.read
        changed = [False]
        def read(fd, count):
            result = real_read(fd, count)
            if result and not changed[0]:
                changed[0] = True
                self.root.rename(self.fixture/'moved-root')
                self.root.mkdir(mode=0o700)
            return result
        with patch.object(os, 'read', side_effect=read):
            self.assertEqual(review_existing().reason, 'JOURNAL_ANCESTOR_CHANGED')

    def test_cleanup_residual_schema_and_review_dto_are_fixed(self):
        owned = self.create()
        self.registry.cleanup_plan([])
        owned.append_cleanup_started()
        decision = CleanupDecision('FAILED_CLOSED', residuals=(('container', SECRET),))
        before = self.log.read_bytes()
        self.assert_denied(lambda: owned.append_cleanup_result(decision), 'JOURNAL_CLEANUP_INVALID')
        self.assertEqual(self.log.read_bytes(), before)
        self.assert_denied(lambda: journal.JournalReview('UNKNOWN', reason=SECRET))
        self.assert_denied(lambda: journal.JournalReview('UNKNOWN', execution='READY'))


if __name__ == '__main__':
    unittest.main()
