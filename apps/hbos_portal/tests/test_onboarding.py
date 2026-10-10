from __future__ import annotations

import types
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from hbos_portal.auth import onboarding
from hbos_portal.auth.feishu import FeishuLoginError
from .test_feishu_auth_contract import settings


class PinyinAliasTest(unittest.TestCase):
    def test_pinyin_surnames_latin_empty_and_reserved(self):
        for name, expected in [('张三', 'zhangsan'), ('单明', 'shanming'), ('曾明', 'zengming'),
            ('解峰', 'xiefeng'), ('尉迟明', 'yuchiming'), ('José Smith', 'josesmith'),
            ('', 'member'), ('Administrator', 'memberadministrator'), ('张 三', 'zhangsan')]:
            with self.subTest(name=name):
                self.assertEqual(expected, onboarding.login_alias_base(name))
        self.assertEqual('zhangsan2', onboarding.alias_candidate('zhangsan', 2))
        self.assertEqual('zhangsan3', onboarding.alias_candidate('zhangsan', 3))
        self.assertLessEqual(len(onboarding.alias_candidate(onboarding.login_alias_base('长' * 120), 99999)), 64)

    def test_revoked_and_disabled_identities_cannot_trigger_onboarding(self):
        fake = types.SimpleNamespace(db=types.SimpleNamespace(get_value=lambda *a, **k: 1, rollback=lambda: None))
        identity = {'open_id': 'ou_synthetic_member123', 'tenant_key': 'tenant-approved'}
        row = types.SimpleNamespace(user='original@example.test', enabled=False)
        with patch.object(onboarding, 'frappe', fake), patch.object(onboarding, 'serialize', return_value=nullcontext()), patch('hbos_portal.auth.accounts.identity_row', return_value=row), patch.object(onboarding, 'insert_ordinary_user') as create:
            with self.assertRaises(FeishuLoginError) as error:
                onboarding.resolve_verified_login(settings(), identity)
            self.assertEqual('identity_revoked', error.exception.code)
            create.assert_not_called()
            fake.db.get_value = lambda *a, **k: 0
            with self.assertRaises(FeishuLoginError) as error:
                onboarding.resolve_verified_login(settings(), identity)
            self.assertEqual('account_disabled', error.exception.code)
            create.assert_not_called()
