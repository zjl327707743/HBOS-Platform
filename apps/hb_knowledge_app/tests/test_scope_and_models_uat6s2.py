"""Gate A3: space titles and personal model defaults must follow the grant set.

Two defects share one cause: a value was built from *all* spaces or from the
hard-coded default model instead of from what this request may actually use.

- ``space_titles`` was always sent, and the SearchRequest contract rejects an
  empty map or more than 20 entries. A user with no space grants therefore got
  ``INVALID_REQUEST`` for every question instead of ``EMPTY_SCOPE``, and a user
  with 21+ spaces could not ask at all.
- ``_personal_models`` fell back to ``DEFAULT_MODEL`` without checking that it
  was available, so an unverified default made every ask fail with
  ``MODEL_UNAVAILABLE`` while a verified alias existed.
"""
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.answer_policy import ALIASES, DEFAULT_MODEL
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def _install_frappe(monkeypatch, *, user_default=None):
    """The import surface ``api`` needs; no Frappe behaviour is under test."""
    frappe = ModuleType('frappe')
    frappe.defaults = SimpleNamespace(
        get_user_default=lambda key, user=None: user_default,
        set_user_default=lambda key, value, user=None: None)
    frappe.local = SimpleNamespace()
    frappe.session = SimpleNamespace(user='reader@example.test')
    frappe.db = SimpleNamespace()
    frappe.get_roles = lambda user: []
    frappe.whitelist = lambda **kwargs: (lambda fn: fn)
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe


def _api(monkeypatch, *, models, user_default=None, raises=None):
    frappe = _install_frappe(monkeypatch, user_default=user_default)

    from hb_knowledge_app.hb_knowledge import api
    # The module-level ``import frappe`` was bound when another test file first
    # imported api; point it at this test's stub so the result is order-free.
    monkeypatch.setattr(api, 'frappe', frappe, raising=False)

    class Gateway:
        def models(self):
            if raises:
                raise KnowledgeError(raises)
            return {'default': DEFAULT_MODEL, 'models': models}

    runtime = SimpleNamespace(gateway=Gateway(), client=SimpleNamespace(client_id='PORTAL'),
                              provider=SimpleNamespace(_current=lambda actor, client: None))
    actor = SimpleNamespace(user_ref='reader@example.test')
    return api, runtime, actor


def _catalog(available):
    return [{'alias': alias, 'available': alias in available,
             'reason': None if alias in available else 'CONFIGURATION_NOT_VERIFIED'}
            for alias in ALIASES]


def test_only_an_unverified_default_falls_back_to_a_verified_alias(monkeypatch):
    api, runtime, actor = _api(monkeypatch, models=_catalog({'deepseek-flash'}))
    selected = api._personal_models(runtime, actor)['selected_alias']
    assert selected == 'deepseek-flash'


def test_a_stored_verified_preference_is_kept(monkeypatch):
    api, runtime, actor = _api(monkeypatch, models=_catalog({'gpt-6-luna', 'deepseek-flash'}),
                               user_default='deepseek-flash')
    assert api._personal_models(runtime, actor)['selected_alias'] == 'deepseek-flash'


def test_a_stored_but_unverified_preference_does_not_select_it(monkeypatch):
    api, runtime, actor = _api(monkeypatch, models=_catalog({'gpt-6-luna'}),
                               user_default='deepseek-flash')
    selected = api._personal_models(runtime, actor)['selected_alias']
    assert selected in {'gpt-6-luna'}
    assert selected != 'deepseek-flash'


def test_no_verified_model_reports_unavailable_instead_of_the_default(monkeypatch):
    api, runtime, actor = _api(monkeypatch, models=_catalog(set()))
    with pytest.raises(KnowledgeError) as caught:
        api._personal_models(runtime, actor)
    assert caught.value.code == 'MODEL_UNAVAILABLE'


def test_a_stored_preference_is_never_rewritten_by_reading_the_catalog(monkeypatch):
    written = []
    api, runtime, actor = _api(monkeypatch, models=_catalog({'deepseek-flash'}),
                               user_default='kimi-k3')
    api.frappe.defaults.set_user_default = lambda key, value, user=None: written.append(value)
    api._personal_models(runtime, actor)
    assert written == []


# --- space_titles --------------------------------------------------------

def _titles_for(spaces, requested=None, monkeypatch=None):
    """The map api.ask should send for a grant set (and optional space_ids)."""
    if monkeypatch is not None:
        _install_frappe(monkeypatch)
    from hb_knowledge_app.hb_knowledge.api import _space_titles
    return _space_titles(spaces, requested)


def test_no_granted_space_produces_no_title_map(monkeypatch):
    assert _titles_for([], monkeypatch=monkeypatch) is None


def test_more_than_twenty_spaces_stays_inside_the_contract(monkeypatch):
    spaces = [{'space_id': f'SPACE_{i:03d}', 'title': f'空间 {i}'} for i in range(37)]
    titles = _titles_for(spaces, monkeypatch=monkeypatch)
    assert titles is not None and 1 <= len(titles) <= 20


def test_a_requested_subset_is_what_gets_sent(monkeypatch):
    spaces = [{'space_id': f'SPACE_{i:03d}', 'title': f'空间 {i}'} for i in range(37)]
    titles = _titles_for(spaces, ['SPACE_004', 'SPACE_030'], monkeypatch=monkeypatch)
    assert titles == {'SPACE_004': '空间 4', 'SPACE_030': '空间 30'}


def test_a_narrow_request_cannot_ask_for_an_unauthorized_space(monkeypatch):
    spaces = [{'space_id': 'SPACE_A', 'title': '甲'}]
    titles = _titles_for(spaces, ['SPACE_A', 'SPACE_Z'], monkeypatch=monkeypatch)
    assert titles == {'SPACE_A': '甲'}


def test_twenty_spaces_are_sent_whole(monkeypatch):
    spaces = [{'space_id': f'SPACE_{i:03d}', 'title': f'空间 {i}'} for i in range(20)]
    assert len(_titles_for(spaces, monkeypatch=monkeypatch)) == 20
