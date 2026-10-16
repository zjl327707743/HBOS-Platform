import importlib,sys
from types import SimpleNamespace

def setup(monkeypatch,legacy=None):
    fake=SimpleNamespace(session=SimpleNamespace(user='maintainer@example.invalid'))
    monkeypatch.setitem(sys.modules,'frappe',fake)
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',
                        SimpleNamespace(configuration=lambda:{}))
    m=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(m,'frappe',fake);monkeypatch.setattr(m,'require',lambda:None)
    state={'batch_sha256':'a'*64,'items':[{'canonical_document_id':'DOC','version_id':'NEW'}]}
    monkeypatch.setattr(m,'_row',lambda *args:({}, {},state))
    committed=[];approvals=[]
    if legacy:committed.append(legacy)
    fake.get_all=lambda table,filters,**kw:[r for r in committed if all(r.get(k)==v for k,v in filters.items())]
    def publish(path,op,expected,reason,approval,docs,**kw):
        approvals.append(approval)
        committed.append({'canonical_document_id':'DOC','target_version':'NEW','batch_sha256':'a'*64,
                          'operation':op,'expected_current_version':expected,'reason':reason,'approval_ref':approval})
        return {'approval':approval}
    admin=importlib.import_module('hb_knowledge_app.hb_knowledge.reference_admin')
    monkeypatch.setattr(admin,'publish',publish)
    return m,fake,committed,approvals

def test_repeat_intent_keeps_receipt_identity_but_other_actor_or_reason_is_distinct(monkeypatch):
    m,fake,_,seen=setup(monkeypatch)
    for _ in range(2):m.publish('BATCH',['DOC'],'replace','OLD','Replace approved fixture')
    assert seen[0]==seen[1]
    fake.session.user='other@example.invalid'
    m.publish('BATCH',['DOC'],'replace','OLD','Replace approved fixture')
    assert seen[2]!=seen[0]
    fake.session.user='maintainer@example.invalid'
    m.publish('BATCH',['DOC'],'replace','OLD','Different intent')
    assert seen[3]!=seen[0]

def test_retry_reuses_immutable_legacy_random_approval(monkeypatch):
    legacy={'canonical_document_id':'DOC','target_version':'NEW','batch_sha256':'a'*64,
        'operation':'replace','expected_current_version':'OLD','reason':'Replace approved fixture',
        'approval_ref':'NATIVE_MAINTENANCE:maintainer@example.invalid:original-random'}
    m,_,committed,seen=setup(monkeypatch,legacy)
    before=dict(legacy)
    m.publish('BATCH',['DOC'],'replace','OLD','Replace approved fixture')
    assert seen==[legacy['approval_ref']] and committed[0]==before

def test_second_withdrawal_returns_receipt_without_another_write(monkeypatch):
    m,fake,_,_=setup(monkeypatch)
    current={'current_version':'NEW','withdrawn':0,'source_hash':'a'*64};writes=[];receipts=[]
    fake.db=SimpleNamespace(sql=lambda *args,**kw:[dict(current)],
        set_value=lambda *args: (current.update(args[-1]),writes.append(args)),commit=lambda:None)
    fake.get_doc=lambda value:SimpleNamespace(insert=lambda **kw:receipts.append(value))
    fake.get_all=lambda *args,**kw:receipts[-1:]
    one=m.withdraw('BATCH','DOC','NEW','Withdraw fixture')
    two=m.withdraw('BATCH','DOC','NEW','Withdraw fixture')
    assert one['receipt_id']==two['receipt_id'] and two['outcome']=='NOOP'
    assert len(writes)==len(receipts)==1
