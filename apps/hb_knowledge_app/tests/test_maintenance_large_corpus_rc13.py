"""RC13: the maintenance dashboard must survive a corpus larger than 1000 docs.

The picker is a bounded projection, not a hard failure: publish #1001 must not
take the entire maintenance page down.
"""
import sys
from types import ModuleType

if 'frappe' not in sys.modules:  # dashboard imports frappe; the helper does not use it
    sys.modules['frappe'] = ModuleType('frappe')
# Import surface only: the helper under test never opens a database or cipher.
sys.modules.setdefault('pymysql', ModuleType('pymysql'))
_cipher = ModuleType('cryptography.fernet'); _cipher.Fernet = lambda *a, **k: None
sys.modules.setdefault('cryptography', ModuleType('cryptography'))
sys.modules.setdefault('cryptography.fernet', _cipher)

from hb_knowledge_app.hb_knowledge.maintenance import _published_documents_for_dashboard  # noqa: E402


def test_published_picker_is_bounded_not_fatal():
    published = {f'DOC_{i:024d}': {'document_id': f'DOC_{i:024d}', 'version_id': f'VER_{i:024d}',
                                    'current_version': f'VER_{i:024d}', 'title': f'资料{i:04d}',
                                    'department': 'public_law'}
                 for i in range(1001)}
    values, total = _published_documents_for_dashboard(published)
    assert total == 1001 and len(values) == 1000
    assert values[0]['title'] == '资料0000' and values[-1]['title'] == '资料0999'


def test_published_picker_keeps_every_row_below_the_cap():
    published = {f'DOC_{i:024d}': {'document_id': f'DOC_{i:024d}', 'version_id': f'VER_{i:024d}',
                                    'current_version': f'VER_{i:024d}', 'title': f'资料{i:04d}',
                                    'department': 'public_law'}
                 for i in range(12)}
    values, total = _published_documents_for_dashboard(published)
    assert total == 12 and len(values) == 12
