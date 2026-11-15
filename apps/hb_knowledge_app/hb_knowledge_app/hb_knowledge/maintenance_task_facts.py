"""Candidate task facts saved by the existing locked SQL batch port."""

import hashlib
import json
from pathlib import Path
import re

from .errors import KnowledgeError
from .service_http import canonical


SHA = re.compile('[0-9a-f]{64}')
ID = re.compile('[a-zA-Z0-9_.:/-]{1,160}')
TASK_ID = re.compile('[0-9a-f]{32}')
IDENTITY = ('batch_id', 'document_id', 'version_id', 'source_sha256', 'dataset_id', 'native_document_id')
NOTIFICATION_GROUP = 'hbos_r2_native_parse'


def prepared_profile_sha(item, default_patch=None):
    profile = item.get('native_profile')
    if profile is not None:
        return profile['profile_sha256']
    if not _matches(SHA, default_patch) or not isinstance(item.get('parser_config'), dict):
        raise ValueError('An exact default parser revision is required')
    return hashlib.sha256(canonical(['R2_STANDARD_PROFILE', default_patch, item['parser_config'],
                                      item.get('parser_input')]).encode()).hexdigest()


def preparation_document(batch_id, item, default_patch=None):
    """Identify the exact source, physical document, and parser revision."""
    scope = {
        'batch_id': batch_id, 'document_id': item['canonical_document_id'],
        'version_id': item['version_id'], 'source_sha256': item['sha256'],
        'dataset_id': item['dataset_id'], 'native_document_id': item['ragflow_document_id'],
        'binding_revision': item['binding_revision'],
        'profile_sha256': prepared_profile_sha(item, default_patch),
        'upload_sha256': item['upload_sha256'],
    }
    if (not all(_matches(ID, scope[name]) for name in ('batch_id', 'document_id', 'version_id', 'binding_revision'))
            or not all(_matches(SHA, value) for value in (scope['source_sha256'], scope['profile_sha256'], item['upload_sha256']))
            or not all(_matches(TASK_ID, scope[name]) for name in ('dataset_id', 'native_document_id'))):
        raise ValueError('Invalid prepared document identity')
    return scope


def planned_shard(batch_id, item, from_page, to_page, default_patch=None):
    """Compute the durable identity of one exact prepared native shard."""
    scope = preparation_document(batch_id, item, default_patch)
    if type(from_page) is not int or type(to_page) is not int or not 0 <= from_page < to_page:
        raise ValueError('Invalid native shard range')
    scope.update(from_page=from_page, to_page=to_page)
    logical_key = hashlib.sha256(canonical(['R2_STANDARD_PARSE', scope]).encode()).hexdigest()
    scope.pop('upload_sha256')
    task_id = logical_key[:32]
    scope.update(logical_task_key=logical_key, stream='hbos:r2:parse:' + task_id,
                 group=NOTIFICATION_GROUP, message_id='1-0')
    return task_id, scope


def preparation_sha(batch_id, item, default_patch=None):
    return hashlib.sha256(canonical(preparation_document(batch_id, item, default_patch)).encode()).hexdigest()


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def task_manifest(config, permit, job=None):
    """Read only the manifest whose bytes are pinned by the current permit."""
    try:
        if permit.get('managed') is True:
            manifest=(job or {}).get('r2_prepared_manifest')
            if hashlib.sha256(canonical(manifest).encode()).hexdigest()!=permit['task_manifest_sha256']:
                raise ValueError()
            return manifest_tasks(manifest)
        path = Path(config['maintenance_task_manifest_file'])
        with path.open('rb') as stream:
            raw = stream.read(4 * 1048576 + 1)
        if len(raw) > 4 * 1048576 or hashlib.sha256(raw).hexdigest() != permit['task_manifest_sha256']:
            raise ValueError()
        return manifest_tasks(json.loads(raw))
    except (OSError, ValueError, KeyError, TypeError):
        raise KnowledgeError('POLICY_UNAVAILABLE') from None


def manifest_tasks(manifest):
    if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'tasks'}
            or manifest['schema'] != 'hbos.native-task-admission.v1'):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    tasks = manifest['tasks']
    if not isinstance(tasks, dict) or len(tasks) > 2048 or any(not _matches(TASK_ID, task) for task in tasks):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    fields = set(IDENTITY) | {'logical_task_key', 'binding_revision', 'profile_sha256',
                             'stream', 'group', 'message_id', 'from_page', 'to_page'}
    if any(not isinstance(item, dict) or set(item) != fields or not _matches(SHA, item['logical_task_key'])
           or item['logical_task_key'][:32] != task_id for task_id, item in tasks.items()):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return tasks


def admission_identity(tasks, request, state_item, default_patch=None):
    """Bind one worker request to a Main-pinned native task and exact message."""
    try:
        entry = tasks[request['task_id']]
        expected = planned_shard(request['batch_id'], state_item, entry['from_page'], entry['to_page'], default_patch)
        if expected != (request['task_id'], entry) or any(entry[key] != request[key] for key in IDENTITY):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise KnowledgeError('POLICY_UNAVAILABLE') from None
    return hashlib.sha256(canonical(entry).encode()).hexdigest(), entry


def _settled_attempts(attempts, recovery):
    parent = recovery.get('parent_attempt_id') if recovery else None
    recovered = parent is not None and any(row.get('parent_attempt_id') == parent and row['outcome']=='SUCCESS'
                                          for row in attempts.values())
    return all(row['outcome']=='SUCCESS' or (
        recovered and key==parent and row['outcome']=='CANCELLED_BEFORE_WIRE') for key,row in attempts.items())


def advance(facts, task_id, identity, generation, operation, details, *, recovery_approved=False):
    """Caller holds the batch row lock and has checked the current job lease."""
    if not isinstance(details, dict):
        raise KnowledgeError('INVALID_REQUEST')
    old = facts.get(task_id)
    if old and old['identity_sha256'] != identity:
        raise KnowledgeError('IMPORT_BUSY')
    recovery = old.get('known_no_wire_recovery') if old else None
    available_recovery = (recovery if recovery_approved and recovery and old['status']=='CANCELLED_BEFORE_WIRE'
        and old['generation'] < generation and not any(row.get('parent_attempt_id') for row in old['attempts'].values())
        and old['attempts'].get(recovery['parent_attempt_id'],{}).get('outcome')=='CANCELLED_BEFORE_WIRE' else None)
    if operation == 'inspect' and not details:
        if not old:
            return {'state': 'PREPARED', 'execute': False}
        response={'state': old['status'], 'execute': False, 'result_sha256': old.get('result_sha256'),
                  'reclaimable': (old['status'] == 'CLAIMED' and old['generation'] < generation and not old['attempts'])}
        if available_recovery is not None:
            response['confirmed_no_wire'] = available_recovery
        return response
    if operation == 'claim' and not details:
        if old and old['status'] in ('RESULT_DURABLE', 'ACK_UNCERTAIN', 'ACKED'):
            return {'state': old['status'], 'execute': False}
        if available_recovery is not None:
            old.update(status='CLAIMED',generation=generation)
            return {'state':'CLAIMED','execute':True,'reclaimed_without_intent':False,
                    'confirmed_no_wire':available_recovery}
        if old and (old['status'] != 'CLAIMED' or old['attempts'] or old['generation'] >= generation):
            raise KnowledgeError('IMPORT_BUSY')
        facts[task_id] = {'identity_sha256': identity, 'generation': generation,
                          'status': 'CLAIMED', 'attempts': {}}
        return {'state': 'CLAIMED', 'execute': True, 'reclaimed_without_intent': old is not None}
    if not old:
        raise KnowledgeError('IMPORT_BUSY')
    state = old['status']
    if operation in ('authorize_ack', 'ack_result'):
        fields = {'result_sha256'} if operation == 'authorize_ack' else {'ack_count', 'result_sha256'}
        if (state not in ('RESULT_DURABLE', 'ACK_UNCERTAIN', 'ACKED')
                or set(details) != fields
                or details['result_sha256'] != old['result_sha256']
                or generation < old['generation']):
            raise KnowledgeError('IMPORT_BUSY')
        if operation == 'authorize_ack':
            return {'state': state, 'execute': False}
        count = details['ack_count']
        if count is not None and (type(count) is not int or count not in (0, 1)):
            raise KnowledgeError('INVALID_REQUEST')
        if state == 'ACKED':
            return {'state': state, 'execute': False}
        state = 'ACKED' if count == 1 else 'ACK_UNCERTAIN'
        old.update(status=state, generation=generation, ack_count=count)
        return {'state': state, 'execute': False}
    terminal_provider = state in ('UNKNOWN_EXTERNAL', 'CANCELLED_BEFORE_WIRE')
    if old['generation'] != generation or (
            state not in ('CLAIMED', 'SEND_INTENT', 'PROVIDER_DONE', 'INDEX_WRITING')
            and not (operation == 'provider_outcome' and terminal_provider)):
        raise KnowledgeError('IMPORT_BUSY')
    attempts = old['attempts']
    # A recovered task has an original probe, a cancelled title request and
    # its linked replacement before any successful body request can exist.
    has_body_attempt = recovery is None or len(attempts) > 3
    if operation == 'send_intent' and set(details) in (
            {'attempt_id', 'operation_id'}, {'attempt_id', 'operation_id', 'parent_attempt_id'}):
        attempt, provider_operation = details['attempt_id'], details['operation_id']
        parent = details.get('parent_attempt_id')
        if recovery is not None:
            child = next((row for row in attempts.values()
                          if row.get('parent_attempt_id') == recovery['parent_attempt_id']), None)
            if child is None and (not recovery_approved or parent != recovery['parent_attempt_id']
                                  or provider_operation != recovery['operation_id']):
                raise KnowledgeError('IMPORT_BUSY')
            if child is not None and (child['outcome'] != 'SUCCESS' or 'parent_attempt_id' in details):
                raise KnowledgeError('IMPORT_BUSY')
        elif 'parent_attempt_id' in details:
            raise KnowledgeError('IMPORT_BUSY')
        if (state == 'INDEX_WRITING' or not _matches(ID, attempt) or not _matches(ID, provider_operation) or len(attempts) >= 256
                or attempt in attempts or any(row['operation_id'] == provider_operation and key != parent
                                              for key,row in attempts.items())):
            raise KnowledgeError('IMPORT_BUSY')
        attempts[attempt] = {'operation_id': provider_operation, 'outcome': None}
        if parent is not None:
            attempts[attempt]['parent_attempt_id']=parent
        state = 'SEND_INTENT'
    elif operation == 'provider_outcome' and set(details) == {'attempt_id', 'outcome', 'receipt_sha256', 'provider_request_id'}:
        attempt, result, receipt = details['attempt_id'], details['outcome'], details['receipt_sha256']
        provider_request_id = details['provider_request_id']
        if (not _matches(ID, attempt) or attempt not in attempts or attempts[attempt]['outcome'] is not None
                or result not in ('SUCCESS', 'UNKNOWN_EXTERNAL', 'CANCELLED_BEFORE_WIRE') or not _matches(SHA, receipt)
                or (provider_request_id is not None and not _matches(ID, provider_request_id))):
            raise KnowledgeError('IMPORT_BUSY')
        attempts[attempt].update(outcome=result, receipt_sha256=receipt, provider_request_id=provider_request_id)
        if result == 'UNKNOWN_EXTERNAL':
            state = 'UNKNOWN_EXTERNAL'
        elif result == 'CANCELLED_BEFORE_WIRE' and state != 'UNKNOWN_EXTERNAL':
            state = 'CANCELLED_BEFORE_WIRE'
        elif _settled_attempts(attempts,recovery):
            state = 'PROVIDER_DONE'
    elif operation == 'index_write' and not details:
        if state not in ('CLAIMED', 'PROVIDER_DONE', 'INDEX_WRITING') or (
                recovery is not None and (not has_body_attempt or not _settled_attempts(attempts,recovery))):
            raise KnowledgeError('IMPORT_BUSY')
        state = 'INDEX_WRITING'
    elif operation == 'result_durable' and set(details) == {'result_sha256'}:
        digest = details['result_sha256']
        if (state != 'INDEX_WRITING' or not _matches(SHA, digest) or not has_body_attempt
                or not _settled_attempts(attempts,recovery)):
            raise KnowledgeError('IMPORT_BUSY')
        old['result_sha256'] = digest
        state = 'RESULT_DURABLE'
    else:
        raise KnowledgeError('INVALID_REQUEST')
    old['status'] = state
    return {'state': state, 'execute': False}


def batch_tasks(tasks, batch_id, selected, default_patch=None):
    """Resolve all prepared shards for the selected documents before claiming."""
    by_document = {}
    for item in selected:
        matches = {key for key, entry in tasks.items()
                   if entry['batch_id'] == batch_id and entry['document_id'] == item['canonical_document_id']}
        if not matches and item.get('status') in ('parsed/indexed', 'skipped_duplicate'):
            continue
        if not matches or item.get('status') not in ('parse_queued', 'parsed/indexed'):
            raise KnowledgeError('POLICY_UNAVAILABLE')
        request = dict(batch_id=batch_id, document_id=item['canonical_document_id'], version_id=item['version_id'],
                       source_sha256=item['sha256'], dataset_id=item['dataset_id'], native_document_id=item['ragflow_document_id'])
        for key in matches:
            admission_identity(tasks, dict(request, task_id=key), item, default_patch)
        by_document[item['canonical_document_id']] = sorted(matches)
    return by_document


def require_durable_task_acks(job, items):
    if not job.get('r2_task_manifest_sha256'):
        if job.get('r2_preparation') and any(item['canonical_document_id'] in job['document_ids'] for item in items):
            raise KnowledgeError('QUALITY_REQUIRED')
        return
    tasks = job.get('r2_tasks_by_document')
    if not isinstance(tasks, dict):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    facts = job.get('task_facts', {})
    if any(not tasks.get(item['canonical_document_id']) or any(facts.get(task_id, {}).get('status')!='ACKED'
           for task_id in tasks[item['canonical_document_id']]) for item in items):
        raise KnowledgeError('QUALITY_REQUIRED')
