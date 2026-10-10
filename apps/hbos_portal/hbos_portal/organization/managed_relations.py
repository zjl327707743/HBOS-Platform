"""Default-closed full-policy bridge for managed relationship facts.

Runs only inside the caller's existing relation transaction/root lock. No RPC,
commit, real operator configuration, business grant or qualification inference.
"""
from dataclasses import asdict, dataclass
import json

from hbos_portal.authorization.errors import ContractError
from .frappe_management_repository import validate_policy_sources
from .management_contracts import ManagementAssignmentFacts, ManagementMatch, ManagementPositionFacts
from .management_policy import (
    _strict_assignment_reduction, _strict_position_reduction,
    evaluate_management_policy, parse_management_context,
)
from .management_storage import POLICY_PROVIDER, PinnedPolicyApprovalVerifier
from .relation_service import RelationCommandResult, _snapshot_digest, _storage_time
from .source_adapter import decode_utc_datetime, resolve_person
from .storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, MASTER_FIELDS, POSITION, POSITION_REVISION, PROVIDER,
    VERSION_FIELDS, canonical_json, digest, receipt_key, require_uuid, revision_key,
)


def _fail(code, path='management'):
    raise ContractError(code, path)


def _position(row):
    if row is None:
        return None
    return ManagementPositionFacts(row['record_key'], row['company'], row['department'], row['title'],
        row['designation'], row['status'], row['revision'])


def _assignment(row):
    if row is None:
        return None
    return ManagementAssignmentFacts(row['record_key'], row['position'], row['person_source_id'], row['subject_user'],
        row['status'], row['is_primary'], decode_utc_datetime(row['valid_from_utc']),
        None if row['valid_until_utc'] is None else decode_utc_datetime(row['valid_until_utc']), row['revision'])


def _json_facts(value):
    if value is None:
        return None
    from .management_storage import _export
    return _export(asdict(value))


@dataclass(frozen=True, slots=True)
class PendingManagementProof:
    """One issued server-side command proof, never an HTTP permission token.

    JSON fields are canonical immutable strings. The adapter additionally binds
    the exact issued object to its service/database and consumes it on recheck.
    A caller must own the outer transaction and abort the whole request on any
    failure; this object cannot detect or authorize an unrelated raw DB rollback.
    """
    site_id: str
    database_sha256: str
    source_provider_id: str
    actor: str
    command_type: str
    kind: str
    request_record_id: str | None
    expected_revision: int
    reason: str
    request_key: str
    request_digest: str
    facts_json: str
    receipt_key: str
    result_json: str
    before_json: str
    after_json: str
    scope_json: str
    history_json: str
    current_master_json: str
    position_master_json: str
    source_digest: str
    policy_match: ManagementMatch
    context_digest: str
    evaluated_at_utc: str


class ManagedRelationAdapter:
    """Trusted server dependency, inactive by default. Not a request parser.

    Policy repository must use exactly the service's relation repository. The
    identity is the native session, not the separately injected actor claim.
    """
    def __init__(self, policy_repository, *, approval_verifier=None, enabled=False, pending_observer=None):
        if pending_observer is not None and not callable(pending_observer):
            _fail('INVALID_PENDING_OBSERVER')
        self.repository = policy_repository
        self.verifier = approval_verifier
        self.enabled = enabled is True
        self.pending_observer = pending_observer
        self._pending_proof = None
        self._pending_service = None
        self._pending_database = None
        self._pending_generation = None
        self._pending_session = None
        self._pending_sid = None

    @staticmethod
    def _generation(repository):
        generation = getattr(repository, '_source_generation', None)
        return None if generation is None else generation.get()

    @staticmethod
    def _database(native, repository):
        # Frappe's module-level db is a LocalProxy, whose identity does not bind
        # the actual request connection and becomes unbound after destroy().
        database = getattr(getattr(native, 'local', None), 'db', None)
        return database if database is not None else getattr(native, 'db', repository)

    @staticmethod
    def _session(native):
        # Bind the real request session, not Frappe's shared LocalProxy identity.
        session = getattr(getattr(native, 'local', None), 'session', None)
        return session if session is not None else getattr(native, 'session', None)

    def discard_pending(self):
        """The owning request boundary must call this when aborting/rolling back."""
        self._pending_proof = None
        self._pending_service = None
        self._pending_database = None
        self._pending_generation = None
        self._pending_session = None
        self._pending_sid = None

    def _issue_pending(self, service, *, actor, command_type, kind, facts, request_key,
                       request_digest, expected_revision, reason, record_id, result,
                       before, after, scope, history, snapshot, evaluation, current):
        current_now = self._current(service, kind, after['record_key'])
        if canonical_json(current_now) != canonical_json(current):
            _fail('SOURCE_CHANGED_RETRY')
        position_now = (current_now if kind == POSITION else
                        self._current(service, POSITION, after['position']))
        if kind == ASSIGNMENT and canonical_json(position_now) != canonical_json(scope):
            _fail('SOURCE_CHANGED_RETRY')
        key = receipt_key(service.repository.site_id, actor, command_type, request_key)
        receipt = service.repository.get_receipt(key)
        if (receipt is None or receipt['request_digest'] != request_digest
                or canonical_json(receipt['result']) != canonical_json(result)):
            _fail('HISTORY_MISMATCH')
        proof = PendingManagementProof(service.repository.site_id,
            self.repository.expected_database_sha256, snapshot.context.provider_id, actor, command_type, kind,
            record_id, expected_revision, reason, request_key, request_digest, canonical_json(facts), key,
            canonical_json(result), canonical_json(before), canonical_json(after), canonical_json(scope),
            canonical_json(history), canonical_json(current_now), canonical_json(position_now),
            _snapshot_digest(snapshot), evaluation.match, evaluation.context_digest,
            evaluation.evaluated_at_utc.isoformat())
        native = self.repository.native()
        self._pending_proof = proof
        self._pending_service = service
        self._pending_database = self._database(native, service.repository)
        self._pending_generation = self._generation(service.repository)
        self._pending_session = self._session(native)
        self._pending_sid = getattr(self._pending_session, 'sid', None)
        if self.pending_observer is not None:
            try:
                self.pending_observer(proof)
            except BaseException:
                self.discard_pending()
                raise

    def recheck_pending(self, service, proof):
        """Consume a proof inside the same DB transaction/root, without writes.

        A request executor may reopen the repository capability and root lock
        while the actual database transaction is still pending. Fresh policy,
        native sources, original revisions, current facts and receipt must all
        remain the same; only evaluation time is refreshed. Returns validation
        evidence, never a commit acknowledgement or business grant.
        """
        if (type(proof) is not PendingManagementProof or proof is not self._pending_proof
                or service is not self._pending_service):
            _fail('PENDING_PROOF_REQUIRED')
        database, generation = self._pending_database, self._pending_generation
        session, sid = self._pending_session, self._pending_sid
        self.discard_pending()  # Failed or successful final checks cannot be replayed.
        heads = self._heads(service, proof.actor)
        native = self.repository.native()
        if (self._database(native, service.repository) is not database
                or self._generation(service.repository) != generation
                or self._session(native) is not session
                or getattr(self._session(native), 'sid', None) != sid
                or service.repository.site_id != proof.site_id
                or self.repository.expected_database_sha256 != proof.database_sha256
                or service.actor_resolver() != proof.actor):
            _fail('MANAGEMENT_CONTEXT_MISMATCH')
        facts = json.loads(proof.facts_json)
        before, after = json.loads(proof.before_json), json.loads(proof.after_json)
        scope, history = json.loads(proof.scope_json), json.loads(proof.history_json)
        result = json.loads(proof.result_json)
        if (proof.request_digest != digest([proof.command_type, proof.request_record_id,
                proof.expected_revision, facts, proof.reason])
                or proof.receipt_key != receipt_key(proof.site_id, proof.actor, proof.command_type, proof.request_key)
                or result['record_id'] != after['record_key'] or result['revision'] != after['revision']
                or result['authorization_generation'] != after['authorization_generation']):
            _fail('HISTORY_MISMATCH')
        snapshot = service.source_loader()
        if (snapshot.context.site_id != proof.site_id or not snapshot.employee_links_complete
                or snapshot.context.provider_id != proof.source_provider_id
                or _snapshot_digest(snapshot) != proof.source_digest):
            _fail('SOURCE_CHANGED_RETRY')
        stored_after, _, _ = self._history(service.repository, proof.kind, after['record_key'], after['revision'])
        if canonical_json(stored_after) != proof.after_json:
            _fail('HISTORY_MISMATCH')
        if before is not None:
            stored_before, _, _ = self._history(service.repository, proof.kind, before['record_key'], before['revision'])
            if canonical_json(stored_before) != proof.before_json:
                _fail('HISTORY_MISMATCH')
        current = self._current(service, proof.kind, after['record_key'])
        if canonical_json(current) != proof.current_master_json:
            _fail('SOURCE_CHANGED_RETRY')
        position = current if proof.kind == POSITION else self._current(service, POSITION, after['position'])
        if canonical_json(position) != proof.position_master_json:
            _fail('SOURCE_CHANGED_RETRY')
        if proof.kind == ASSIGNMENT and canonical_json(position) != proof.scope_json:
            _fail('SOURCE_CHANGED_RETRY')
        if history is not None:
            checked_history = self._historical_scope(service, proof.kind, before,
                before if proof.kind == POSITION else position)
            if canonical_json(checked_history) != proof.history_json:
                _fail('HISTORY_MISMATCH')
        else:
            if proof.kind == ASSIGNMENT:
                person = resolve_person(snapshot, 'Employee', after['person_source_id'])
                if person.subject_user != after['subject_user']:
                    _fail('SOURCE_ASSOCIATION_CHANGED')
            service._evidence(proof.kind, dict(after), snapshot, scope, _storage_time(service.clock()))
        receipt = service.repository.get_receipt(proof.receipt_key)
        if (receipt is None or receipt['request_digest'] != proof.request_digest
                or canonical_json(receipt['result']) != proof.result_json):
            _fail('HISTORY_MISMATCH')
        context = self._context(service, proof.actor, proof.command_type, proof.kind,
            before, after, scope, snapshot, history)
        evaluation = self._authorize(heads, context, snapshot)
        if evaluation.match != proof.policy_match:
            _fail('MANAGEMENT_CHANGED_RETRY')
        return evaluation

    def _heads(self, service, actor):
        if not self.enabled:
            _fail('MANAGEMENT_ADAPTER_DISABLED')
        if self.repository.relations is not service.repository:
            _fail('MANAGEMENT_CONTEXT_MISMATCH')
        native = self.repository.native()
        if native.session.user != actor or actor == 'Guest':
            _fail('MANAGEMENT_DENIED', 'management.actor')
        return self.repository.current_for_subject(actor)

    @staticmethod
    def _history(repository, kind, record_id, revision):
        version = repository.get_revision(kind, record_id, revision)
        try:
            row = json.loads(version['snapshot_json'])
            evidence = json.loads(version['source_evidence_json'])
            if (not isinstance(row, dict) or not isinstance(evidence, dict)
                    or version['record_key'] != revision_key(kind, record_id, revision)
                    or version['revision'] != revision or type(version['revision']) is not int
                    or version['previous_revision'] != revision - 1
                    or version.get('position' if kind == POSITION else 'assignment') != record_id
                    or row.get('record_key') != record_id or row.get('revision') != revision
                    or type(row.get('revision')) is not int or version['content_digest'] != digest(row)):
                _fail('HISTORY_MISMATCH')
            anchor = row.pop('_management_evidence_digest', None)
            if anchor is not None and anchor != digest(evidence):
                _fail('HISTORY_MISMATCH')
            expected_fields = {'record_key', *MASTER_FIELDS[kind], *VERSION_FIELDS}
            if (set(row) != expected_fields or row['source_provider'] != PROVIDER
                    or row['source_key'] != record_id):
                _fail('HISTORY_MISMATCH')
            return row, evidence, anchor
        except (TypeError, KeyError, json.JSONDecodeError):
            _fail('HISTORY_MISMATCH')

    def _current(self, service, kind, key):
        row = service.repository.get_master(kind, key)
        if row is None:
            _fail('UNKNOWN_REFERENCE', 'record')
        snapshot, _, _ = self._history(service.repository, kind, key, row['revision'])
        actual = {field: row[field] for field in snapshot}
        if canonical_json(actual) != canonical_json(snapshot):
            _fail('HISTORY_MISMATCH')
        return snapshot

    def _historical_scope(self, service, kind, before, scope):
        row, evidence, anchor = self._history(service.repository, kind, before['record_key'], before['revision'])
        if row != before:
            _fail('HISTORY_MISMATCH')
        raw = evidence.get('management_scope_v1')
        if anchor is None or raw is None:
            _fail('HISTORICAL_SCOPE_REQUIRED')
        history_fields = {'site_id', 'source_provider', 'record_kind', 'record_id', 'revision', 'revision_ref',
            'company_id', 'department_id', 'person_source_id', 'person_company_id', 'person_department_id', 'subject_user'}
        if (not isinstance(raw, dict) or set(raw) != history_fields | {'schema_version', 'position_id', 'position_revision', 'position_generation'}
                or type(raw['schema_version']) is not int or raw['schema_version'] != 1
                or raw['site_id'] != service.repository.site_id or evidence.get('site_id') != service.repository.site_id
                or raw['source_provider'] != PROVIDER or raw['record_kind'] != kind
                or raw['record_id'] != before['record_key'] or raw['revision'] != before['revision']
                or raw['revision_ref'] != revision_key(kind, before['record_key'], before['revision'])
                or raw['company_id'] != scope['company'] or raw['department_id'] != scope['department']
                or type(raw['position_revision']) is not int or type(raw['position_generation']) is not int):
            _fail('HISTORY_MISMATCH')
        pos_id = before['position'] if kind == ASSIGNMENT else before['record_key']
        if raw['position_id'] != pos_id:
            _fail('HISTORY_MISMATCH')
        pos, _, _ = self._history(service.repository, POSITION, pos_id, raw['position_revision'])
        if (pos['company'] != raw['company_id'] or pos['department'] != raw['department_id']
                or pos['authorization_generation'] != raw['position_generation']):
            _fail('HISTORY_MISMATCH')
        if kind == ASSIGNMENT:
            if (raw['person_source_id'] != before['person_source_id'] or raw['subject_user'] != before['subject_user']
                    or raw['person_company_id'] != raw['company_id'] or not raw['person_department_id']):
                _fail('HISTORY_MISMATCH')
        elif any(raw[key] is not None for key in ('person_source_id', 'person_company_id', 'person_department_id', 'subject_user')):
            _fail('HISTORY_MISMATCH')
        return {key: raw[key] for key in history_fields}

    @staticmethod
    def _person(snapshot, candidate, history=None):
        employee_id = candidate['person_source_id']
        employee = snapshot.rows['Employee'].get(employee_id)
        if history is None:
            person = resolve_person(snapshot, 'Employee', employee_id)
            if person.company_ref is None or person.department_ref is None:
                _fail('PERSON_UNAVAILABLE')
            return dict(source_type='Employee', source_id=employee_id, company_id=person.company_ref.source_id,
                department_id=person.department_ref.source_id, link_status=person.link_status,
                subject_user=person.subject_user, employee_status=person.employee_status,
                user_enabled=person.user_enabled if person.link_status == 'linked' else None)
        # Current linking facts remain separate from the old immutable beneficiary.
        # Do not call the growth adapter or overwrite the old assignment subject.
        person = None if employee is None else resolve_person(snapshot, 'Employee', employee_id)
        linked = person is not None and person.link_status == 'linked'
        return dict(source_type='Employee', source_id=employee_id, company_id=history['person_company_id'],
            department_id=history['person_department_id'], link_status='linked' if linked else 'unknown',
            subject_user=person.subject_user if linked else None,
            employee_status=employee['status'] if employee is not None else 'Missing',
            user_enabled=person.user_enabled if linked else None)

    def _context(self, service, actor, command_type, kind, before, after, scope, snapshot, history):
        family = 'position' if kind == POSITION else 'assignment'
        verb = 'create' if command_type.startswith('create_') else 'update'
        now = service.clock()
        _storage_time(now)
        person = None if kind == POSITION else self._person(snapshot, after, history)
        return parse_management_context(dict(operation_id='hbos.organization.' + family + '.' + verb,
            operation_schema_version=1, now_utc=now.isoformat(), expected_revision=0 if before is None else before['revision'],
            organization_status='historical' if history is not None else 'active',
            position_before=_json_facts(_position(before if kind == POSITION else scope)),
            position_after=_json_facts(_position(after)) if kind == POSITION else None,
            assignment_before=_json_facts(_assignment(before)) if kind == ASSIGNMENT else None,
            assignment_after=_json_facts(_assignment(after)) if kind == ASSIGNMENT else None,
            person=person, historical_scope=history), site_id=service.repository.site_id,
            policy_provider_id=POLICY_PROVIDER, actor_user=actor,
            actor_enabled=bool(snapshot.rows['User'].get(actor, {}).get('enabled', False)))

    def _authorize(self, heads, context, snapshot):
        for policy in heads:
            if policy.status != 'active':
                continue
            if type(self.verifier) is not PinnedPolicyApprovalVerifier:
                _fail('POLICY_APPROVAL_REQUIRED')
            self.verifier.verify(policy, database_sha256=self.repository.expected_database_sha256, now_utc=context.now_utc)
            if context.historical_scope is None:
                validate_policy_sources(policy, snapshot)
            else:
                # Org existence/activity is replaced only by checked historical
                # scope for strict reductions, never for growth or ordinary reads.
                for user in (policy.subject_user, policy.approval.approved_by):
                    if user == 'Guest' or not snapshot.rows['User'].get(user, {}).get('enabled', False):
                        _fail('POLICY_SOURCE_UNAVAILABLE')
        evaluation = evaluate_management_policy(heads, context, enabled=True)
        if not evaluation.matched:
            _fail(evaluation.reason_codes[0])
        return evaluation

    def execute(self, service, *, actor, command_type, kind, facts, request_key, request_digest,
                expected_revision, reason, record_id):
        # RelationService already parsed the exact request shape and holds root.
        heads = self._heads(service, actor)
        snapshot = service.source_loader()
        if snapshot.context.site_id != service.repository.site_id or not snapshot.employee_links_complete:
            _fail('INCOMPLETE_SOURCE')
        key = receipt_key(service.repository.site_id, actor, command_type, request_key)
        receipt = service.repository.get_receipt(key)
        create = command_type.startswith('create_')
        replay = receipt is not None
        if replay:
            if receipt['request_digest'] != request_digest:
                _fail('IDEMPOTENCY_CONFLICT')
            result = receipt['result']
            probe_id = require_uuid(result['record_id'], 'receipt.record_id')
            current = self._current(service, kind, probe_id)
            after, _, _ = self._history(service.repository, kind, probe_id, result['revision'])
            before = None if create else self._history(service.repository, kind, probe_id, expected_revision)[0]
            if (after['revision'] != (1 if create else expected_revision + 1)
                    or after['authorization_generation'] != result['authorization_generation']
                    or any(after[field] != value for field, value in facts.items())):
                _fail('HISTORY_MISMATCH')
            immutable = ('company', 'department') if kind == POSITION else ('person_source_type', 'person_source_id', 'position', 'subject_user', 'valid_from_utc')
            if any(current[field] != after[field] for field in immutable):
                _fail('HISTORY_MISMATCH')
        else:
            before = None if create else self._current(service, kind, record_id)
            if before is not None and before['revision'] != expected_revision:
                _fail('REVISION_CONFLICT', 'expected_revision')
            probe_id = record_id or require_uuid(str(service.id_factory()), 'generated_id')
            after = dict(facts, record_key=probe_id, revision=1 if create else before['revision'] + 1,
                authorization_generation=1 if create else before['authorization_generation'], source_provider=PROVIDER, source_key=probe_id)
            if kind == ASSIGNMENT:
                after['subject_user'] = None if before is None else before['subject_user']
        if before is not None:
            immutable = ('company', 'department') if kind == POSITION else ('person_source_type', 'person_source_id', 'position', 'valid_from_utc')
            if any(before[field] != after[field] for field in immutable):
                _fail('NEW_RELATION_REQUIRED')
        scope = after if kind == POSITION else self._current(service, POSITION, after['position'])
        reduction = (not create and (_strict_position_reduction(_position(before), _position(after)) if kind == POSITION
            else _strict_assignment_reduction(_assignment(before), _assignment(after))))
        history = self._historical_scope(service, kind, before, before if kind == POSITION else scope) if reduction else None
        stamp = _storage_time(service.clock())
        evidence = None
        refs = {('User', actor)}
        if history is None:
            if kind == ASSIGNMENT:
                person = resolve_person(snapshot, 'Employee', after['person_source_id'])
                if not replay:
                    after['subject_user'] = person.subject_user
                if before is not None and before['subject_user'] != after['subject_user']:
                    _fail('SOURCE_ASSOCIATION_CHANGED')
            evidence, native_refs = service._evidence(kind, after, snapshot, scope, stamp)
            refs.update(native_refs)
        context = self._context(service, actor, command_type, kind, before, after, scope, snapshot, history)
        first = self._authorize(heads, context, snapshot)
        service.repository.lock_sources(tuple(sorted(refs)))
        current_heads = self._heads(service, actor)
        refreshed = service.source_loader()
        if _snapshot_digest(refreshed) != _snapshot_digest(snapshot):
            _fail('SOURCE_CHANGED_RETRY')
        context = self._context(service, actor, command_type, kind, before, after, scope, refreshed, history)
        second = self._authorize(current_heads, context, refreshed)
        if first.match != second.match:
            _fail('MANAGEMENT_CHANGED_RETRY')
        if replay:
            self._issue_pending(service, actor=actor, command_type=command_type, kind=kind, facts=facts,
                request_key=request_key, request_digest=request_digest, expected_revision=expected_revision,
                reason=reason, record_id=record_id, result=receipt['result'], before=before, after=after,
                scope=scope, history=history, snapshot=refreshed, evaluation=second, current=current)
            return RelationCommandResult(**receipt['result'], replayed=True)
        if kind == ASSIGNMENT and not reduction:
            service._check_intervals(after, evidence.person, refreshed)
        if before is not None:
            after['authorization_generation'] += service._generation_change(kind, before, after, context.now_utc)
        source_evidence = dict(site_id=service.repository.site_id, provider_id=refreshed.context.provider_id,
            captured_at=refreshed.context.captured_at.isoformat(), runtime_verified=False,
            current_source_digest=_snapshot_digest(refreshed), historical_cleanup=reduction,
            historical_revision_ref=None if history is None else history['revision_ref'])
        source_evidence['management_scope_v1'] = self._proof(service, kind, after, scope, context.person)
        source_evidence['management_match'] = dict(match=asdict(second.match), context_digest=second.context_digest,
            evaluated_at_utc=second.evaluated_at_utc.isoformat(), authorization_effect='none')
        # Bind all provenance into the immutable snapshot's existing digest.
        historical_snapshot = {**after, '_management_evidence_digest': digest(source_evidence)}
        version = dict(record_key=revision_key(kind, probe_id, after['revision']),
            **{'position' if kind == POSITION else 'assignment': probe_id}, revision=after['revision'], previous_revision=after['revision'] - 1,
            snapshot_json=canonical_json(historical_snapshot), content_digest=digest(historical_snapshot), actor=actor,
            policy_ref='management-match-v1:' + digest(asdict(second.match)), reason=reason,
            source_evidence_json=canonical_json(source_evidence), recorded_at_utc=stamp)
        result = dict(record_id=probe_id, revision=after['revision'], authorization_generation=after['authorization_generation'])
        service.repository.save_master(kind, after, expected_revision=expected_revision)
        service.repository.append_revision(POSITION_REVISION if kind == POSITION else ASSIGNMENT_REVISION, version)
        service.repository.insert_receipt(key, dict(site_id=service.repository.site_id, actor=actor, command_type=command_type,
            request_key=request_key, request_digest=request_digest, result=result, recorded_at_utc=stamp))
        # Reject a clock crossing during persistence. An outer delayed commit still
        # needs the later HTTP/request transaction boundary; never claim closure.
        final_context = self._context(service, actor, command_type, kind, before, after, scope, refreshed, history)
        final = self._authorize(self._heads(service, actor), final_context, refreshed)
        if final.match != second.match:
            _fail('MANAGEMENT_CHANGED_RETRY')
        self._issue_pending(service, actor=actor, command_type=command_type, kind=kind, facts=facts,
            request_key=request_key, request_digest=request_digest, expected_revision=expected_revision,
            reason=reason, record_id=record_id, result=result, before=before, after=after,
            scope=scope, history=history, snapshot=refreshed, evaluation=final, current=after)
        return RelationCommandResult(**result)

    @staticmethod
    def _proof(service, kind, candidate, scope, person):
        position = candidate if kind == POSITION else scope
        return dict(schema_version=1, site_id=service.repository.site_id, source_provider=PROVIDER, record_kind=kind,
            record_id=candidate['record_key'], revision=candidate['revision'], revision_ref=revision_key(kind, candidate['record_key'], candidate['revision']),
            company_id=position['company'], department_id=position['department'],
            person_source_id=None if person is None else person.source_id,
            person_company_id=None if person is None else person.company_id,
            person_department_id=None if person is None else person.department_id,
            subject_user=None if kind == POSITION else candidate['subject_user'], position_id=position['record_key'],
            position_revision=position['revision'], position_generation=position['authorization_generation'])
