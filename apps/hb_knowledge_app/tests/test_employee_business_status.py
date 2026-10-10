import importlib,sys
from types import SimpleNamespace

def api_module(monkeypatch):
    fake=SimpleNamespace(whitelist=lambda **kw:lambda fn:fn,
        session=SimpleNamespace(user='employee@example.invalid'),
        get_roles=lambda *args:[])
    monkeypatch.setitem(sys.modules,'frappe',fake)
    api=importlib.import_module('hb_knowledge_app.hb_knowledge.api')
    monkeypatch.setattr(api,'frappe',fake)
    access=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_access')
    monkeypatch.setattr(access,'permitted',lambda:False)
    monkeypatch.setattr(api,'_run',lambda fn:fn('STATUS_TEST'))
    monkeypatch.setattr(api,'_can_search',lambda *args:True)
    monkeypatch.setattr(api,'_ask_enabled',lambda *args:True)
    return api

def test_employee_status_cannot_reactivate_legacy_frontend_financial_stops(monkeypatch):
    api=api_module(monkeypatch)
    from knowledge_service.hbos_gateway.availability import unknown
    for state in ('ACCOUNTING_PENDING','EXPIRED','EXHAUSTED','UNAVAILABLE','UNKNOWN'):
        snapshot=dict(unknown(True),status='AVAILABLE',budget_status=state)
        gateway=SimpleNamespace(configured=True,availability=lambda **kw:dict(snapshot),
            answer_status=lambda:dict(configured=True,available=True,budget_status=state))
        runtime=SimpleNamespace(gateway=gateway,actor=lambda:SimpleNamespace(enabled=True),profile='production')
        monkeypatch.setattr(api,'load_runtime',lambda:runtime)
        status=api.get_status()
        assert status['can_search'] and status['ask_enabled'] and status['answer_availability']['available']
        assert 'budget_status' not in status['answer_availability']
        assert 'budget_status' not in status['retrieval_availability']
        # The private diagnostic still carries the original, unmodified fact.
        assert api._availability(runtime,diagnostics=True)['budget_status']==state
        assert snapshot['budget_status']==state

def test_employee_unknown_fallback_has_no_financial_field(monkeypatch):
    api=api_module(monkeypatch)
    runtime=SimpleNamespace(gateway=SimpleNamespace(configured=True))
    result=api._availability(runtime)
    assert result['status']=='UNKNOWN' and not result['blocked']
    assert 'budget_status' not in result
    assert api._availability(runtime,diagnostics=True)['budget_status']=='UNKNOWN'
