"""RC14.1: a source excerpt that cites a URL or a path must not fail the request.

Six RC14 documents were published and searchable in the service, yet the HBOS
search API answered ``UPSTREAM_INVALID_RESULT`` for each of them. The excerpt
gate that runs on the *source* text accepts them (a regulation that cites a
standard's URL is still the document), but the History/Bookmark preview writer
re-ran the *model-output* gate, whose pattern rejects a URL or an absolute path.
The write happens after the search has already succeeded, so the whole request
failed.

These tests pin the behaviour at the point that failed: the preview writer uses
the source gate, stores the excerpt unchanged, and still refuses what the source
gate refuses (credentials, markup, traversal).
"""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def _record(excerpt, *, document='DOC'):
    binding = SimpleNamespace(canonical_document_id=document, version_id='VER',
                              binding_ref='BIND', dataset_alias='ALIAS', space_id='SPACE',
                              title='合成资料', business_version=None, section=None)
    return SimpleNamespace(binding=binding, excerpt=excerpt, page_number=None, chunk_id='CHUNK')


def _fixture(monkeypatch):
    """Minimal frappe double: only the insert that ends ``write``."""
    actor = SimpleNamespace(user_ref='synthetic-owner')
    captured = {}

    class Doc(dict):
        def insert(self, **kwargs):
            captured['payload'] = dict(self)

    monkeypatch.setitem(sys.modules, 'frappe', SimpleNamespace(get_doc=Doc))
    monkeypatch.setattr(activity, 'current', lambda runtime: (actor, {}))
    runtime = SimpleNamespace(publication=SimpleNamespace(publication_id='PUB'))
    return runtime, captured


def test_a_source_excerpt_that_prints_a_url_or_a_path_is_stored_unchanged(monkeypatch):
    excerpt = ('推荐参考以下指南：https://example.invalid/guide.pdf；'
               '并按 /附录/示例 的格式记录。')
    runtime, captured = _fixture(monkeypatch)
    activity.write('History', '合成问题', ['SPACE'], [_record(excerpt)], runtime,
                   search_mode='STANDARD')
    # The payload column is canonical JSON (ASCII-escaped), so decode it first.
    stored = json.loads(captured['payload']['payload_json'])['previews'][0]['excerpt']
    assert stored == excerpt


@pytest.mark.parametrize('excerpt', [
    '访问 api_key: abcdef 获取数据。',
    '内容 <script>x</script> 结束。',
    '路径 ../../private 泄漏。',
])
def test_credentials_markup_and_traversal_are_still_refused(monkeypatch, excerpt):
    runtime, captured = _fixture(monkeypatch)
    with pytest.raises(KnowledgeError):
        activity.write('History', '合成问题', ['SPACE'], [_record(excerpt)], runtime,
                       search_mode='STANDARD')
    assert not captured


@pytest.mark.parametrize('excerpt,allowed', [
    ('资料印刷链接 https://example.invalid/reference.pdf', True),
    ('资料中的 token: fixture-token', False),
    ('资料中的 <script>alert(1)</script>', False),
    ('资料中的 ../../private/source', False),
])
def test_maintainer_preview_uses_source_hygiene(monkeypatch,tmp_path,excerpt,allowed):
    import requests
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace())
    monkeypatch.setitem(sys.modules,'pymysql',ModuleType('pymysql'))
    cipher=ModuleType('cryptography.fernet')
    cipher.Fernet=object
    monkeypatch.setitem(sys.modules,'cryptography.fernet',cipher)
    from hb_knowledge_app.hb_knowledge import maintenance,reference_admin

    source=tmp_path/'auth.json'
    source.write_text(json.dumps({'base_url':'http://localhost:19380','token':'fixture'}))
    item={'canonical_document_id':'DOC','version_id':'VER','title':'合成资料','sha256':'a'*64,
          'status':'parsed/indexed','chunk_count':1,'dataset_id':'b'*32,'ragflow_document_id':'c'*32}
    monkeypatch.setattr(maintenance,'require',lambda:None)
    monkeypatch.setattr(maintenance,'_row',lambda batch:({}, {}, {'items':[item]}))
    monkeypatch.setattr(maintenance,'configuration',lambda:{'publication_ragflow_auth_file':str(source)})
    monkeypatch.setattr(reference_admin,'_verify_backend',lambda cfg,selected:None)

    class Session:
        def __enter__(self):
            self.headers={}
            return self

        def __exit__(self,*_):
            return None

        def get(self,*args,**kwargs):
            return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'code':0,'data':{'chunks':[{'content':excerpt}]}})

    monkeypatch.setattr(requests,'Session',Session)
    if allowed:
        assert maintenance.preview('IMP_FIXTURE','DOC')['fragments'][0]['text']==excerpt
    else:
        with pytest.raises(KnowledgeError):
            maintenance.preview('IMP_FIXTURE','DOC')
