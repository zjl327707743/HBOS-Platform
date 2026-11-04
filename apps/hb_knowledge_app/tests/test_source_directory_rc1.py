import pytest
from hb_knowledge_app.hb_knowledge.source_directory import select,folder_id
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

def test_original_paths_and_aliases_have_one_document_count():
    docs=[{'document_id':'A','source_directories':[['安全部门','标准'],['法规文档','标准']]},
          {'document_id':'B','source_directories':[['安全部门','标准']]}]
    chosen,tree=select(docs)
    assert len(chosen)==2
    assert {v['name']:v['count'] for v in tree['children']}=={'安全部门':2,'法规文档':1}
    chosen,tree=select(docs,folder_id(['安全部门','标准']))
    assert [d['document_id'] for d in chosen]==['A','B']
    assert [c['name'] for c in tree['breadcrumbs']]==['安全部门','标准']

def test_unauthorized_or_withdrawn_folder_name_and_count_never_return():
    allowed=[{'document_id':'A','source_directories':[['安全部门']]}]
    with pytest.raises(KnowledgeError) as exc:select(allowed,folder_id(['人事部门','隐私']))
    assert exc.value.code=='SCOPE_REJECTED'
    assert '人事部门' not in str(select(allowed))
