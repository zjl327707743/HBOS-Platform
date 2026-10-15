from __future__ import annotations

import contextlib
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.release.full_site_restore.common import (
    APP_NAMES, BACKUP_EXPECTED, BEFORE_SHA256, BENCH, DOCKER, OWNER, ROOT, VOLUME_NAMES,
)
from scripts.release.full_site_restore.ownership import MountSpec, ResourceRecord
from scripts.release.tests.test_full_site_restore_ownership import DB_ID, inspect_fixture
from scripts.release.full_site_restore.plan import (build_proposal, frontend_config_template,
    forward_entrypoint_template, FORWARD_PACKAGE_FILES)
from scripts.release.prepare_full_site_restore import main


class PlanTests(unittest.TestCase):
    def test_resource_set_has_only_exact_five_and_nine(self):
        p = build_proposal()
        self.assertEqual([c['role'] for c in p['containers']], ['db', 'redis-cache', 'redis-queue', 'backend', 'frontend'])
        self.assertEqual({v['name'] for v in p['volumes']}, set(VOLUME_NAMES))
        self.assertEqual(p['custom_networks'], [])
        self.assertFalse(p['runtime_ready'])
        self.assertEqual(p['execution'], 'NOT_IMPLEMENTED')

    def test_every_review_argv_is_non_executable_and_without_channels(self):
        for c in build_proposal()['containers']:
            argv = c['argv_template']
            self.assertEqual(argv[:2], [DOCKER, 'create'])
            self.assertIn('<VERIFIED_SERVICE_UID_GID>', argv)
            self.assertFalse(c['executable'])
            self.assertEqual(c['published_ports'], [])
            self.assertEqual(c['ownership_admission'], 'SERVICE_COMMAND_NOT_ADMITTED')
            for denied in ('--privileged', '--publish', '-p', '--publish-all', '--cap-add', '--device'):
                self.assertNotIn(denied, argv)
            if c['role'] == 'db':
                self.assertEqual(c['network'], 'none')
            else:
                self.assertEqual(c['network'], 'container:<VERIFIED_NEW_SERVICE_DB_ID>')

    def test_no_old_paths_or_socket_or_anonymous_volume_in_mounts(self):
        for c in build_proposal()['containers']:
            for m in c['mounts']:
                if m['kind'] == 'volume':
                    self.assertIn(m['source'], VOLUME_NAMES)
                else:
                    self.assertTrue(m['source'].startswith(str(ROOT) + '/'))
                    self.assertTrue(m['read_only'])
                self.assertNotIn('docker.sock', m['source'])
                self.assertNotIn('hbos-m0-r3a', m['source'])
                self.assertNotIn('..', Path(m['source']).parts)

    def test_all_apps_env_and_dists_have_explicit_readonly_proposal(self):
        for c in build_proposal()['containers'][3:]:
            binds = {m['destination']: m for m in c['mounts'] if m['kind'] == 'bind'}
            for app in APP_NAMES:
                self.assertTrue(binds[BENCH + '/apps/' + app]['read_only'])
            self.assertTrue(binds[BENCH + '/env']['read_only'])
            sites = next(m for m in c['mounts'] if m['destination'] == BENCH + '/sites')
            self.assertEqual(sites['read_only'], c['role'] == 'frontend')

    def test_proposal_mutation_does_not_change_next_call(self):
        p = build_proposal()
        p['containers'][0]['argv_template'].clear()
        p['volumes'][0]['name'] = 'original'
        p['pending_gates'].clear()
        other = build_proposal()
        self.assertTrue(other['containers'][0]['argv_template'])
        self.assertEqual(other['volumes'][0]['name'], OWNER + '-db-data')
        self.assertTrue(other['pending_gates'])

    def test_forward_proposal_includes_wrapper_package_and_closed_gate(self):
        p = build_proposal()
        backend = next(c for c in p['containers'] if c['role'] == 'backend')
        binds = {m['destination']: m for m in backend['mounts'] if m['kind'] == 'bind'}
        self.assertTrue(binds['/run/hbos-restore/forward.py']['read_only'])
        self.assertTrue(binds['/run/hbos-restore/full_site_restore']['read_only'])
        self.assertFalse(p['forward_deployment']['materialized'])
        self.assertEqual(p['host_relay']['production_admission'], 'HARD_BLOCKED')

    def test_forward_wrapper_imports_companions_and_stays_disabled(self):
        source = Path(__file__).resolve().parents[1] / 'full_site_restore'
        with tempfile.TemporaryDirectory(prefix='hbos-forward-wrapper-', dir='/private/tmp') as temporary:
            root = Path(temporary)
            package = root / 'full_site_restore'
            package.mkdir(mode=0o700)
            for name in FORWARD_PACKAGE_FILES:
                (package / name).write_bytes((source / name).read_bytes())
            (root / 'forward.py').write_text(forward_entrypoint_template())
            result = subprocess.run([sys.executable, '-B', str(root / 'forward.py')],
                input=b'', capture_output=True, timeout=2)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'')

    def test_observed_source_uid_does_not_admit_new_service_or_volume(self):
        p = build_proposal()
        observed = {c['role']: c['source_pid1_uid_gid_observed'] for c in p['containers']}
        self.assertEqual(observed['db'], '999:999')
        self.assertEqual(observed['redis-cache'], '999:1000')
        for container in p['containers']:
            self.assertEqual(container['uid_gid'], 'NOT_VERIFIED')
            self.assertEqual(container['new_volume_initialization'], 'OFFLINE_COMPONENTS_ONLY_DAEMON_NOT_RUN')
            self.assertFalse(container['executable'])

    def test_two_same_name_batches_require_new_ids_and_all_first_batch_absent(self):
        p = build_proposal()
        self.assertEqual(p['phases'], ['namespace-volume-initialize', 'service'])
        self.assertEqual(len(p['initialization_containers']) + len(p['containers']), 10)
        self.assertEqual(p['resource_limits'], {'container_incarnations': 10,
            'max_simultaneous_containers': 5, 'named_volumes': 9, 'custom_networks': 0, 'host_relays': 1})
        self.assertEqual([c['name'] for c in p['initialization_containers']], [c['name'] for c in p['containers']])
        replacement = p['replacement']
        self.assertEqual(replacement['execution'], 'HARD_BLOCKED')
        self.assertFalse(replacement['in_place_command_or_mount_switch'])
        self.assertFalse(replacement['reuse_previous_container_ids'])
        self.assertTrue(replacement['same_names_new_container_ids'])
        self.assertTrue(replacement['remove_initialization_db_last'])
        self.assertTrue(replacement['create_service_db_first'])
        self.assertTrue(replacement['requires_fresh_all_initialization_absent_receipts'])
        self.assertTrue(replacement['requires_registered_new_generation_receipts'])
        self.assertEqual(replacement['generation_registration'], 'NOT_IMPLEMENTED')
        for c in p['initialization_containers'][1:]:
            self.assertEqual(c['network'], 'container:<VERIFIED_NEW_INITIALIZATION_DB_ID>')

    def test_initialization_has_fixed_nonroot_sleep_and_only_explicit_owned_volumes(self):
        for c in build_proposal()['initialization_containers']:
            argv = c['argv_template']
            self.assertEqual(argv[:2], [DOCKER, 'create'])
            self.assertEqual(argv[-3:], [c['image'], '/bin/sleep', '2700'])
            self.assertEqual(argv[argv.index('--entrypoint')+1], '')
            self.assertEqual(argv[argv.index('--user')+1], '1000:1000')
            self.assertIn('hbos.restore.phase=' + c['phase'], argv)
            self.assertTrue(c['read_only_rootfs'])
            self.assertFalse(c['executable'])
            self.assertEqual(c['entrypoint'], [])
            self.assertEqual(c['command'], ['/bin/sleep', '2700'])
            self.assertEqual(c['cap_drop'], ['ALL'])
            self.assertEqual(c['published_ports'], [])
            self.assertTrue(all(m['kind'] == 'volume' and m['source'] in VOLUME_NAMES for m in c['mounts']))
            for denied in ('--privileged', '--publish', '--cap-add', '--device'):
                self.assertNotIn(denied, argv)

    def test_backend_initialization_six_rw_unique_volumes_and_frontend_readonly_content(self):
        containers = {c['role']: c for c in build_proposal()['initialization_containers']}
        backend = containers['backend']
        self.assertEqual(backend['phase'], 'volume-initialize')
        self.assertEqual(len(backend['mounts']), 6)
        self.assertEqual(len({m['source'] for m in backend['mounts']}), 6)
        self.assertTrue(all(m['read_only'] is False for m in backend['mounts']))
        destinations = {m['destination'] for m in backend['mounts']}
        self.assertIn(BENCH + '/sites/assets', destinations)
        self.assertNotIn(BENCH + '/assets', destinations)
        frontend = containers['frontend']
        self.assertEqual(frontend['phase'], 'namespace-precheck')
        self.assertTrue(all(m['read_only'] is (m['destination'] != BENCH + '/logs') for m in frontend['mounts']))
        self.assertTrue({BENCH + '/sites', BENCH + '/logs', BENCH + '/assets', BENCH + '/sites/assets'}.issubset(
            {m['destination'] for m in frontend['mounts']}))
        for role in ('db', 'redis-cache', 'redis-queue'):
            self.assertEqual(containers[role]['phase'], 'volume-initialize')
            self.assertEqual(len(containers[role]['mounts']), 1)
            self.assertFalse(containers[role]['mounts'][0]['read_only'])

    def test_every_volume_in_both_templates_prevents_image_copy_up(self):
        p = build_proposal()
        for c in p['initialization_containers'] + p['containers']:
            mount_arguments = [c['argv_template'][i+1] for i, word in enumerate(c['argv_template']) if word == '--mount']
            for m, argument in zip(c['mounts'], mount_arguments, strict=True):
                if m['kind'] == 'volume':
                    self.assertIs(m['no_copy'], True)
                    self.assertIn(',volume-nocopy', argument)
                else:
                    self.assertNotIn('volume-nocopy', argument)

    def test_initialization_metadata_shapes_pass_actual_guard_without_runtime_claim(self):
        for c in build_proposal()['initialization_containers']:
            mounts = tuple(MountSpec(**m) for m in c['mounts'])
            spec, metadata = inspect_fixture(c['role'], mounts=mounts)
            spec = replace(spec, phase=c['phase'])
            metadata['Config']['Labels']['hbos.restore.phase'] = c['phase']
            record = ResourceRecord.from_inspect(metadata, expected=spec, original_ids=('f'*64,),
                original_names=('original-backend',), original_volume_names=('original-sites',),
                db_id=None if c['role'] == 'db' else DB_ID)
            self.assertEqual(record.spec.phase, c['phase'])
            self.assertEqual(c['ownership_admission'], 'OFFLINE_METADATA_ONLY_RUNTIME_NOT_RUN')

    def test_new_pending_gates_describe_components_without_claiming_runtime(self):
        pending = build_proposal()['pending_gates']
        self.assertIn('REGISTRY_AND_JOURNAL_OFFLINE_VALIDATED_TRUSTED_CAPTURE_NOT_IMPLEMENTED', pending)
        self.assertIn('VOLUME_INITIALIZATION_OFFLINE_VALIDATED_DAEMON_UID_MODE_AND_NO_COPY_NOT_RUN', pending)
        self.assertIn('NESTED_MOUNT_EMPTY_VOLUME_CAPTURE_NOT_VERIFIED', pending)
        self.assertIn('TWO_BATCH_REPLACEMENT_FRESH_ABSENCE_RECEIPTS_AND_GENERATIONS_NOT_IMPLEMENTED', pending)
        self.assertIn('DEADLINE_AND_OWNED_CLEANUP_OFFLINE_VALIDATED_COMPLETE_RUNTIME_ABSENCE_NOT_IMPLEMENTED', pending)

    def test_nginx_review_config_only_loopback_no_ws_or_original_upstream(self):
        text = frontend_config_template()
        self.assertIn('listen 127.0.0.1:8080', text)
        self.assertIn('proxy_pass http://127.0.0.1:8000;', text)
        self.assertIn('location /socket.io { return 403; }', text)
        self.assertIn('location /private { return 403; }', text)
        for denied in ('0.0.0.0', '[::]', '5178', 'hbos-m0-r3a', 'resolver', 'websocket'):
            self.assertNotIn(denied, text)

    def test_pins_match_public_preparation_evidence_and_are_immutable(self):
        source = Path(__file__).resolve().parents[3] / 'docs/milestones/evidence/人员权限_完整Site恢复准备摘要_20261010.json'
        evidence = json.loads(source.read_text())['validated_backup_recheck']
        self.assertEqual({k: dict(v) for k, v in BACKUP_EXPECTED.items()}, evidence['files'])
        self.assertEqual(BEFORE_SHA256, evidence['private_before_and_manifest']['before.json']['sha256'])
        with self.assertRaises(TypeError):
            BACKUP_EXPECTED['database']['sha256'] = '0' * 64

    def test_default_cli_cannot_connect_launch_or_read_inputs(self):
        output = io.StringIO()
        with patch('subprocess.run', side_effect=AssertionError('process')), patch('socket.socket', side_effect=AssertionError('socket')), patch('builtins.open', side_effect=AssertionError('open')), contextlib.redirect_stdout(output):
            code = main([])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['execution'], 'NOT_IMPLEMENTED')

    def test_execute_and_arbitrary_arguments_are_rejected_without_echo(self):
        for argv in (['--execute'], ['--expected-evidence', 'SECRET_SENTINEL'], ['SECRET_SENTINEL']):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(argv)
            self.assertEqual(code, 2)
            self.assertNotIn('SECRET_SENTINEL', output.getvalue())
            self.assertEqual(json.loads(output.getvalue())['code'], 'RESTORE_ARGUMENTS_INVALID')

    def test_cli_manifest_uses_fixed_pins_and_sanitizes_os_failure(self):
        output = io.StringIO()
        module = 'scripts.release.full_site_restore.inputs.validate_backup_inputs'
        with patch(module, side_effect=OSError('PRIVATE_PATH_SECRET_SENTINEL')) as check, contextlib.redirect_stdout(output):
            code = main(['--manifest', '/private/path/SECRET_SENTINEL'])
        self.assertEqual(code, 2)
        self.assertEqual(check.call_args.args[1], {k: dict(v) for k, v in BACKUP_EXPECTED.items()})
        self.assertEqual(check.call_args.args[2], BEFORE_SHA256)
        self.assertNotIn('SECRET_SENTINEL', output.getvalue())


if __name__ == '__main__':
    unittest.main()
