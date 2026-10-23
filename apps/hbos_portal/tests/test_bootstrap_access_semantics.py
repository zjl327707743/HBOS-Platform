import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch

sys.modules.setdefault('frappe',types.SimpleNamespace())
from hbos_portal.services import bootstrap
from hbos_portal.contracts.access import AccessContext


class BootstrapAccessSemanticsTest(unittest.TestCase):
    def test_only_visible_apps_keep_their_providers_actual_semantic_capabilities(self):
        allowed=types.SimpleNamespace(manifest=types.SimpleNamespace(id='attendance',to_dict=lambda:{'id':'attendance'}))
        hidden=types.SimpleNamespace(manifest=types.SimpleNamespace(id='hidden',to_dict=lambda:{'id':'hidden'}))
        fake=types.SimpleNamespace(utils=types.SimpleNamespace(now_datetime=lambda:datetime(2026,10,19)))
        registry=types.SimpleNamespace(ordered_entries=lambda:[allowed,hidden])
        def access(entry):
            return AccessContext(entry.manifest.id,entry is allowed,('attendance.role.managed','attendance.read') if entry is allowed else ('hidden.secret',))
        with patch.dict(sys.modules,{'frappe':fake}),patch.object(bootstrap,'require_authenticated_user',return_value='synthetic'),patch.object(bootstrap,'build_registry',return_value=registry),patch.object(bootstrap,'evaluate_access',side_effect=access),patch.object(bootstrap,'get_user_identity',return_value={}),patch.object(bootstrap,'get_branding',return_value={}):
            result=bootstrap.build_bootstrap()
        self.assertEqual(result['apps'],[{'manifest':{'id':'attendance'},'access':{'can_enter':True,'capabilities':['attendance.role.managed','attendance.read']}}])
