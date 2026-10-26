"""Exercise the real operator script with simulated storage interruptions."""
from contextlib import ExitStack
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from hbos_portal.auth import feishu, accounts
from .test_feishu_auth_contract import settings

SCRIPT = Path(__file__).resolve().parents[3] / 'scripts/release/configure_feishu.py'
CANONICAL = 'pilot@example.invalid'


class PilotConfigureTest(unittest.TestCase):
    def run_configure(self, fail_key=None):
        writes = []
        values = {'hbos_feishu_app_published': 1, 'hbos_feishu_auto_provision_internal': 1}
        fake = SimpleNamespace(init=Mock(), connect=Mock(), destroy=Mock(), conf=SimpleNamespace(), db=SimpleNamespace(get_value=Mock(return_value=CANONICAL)))
        def update(key, value):
            if key == fail_key:
                raise OSError('synthetic storage interruption')
            values[key] = value
            writes.append((key, value))
            if values['hbos_feishu_app_published']:
                self.assertEqual(1, values.get('hbos_feishu_pilot_enabled'))
                self.assertEqual([CANONICAL], values.get('hbos_feishu_pilot_users'))
                self.assertEqual(0, values.get('hbos_feishu_auto_provision_internal'))
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {'frappe': fake, 'frappe.installer': SimpleNamespace(update_site_config=update)}))
            stack.enter_context(patch.object(sys, 'argv', [str(SCRIPT), '--site', 'synthetic', '--bench', '/synthetic', '--app-id', 'cli_test', '--origin', 'https://hbos.example.test', '--pilot-user', 'Pilot@Example.Invalid']))
            stack.enter_context(patch('os.chdir'))
            stack.enter_context(patch('builtins.print'))
            stack.enter_context(patch('builtins.input', return_value='Synthetic Company'))
            stack.enter_context(patch.object(accounts, 'require_user'))
            stack.enter_context(patch.object(feishu, 'load_settings', return_value=settings()))
            stack.enter_context(patch.object(feishu, 'discover_enterprise', return_value={'name': 'Synthetic Company', 'tenant_key': 'tenant-approved'}))
            stack.enter_context(patch.object(feishu, '_site_private_path', return_value=Path('/synthetic')))
            stack.enter_context(patch.object(feishu, '_store_protected_text'))
            try:
                runpy.run_path(str(SCRIPT), run_name='__main__')
            except OSError:
                if not fail_key:
                    raise
            else:
                if fail_key:
                    self.fail('expected storage interruption')
        fake.destroy.assert_called_once()
        return writes, values

    def test_closes_first_enables_last_and_persists_canonical_user(self):
        writes, values = self.run_configure()
        self.assertEqual(('hbos_feishu_app_published', 0), writes[0])
        self.assertEqual(('hbos_feishu_app_published', 1), writes[-1])
        self.assertEqual([CANONICAL], values['hbos_feishu_pilot_users'])

    def test_partial_configuration_never_reopens_login(self):
        writes, values = self.run_configure('hbos_feishu_oauth_scopes')
        self.assertEqual(0, values['hbos_feishu_app_published'])
        self.assertNotIn(('hbos_feishu_app_published', 1), writes)
