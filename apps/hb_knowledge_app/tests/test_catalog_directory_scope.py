"""The original directory and the list must use one filter context.

Owner hit a folder badge reading 208 while the page under it said "0 份"; the
cause was two different denominators. These tests pin the contract:

- entering an original directory never empties the list merely because another
  filter (department, law category, keyword) was left selected;
- the child counts offered beside the list count exactly the documents the list
  would show, so a badge can never promise rows the page does not have;
- a child with nothing visible is omitted, because the portal client rejects a
  zero count as a malformed response;
- authorization still decides whether a folder exists at all, so a guessed or
  fully withdrawn folder stays refused rather than becoming an empty folder.
"""
import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.source_directory import select, folder_id


def test_filtered_selection_counts_children_from_the_same_rows():
    docs = [
        {'document_id': 'A', 'space_id': 'DEPT_PRODUCTION', 'source_directories': [['无菌车间', 'SOP']]},
        {'document_id': 'B', 'space_id': 'DEPT_PRODUCTION', 'source_directories': [['无菌车间', 'TSD']]},
        {'document_id': 'C', 'space_id': 'DEPT_SAFETY', 'source_directories': [['安全部门', '标准']]},
    ]
    # Unfiltered: the folder resolves and every authorized row is offered.
    chosen, tree = select(docs, folder_id(['无菌车间']))
    assert [d['document_id'] for d in chosen] == ['A', 'B']
    assert {c['name']: c['count'] for c in tree['children']} == {'SOP': 1, 'TSD': 1}

    # Same folder under a department filter that matches one row: the counts
    # follow the rows, not the whole authorized set.
    production = [d for d in docs if d['space_id'] == 'DEPT_PRODUCTION']
    safety = [d for d in docs if d['space_id'] == 'DEPT_SAFETY']
    chosen, tree = select(docs, folder_id(['无菌车间']), filtered_documents=production)
    assert [d['document_id'] for d in chosen] == ['A', 'B']
    assert {c['name']: c['count'] for c in tree['children']} == {'SOP': 1, 'TSD': 1}

    chosen, tree = select(docs, folder_id(['无菌车间']), filtered_documents=safety)
    assert chosen == [] and tree['children'] == []


def test_folder_resolution_uses_authorization_not_the_filters():
    docs = [{'document_id': 'A', 'space_id': 'DEPT_PRODUCTION', 'source_directories': [['无菌车间', 'SOP']]}]
    # Nothing matches the filter, but the folder is authorized: it resolves to
    # an empty listing rather than a scope rejection.
    chosen, tree = select(docs, folder_id(['无菌车间']), filtered_documents=[])
    assert chosen == [] and [c['name'] for c in tree['breadcrumbs']] == ['无菌车间']

    # A folder no authorized document reaches still cannot be guessed.
    with pytest.raises(KnowledgeError) as exc:
        select(docs, folder_id(['人事部门']), filtered_documents=[])
    assert exc.value.code == 'SCOPE_REJECTED'


def test_aliased_document_counts_once_per_child():
    docs = [
        {'document_id': 'A', 'source_directories': [['法规文档', '注册部法规'], ['法规文档', '注册部法规']]},
        {'document_id': 'A', 'source_directories': [['法规文档', '注册部法规']]},
    ]
    chosen, tree = select(docs, folder_id(['法规文档']), filtered_documents=docs)
    assert [c['count'] for c in tree['children']] == [1]


def _catalog(tmp_path, monkeypatch):
    """A catalog runtime whose two spaces both hold documents in one folder."""
    from dataclasses import replace
    from hb_knowledge_app.hb_knowledge import source_directory
    from hb_knowledge_app.hb_knowledge.execution_plan import GrantPair
    from .test_catalog_page import catalog_runtime

    app, actor, repo, base = catalog_runtime()
    map_file = tmp_path / 'source-directory.json'
    entries = {
        'VER_PROD_SOP': ('DOC_PROD_SOP', [['无菌车间', 'SOP']]),
        'VER_PROD_TSD': ('DOC_PROD_TSD', [['无菌车间', 'TSD']]),
        'VER_QA_SOP': ('DOC_QA_SOP', [['无菌车间', 'SOP']]),
        'VER_LAW': ('DOC_LAW', [['法规文档', '注册部法规']]),
    }
    map_file.write_text(__import__('json').dumps({'schema_version': 1, 'by_version': {
        version: {'canonical_document_id': doc, 'directories': paths}
        for version, (doc, paths) in entries.items()}}, ensure_ascii=False))
    monkeypatch.setattr(source_directory, 'MAP', map_file)

    def bound(version, doc, space):
        return replace(base, version_id=version, canonical_document_id=doc, space_id=space, title=doc)
    repo.snapshot = replace(
        repo.snapshot,
        grants=repo.snapshot.grants + tuple(
            GrantPair('ROLE_QA', 'SPACE_PROD', action, 'GRANT_PROD_' + action)
            for action in ('knowledge.spaces', 'knowledge.search')),
        bindings=(bound('VER_PROD_SOP', 'DOC_PROD_SOP', 'SPACE_PROD'),
                  bound('VER_PROD_TSD', 'DOC_PROD_TSD', 'SPACE_PROD'),
                  bound('VER_QA_SOP', 'DOC_QA_SOP', 'SPACE_QA'),
                  bound('VER_LAW', 'DOC_LAW', 'SPACE_PROD')))
    return app, actor


def test_catalog_page_children_counts_match_the_listed_rows(tmp_path, monkeypatch):
    from hb_knowledge_app.hb_knowledge.reference_admin import get_catalog_page

    app, actor = _catalog(tmp_path, monkeypatch)
    folder = folder_id(['无菌车间'])

    whole = get_catalog_page(app, actor, folder_id=folder, page_size=50)
    assert whole['total'] == 3
    assert {c['name']: c['count'] for c in whole['source_directory']['children']} == {'SOP': 2, 'TSD': 1}

    production = get_catalog_page(app, actor, folder_id=folder, space_id='SPACE_PROD', page_size=50)
    assert production['total'] == 2
    assert {c['name']: c['count'] for c in production['source_directory']['children']} == {'SOP': 1, 'TSD': 1}

    # Under a filter with one visible SOP row, TSD has nothing to show and is
    # not offered at all: a zero count is what the portal client rejects.
    qa = get_catalog_page(app, actor, folder_id=folder, space_id='SPACE_QA', page_size=50)
    assert qa['total'] == 1
    assert [c['name'] for c in qa['source_directory']['children']] == ['SOP']
    assert qa['source_directory']['children'][0]['count'] == 1


def test_catalog_page_never_opens_a_folder_the_actor_cannot_reach(tmp_path, monkeypatch):
    from hb_knowledge_app.hb_knowledge.reference_admin import get_catalog_page

    app, actor = _catalog(tmp_path, monkeypatch)
    with pytest.raises(KnowledgeError) as exc:
        get_catalog_page(app, actor, folder_id=folder_id(['人事部门', '薪酬']))
    assert exc.value.code == 'SCOPE_REJECTED'


def test_root_badges_stay_a_map_of_the_authorized_directories(tmp_path, monkeypatch):
    """A department filter narrows the rows, not the way back to the whole map.

    Owner could not see 无菌车间 at all while 安全部门 was selected, because the
    root badges were filtered too. The root is the navigation map of what this
    identity may enter, so its badges count authorized documents, while `total`
    still answers the filter actually in force.
    """
    from hb_knowledge_app.hb_knowledge.reference_admin import get_catalog_page

    app, actor = _catalog(tmp_path, monkeypatch)
    filtered = get_catalog_page(app, actor, folder_id='SOURCE_ROOT', space_id='SPACE_QA', page_size=50)
    assert filtered['total'] == 1
    assert [d['document_id'] for d in filtered['documents']] == ['DOC_QA_SOP']
    assert {c['name']: c['count'] for c in filtered['source_directory']['children']} == {'无菌车间': 3, '法规文档': 1}

    # Without a folder the response carries no tree, as before.
    assert 'source_directory' not in get_catalog_page(app, actor, space_id='SPACE_QA')
