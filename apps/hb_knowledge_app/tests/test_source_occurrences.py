"""Directory positions add up, while identity/authorization stay document based."""
import json
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import source_directory as directory
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


@pytest.fixture
def positioned(tmp_path,monkeypatch):
    path=tmp_path/'directory.json'
    value={'schema_version':2,'by_version':{
        'V1':{'canonical_document_id':'D1','directories':[['安全部门'],['安全部门','子目录']],
            'occurrences':[{'occurrence_id':'OCC-'+str(i)*24,'relative_path':p,'content_sha256':'a'*64}
                for i,p in enumerate(['安全部门/a.pdf','安全部门/alias.pdf','安全部门/子目录/a.pdf'],1)]},
        'V2':{'canonical_document_id':'D2','directories':[['人事部门']],
            'occurrences':[{'occurrence_id':'OCC-'+'4'*24,'relative_path':'人事部门/private.pdf','content_sha256':'a'*64}]}}}
    path.write_text(json.dumps(value));monkeypatch.setattr(directory,'MAP',path)
    directory._read_map.cache_clear()
    yield value,path
    directory._read_map.cache_clear()


def doc():return {'document_id':'D1','version_id':'V1','title':'Example',
                  'source_directories':[['安全部门'],['安全部门','子目录']]}


def test_positions_count_and_pages_agree(positioned):
    rows,tree=directory.select([doc()],directory.folder_id(['安全部门']))
    assert len(rows)==3
    assert tree['direct_count']==2
    assert tree['children'][0]['count']==1
    assert tree['direct_count']+sum(c['count'] for c in tree['children'])==len(rows)
    assert len({r['source_occurrence_id'] for r in rows})==3
    assert {r['document_id'] for r in rows}=={'D1'}
    assert tree['count_kind']=='SOURCE_OCCURRENCES'


def test_filter_counts_and_unauthorized_hash_alias(positioned):
    rows,tree=directory.select([doc()],directory.ROOT,filtered_documents=[])
    assert rows==[] and tree['children']==[]
    with pytest.raises(KnowledgeError):directory.select([doc()],directory.folder_id(['人事部门']))
    # Identical content hash does not import the private document's path.
    assert all('private' not in str(r) for r in directory.select([doc()])[0])
    with pytest.raises(KnowledgeError):
        directory.select([doc()],directory.ROOT,filtered_documents=[{'document_id':'D2','version_id':'V2'}])


def test_projection_rejects_path_traversal_and_identity_mismatch(positioned):
    value,path=positioned
    value['by_version']['V1']['occurrences'][0]['relative_path']='安全部门/../outside.pdf'
    path.write_text(json.dumps(value));directory._read_map.cache_clear()
    with pytest.raises(KnowledgeError):directory.select([doc()])
    value['by_version']['V1']['occurrences'][0]['relative_path']='安全部门/a.pdf'
    value['by_version']['V1']['canonical_document_id']='another-document'
    path.write_text(json.dumps(value));directory._read_map.cache_clear()
    with pytest.raises(KnowledgeError):directory.select([doc()])
