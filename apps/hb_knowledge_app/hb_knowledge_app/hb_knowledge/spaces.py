"""Authorized titles/counts; this use case performs no upstream/model request."""
from .errors import KnowledgeError
from .execution_plan import validate_admission
from .r1_contract import validate_structure


def authorized_spaces(snapshot,*,actions=('knowledge.spaces',)):
    allowed=set(snapshot.active_spaces)-set(snapshot.denied_spaces)
    for action in actions:
        allowed &= {g.space_id for g in snapshot.grants
                    if g.action==action and g.role_ref in snapshot.actor_state.roles}
    return allowed


def list_spaces(runtime, actor):
    def project(snapshot):
        from .public_strings import safe_string
        allowed = authorized_spaces(snapshot)
        if len(allowed) > 100:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        titles = dict(snapshot.space_titles)
        records = []
        physical = tuple(identity for b in snapshot.bindings for identity in (b.dataset_id, b.document_id))
        for space in sorted(allowed):
            documents = set()
            for binding in snapshot.bindings:
                if binding.space_id != space or binding.dataset_id not in snapshot.allowed_datasets:
                    continue
                try:
                    validate_admission(binding, runtime.profile, runtime.provider.clock())
                except KnowledgeError:
                    continue
                documents.add((binding.canonical_document_id, binding.version_id))
            records.append({'space_id': safe_string(space, 120, physical_ids=physical),
                            'title': safe_string(titles.get(space, '知识空间'), 120, physical_ids=physical),
                            'document_count': len(documents)})
        value = {'spaces': records}
        validate_structure('SpacesData', value)
        return value

    output = project(runtime.provider._current(actor, runtime.client))
    runtime.checkpoint('before_spaces_return')
    if output != project(runtime.provider._current(actor, runtime.client)):
        raise KnowledgeError('SCOPE_REJECTED')
    return output


def authorized_title_records(runtime, actor):
    """Display-only space titles for the authorized spaces.

    The ask path only needs the title map for space-scoped evidence labels; the
    full list_spaces projection also validates every binding, which is not part
    of this display step. Scope is enforced by the decision ticket and the
    evidence authorization phases, so this avoids a redundant 1103-binding loop.
    """
    snapshot = runtime.provider._current(actor, runtime.client)
    allowed = authorized_spaces(snapshot)
    if len(allowed) > 100:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    titles = dict(snapshot.space_titles)
    return [{'space_id': space, 'title': titles.get(space, '知识空间')} for space in sorted(allowed)]
