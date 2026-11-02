import json,time,sys
from types import SimpleNamespace
from hb_knowledge_app.hb_knowledge import request_profile as p

def test_profile_real_login_once_without_payload_or_credentials(tmp_path,monkeypatch):
    rid='rc1-profile-SYNTHETIC';arm=tmp_path/'arm.json';out=tmp_path/'out'
    arm.write_text(json.dumps({'request_id':rid,'expires_at':time.time()+60}))
    local=SimpleNamespace(form_dict={'password':'SYNTHETIC_SECRET','query':'PRIVATE_BODY'})
    frappe=SimpleNamespace(local=local,request=SimpleNamespace(path='/api/method/hb_knowledge_app.hb_knowledge.api.search',headers={'X-HBOS-Request-ID':rid}),session=SimpleNamespace(user='Synthetic employee'))
    monkeypatch.setitem(sys.modules,'frappe',frappe);monkeypatch.setattr(p,'ARM',arm);monkeypatch.setattr(p,'OUT',out)
    p.begin();sum(range(100));p.finish(SimpleNamespace(status_code=200))
    result=list(out.glob('*.json'));assert len(result)==1
    text=result[0].read_text();value=json.loads(text)
    assert value['handler_wall_s']>0 and value['handler_thread_cpu_s']>=0 and value['functions']
    assert 'SYNTHETIC_SECRET' not in text and 'PRIVATE_BODY' not in text
    frappe.session.user='Guest';p.begin();assert not hasattr(local,'hbos_request_profile')
