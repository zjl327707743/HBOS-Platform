"""Knowledge-domain tests use fake providers and no real network."""
import socket
import sys
from pathlib import Path
import pytest

# The Frappe app is imported as ``hb_knowledge_app`` from its package parent
# (``apps/hb_knowledge_app``), where ``hb_knowledge_app/`` is the real package.
# pytest also inserts the repository ``apps`` directory, whose same-named
# directory is only a container; importing from there yields an empty package
# with no ``hb_knowledge`` submodule. Put the package parent first and drop a
# container package that an earlier import may have cached.
_APP_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE_PARENT = str(_APP_ROOT)
if _PACKAGE_PARENT in sys.path:
    sys.path.remove(_PACKAGE_PARENT)
sys.path.insert(0, _PACKAGE_PARENT)
_cached = sys.modules.get('hb_knowledge_app')
if _cached is not None and not hasattr(_cached, 'hb_knowledge'):
    # Never evict a module that is currently being imported (this conftest).
    for _name in [n for n in list(sys.modules)
                  if (n == 'hb_knowledge_app' or n.startswith('hb_knowledge_app.'))
                  and n != __name__ and not __name__.startswith(n + '.')]:
        sys.modules.pop(_name, None)

@pytest.fixture(autouse=True)
def no_provider_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Synthetic test attempted an actual network connection')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket.socket, 'connect_ex', blocked)


# HBOS-only CI mocks the independent service; joint tests use the real service.
import importlib.util,sys,types
import pytest

@pytest.fixture(autouse=True)
def external_service_adapter(monkeypatch,request):
    if request.module.__name__.rsplit('.',1)[-1] not in {
        'test_bulk_review_uat4','test_sharing_approval_uat4','test_publication_metadata_settle_uat4'}:
        return
    try:
        dependency=importlib.import_module('knowledge_service.ingestion')
        if hasattr(dependency,'processing_approved'):return
    except ModuleNotFoundError:
        pass
    service=types.ModuleType('knowledge_service');service.__path__=[]
    adapter=types.ModuleType('knowledge_service.ingestion')
    # Synthetic authority result for the legacy fixture's explicit approval.
    adapter.processing_approved=lambda frozen,item:bool(item.get('owner_inclusion_confirmed') and item.get('internal_sharing_confirmed') and item.get('approval_ref'))
    def unavailable(*a,**kw):raise AssertionError('External service must be explicitly mocked in this unit test')
    adapter.validate_admin_base=unavailable
    adapter.RUNTIME_STATE_FIELDS={'mode','dataset_id'}
    adapter.RUNTIME_ITEM_FIELDS={'status','dataset_id','ragflow_document_id'}
    service.ingestion=adapter
    monkeypatch.setitem(sys.modules,'knowledge_service',service)
    monkeypatch.setitem(sys.modules,'knowledge_service.ingestion',adapter)
