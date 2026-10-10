"""Offline lifecycle adversarial fixtures; no resources or processes are created."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
import socket
import subprocess
import unittest
from unittest.mock import patch

from scripts.release.full_site_restore.common import (
    DOCKER, ORIGIN, OWNER, ROLES, VOLUME_NAMES, RestoreError,
)
from scripts.release.full_site_restore.lifecycle import (
    CleanupDecision, GateProof, LifecycleRegistry, OriginalBaseline,
    OwnerAuthorization, RestoreScope, TaskExitProof,
)
from scripts.release.full_site_restore.ownership import ContainerSpec, MountSpec
from scripts.release.tests.test_full_site_restore_ownership import (
    DB_ID, inspect_fixture, process_fixture, volume_fixture,
)

BASELINE = OriginalBaseline(("f" * 64,), ("original-backend",),
                            ("original-sites",), (7001,), "e" * 64)


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


class FakeOperations:
    """Only synthesizes inspect data and receipts, never executes an adapter."""
    def __init__(self, registry):
        self.registry = registry
        self.events = []
        self.containers = {}
        self.volumes = {}

    def create_container(self, role, *, mounts=(), alter=None):
        intent = self.registry.create_intent("container", role)
        self.events.append(("INTENT_RECORDED", intent.intent_id))
        spec, metadata = inspect_fixture(role, mounts=mounts)
        if alter:
            alter(metadata)
        self.events.append(("SYNTHETIC_CREATE_RECEIPT", metadata["Id"]))
        record = self.registry.confirm_container(intent.intent_id,
            returned_id=metadata["Id"], metadata=metadata, spec=spec)
        self.containers[record.container_id] = metadata
        return record

    def create_volume(self, name):
        intent = self.registry.create_intent("volume", name)
        self.events.append(("INTENT_RECORDED", intent.intent_id))
        metadata = volume_fixture(name)
        self.events.append(("SYNTHETIC_VOLUME_RECEIPT", name))
        record = self.registry.confirm_volume(intent.intent_id,
            returned_name=name, metadata=metadata)
        self.volumes[name] = metadata
        return record

    def unknown_container(self, role):
        intent = self.registry.create_intent("container", role)
        self.events.append(("INTENT_RECORDED", intent.intent_id))
        self.registry.mark_unknown(intent.intent_id, "c" * 64)
        return intent

    def cleanup_plan(self):
        return self.registry.cleanup_plan(list(self.containers.values()),
                                          list(self.volumes.values()))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        authorization = OwnerAuthorization.from_confirmation(
            explicit=True, reference_sha256="a" * 64)
        self.registry = LifecycleRegistry(authorization=authorization,
                                          baseline=BASELINE, clock=self.clock)
        self.ops = FakeOperations(self.registry)

    def assert_denied(self, function, code=None):
        with self.assertRaises(RestoreError) as caught:
            function()
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertRegex(str(caught.exception), r"^[A-Z][A-Z0-9_]+$")
        self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", str(caught.exception))

    def host_tasks(self):
        self.ops.create_container("db")
        backend = self.ops.create_container("backend")
        intent = self.registry.create_intent("host-relay", self.registry.scope.relay_name)
        relay = self.registry.register_host_task(intent.intent_id,
            snapshot=process_fixture(4001), expected_executable="/usr/bin/python3",
            expected_script_sha256="a" * 64, backend_id=backend.container_id)
        intent = self.registry.create_intent("host-child", backend.container_id)
        child = self.registry.register_host_task(intent.intent_id,
            snapshot=process_fixture(4002, parent=relay.pid), expected_executable="/usr/bin/python3",
            expected_script_sha256="a" * 64, backend_id=backend.container_id,
            parent_handle_id=relay.handle_id)
        intent = self.registry.create_intent("container-exec", backend.container_id)
        exec_task = self.registry.register_exec_task(intent.intent_id,
            exec_id="b" * 64, backend_id=backend.container_id, pid=34,
            start_time="synthetic-boot:1002", parent_handle_id=child.handle_id)
        return relay, child, exec_task

    def exit_proof(self, task, **kwargs):
        values = dict(handle_id=task.handle_id, identity_sha256=task.identity_sha256,
                      exited=True, origin="SYNTHETIC", evidence_sha256="d" * 64)
        values.update(kwargs)
        return TaskExitProof(**values)

    def test_scope_is_fixed_and_immutable(self):
        scope = RestoreScope()
        self.assertEqual((len(scope.roles), len(scope.volumes), scope.networks,
                          scope.port, scope.run_seconds, scope.cleanup_seconds), (5, 9, 0, 18092, 2700, 600))
        with self.assertRaises(FrozenInstanceError):
            scope.port = 5178
        for key, value in (('owner', 'another'), ('root', '/tmp'), ('roles', ('db',)),
                           ('volumes', ()), ('networks', 1), ('networks', False),
                           ('host', '127.0.0.1:5178'), ('origin', 'http://original'),
                           ('host_bind', '0.0.0.0'), ('port', 18093),
                           ('run_seconds', 2701), ('cleanup_seconds', 601)):
            with self.subTest(key=key):
                self.assert_denied(lambda: replace(scope, **{key: value}), 'LIFECYCLE_SCOPE_DENIED')

    def test_default_is_closed_and_adapter_never_called(self):
        registry = LifecycleRegistry(clock=self.clock)
        calls = []
        self.assert_denied(lambda: registry.create_intent('container', 'db'),
                           'LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED')
        self.assert_denied(lambda: registry.execute(lambda: calls.append('called')),
                           'LIFECYCLE_PRODUCTION_EXECUTION_DISABLED')
        self.assertFalse(calls)
        decision = registry.cleanup_plan([])
        self.assertFalse(decision.actions)
        self.assertIn('LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED', decision.blockers)
        self.assertIn('LIFECYCLE_BASELINE_REQUIRED', decision.blockers)

    def test_authorization_requires_explicit_new_confirmation(self):
        for args in ({}, {'explicit': False, 'reference_sha256': 'a' * 64},
                     {'explicit': 1, 'reference_sha256': 'a' * 64},
                     {'explicit': True, 'reference_sha256': 'SYNTHETIC_PRIVATE_VALUE'}):
            self.assert_denied(lambda: OwnerAuthorization.from_confirmation(**args),
                               'LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED')
        with self.assertRaises(FrozenInstanceError):
            self.registry.authorization.reference_sha256 = 'b' * 64
        for field in ('scope', 'authorization', 'baseline', 'run_id'):
            with self.subTest(field=field), self.assertRaises(AttributeError):
                setattr(self.registry, field, None)

    def test_empty_malformed_or_colliding_baseline_is_denied(self):
        for field in ('container_ids', 'container_names', 'volume_names', 'pids'):
            with self.subTest(field=field):
                self.assert_denied(lambda: replace(BASELINE, **{field: ()}), 'LIFECYCLE_BASELINE_REQUIRED')
                self.assert_denied(lambda: replace(BASELINE, **{field: ([],)}), 'LIFECYCLE_BASELINE_REQUIRED')
        self.assert_denied(lambda: replace(BASELINE, container_names=(OWNER + '-db',)),
                           'LIFECYCLE_TARGET_COLLISION')
        self.assert_denied(lambda: replace(BASELINE, volume_names=(VOLUME_NAMES[0],)),
                           'LIFECYCLE_TARGET_COLLISION')
        self.assert_denied(lambda: replace(BASELINE, pids=(7001, 7001)), 'LIFECYCLE_BASELINE_REQUIRED')

    def test_intents_precede_receipts_and_bind_each_resource(self):
        record = self.ops.create_container('db')
        self.assertEqual(self.ops.events[0][0], 'INTENT_RECORDED')
        self.assertEqual(self.ops.events[1], ('SYNTHETIC_CREATE_RECEIPT', record.container_id))
        self.assertEqual(self.registry.registered_container('db'), record)
        self.assert_denied(lambda: self.registry.create_intent('container', 'db'), 'LIFECYCLE_DUPLICATE_INTENT')
        self.assert_denied(lambda: self.registry.confirm_container('a' * 64,
            returned_id=record.container_id, metadata=self.ops.containers[record.container_id], spec=record.spec),
            'LIFECYCLE_INTENT_REQUIRED')
        with self.assertRaises(FrozenInstanceError):
            record.name = 'foreign'

    def test_db_anchor_required_and_backend_lookup_readonly(self):
        self.assert_denied(lambda: self.registry.create_intent('container', 'backend'),
                           'LIFECYCLE_DB_ANCHOR_REQUIRED')
        self.assert_denied(self.registry.obtain_precheck_backend, 'LIFECYCLE_CONTAINER_NOT_REGISTERED')
        self.ops.create_container('db')
        backend = self.ops.create_container('backend')
        self.assertIs(self.registry.obtain_precheck_backend(), backend)
        self.assert_denied(lambda: self.registry.registered_container('SYNTHETIC_PRIVATE_VALUE'))

    def test_partial_creation_exact_subset_and_confirmed_absence(self):
        volume = self.ops.create_volume(VOLUME_NAMES[0])
        db = self.ops.create_container('db')
        intent = self.registry.create_intent('container', 'backend')
        self.assert_denied(lambda: self.registry.mark_not_created(intent.intent_id),
                           'LIFECYCLE_CREATE_OUTCOME_UNKNOWN')
        self.registry.mark_not_created(intent.intent_id, confirmed=True)
        decision = self.ops.cleanup_plan()
        self.assertEqual(decision.actions, ((DOCKER, 'stop', db.container_id),
                         (DOCKER, 'rm', db.container_id), (DOCKER, 'volume', 'rm', volume.name)))
        self.assertFalse(decision.executable)
        for action in decision.actions:
            receipt = self.registry.acknowledge_cleanup(action, outcome='SUCCESS')
        self.assertEqual(receipt.status, 'RECORDED_CLEAN')
        self.assertFalse(receipt.residuals)
        self.assertFalse(self.registry.readiness()['ready'])

    def test_unknown_create_outcome_blocks_all_cleanup(self):
        self.ops.create_container('db')
        intent = self.ops.unknown_container('backend')
        decision = self.ops.cleanup_plan()
        self.assertEqual(decision.status, 'BLOCKED_CLOSED')
        self.assertFalse(decision.actions)
        self.assertIn(('intent', intent.intent_id), decision.residuals)
        self.assertNotIn(('container', 'c' * 64), decision.residuals)
        self.assert_denied(lambda: self.registry.create_intent('volume', VOLUME_NAMES[0]), 'LIFECYCLE_CLOSED')
        self.assertEqual(self.registry.snapshot()['failure_code'], 'LIFECYCLE_CREATE_OUTCOME_UNKNOWN')

    def test_pending_creation_outcome_never_infers_absence(self):
        self.ops.create_container('db')
        self.registry.create_intent('volume', VOLUME_NAMES[0])
        decision = self.ops.cleanup_plan()
        self.assertFalse(decision.actions)
        self.assertIn('LIFECYCLE_INTENT_UNRESOLVED', decision.blockers)

    def test_original_id_or_mismatched_receipt_becomes_unknown(self):
        for alteration in (lambda data: data.update(Id=BASELINE.container_ids[0]),
                           lambda data: data['Config'].update(Labels={}),
                           lambda data: data.update(Name='/SYNTHETIC_PRIVATE_VALUE')):
            with self.subTest(alteration=alteration):
                clock = FakeClock()
                registry = LifecycleRegistry(authorization=self.registry.authorization,
                                             baseline=BASELINE, clock=clock)
                ops = FakeOperations(registry)
                self.assert_denied(lambda: ops.create_container('db', alter=alteration))
                self.assertEqual(registry.snapshot()['intent_statuses'][0][1], 'UNKNOWN')
                self.assertFalse(ops.cleanup_plan().actions)

    def test_returned_id_must_equal_inspected_identity(self):
        intent = self.registry.create_intent('container', 'db')
        spec, metadata = inspect_fixture()
        self.assert_denied(lambda: self.registry.confirm_container(intent.intent_id,
            returned_id='9' * 64, metadata=metadata, spec=spec), 'LIFECYCLE_RECEIPT_MISMATCH')
        self.assertEqual(self.registry.snapshot()['intent_statuses'][0][1], 'UNKNOWN')

    def test_volume_receipt_and_container_mount_require_exact_registration(self):
        intent = self.registry.create_intent('volume', VOLUME_NAMES[0])
        self.assert_denied(lambda: self.registry.confirm_volume(intent.intent_id,
            returned_name=VOLUME_NAMES[1], metadata=volume_fixture(VOLUME_NAMES[1])), 'LIFECYCLE_RECEIPT_MISMATCH')
        self.assertFalse(self.registry.cleanup_plan([]).actions)
        registry = LifecycleRegistry(authorization=self.registry.authorization, baseline=BASELINE, clock=self.clock)
        ops = FakeOperations(registry)
        mount = MountSpec('volume', VOLUME_NAMES[0], '/var/lib/mysql', False)
        self.assert_denied(lambda: ops.create_container('db', mounts=(mount,)),
                           'LIFECYCLE_VOLUME_REGISTRATION_REQUIRED')

    def test_fresh_guard_failure_cancels_entire_plan(self):
        self.ops.create_container('db')
        backend = self.ops.create_container('backend')
        self.ops.create_volume(VOLUME_NAMES[0])
        changed = deepcopy(list(self.ops.containers.values()))
        changed[-1]['HostConfig']['Privileged'] = True
        decision = self.registry.cleanup_plan(changed, list(self.ops.volumes.values()))
        self.assertEqual(decision.status, 'FAILED_GUARD_CLOSED')
        self.assertFalse(decision.actions)
        self.assertIn(('container', backend.container_id), decision.residuals)
        self.assert_denied(lambda: self.registry.acknowledge_cleanup((DOCKER, 'rm', DB_ID), outcome='SUCCESS'),
                           'LIFECYCLE_CLEANUP_RECEIPT_INVALID')

    def test_cleanup_exact_set_rejects_missing_and_unregistered_metadata(self):
        db = self.ops.create_container('db')
        metadata = self.ops.containers[db.container_id]
        for current in ([], [metadata, inspect_fixture('backend')[1]]):
            with self.subTest(current=len(current)):
                decision = self.registry.cleanup_plan(current)
                self.assertEqual(decision.status, 'FAILED_GUARD_CLOSED')
                self.assertFalse(decision.actions)

    def test_cleanup_orders_children_roles_db_anchor_and_volumes(self):
        for role in ROLES:
            self.ops.create_container(role)
        for name in VOLUME_NAMES:
            self.ops.create_volume(name)
        decision = self.ops.cleanup_plan()
        self.assertEqual([action[2] for action in decision.actions[:10:2]],
                         [f'{number:064x}' for number in (5, 4, 3, 2, 1)])
        self.assertEqual(decision.actions[9], (DOCKER, 'rm', DB_ID))
        self.assertEqual([action[3] for action in decision.actions[10:]], list(VOLUME_NAMES))
        self.assertTrue(all(action[0] == DOCKER for action in decision.actions))
        self.assertFalse(any(arg in ('--force', '-f', '--filter', 'prune', '*')
                             for action in decision.actions for arg in action))

    def test_run_deadline_starts_once_and_cannot_refresh(self):
        self.assertEqual(self.registry.remaining_seconds(), 2700)
        self.clock.value = 200
        self.ops.create_container('db')
        self.clock.value = 1000
        self.registry.note_owned_action()
        self.assertEqual(self.registry.remaining_seconds(), 1900)
        self.clock.value = 2899
        self.assertEqual(self.registry.remaining_seconds(), 1)
        self.clock.value = 2900
        self.assert_denied(lambda: self.registry.create_intent('volume', VOLUME_NAMES[0]),
                           'LIFECYCLE_DEADLINE_EXPIRED')
        self.assert_denied(self.registry.note_owned_action, 'LIFECYCLE_DEADLINE_EXPIRED')
        self.assertEqual(self.registry.remaining_seconds(), 0)

    def test_new_registry_cannot_resume_old_intents(self):
        db = self.ops.create_container('db')
        old_intent = self.registry.snapshot()['intent_statuses'][0][0]
        restarted = LifecycleRegistry(authorization=self.registry.authorization, baseline=BASELINE, clock=self.clock)
        self.assertNotEqual(restarted.run_id, self.registry.run_id)
        self.assert_denied(lambda: restarted.confirm_container(old_intent,
            returned_id=db.container_id, metadata=self.ops.containers[db.container_id], spec=db.spec),
            'LIFECYCLE_INTENT_REQUIRED')
        self.assertFalse(restarted.cleanup_plan(list(self.ops.containers.values())).actions)

    def test_cleanup_deadline_starts_once_and_never_refreshes(self):
        self.ops.create_container('db')
        first = self.ops.cleanup_plan()
        self.assertTrue(first.actions)
        self.clock.value += 599
        self.assertTrue(self.ops.cleanup_plan().actions)
        self.clock.value += 1
        self.assertEqual(self.registry.cleanup_remaining_seconds(), 0)
        final = self.ops.cleanup_plan()
        self.assertFalse(final.actions)
        self.assertIn('LIFECYCLE_CLEANUP_DEADLINE_EXPIRED', final.blockers)

    def test_invalid_or_backwards_clock_is_denied(self):
        self.registry.remaining_seconds()
        for value in (99, float('nan'), float('inf'), True, 10**999, 'SYNTHETIC_PRIVATE_VALUE'):
            self.clock.value = value
            with self.subTest(value=str(value)):
                self.assert_denied(self.registry.remaining_seconds, 'LIFECYCLE_CLOCK_INVALID')

    def test_host_and_exec_handles_bind_exact_backend_and_fingerprint(self):
        relay, child, exec_task = self.host_tasks()
        self.assertEqual((relay.pid, relay.start_time, exec_task.pid, exec_task.start_time),
                         (4001, 123456, 34, 'synthetic-boot:1002'))
        self.assertEqual(exec_task.exec_id, 'b' * 64)
        self.assertEqual(exec_task.backend_id, self.registry.obtain_precheck_backend().container_id)
        self.assertEqual(exec_task.parent_handle_id, child.handle_id)
        self.assertEqual(child.parent_handle_id, relay.handle_id)
        with self.assertRaises(FrozenInstanceError):
            exec_task.backend_id = BASELINE.container_ids[0]
        intent = self.registry.create_intent('container-exec', exec_task.backend_id)
        self.assert_denied(lambda: self.registry.register_exec_task(intent.intent_id,
            exec_id='c' * 64, backend_id=BASELINE.container_ids[0], pid=35,
            start_time=1001, parent_handle_id=child.handle_id), 'LIFECYCLE_TASK_DENIED')

    def test_task_registration_rejects_pid_reuse_exec_reuse_and_wrong_parent(self):
        for failure in ('pid-reuse', 'exec-reuse', 'wrong-parent'):
            with self.subTest(failure=failure):
                self.setUp()
                relay, child, exec_task = self.host_tasks()
                if failure == 'pid-reuse':
                    intent = self.registry.create_intent('host-child', relay.backend_id)
                    self.assert_denied(lambda: self.registry.register_host_task(intent.intent_id,
                        snapshot=process_fixture(relay.pid, parent=relay.pid), expected_executable='/usr/bin/python3',
                        expected_script_sha256='a' * 64, backend_id=relay.backend_id,
                        parent_handle_id=relay.handle_id))
                else:
                    intent = self.registry.create_intent('container-exec', relay.backend_id)
                    self.assert_denied(lambda: self.registry.register_exec_task(intent.intent_id,
                        exec_id=exec_task.exec_id if failure == 'exec-reuse' else 'c' * 64,
                        backend_id=relay.backend_id, pid=39, start_time=1,
                        parent_handle_id=child.handle_id if failure == 'exec-reuse' else []),
                        'LIFECYCLE_TASK_DUPLICATE' if failure == 'exec-reuse' else 'LIFECYCLE_TASK_PARENT_REQUIRED')
                self.assertIn((intent.intent_id, 'UNKNOWN'), self.registry.snapshot()['intent_statuses'])
                self.assertEqual(self.registry.snapshot()['status'], 'CLOSED')
                self.assertFalse(self.ops.cleanup_plan().actions)

    def test_cleanup_requires_ingress_withdrawal_and_all_task_exits(self):
        relay, child, exec_task = self.host_tasks()
        decision = self.ops.cleanup_plan()
        self.assertFalse(decision.actions)
        self.assertIn('LIFECYCLE_INGRESS_UNCONFIRMED', decision.blockers)
        self.assertIn('LIFECYCLE_TASK_EXIT_UNCONFIRMED', decision.blockers)
        self.assert_denied(lambda: self.registry.confirm_ingress_closed(
            origin='http://original:5178', evidence_sha256='a' * 64), 'LIFECYCLE_INGRESS_UNCONFIRMED')
        self.registry.confirm_ingress_closed(origin=ORIGIN, evidence_sha256='a' * 64)
        self.assertFalse(self.ops.cleanup_plan().actions)
        self.assertEqual(self.registry.pending_shutdown_tasks(), (exec_task, child, relay))
        self.assert_denied(lambda: self.registry.confirm_task_exit(self.exit_proof(relay)),
                           'LIFECYCLE_TASK_CHILDREN_ACTIVE')
        for task in (exec_task, child, relay):
            self.registry.confirm_task_exit(self.exit_proof(task))
        decision = self.ops.cleanup_plan()
        self.assertTrue(decision.actions)
        self.assertFalse(decision.executable)
        self.assertFalse(self.registry.readiness()['ready'])

    def test_exit_proof_identity_and_no_actual_exit_are_rejected(self):
        relay, child, exec_task = self.host_tasks()
        self.assert_denied(lambda: self.registry.confirm_task_exit(
            self.exit_proof(exec_task, identity_sha256='e' * 64)), 'LIFECYCLE_TASK_EXIT_UNCONFIRMED')
        self.assert_denied(lambda: self.exit_proof(exec_task, exited=False), 'LIFECYCLE_TASK_EXIT_UNCONFIRMED')
        self.assertEqual(len(self.registry.pending_shutdown_tasks()), 3)

    def test_failed_or_unknown_cleanup_receipt_preserves_residuals_and_closes(self):
        for outcome in ('FAILED', 'UNKNOWN'):
            with self.subTest(outcome=outcome):
                registry = LifecycleRegistry(authorization=self.registry.authorization,
                                             baseline=BASELINE, clock=FakeClock())
                ops = FakeOperations(registry)
                db = ops.create_container('db')
                plan = ops.cleanup_plan()
                decision = registry.acknowledge_cleanup(plan.actions[0], outcome=outcome)
                self.assertEqual(decision.status, 'FAILED_CLOSED')
                self.assertIn(('container', db.container_id), decision.residuals)
                self.assert_denied(lambda: registry.acknowledge_cleanup(plan.actions[1], outcome='SUCCESS'),
                                   'LIFECYCLE_CLEANUP_RECEIPT_INVALID')
                self.assert_denied(lambda: registry.create_intent('volume', VOLUME_NAMES[0]), 'LIFECYCLE_CLOSED')

    def test_cleanup_receipts_cannot_skip_or_reorder_actions(self):
        self.ops.create_container('db')
        plan = self.ops.cleanup_plan()
        self.assert_denied(lambda: self.registry.acknowledge_cleanup(plan.actions[1], outcome='SUCCESS'),
                           'LIFECYCLE_CLEANUP_RECEIPT_INVALID')
        self.assert_denied(lambda: self.registry.acknowledge_cleanup(plan.actions[0], outcome='SYNTHETIC_PRIVATE_VALUE'),
                           'LIFECYCLE_CLEANUP_RECEIPT_INVALID')
        self.clock.value += 600
        result = self.registry.acknowledge_cleanup(plan.actions[0], outcome='SUCCESS')
        self.assertEqual(result.status, 'FAILED_CLOSED')
        self.assertIn(('container', DB_ID), result.residuals)

    def test_fixed_two_phase_container_budget_rejects_type_aliases_or_expansion(self):
        scope = RestoreScope()
        self.assertEqual(scope.container_incarnations, 10)
        self.assertEqual(scope.max_simultaneous_containers, 5)
        self.assertEqual(scope.phases, ('namespace-volume-initialize', 'service'))
        for field, values in (
            ('container_incarnations', (False, True, 1, 5, 9, 11, 10.0, '10')),
            ('max_simultaneous_containers', (False, True, 1, 4, 6, 10, 5.0, '5')),
            ('phases', ([], ['namespace-volume-initialize', 'service'], ('service',),
                        ('service', 'namespace-volume-initialize'), (True, 'service'),
                        ('namespace-volume-initialize', 'service', 'another-stage'))),
        ):
            for value in values:
                self.assert_denied(lambda: replace(scope, **{field: value}), 'LIFECYCLE_SCOPE_DENIED')

    def test_generation_transition_never_rebuilds_or_invokes_a_callback(self):
        for role in ROLES:
            self.ops.create_container(role)
        for gate in ('uid', 'network', 'restore', 'session'):
            self.registry.add_gate_proof(GateProof(gate, self.registry.run_id, 'REAL', True, 'a'*64))
        before = self.registry.snapshot()
        calls = []
        for arguments in ((), ('service',), ('namespace-volume-initialize', 'service')):
            self.assert_denied(lambda: self.registry.stage_transition(*arguments,
                callback=lambda: calls.append('called')), 'LIFECYCLE_STAGE_TRANSITION_HARD_BLOCKED')
        self.assertEqual(calls, [])
        self.assertEqual(before, self.registry.snapshot())
        self.assertEqual(self.registry.readiness()['stage_transition'], 'HARD_BLOCKED')
        self.assertEqual(self.registry.readiness()['container_generations'], 'NOT_IMPLEMENTED')
        self.assertFalse(self.registry.readiness()['ready'])
        self.assert_denied(lambda: self.registry.create_intent('container', 'db'), 'LIFECYCLE_DUPLICATE_INTENT')
        self.assert_denied(self.registry.require_service_ready, 'LIFECYCLE_SERVICE_NOT_READY')

    def test_metadata_and_real_claims_never_open_service_stage(self):
        self.assertEqual(self.registry.readiness()['missing_real_gates'], ('uid', 'network', 'restore', 'session'))
        for gate in ('uid', 'network', 'restore', 'session'):
            self.registry.add_gate_proof(GateProof(gate, self.registry.run_id, 'SYNTHETIC', True, 'c' * 64))
        self.assertEqual(len(self.registry.readiness()['missing_real_gates']), 4)
        for gate in ('uid', 'network', 'restore', 'session'):
            self.registry.add_gate_proof(GateProof(gate, self.registry.run_id, 'REAL', True, 'c' * 64))
        self.assertFalse(self.registry.readiness()['missing_real_gates'])
        self.assertFalse(self.registry.readiness()['ready'])
        self.assert_denied(self.registry.require_service_ready, 'LIFECYCLE_SERVICE_NOT_READY')
        self.assert_denied(lambda: self.registry.service_plan('/bin/sh'), 'LIFECYCLE_SERVICE_NOT_READY')
        self.assert_denied(lambda: self.registry.execute(('arbitrary',)), 'LIFECYCLE_PRODUCTION_EXECUTION_DISABLED')
        self.assert_denied(lambda: self.registry.add_gate_proof(
            GateProof('uid', 'e' * 64, 'REAL', True, 'c' * 64)), 'LIFECYCLE_PROOF_INVALID')

    def test_errors_and_snapshot_do_not_expose_raw_inspect_values(self):
        intent = self.registry.create_intent('container', 'db')
        spec, metadata = inspect_fixture()
        metadata['Config']['Env'].append('HTTPS_PROXY=SYNTHETIC_PRIVATE_VALUE')
        self.assert_denied(lambda: self.registry.confirm_container(intent.intent_id,
            returned_id=metadata['Id'], metadata=metadata, spec=spec))
        sanitized = json.dumps(self.registry.snapshot())
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', sanitized)
        self.assertNotIn('Env', sanitized)
        self.assertNotIn('original-backend', sanitized)

    def test_no_process_network_or_docker_operation_is_performed(self):
        with (patch.object(subprocess, 'Popen', side_effect=AssertionError('process forbidden')),
             patch.object(subprocess, 'run', side_effect=AssertionError('process forbidden')),
              patch.object(socket, 'socket', side_effect=AssertionError('network forbidden'))):
            self.ops.create_container('db')
            self.ops.create_volume(VOLUME_NAMES[0])
            plan = self.ops.cleanup_plan()
            self.assertTrue(plan.actions)
            self.assertFalse(plan.executable)
            self.assert_denied(lambda: self.registry.execute(plan), 'LIFECYCLE_PRODUCTION_EXECUTION_DISABLED')

    def test_cleanup_decision_cannot_claim_executable(self):
        self.assert_denied(lambda: CleanupDecision('READY', executable=True), 'LIFECYCLE_INVALID')

    def test_arbitrary_service_spec_cannot_be_registered_as_precheck(self):
        intent = self.registry.create_intent('container', 'db')
        spec, metadata = inspect_fixture()
        spec = replace(spec, command=('/bin/sh', '-c', 'SYNTHETIC_PRIVATE_VALUE'))
        metadata['Config']['Cmd'] = list(spec.command)
        self.assert_denied(lambda: self.registry.confirm_container(intent.intent_id,
            returned_id=metadata['Id'], metadata=metadata, spec=spec))
        self.assertEqual(self.registry.snapshot()['intent_statuses'][0][1], 'UNKNOWN')
        self.assertFalse(self.registry.cleanup_plan([]).actions)

    def test_nonfixed_intent_targets_and_wildcards_are_denied(self):
        for kind, target in (('network', OWNER), ('container', OWNER + '*'),
                             ('container', 'db-extra'), ('volume', 'original-sites'),
                             ([], 'db'), ('container', None), ('host-relay', 'arbitrary')):
            with self.subTest(kind=str(kind), target=str(target)):
                self.assert_denied(lambda: self.registry.create_intent(kind, target), 'LIFECYCLE_INTENT_DENIED')
        self.assertFalse(self.registry.snapshot()['intent_statuses'])

    def test_fresh_volume_change_cancels_container_cleanup_too(self):
        db = self.ops.create_container('db')
        self.ops.create_volume(VOLUME_NAMES[0])
        changed = deepcopy(list(self.ops.volumes.values()))
        changed[0]['Labels'] = {}
        decision = self.registry.cleanup_plan(list(self.ops.containers.values()), changed)
        self.assertEqual(decision.status, 'FAILED_GUARD_CLOSED')
        self.assertFalse(decision.actions)
        self.assertIn(('container', db.container_id), decision.residuals)

    def test_host_snapshot_original_pid_or_changed_fingerprint_blocks_cleanup(self):
        self.ops.create_container('db')
        backend = self.ops.create_container('backend')
        intent = self.registry.create_intent('host-relay', self.registry.scope.relay_name)
        self.assert_denied(lambda: self.registry.register_host_task(intent.intent_id,
            snapshot=process_fixture(BASELINE.pids[0]), expected_executable='/usr/bin/python3',
            expected_script_sha256='a' * 64, backend_id=backend.container_id))
        self.assertFalse(self.ops.cleanup_plan().actions)
        self.assertIn('LIFECYCLE_INTENT_UNRESOLVED', self.ops.cleanup_plan().blockers)


if __name__ == '__main__':
    unittest.main()
