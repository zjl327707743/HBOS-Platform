from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from hbos_portal.auth import diagnostics


class DiagnosticPrivacyTest(unittest.TestCase):
    def test_provider_payload_and_non_numeric_errors_never_enter_trace(self):
        trace = {'calls': []}
        response = types.SimpleNamespace(status_code=403, json=lambda: {
            'code': 'credential-in-error', 'msg': 'private provider profile',
            'access_token': 'private-bearer', 'user': {'name': 'private-person'}})
        diagnostics.safe_http(response, 'internal_member', trace)
        self.assertEqual({'calls': [{'stage': 'internal_member', 'http': 403, 'api_code': None}]}, trace)

    def test_numeric_api_error_and_unknown_boolean_are_distinct(self):
        trace = {'calls': []}
        diagnostics.safe_http(types.SimpleNamespace(status_code=200, json=lambda: {'code': 99991672}), 'internal_member', trace)
        self.assertEqual('99991672', trace['calls'][0]['api_code'])
        self.assertEqual('unknown', diagnostics.shape(None)['judgement'])
        self.assertEqual('false', diagnostics.shape(False)['judgement'])

    def test_private_only_storage_refuses_permissive_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.jsonl'
            fake = types.SimpleNamespace(get_site_path=lambda *a: str(path))
            with patch.object(diagnostics, 'frappe', fake):
                diagnostics.persist({'result': 'member_status_missing'})
                self.assertEqual(0o600, path.stat().st_mode & 0o777)
                self.assertEqual('member_status_missing', json.loads(path.read_text())['result'])
                path.chmod(0o644)
                diagnostics.persist({'result': 'must-not-append'})
                self.assertNotIn('must-not-append', path.read_text())
