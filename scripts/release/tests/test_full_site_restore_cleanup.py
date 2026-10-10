"""Synthetic cleanup adapters and fake Popen streams; no engine or PID I/O."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.release.full_site_restore import cleanup
from scripts.release.full_site_restore.common import DOCKER, ORIGIN, ROLES, VOLUME_NAMES, RestoreError
from scripts.release.full_site_restore.lifecycle import LifecycleRegistry, OwnerAuthorization, TaskExitProof
from scripts.release.tests.test_full_site_restore_lifecycle import BASELINE, FakeClock, FakeOperations
from scripts.release.tests.test_full_site_restore_ownership import process_fixture


SECRET = "SYNTHETIC_CLEANUP_SECRET_DO_NOT_PRINT"
MUTATIONS = frozenset({"stop", "rm", "volume-rm"})


class FakeStream:
    def __init__(self, descriptor, data=b""):
        self.descriptor = descriptor
        self.chunks = [data, b""] if data else [b""]
        self.closed = False

    def fileno(self):
        return self.descriptor

    def close(self):
        self.closed = True


class FakePopen:
    def __init__(self, stdout=b"", stderr=b"", exit_code=0):
        self.stdout = FakeStream(20001, stdout)
        self.stderr = FakeStream(20002, stderr)
        self.exit_code = exit_code
        self.reaped = False
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.exit_code

    def wait(self, timeout):
        self.reaped = True
        return self.exit_code

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class FakeSelector:
    def __init__(self):
        self.mapping = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def register(self, stream, _event, kind):
        self.mapping[stream.fileno()] = SimpleNamespace(fd=stream.fileno(), fileobj=stream, data=kind)

    def unregister(self, stream):
        del self.mapping[stream.fileno()]

    def get_map(self):
        return self.mapping

    def select(self, _timeout):
        return [(key, 1) for key in tuple(self.mapping.values())]


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.registry = LifecycleRegistry(authorization=OwnerAuthorization.from_confirmation(
            explicit=True, reference_sha256="a" * 64), baseline=BASELINE, clock=self.clock)
        self.ops = FakeOperations(self.registry)

    def create(self, *, roles=ROLES, volumes=VOLUME_NAMES):
        for name in volumes:
            self.ops.create_volume(name)
        for role in roles:
            self.ops.create_container(role)
        return self.adapter()

    def adapter(self, *, faults=None):
        return cleanup.SyntheticCleanupAdapter(containers=list(self.ops.containers.values()),
            volumes=list(self.ops.volumes.values()), faults=faults)

    def mutations(self, adapter):
        return [event for event in adapter.events if event[0] in MUTATIONS]

    def run_fixture(self, adapter, **kwargs):
        kwargs.setdefault("enabled", True)
        report = cleanup.execute_fixture_cleanup(self.registry, adapter, **kwargs)
        self.assertFalse(report.production_ready)
        self.assertEqual(report.landing_cleanup, "SEPARATE_AUDIT_REQUIRED")
        self.assertNotIn(SECRET, repr(report))
        return report

    def rejected(self, operation, code):
        with self.assertRaises(RestoreError) as caught:
            operation()
        self.assertEqual(str(caught.exception), code)
        self.assertNotIn(SECRET, str(caught.exception))

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
            expected_script_sha256="a" * 64, backend_id=backend.container_id, parent_handle_id=relay.handle_id)
        intent = self.registry.create_intent("container-exec", backend.container_id)
        task = self.registry.register_exec_task(intent.intent_id, exec_id="b" * 64,
            backend_id=backend.container_id, pid=34, start_time="synthetic:1000", parent_handle_id=child.handle_id)
        return relay, child, task

    def proof(self, task, origin="SYNTHETIC"):
        return TaskExitProof(task.handle_id, task.identity_sha256, True, origin, "d" * 64)

    def test_production_facade_never_calls_arbitrary_adapter_or_popen(self):
        adapter = self.create()
        with patch.object(cleanup.subprocess, "Popen", side_effect=AssertionError("real process forbidden")):
            for enabled in (False, True, 1, "yes"):
                report = cleanup.execute_cleanup(self.registry, adapter, enabled=enabled)
                self.assertEqual(report.status, "PRODUCTION_CLEANUP_DISABLED")
        self.assertEqual(adapter.events, [])

    def test_fixture_requires_exact_adapter_and_explicit_boolean(self):
        adapter = self.create(roles=("db",), volumes=())
        for enabled in (False, None, 1, "yes"):
            self.assertEqual(self.run_fixture(adapter, enabled=enabled).status, "FIXTURE_CLEANUP_BLOCKED")
        class Subclass(cleanup.SyntheticCleanupAdapter):
            pass
        self.assertEqual(self.run_fixture(Subclass()).status, "FIXTURE_CLEANUP_BLOCKED")
        self.assertEqual(adapter.events, [])

    def test_full_exact_order_db_last_containers_before_volumes(self):
        adapter = self.create()
        report = self.run_fixture(adapter)
        self.assertEqual(report.status, "FIXTURE_RECORDED_RESOURCES_CLEAN")
        self.assertEqual(report.residuals, ())
        expected = []
        for role in ("frontend", "backend", "redis-queue", "redis-cache", "db"):
            target = self.ops.containers[next(key for key, row in self.ops.containers.items() if row["Name"].endswith("-" + role))]["Id"]
            expected.extend((("stop", target), ("rm", target)))
        expected.extend(("volume-rm", name) for name in VOLUME_NAMES)
        self.assertEqual(self.mutations(adapter), expected)
        self.assertTrue(all(action[0] == DOCKER for action in report.completed_actions))

    def test_each_mutation_has_its_own_fresh_capture_and_intent(self):
        adapter = self.create(roles=("db", "backend"), volumes=VOLUME_NAMES[:1])
        self.run_fixture(adapter)
        since_mutation = []
        for event in adapter.events:
            if event[0] in MUTATIONS:
                target = event[1]
                self.assertIn(("inspect-volume" if event[0] == "volume-rm" else "inspect-container", target), since_mutation)
                self.assertEqual(since_mutation[-1], ("intent-" + event[0], target))
                since_mutation = []
            else:
                since_mutation.append(event)

    def test_pending_intent_causes_zero_mutations(self):
        adapter = self.create(roles=("db",), volumes=())
        self.registry.create_intent("container", "backend")
        report = self.run_fixture(adapter)
        self.assertIn("LIFECYCLE_INTENT_UNRESOLVED", report.blockers)
        self.assertEqual(self.mutations(adapter), [])

    def test_unknown_creation_causes_zero_mutations_and_exact_residual(self):
        adapter = self.create(roles=("db",), volumes=())
        intent = self.registry.create_intent("container", "backend")
        self.registry.mark_unknown(intent.intent_id, "e" * 64)
        report = self.run_fixture(adapter)
        self.assertIn(("intent", intent.intent_id), report.residuals)
        self.assertEqual(self.mutations(adapter), [])

    def test_unclosed_ingress_or_unconfirmed_exec_exit_prevents_mutations(self):
        relay, child, task = self.host_tasks()
        adapter = self.adapter()
        report = self.run_fixture(adapter)
        self.assertIn("LIFECYCLE_INGRESS_UNCONFIRMED", report.blockers)
        self.assertIn("LIFECYCLE_TASK_EXIT_UNCONFIRMED", report.blockers)
        self.assertEqual(self.mutations(adapter), [])
        self.assertIn(("task", task.handle_id), report.residuals)

    def test_host_reap_proof_does_not_confirm_container_exec_exit(self):
        relay, child, task = self.host_tasks()
        self.registry.confirm_ingress_closed(origin=ORIGIN, evidence_sha256="c" * 64)
        self.rejected(lambda: self.registry.confirm_task_exit(self.proof(child)), "LIFECYCLE_TASK_CHILDREN_ACTIVE")
        adapter = self.adapter()
        self.assertIn("LIFECYCLE_TASK_EXIT_UNCONFIRMED", self.run_fixture(adapter).blockers)
        self.assertEqual(self.mutations(adapter), [])

    def test_caller_real_exit_dto_never_becomes_real_adapter_admission(self):
        relay, child, task = self.host_tasks()
        for handle in (task, child, relay):
            self.registry.confirm_task_exit(self.proof(handle, origin="REAL"))
        self.registry.confirm_ingress_closed(origin=ORIGIN, evidence_sha256="c" * 64)
        adapter = self.adapter()
        self.assertIn("CLEANUP_SYNTHETIC_SCOPE_REQUIRED", self.run_fixture(adapter).blockers)
        self.assertEqual(self.mutations(adapter), [])
        self.assertEqual(cleanup.execute_cleanup(self.registry, adapter, enabled=True).status, "PRODUCTION_CLEANUP_DISABLED")

    def test_all_synthetic_exit_proofs_allow_only_memory_cleanup(self):
        relay, child, task = self.host_tasks()
        for handle in (task, child, relay):
            self.registry.confirm_task_exit(self.proof(handle))
        self.registry.confirm_ingress_closed(origin=ORIGIN, evidence_sha256="c" * 64)
        self.assertEqual(self.run_fixture(self.adapter()).status, "FIXTURE_RECORDED_RESOURCES_CLEAN")

    def test_initial_inspect_failure_causes_zero_mutations(self):
        adapter = self.create(roles=("db",), volumes=())
        target = next(iter(adapter._containers))
        adapter._faults[("inspect-container", target)] = "TIMEOUT"
        report = self.run_fixture(adapter)
        self.assertEqual(report.blockers, ("CLEANUP_INSPECT_FAILED",))
        self.assertEqual(self.mutations(adapter), [])
        self.assertIn(("container", target), report.residuals)

    def test_missing_authorization_or_baseline_prevents_fixture_mutation(self):
        adapter = cleanup.SyntheticCleanupAdapter()
        report = cleanup.execute_fixture_cleanup(LifecycleRegistry(), adapter, enabled=True)
        self.assertIn("LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED", report.blockers)
        self.assertIn("LIFECYCLE_BASELINE_REQUIRED", report.blockers)
        self.assertEqual(self.mutations(adapter), [])

    def test_unowned_or_changed_metadata_causes_zero_mutations(self):
        adapter = self.create(roles=("db",), volumes=())
        target = next(iter(adapter._containers))
        adapter._containers[target]["Config"]["Env"].append("SYNTHETIC_NOTE=" + SECRET)
        report = self.run_fixture(adapter)
        self.assertIn("OWNERSHIP_CHANGED", report.blockers)
        self.assertEqual(self.mutations(adapter), [])

    def test_metadata_changed_before_first_action_is_not_caught_only_at_start(self):
        adapter = self.create(roles=("db",), volumes=())
        target = next(iter(adapter._containers))
        original = cleanup.SyntheticCleanupAdapter.inspect_container
        calls = [0]
        def inspect(instance, identity):
            calls[0] += 1
            if calls[0] == 2:
                instance._containers[identity]["Config"]["Env"].append("SYNTHETIC_NOTE=" + SECRET)
            return original(instance, identity)
        with patch.object(cleanup.SyntheticCleanupAdapter, "inspect_container", inspect):
            report = self.run_fixture(adapter)
        self.assertIn("OWNERSHIP_CHANGED", report.blockers)
        self.assertEqual(self.mutations(adapter), [])

    def test_stop_failure_or_timeout_preserves_target_and_stops_sequence(self):
        for outcome in ("FAILED", "TIMEOUT", "UNKNOWN"):
            with self.subTest(outcome=outcome):
                self.setUp()
                adapter = self.create(roles=("db", "backend"), volumes=())
                target = self.registry.registered_container("backend").container_id
                adapter._faults[("stop", target)] = outcome
                report = self.run_fixture(adapter)
                self.assertEqual(report.blockers, ("CLEANUP_OPERATION_" + outcome,))
                self.assertEqual(self.mutations(adapter), [("stop", target)])
                self.assertIn(("container", target), report.residuals)

    def test_stop_receipt_without_stopped_state_refuses_rm(self):
        adapter = self.create(roles=("db",), volumes=())
        original = cleanup.SyntheticCleanupAdapter.stop_container
        def stop(instance, target, **kwargs):
            receipt = original(instance, target, **kwargs)
            instance._containers[target]["State"]["Running"] = True
            return receipt
        with patch.object(cleanup.SyntheticCleanupAdapter, "stop_container", stop):
            report = self.run_fixture(adapter)
        self.assertIn("CLEANUP_STOP_UNCONFIRMED", report.blockers)
        self.assertEqual(len(self.mutations(adapter)), 1)

    def test_metadata_changed_after_stop_refuses_rm(self):
        adapter = self.create(roles=("db",), volumes=())
        original = cleanup.SyntheticCleanupAdapter.stop_container
        def stop(instance, target, **kwargs):
            receipt = original(instance, target, **kwargs)
            instance._containers[target]["Config"]["Env"].append("SYNTHETIC_NOTE=" + SECRET)
            return receipt
        with patch.object(cleanup.SyntheticCleanupAdapter, "stop_container", stop):
            report = self.run_fixture(adapter)
        self.assertIn("OWNERSHIP_CHANGED", report.blockers)
        self.assertEqual(len(self.mutations(adapter)), 1)

    def test_restart_after_stop_confirmation_is_rejected_before_rm(self):
        adapter = self.create(roles=("db",), volumes=())
        original = cleanup.SyntheticCleanupAdapter.inspect_container
        calls = [0]
        def inspect(instance, target):
            calls[0] += 1
            if calls[0] == 5:
                instance._containers[target]["State"]["Running"] = True
            return original(instance, target)
        with patch.object(cleanup.SyntheticCleanupAdapter, "inspect_container", inspect):
            report = self.run_fixture(adapter)
        self.assertEqual(report.blockers, ("CLEANUP_STOP_UNCONFIRMED",))
        self.assertEqual([event[0] for event in self.mutations(adapter)], ["stop"])
        self.assertTrue(report.residuals)

    def test_rm_failure_preserves_exact_residual_and_does_not_drop_db(self):
        adapter = self.create(roles=("db", "backend"), volumes=())
        target = self.registry.registered_container("backend").container_id
        db = self.registry.registered_container("db").container_id
        adapter._faults[("rm", target)] = "FAILED"
        report = self.run_fixture(adapter)
        self.assertEqual(self.mutations(adapter), [("stop", target), ("rm", target)])
        self.assertIn(("container", target), report.residuals)
        self.assertIn(("container", db), report.residuals)

    def test_volume_failure_preserves_volume_after_confirmed_container_removal(self):
        adapter = self.create(roles=("db",), volumes=VOLUME_NAMES[:1])
        adapter._faults[("volume-rm", VOLUME_NAMES[0])] = "FAILED"
        report = self.run_fixture(adapter)
        self.assertEqual(report.residuals, (("volume", VOLUME_NAMES[0]),))

    def test_volume_metadata_is_rechecked_after_containers_are_removed(self):
        adapter = self.create(roles=("db",), volumes=VOLUME_NAMES[:1])
        original = cleanup.SyntheticCleanupAdapter.inspect_volume
        calls = [0]
        def inspect(instance, name):
            calls[0] += 1
            if calls[0] == 5:
                instance._volumes[name]["Labels"]["synthetic-note"] = SECRET
            return original(instance, name)
        with patch.object(cleanup.SyntheticCleanupAdapter, "inspect_volume", inspect):
            report = self.run_fixture(adapter)
        self.assertEqual(report.blockers, ("OWNERSHIP_CHANGED",))
        self.assertEqual(report.residuals, (("volume", VOLUME_NAMES[0]),))
        self.assertEqual([event[0] for event in self.mutations(adapter)], ["stop", "rm"])

    def test_removed_receipt_without_absence_is_not_acknowledged(self):
        adapter = self.create(roles=("db",), volumes=())
        original = cleanup.SyntheticCleanupAdapter.remove_container
        def remove(instance, target, **kwargs):
            saved = deepcopy(instance._containers[target])
            receipt = original(instance, target, **kwargs)
            instance._containers[target] = saved
            return receipt
        with patch.object(cleanup.SyntheticCleanupAdapter, "remove_container", remove):
            report = self.run_fixture(adapter)
        self.assertIn("CLEANUP_REMOVAL_UNCONFIRMED", report.blockers)
        self.assertTrue(report.residuals)

    def test_caller_receipt_dict_cannot_confirm_action(self):
        adapter = self.create(roles=("db",), volumes=())
        with patch.object(cleanup.SyntheticCleanupAdapter, "stop_container", return_value={"outcome": "SUCCESS"}):
            report = self.run_fixture(adapter)
        self.assertIn("CLEANUP_RECEIPT_INVALID", report.blockers)
        self.assertTrue(report.residuals)

    def test_deadline_expired_before_next_action_preserves_remaining_ids(self):
        adapter = self.create(roles=("db",), volumes=())
        original = cleanup.SyntheticCleanupAdapter.stop_container
        def stop(instance, target, **kwargs):
            receipt = original(instance, target, **kwargs)
            self.clock.value += 601
            return receipt
        with patch.object(cleanup.SyntheticCleanupAdapter, "stop_container", stop):
            report = self.run_fixture(adapter)
        self.assertIn("LIFECYCLE_CLEANUP_DEADLINE_EXPIRED", report.blockers)
        self.assertTrue(report.residuals)
        self.assertEqual(len(self.mutations(adapter)), 1)

    def test_fixture_rejects_objects_with_deepcopy_callbacks(self):
        class Callback:
            def __deepcopy__(self, memo):
                self.fail("callback executed")
        self.rejected(lambda: cleanup.SyntheticCleanupAdapter(containers=[{"Id": "a" * 64, "secret": Callback()}]), "CLEANUP_FIXTURE_INVALID")

    def test_fixture_fault_outcomes_are_exact_strings_without_custom_magic(self):
        calls = []
        class Outcome:
            def __hash__(self):
                calls.append("hash")
                raise AssertionError("magic forbidden")

            def __eq__(self, _other):
                calls.append("equality")
                raise AssertionError("magic forbidden")
        class TextOutcome(str, Outcome):
            __hash__ = Outcome.__hash__
            __eq__ = Outcome.__eq__
        for outcome in ([], {}, Outcome(), TextOutcome("SUCCESS")):
            self.rejected(lambda: cleanup.SyntheticCleanupAdapter(
                faults={("stop", "a" * 64): outcome}), "CLEANUP_FIXTURE_INVALID")
        self.assertEqual(calls, [])

    def test_fixed_adapter_construction_and_methods_are_default_inert(self):
        self.create(roles=("db",), volumes=())
        target = self.registry.registered_container("db").container_id
        with patch.object(cleanup.subprocess, "Popen", side_effect=AssertionError("real child forbidden")):
            adapter = cleanup.FixedDockerCleanupAdapter(self.registry)
            self.rejected(lambda: adapter.inspect_container(target), "CLEANUP_ADAPTER_DISABLED")
            admitted = cleanup.FixedDockerCleanupAdapter(self.registry, enabled=True)
            self.rejected(lambda: admitted.inspect_container(target), "CLEANUP_DURABLE_RUNTIME_CAPTURE_NOT_IMPLEMENTED")
            self.assertEqual(cleanup.execute_cleanup(self.registry, admitted, enabled=True).status, "PRODUCTION_CLEANUP_DISABLED")

    def test_fixed_adapter_rejects_missing_auth_original_or_unregistered_target(self):
        self.rejected(lambda: cleanup.FixedDockerCleanupAdapter(LifecycleRegistry(), enabled=True), "CLEANUP_AUTHORIZATION_REQUIRED")
        self.create(roles=("db",), volumes=())
        adapter = cleanup.FixedDockerCleanupAdapter(self.registry, enabled=True)
        for target in (BASELINE.container_ids[0], "x;kill", "e" * 64):
            self.rejected(lambda: adapter.inspect_container(target), "CLEANUP_UNREGISTERED_TARGET")

    def test_production_adapter_cannot_use_a_different_registry(self):
        self.create(roles=("db",), volumes=())
        adapter = cleanup.FixedDockerCleanupAdapter(self.registry, enabled=True)
        other = LifecycleRegistry(authorization=self.registry.authorization, baseline=BASELINE)
        with patch.object(cleanup.subprocess, "Popen", side_effect=AssertionError("real child forbidden")):
            report = cleanup.execute_cleanup(other, adapter, enabled=True)
        self.assertEqual(report.blockers, ("CLEANUP_PRODUCTION_ADAPTER_REQUIRED",))

    def fixed_call(self, operation, output=b"", stderr=b"", *, exit_code=0, clock=None):
        adapter = cleanup.FixedDockerCleanupAdapter(self.registry, enabled=True)
        process = FakePopen(output, stderr, exit_code)
        streams = {stream.fileno(): stream for stream in (process.stdout, process.stderr)}
        def read(descriptor, _maximum):
            return streams[descriptor].chunks.pop(0)
        with patch.object(adapter, "_require_runtime_capture_ready", return_value=None), patch.object(cleanup.subprocess, "Popen", return_value=process) as popen, patch.object(cleanup.selectors, "DefaultSelector", FakeSelector), patch.object(cleanup.os, "set_blocking"), patch.object(cleanup.os, "read", side_effect=read):
            if clock is None:
                result = operation(adapter)
            else:
                with patch.object(cleanup.time, "monotonic", side_effect=clock):
                    result = operation(adapter)
        return result, process, popen.call_args

    def test_fixed_inspect_exact_engine_endpoint_argv_and_env_with_fake_popen(self):
        self.create(roles=("db",), volumes=())
        target, metadata = next(iter(self.ops.containers.items()))
        result, process, call = self.fixed_call(lambda adapter: adapter.inspect_container(target), json.dumps([metadata]).encode())
        self.assertEqual(result.metadata, metadata)
        self.assertEqual(call.args[0], (DOCKER, "--host", cleanup.DOCKER_ENDPOINT, "container", "inspect", target))
        self.assertFalse(call.kwargs["shell"])
        self.assertEqual(set(call.kwargs["env"]), {"DOCKER_CONFIG"})
        self.assertTrue(process.reaped)
        self.assertTrue(process.stdout.closed and process.stderr.closed)

    def test_fixed_stop_rm_volume_argv_have_no_force_or_arbitrary_parameters(self):
        self.create(roles=("db",), volumes=VOLUME_NAMES[:1])
        target = self.registry.registered_container("db").container_id
        for operation, name, tail in (("stop_container", target, ("stop", "--time", "9", target)), ("remove_container", target, ("rm", target)), ("remove_volume", VOLUME_NAMES[0], ("volume", "rm", VOLUME_NAMES[0]))):
            result, process, call = self.fixed_call(lambda adapter: getattr(adapter, operation)(name, timeout_seconds=10), (name + "\n").encode())
            self.assertEqual(call.args[0][3:], tail)
            self.assertEqual(result.outcome, "SUCCESS")

    def test_fixed_nonzero_or_stderr_is_not_a_missing_resource_proof(self):
        self.create(roles=("db",), volumes=())
        target = self.registry.registered_container("db").container_id
        for stderr, code in ((b"", 1), (SECRET.encode(), 0)):
            self.rejected(lambda: self.fixed_call(lambda adapter: adapter.inspect_container(target), b"[]", stderr, exit_code=code), "CLEANUP_DOCKER_COMMAND_FAILED")

    def test_fixed_capture_stdout_stderr_limits_and_timeout_use_fixed_errors(self):
        self.create(roles=("db",), volumes=())
        target = self.registry.registered_container("db").container_id
        self.rejected(lambda: self.fixed_call(lambda adapter: adapter.inspect_container(target), b"x" * (cleanup.MAX_INSPECT_BYTES + 1)), "CLEANUP_STDOUT_LIMIT")
        self.rejected(lambda: self.fixed_call(lambda adapter: adapter.inspect_container(target), b"", b"x" * (cleanup.MAX_STDERR_BYTES + 1)), "CLEANUP_STDERR_LIMIT")
        times = iter((0.0, 11.0))
        self.rejected(lambda: self.fixed_call(lambda adapter: adapter.inspect_container(target), b"[]", clock=lambda: next(times)), "CLEANUP_DEADLINE_EXPIRED")

    def test_fixed_inspect_rechecks_original_deadline_after_json_decode(self):
        self.create(roles=("db",), volumes=())
        target, metadata = next(iter(self.ops.containers.items()))
        raw = json.dumps([metadata]).encode()
        current_time = [0.0]
        original = cleanup.json.loads
        def decode(*args, **kwargs):
            result = original(*args, **kwargs)
            current_time[0] = 11.0
            return result
        with patch.object(cleanup.json, "loads", side_effect=decode):
            self.rejected(lambda: self.fixed_call(lambda adapter: adapter.inspect_container(target),
                raw, clock=lambda: current_time[0]), "CLEANUP_DEADLINE_EXPIRED")

    def test_fixed_mutation_receipt_rechecks_original_deadline_after_capture(self):
        self.create(roles=("db",), volumes=())
        target = self.registry.registered_container("db").container_id
        current_time = [0.0]
        original = cleanup.FixedDockerCleanupAdapter._reap
        def reap(process):
            original(process)
            current_time[0] = 11.0
        with patch.object(cleanup.FixedDockerCleanupAdapter, "_reap", side_effect=reap):
            self.rejected(lambda: self.fixed_call(lambda adapter: adapter.remove_container(
                target, timeout_seconds=10), (target + "\n").encode(),
                clock=lambda: current_time[0]), "CLEANUP_DEADLINE_EXPIRED")

    def test_fixed_capture_sanitizes_os_errors_and_refuses_invalid_deadlines(self):
        self.create(roles=("db",), volumes=())
        target = self.registry.registered_container("db").container_id
        adapter = cleanup.FixedDockerCleanupAdapter(self.registry, enabled=True)
        with patch.object(adapter, "_require_runtime_capture_ready", return_value=None), patch.object(cleanup.subprocess, "Popen", side_effect=OSError(SECRET)) as popen:
            self.rejected(lambda: adapter.inspect_container(target), "CLEANUP_DOCKER_COMMAND_FAILED")
            popen.reset_mock()
            for deadline in (True, 0, -1, 11, float("nan"), float("inf"), 10 ** 1000):
                self.rejected(lambda: adapter.stop_container(target, timeout_seconds=deadline), "CLEANUP_DEADLINE_EXPIRED")
            popen.assert_not_called()

    def test_fixed_host_child_reap_has_finite_escalation_and_fixed_failure(self):
        child = FakePopen()
        child.exit_code = None
        waits = []
        def wait(timeout):
            waits.append(timeout)
            if len(waits) == 1:
                raise cleanup.subprocess.TimeoutExpired("synthetic", timeout)
            child.exit_code = 0
            child.reaped = True
            return 0
        child.wait = wait
        cleanup.FixedDockerCleanupAdapter._reap(child)
        self.assertEqual(waits, [0.25, 0.25])
        self.assertTrue(child.terminated and child.killed and child.reaped)
        with patch.object(child, "poll", side_effect=OSError(SECRET)):
            self.rejected(lambda: cleanup.FixedDockerCleanupAdapter._reap(child), "CLEANUP_HOST_CHILD_REAP_UNCONFIRMED")

    def test_fixed_inspect_rejects_duplicate_keys_multiple_rows_and_wrong_target(self):
        self.create(roles=("db",), volumes=())
        target = self.registry.registered_container("db").container_id
        for raw in (b'[{"Id":"a","Id":"b"}]', b"[{},{}]", b"[null]", b"[]", b'[{"Id":"wrong"}]', b'[{"Id":NaN}]'):
            self.rejected(lambda: self.fixed_call(lambda adapter: adapter.inspect_container(target), raw), "CLEANUP_CAPTURE_INVALID")

    def test_fixed_success_receipt_requires_exact_id_output(self):
        self.create(roles=("db",), volumes=())
        target = self.registry.registered_container("db").container_id
        self.rejected(lambda: self.fixed_call(lambda adapter: adapter.remove_container(target, timeout_seconds=5), SECRET.encode()), "CLEANUP_RECEIPT_INVALID")


if __name__ == "__main__":
    unittest.main()
