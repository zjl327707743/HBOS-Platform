from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock, patch

sys.modules.setdefault('frappe', types.SimpleNamespace(whitelist=lambda **kw: lambda fn: fn))
from hbos_portal.auth.profile import normalized_avatar_url, sync_verified_avatar


class VerifiedAvatarTest(unittest.TestCase):
    def test_only_https_profile_urls_without_embedded_credentials_are_accepted(self):
        self.assertEqual('https://s1-imfile.feishucdn.com/avatar.png', normalized_avatar_url('https://s1-imfile.feishucdn.com/avatar.png'))
        for value in [None, {}, 'data:image/svg+xml,x', 'javascript:alert(1)', '//evil.test/x',
                      'http://images.test/x', 'https://u:p@images.test/x', 'https://localhost/x',
                      'https://images.test/x?access_token=secret', 'https://images.test/x#fragment', 'https://images.test/a b']:
            with self.subTest(value=value):
                self.assertEqual('', normalized_avatar_url(value))

    def test_missing_avatar_preserves_existing_profile(self):
        db = Mock()
        with patch.object(sys.modules['frappe'], 'db', db, create=True):
            sync_verified_avatar('owned@example.test', {'avatar_url': ''})
        db.set_value.assert_not_called()

    def test_sync_uses_only_user_image_and_picture_failure_rolls_back_its_savepoint(self):
        db, clear_cache = Mock(), Mock()
        db.set_value.side_effect = RuntimeError('synthetic picture failure')
        with patch.object(sys.modules['frappe'], 'db', db, create=True), patch.object(sys.modules['frappe'], 'clear_cache', clear_cache, create=True):
            sync_verified_avatar('owned@example.test', {'avatar_url': 'https://images.test/avatar.png'})
        db.set_value.assert_called_once_with('User', 'owned@example.test', 'user_image', 'https://images.test/avatar.png', update_modified=False)
        db.rollback.assert_called_once_with(save_point='hbos_avatar_sync')
        clear_cache.assert_not_called()
