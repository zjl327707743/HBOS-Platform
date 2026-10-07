"""Authorized titles/counts; this use case performs no upstream/model request."""
from .errors import KnowledgeError
from .execution_plan import validate_admission
from .r1_contract import validate_structure


def list_spaces(runtime, actor):
    def project(snapshot):
        from .public_strings import safe_string
        allowed = {grant.space_id for grant in snapshot.grants
                   if grant.action == 'knowledge.spaces' and grant.role_ref in snapshot.actor_state.roles
                   and grant.space_id in snapshot.active_spaces and grant.space_id not in snapshot.denied_spaces}
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
