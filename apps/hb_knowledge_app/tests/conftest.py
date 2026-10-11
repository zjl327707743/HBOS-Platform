"""Knowledge-domain tests use fake providers and no real network."""
import socket
import pytest

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
