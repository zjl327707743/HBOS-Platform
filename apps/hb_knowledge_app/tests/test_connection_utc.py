import sys
from types import SimpleNamespace
from datetime import datetime,timedelta,timezone
from hb_knowledge_app.hb_knowledge import connections

def test_connection_expiry_does_not_use_the_site_local_timezone(monkeypatch):
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    row=SimpleNamespace(name="SYNTHETIC",label="SYNTHETIC",client_name="Hermes",expires_at=now+timedelta(hours=1),revoked=0,last_used_at=None,stage="Configured")
    fake=SimpleNamespace(get_all=lambda *a,**k:[row],utils=SimpleNamespace(now_datetime=lambda:now+timedelta(hours=8)))
    monkeypatch.setitem(sys.modules,"frappe",fake)
    monkeypatch.setattr(connections,"cfg_endpoint",lambda:"http://local.test/mcp")
    monkeypatch.setattr(connections,"configuration_metadata",lambda field:{})
    monkeypatch.setitem(sys.modules,"hb_knowledge_app.hb_knowledge.api",SimpleNamespace(_availability=lambda runtime:{"blocked":True}))
    runtime=SimpleNamespace(actor=lambda:SimpleNamespace(user_ref="SYNTHETIC"),provider=SimpleNamespace(_current=lambda *a:None),client=None)
    value=connections.list_owned(runtime)
    assert value["items"][0]["expired"] is False
    assert value["items"][0]["expires_at"].endswith("Z")
