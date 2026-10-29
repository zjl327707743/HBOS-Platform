import importlib,sys
from types import SimpleNamespace
import pytest

@pytest.mark.parametrize("failure",[ValueError("synthetic storage failure"),RuntimeError("synthetic receipt rejection")])
def test_native_maintenance_envelope_rolls_back_before_reporting_failure(monkeypatch,failure):
    writes=[];rolled_back=[]
    def rollback():
        writes.clear();rolled_back.append(True)
    fake=SimpleNamespace(whitelist=lambda **kwargs:lambda fn:fn,local=SimpleNamespace(response_headers={},request=None),db=SimpleNamespace(rollback=rollback))
    monkeypatch.setitem(sys.modules,"frappe",fake)
    api=importlib.import_module("hb_knowledge_app.hb_knowledge.api")
    monkeypatch.setattr(api,"frappe",fake)
    from hb_knowledge_app.hb_knowledge import maintenance_access
    monkeypatch.setattr(maintenance_access,"require",lambda:None)
    def failed_mutation():
        writes.append("withdraw flag changed before immutable receipt was saved")
        raise failure
    result=api._maintenance_action("withdraw_import",{},failed_mutation)
    assert result["error"]["code"]=="SERVICE_ERROR"
    assert not writes and rolled_back==[True]
