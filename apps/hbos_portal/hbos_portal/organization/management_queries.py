"""Default-closed, current-policy projections for managed fact queries.

No RPC, writes, commits, phone reads or business authorization. The request
boundary owns rollback and only releases a result after its exact proof recheck.
"""
from dataclasses import dataclass
from datetime import timezone
import json
from types import MappingProxyType

from hbos_portal.authorization.errors import ContractError
from .frappe_management_repository import validate_policy_sources
from .managed_relations import ManagedRelationAdapter, _assignment, _json_facts, _position
from .management_policy import evaluate_management_policy, parse_management_context
from .management_storage import POLICY_PROVIDER, PinnedPolicyApprovalVerifier, policy_data, stored_time
from .relation_service import _snapshot_digest
from .source_adapter import _department_chain, resolve_person
from .storage_schema import ASSIGNMENT, POSITION, canonical_json, digest, validate_storage_record


QUERY_OPERATIONS = MappingProxyType({
    'list_positions': 'hbos.organization.position.read',
    'get_person_assignments': 'hbos.organization.assignment.read',
    'lookup_people': 'hbos.organization.person.lookup',
})
QUERIES = frozenset(('get_management_context', *QUERY_OPERATIONS))
_FLAGS = dict(read_only=True, runtime_verified=False, authorization_effect='none',
              position_authorization_connected=False)


def _fail(code, path='query'):
    raise ContractError(code, path)


def _text(value, maximum=140, *, required=False):
    if (not isinstance(value, str) or len(value) > maximum
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        _fail('INVALID_REQUEST')
    value = value.strip()
    if required and not value:
        _fail('INVALID_REQUEST')
    return value


def _params(query, params):
    if type(query) is not str or query not in QUERIES or type(params) is not dict:
        _fail('INVALID_REQUEST')
    keys = ({'page', 'page_size', 'employee_id'} if query == 'get_person_assignments'
            else {'page', 'page_size', 'company_id', 'department_id', 'q'}
            if query != 'get_management_context' else set())
    if set(params) - keys:
        _fail('INVALID_REQUEST')
    if query == 'get_management_context':
        return {}
    page, size = params.get('page', 1), params.get('page_size', 10)
    if type(page) is not int or not 1 <= page <= 10000 or type(size) is not int or not 1 <= size <= 50:
        _fail('INVALID_REQUEST')
    result = dict(page=page, page_size=size)
    if query == 'get_person_assignments':
        result['employee_id'] = _text(params.get('employee_id'), required=True)
    else:
        result.update(company_id=_text(params.get('company_id', '')),
                      department_id=_text(params.get('department_id', '')),
                      q=_text(params.get('q', ''), 80))
    return result


@dataclass(frozen=True, slots=True)
class PendingManagementQueryProof:
    """Immutable request-local evidence; never a client permission token."""
    site_id: str
    database_sha256: str
    source_provider_id: str
    actor: str
    query: str
    params_json: str
    result_json: str
    source_digest: str
    policy_digest: str
    fingerprint: str
    evaluated_at_utc: str


@dataclass(frozen=True, slots=True)
class _Evaluation:
    result_json: str
    source_digest: str
    policy_digest: str
    fingerprint: str
    source_provider_id: str
    actor: str
    evaluated_at_utc: str
    database: object
    session: object
    sid: object
    generation: object


class ManagementQueryService:
    def __init__(self, repository, policy_repository, *, source_loader, clock,
                 approval_verifier=None, enabled=False):
        self.repository = repository
        self.policy_repository = policy_repository
        self.source_loader = source_loader
        self.clock = clock
        self.approval_verifier = approval_verifier
        self.enabled = enabled is True
        self._pending_proof = None
        self._pending_database = None
        self._pending_session = None
        self._pending_sid = None
        self._pending_generation = None

    @property
    def pending_proof(self):
        return self._pending_proof

    def discard_pending(self):
        self._pending_proof = None
        self._pending_database = None
        self._pending_session = None
        self._pending_sid = None
        self._pending_generation = None

    def _now(self):
        now = self.clock()
        stored_time(now)
        return now.astimezone(timezone.utc)

    def execute(self, query, params):
        if not self.enabled:
            _fail('QUERY_READS_DISABLED')
        if self._pending_proof is not None:
            _fail('PENDING_PROOF_EXISTS')
        params = _params(query, params)
        evaluated = self._evaluate(query, params)
        self._pending_proof = PendingManagementQueryProof(
            self.repository.site_id, self.policy_repository.expected_database_sha256,
            evaluated.source_provider_id, evaluated.actor, query, canonical_json(params),
            evaluated.result_json, evaluated.source_digest, evaluated.policy_digest,
            evaluated.fingerprint, evaluated.evaluated_at_utc)
        self._pending_database = evaluated.database
        self._pending_session = evaluated.session
        self._pending_sid = evaluated.sid
        self._pending_generation = evaluated.generation
        return json.loads(evaluated.result_json)

    def recheck_pending(self, proof):
        if type(proof) is not PendingManagementQueryProof or proof is not self._pending_proof:
            _fail('PENDING_PROOF_MISMATCH')
        binding = (self._pending_database, self._pending_session, self._pending_sid,
                   self._pending_generation, proof.actor)
        self.discard_pending()
        if (not self.enabled or proof.site_id != self.repository.site_id
                or proof.database_sha256 != self.policy_repository.expected_database_sha256):
            _fail('PENDING_PROOF_MISMATCH')
        params = _params(proof.query, json.loads(proof.params_json))
        if canonical_json(params) != proof.params_json:
            _fail('PENDING_PROOF_MISMATCH')
        evaluated = self._evaluate(proof.query, params, binding=binding, expected_proof=proof)
        if (evaluated.source_provider_id != proof.source_provider_id
                or evaluated.source_digest != proof.source_digest):
            _fail('SOURCE_CHANGED_RETRY')
        if evaluated.policy_digest != proof.policy_digest:
            _fail('MANAGEMENT_CHANGED_RETRY')
        if evaluated.fingerprint != proof.fingerprint or evaluated.result_json != proof.result_json:
            _fail('SOURCE_CHANGED_RETRY')
        return json.loads(evaluated.result_json)

    @staticmethod
    def _binding(native, repository):
        session = ManagedRelationAdapter._session(native)
        return (ManagedRelationAdapter._database(native, repository), session,
                getattr(session, 'sid', None), ManagedRelationAdapter._generation(repository),
                getattr(session, 'user', None))

    def _heads(self, native, actor, snapshot, now, *, expected_digest=None):
        heads = self.policy_repository.current_for_subject(actor)
        if type(heads) not in (list, tuple):
            _fail('POLICY_STORAGE_MISMATCH')
        for policy in heads:
            policy_data(policy)
            if (policy.site_id != self.repository.site_id or policy.subject_user != actor
                    or policy.source_provider != POLICY_PROVIDER):
                _fail('MANAGEMENT_CONTEXT_MISMATCH')
        if len({policy.policy_id for policy in heads}) != len(heads):
            _fail('DUPLICATE_POLICY')
        if expected_digest is not None and self._policy_fingerprint(heads, now) != expected_digest:
            _fail('MANAGEMENT_CHANGED_RETRY')
        for policy in heads:
            if policy.status == 'active':
                self.approval_verifier.verify(policy,
                    database_sha256=self.policy_repository.expected_database_sha256, now_utc=now)
                validate_policy_sources(policy, snapshot)
        return tuple(heads)

    @staticmethod
    def _policy_fingerprint(heads, now):
        return digest(dict(heads=[policy_data(policy) for policy in sorted(heads, key=lambda item: item.policy_id)],
            current=[policy.policy_id for policy in sorted(heads, key=lambda item: item.policy_id)
                     if policy.status == 'active' and policy.valid_from_utc <= now < policy.valid_until_utc]))

    @staticmethod
    def _organization(snapshot, company, department, designation=None):
        if company not in snapshot.rows['Company'] or not department:
            return False
        try:
            chain = _department_chain(snapshot, department, company)
        except ContractError:
            return False
        return (chain[0]['company'] == company
                and (designation is None or designation in snapshot.rows['Designation']))

    def _person(self, snapshot, key):
        try:
            person = resolve_person(snapshot, 'Employee', key)
        except ContractError:
            return None
        if (person.link_status not in ('linked', 'unlinked') or person.company_ref is None
                or person.department_ref is None or person.reason_codes and set(person.reason_codes) - {
                    'ACCOUNT_UNLINKED', 'ACCOUNT_DISABLED', 'EMPLOYEE_NOT_ACTIVE',
                    'EMPLOYEE_DATE_POLICY_UNRESOLVED', 'EMPLOYEE_DATES_INCONSISTENT'}):
            return None
        company, department = person.company_ref.source_id, person.department_ref.source_id
        designation = person.designation_ref.source_id if person.designation_ref else None
        if not self._organization(snapshot, company, department, designation):
            return None
        return dict(source_type='Employee', source_id=key, company_id=company, department_id=department,
                    link_status=person.link_status, subject_user=person.subject_user,
                    employee_status=person.employee_status,
                    user_enabled=person.user_enabled if person.link_status == 'linked' else None)

    def _matches(self, heads, snapshot, actor, now, operation, *, position=None, assignment=None, person=None):
        try:
            context = parse_management_context(dict(operation_id=operation, operation_schema_version=1,
                now_utc=now.isoformat(), expected_revision=assignment['revision'] if assignment is not None
                    else position['revision'] if position is not None else 0,
                organization_status='active', position_before=_json_facts(_position(position)),
                position_after=None, assignment_before=_json_facts(_assignment(assignment)),
                assignment_after=None, person=person), site_id=self.repository.site_id,
                policy_provider_id=POLICY_PROVIDER, actor_user=actor,
                actor_enabled=bool(snapshot.rows['User'][actor]['enabled']))
        except (ContractError, KeyError, TypeError, ValueError):
            return False
        return evaluate_management_policy(heads, context, enabled=True).matched

    def _current(self, kind, row):
        validate_storage_record(kind, row['record_key'], row.get)
        adapter = ManagedRelationAdapter(self.policy_repository, approval_verifier=self.approval_verifier, enabled=True)
        return adapter._current(self, kind, row['record_key'])

    @staticmethod
    def _context_result(heads, now):
        scopes = {}
        operations = set()
        for policy in heads:
            if policy.status != 'active' or not policy.valid_from_utc <= now < policy.valid_until_utc:
                continue
            for rule in policy.rules:
                for operation in sorted(set(rule.operation_ids) & set(QUERY_OPERATIONS.values())):
                    operations.add(operation)
                    person = rule.person_scope
                    scope = dict(operation_id=operation, operation_schema_version=1,
                        company_id=rule.company_id, target_department_ids=list(rule.target_department_ids),
                        include_children=False, person_scope=None if person is None else dict(
                            source_type=person.source_type, company_id=person.company_id,
                            department_ids=list(person.department_ids)))
                    scopes[canonical_json(scope)] = scope
        return dict(operation_ids=sorted(operations), scopes=[scopes[key] for key in sorted(scopes)], **_FLAGS)

    def _rows(self, query, params, heads, snapshot, actor, now):
        items, facts, labels = [], [], {}
        operation = QUERY_OPERATIONS[query]
        if query == 'list_positions':
            for row in self.repository.list_positions():
                if (not self._organization(snapshot, row.get('company'), row.get('department'), row.get('designation'))
                        or not self._matches(heads, snapshot, actor, now, operation, position=row)):
                    continue
                current = self._current(POSITION, row)
                if any(row.get(key) != value for key, value in current.items()):
                    _fail('SOURCE_CHANGED_RETRY')
                facts.append(current)
                items.append(dict(record_id=current['record_key'], title=current['title'],
                    company_id=current['company'], department_id=current['department'],
                    designation_id=current['designation'], status=current['status'], revision=current['revision']))
        elif query == 'get_person_assignments':
            person = self._person(snapshot, params['employee_id'])
            for row in self.repository.list_assignments():
                if (person is None or row.get('person_source_type') != 'Employee'
                        or row.get('person_source_id') != params['employee_id']
                        or row.get('subject_user') != person['subject_user']):
                    continue
                position = self.repository.get_master(POSITION, row['position'])
                if (position is None or not self._organization(snapshot, position.get('company'),
                        position.get('department'), position.get('designation'))
                        or not self._matches(heads, snapshot, actor, now, operation,
                            position=position, assignment=row, person=person)):
                    continue
                current = self._current(ASSIGNMENT, row)
                current_position = self._current(POSITION, position)
                if any(row.get(key) != value for key, value in current.items()):
                    _fail('SOURCE_CHANGED_RETRY')
                if any(position.get(key) != value for key, value in current_position.items()):
                    _fail('SOURCE_CHANGED_RETRY')
                facts.append(dict(assignment=current, position=current_position))
                value = _json_facts(_assignment(current))
                items.append({key: value[key] for key in ('record_id', 'position_id', 'person_source_id',
                    'status', 'is_primary', 'valid_from_utc', 'valid_until_utc', 'revision')})
        else:
            for key in sorted(snapshot.rows['Employee']):
                person = self._person(snapshot, key)
                if person is None or not self._matches(heads, snapshot, actor, now, operation, person=person):
                    continue
                label = self.repository.get_person_label(key)
                if label is None:
                    _fail('SOURCE_CHANGED_RETRY')
                try:
                    label = _text(label) or key
                except ContractError:
                    _fail('SOURCE_LABEL_UNAVAILABLE')
                labels[key] = label
                employee = snapshot.rows['Employee'][key]
                items.append(dict(source_id=key, display_name=label, company_id=person['company_id'],
                    department_id=person['department_id'], designation_id=employee['designation'],
                    link_status=person['link_status'], employee_status=person['employee_status']))
        # Authorization is complete before client filters, totals and pagination.
        if query != 'get_person_assignments':
            items = [item for item in items
                if (not params['company_id'] or item['company_id'] == params['company_id'])
                and (not params['department_id'] or item['department_id'] == params['department_id'])
                and (not params['q'] or any(params['q'].casefold() in item[key].casefold()
                    for key in (('record_id', 'title') if query == 'list_positions' else ('source_id', 'display_name'))))]
        items.sort(key=lambda item: item.get('record_id', item.get('source_id')))
        total = len(items)
        start = (params['page'] - 1) * params['page_size']
        return dict(items=items[start:start + params['page_size']], total=total,
                    page=params['page'], page_size=params['page_size'], **_FLAGS), facts, labels

    def _evaluate(self, query, params, *, binding=None, expected_proof=None):
        if (not self.enabled or self.policy_repository.relations is not self.repository
                or not callable(self.source_loader) or not callable(self.clock)):
            _fail('QUERY_READS_DISABLED')
        if type(self.approval_verifier) is not PinnedPolicyApprovalVerifier:
            _fail('POLICY_APPROVAL_REQUIRED')
        with self.repository.transaction():
            self.repository.lock_writer()
            native = self.policy_repository.native()
            actual = self._binding(native, self.repository)
            if binding is not None and (actual[0] is not binding[0] or actual[1] is not binding[1]
                    or actual[2:] != binding[2:]):
                _fail('PENDING_PROOF_MISMATCH')
            actor = actual[4]
            if not actor or actor == 'Guest':
                _fail('MANAGEMENT_DENIED')
            now = self._now()
            snapshot = self.source_loader()
            if snapshot.context.site_id != self.repository.site_id or not snapshot.employee_links_complete:
                _fail('SOURCE_CONTEXT_MISMATCH')
            if (expected_proof is not None and (snapshot.context.provider_id != expected_proof.source_provider_id
                    or _snapshot_digest(snapshot) != expected_proof.source_digest)):
                _fail('SOURCE_CHANGED_RETRY')
            if not snapshot.rows['User'].get(actor, {}).get('enabled', False):
                _fail('MANAGEMENT_DENIED')
            heads = self._heads(native, actor, snapshot, now,
                expected_digest=expected_proof.policy_digest if expected_proof is not None else None)
            policy_fingerprint = self._policy_fingerprint(heads, now)
            context_result = self._context_result(heads, now)
            available = context_result['operation_ids']
            if (not available or query != 'get_management_context' and QUERY_OPERATIONS[query] not in available):
                _fail('MANAGEMENT_DENIED')
            if query == 'get_management_context':
                result, facts, labels = context_result, [], {}
            else:
                result, facts, labels = self._rows(query, params, heads, snapshot, actor, now)
            fresh = self.source_loader()
            if _snapshot_digest(fresh) != _snapshot_digest(snapshot):
                _fail('SOURCE_CHANGED_RETRY')
            final_now = self._now()
            final_heads = self._heads(native, actor, fresh, final_now)
            if self._policy_fingerprint(final_heads, final_now) != policy_fingerprint:
                _fail('MANAGEMENT_CHANGED_RETRY')
            final_binding = self._binding(native, self.repository)
            if (final_binding[0] is not actual[0] or final_binding[1] is not actual[1]
                    or final_binding[2:] != actual[2:]):
                _fail('PENDING_PROOF_MISMATCH')
            result_json = canonical_json(result)
            source_digest = _snapshot_digest(fresh)
            fingerprint = digest(dict(query=query, params=params, source=source_digest,
                policies=policy_fingerprint, facts=facts, labels=labels, result=result))
            return _Evaluation(result_json, source_digest, policy_fingerprint, fingerprint,
                fresh.context.provider_id, actor, final_now.isoformat(), *actual[:4])
