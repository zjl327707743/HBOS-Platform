"""Explicit real internal-reference profile using native Frappe identity."""
from __future__ import annotations
from collections import OrderedDict
import hashlib, json, os
from functools import lru_cache
from pathlib import Path
from threading import Lock
from .errors import KnowledgeError
from .execution_plan import Client, GrantPair, ProviderStamp
from .repositories import AuthoritySnapshot
from .frappe_authority import FrappePairedAuthority, committed_view, rows
from .metadata_integrity import binding_from_row
from .policy_provider import LegacyHbosPolicyProvider

def configuration():
    import frappe
    path=os.environ.get('HBOS_KNOWLEDGE_REFERENCE_CONFIG')
    if not path:raise KnowledgeError('POLICY_UNAVAILABLE')
    cfg=json.loads(Path(path).read_text())
    if (cfg.get('profile')!='INTERNAL_SHARED_REFERENCE' or cfg.get('environment')!='production'
        or cfg.get('site')!=frappe.local.site or frappe.conf.get('ignore_csrf')
        or frappe.conf.get('hbos_knowledge_reference_run')!=cfg.get('run_id')
        or not cfg.get('internal_sharing_approved') or not cfg.get('approved_space_ids')
        or not cfg.get('approved_dataset_ids') or not cfg.get('reader_role')
        or not cfg.get('model_policy_ref') or cfg.get('enable_synthetic_faults')):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return cfg

# Registry admission remains fresh per HTTP request. Only the projection inside
# one request is reused; no count/MAX(modified) aggregate authorizes cached data.
# Full bodies are needed only after current quality metadata has a Passed entry.
_REGISTRY_SCHEMA='registry-v1'

def _registry_revision(cur):
    from .shared_reference import rows as _rows  # module-level helper
    try:
        probe=_rows(cur,'SELECT COUNT(*) AS n,COALESCE(MAX(modified),\'\') AS m FROM `tabHBOS Knowledge Import Batch`')[0]
        return f"{probe['n']}:{probe['m']}"
    except Exception:
        return None

def _project_registry_row(frozen_json, state_json, quality_json):
    from .maintenance_contract import registered

    frozen = json.loads(frozen_json)
    state = json.loads(state_json)
    quality = json.loads(quality_json or '{}')
    if not isinstance(quality, dict):
        return ()
    registered(frozen, state)
    pairs = []
    for item in state['items']:
        review = quality.get(item['version_id'], {})
        if (item['status'] == 'parsed/indexed' and item.get('disposition') != 'SAME_CONTENT_SKIP'
                and item.get('internal_sharing_confirmed') is True
                and item.get('owner_inclusion_confirmed') is True
                and review.get('status') == 'Passed' and review.get('source_sha256') == item['sha256']
                and review.get('upload_sha256') == item.get('upload_sha256')):
            pairs.append((item['canonical_document_id'], item['version_id'], item['dataset_id'],
                          item['ragflow_document_id'], item['binding_revision']))
    return tuple(pairs)


_cached_registry_row = lru_cache(maxsize=512)(_project_registry_row)
_large_registry_rows = OrderedDict()
_large_registry_lock = Lock()


def _project_large_registry_row(*values):
    # The digest keys the complete bytes of each field from the fresh snapshot.
    # Keep the projection only so the cache does not retain large manifests.
    key = tuple(hashlib.sha256(value.encode()).digest() for value in values)
    with _large_registry_lock:
        if key in _large_registry_rows:
            _large_registry_rows.move_to_end(key)
            return _large_registry_rows[key]
    pairs = _project_registry_row(*values)
    with _large_registry_lock:
        _large_registry_rows[key] = pairs
        _large_registry_rows.move_to_end(key)
        if len(_large_registry_rows) > 256:
            _large_registry_rows.popitem(last=False)
    return pairs


def _registry_pairs(cur,config,rows_fn):
    """Registry pairs for this request.

    The cross-request cache was removed rather than tuned: COUNT(*) plus
    MAX(modified) cannot prove that a registry row changed from Passed to
    Rejected or lost its sharing confirmation, because such an update can keep
    both aggregates identical, and the registry does take part in authorization.
    Rebuild the set from rows read in the current request. Reuse only immutable
    results of validating an identical frozen, state and quality payload.
    """
    import frappe
    cached=getattr(frappe.local,'_hbos_registry_value',None)
    if cached is not None:
        return cached
    pairs=set();datasets=set()
    # Quality is read afresh from this committed snapshot. A batch without any
    # Passed review cannot contribute a registered pair, so do not load its
    # potentially large frozen/source-page/profile JSON. This is a conservative
    # preselection, not an authorization cache: selected rows are read again and
    # still pass every existing frozen, state, sharing and checksum check below.
    reviews=rows_fn(cur,'SELECT name,quality_json FROM `tabHBOS Knowledge Import Batch`')
    eligible=[]
    for entry in reviews:
        try:quality=json.loads(entry['quality_json'] or '{}')
        except (ValueError,TypeError,KeyError):continue
        if isinstance(quality,dict) and any(isinstance(q,dict) and q.get('status')=='Passed' for q in quality.values()):
            eligible.append(entry['name'])
    batches=[]
    for start in range(0,len(eligible),128):
        ids=eligible[start:start+128]
        batches.extend(rows_fn(cur,'SELECT frozen_json,state_json,quality_json FROM `tabHBOS Knowledge Import Batch` WHERE name IN ('+
                               ','.join(['%s']*len(ids))+')',tuple(ids)))
    for entry in batches:
        try:
            values = entry['frozen_json'], entry['state_json'], entry['quality_json']
            project = _project_registry_row
            if all(isinstance(value, str) for value in values):
                project = _cached_registry_row if sum(map(len, values)) <= 32768 else _project_large_registry_row
            accepted = project(*values)
            pairs.update(accepted)
            datasets.update(pair[2] for pair in accepted)
        except (ValueError,KeyError,TypeError,KnowledgeError):
            continue
    value=(pairs,datasets)
    frappe.local._hbos_registry_value=value
    return value


class InternalSharedAuthority(FrappePairedAuthority):
    test_only=False
    def client_for(self,actor):
        raw=self.proofs.state.get('private-proof:'+actor.session_ref)
        if not raw or json.loads(raw)['client']!=self.config['portal_client_id']:
            raise KnowledgeError('CLIENT_AUTH_FAILED')
        return Client(self.config['portal_client_id'])
    def read_current(self,actor):
        state=self.proofs.resolve(actor,self.client_for(actor))
        if self.config['reader_role'] not in state.roles:
            raise KnowledgeError('SCOPE_REJECTED')
        with committed_view() as cur:
            extra=(',maintenance_department,template_json,parent_space,space_admission_json'
                   if self.config.get('maintenance_space_creation_enabled') is True else '')
            spaces=rows(cur,'SELECT name,title,required_role'+extra+' FROM `tabHBOS Knowledge Space` WHERE enabled=1')
            from .maintenance_spaces import approved_child_spaces
            permitted_spaces=approved_child_spaces(spaces,self.config)
            spaces=[s for s in spaces if s['name'] in permitted_spaces and s['required_role']==self.config['reader_role']]
            space_ids={space['name'] for space in spaces}
            data=rows(cur,'SELECT b.*,s.name as space_record_id,s.enabled as space_enabled, '
                'v.name as version_record_id,v.version_id as version_record_identity, '
                'v.canonical_document_id as version_document_id, '
                'd.name as document_record_id,d.document_id as document_record_identity, '
                'd.current_version,d.withdrawn,d.ingestion_status '
                'FROM `tabHBOS Knowledge Backend Binding` b '
                'LEFT JOIN `tabHBOS Knowledge Space` s ON s.name=b.space_id '
                'LEFT JOIN `tabHBOS Knowledge Version` v ON v.name=b.version_id '
                'LEFT JOIN `tabHBOS Knowledge Document` d ON d.name=b.canonical_document_id WHERE b.enabled=1')
            allowed_datasets=set(self.config['approved_dataset_ids'])
            allowed_documents=set(self.config['approved_document_ids'])
            registered_pairs=set()
            if self.config.get('maintenance_registry_enabled'):
                registered_pairs,registry_datasets=_registry_pairs(cur,self.config,rows)
                allowed_datasets.update(registry_datasets)
            accepted=[]
            for row in data:
                try:b=binding_from_row(row)
                except KnowledgeError:continue
                if (b.space_id in space_ids and b.dataset_id in self.config['approved_dataset_ids']
                    and b.canonical_document_id in allowed_documents and b.source_type!='SYNTHETIC_TEST') or (
                    b.space_id in space_ids and b.source_type!='SYNTHETIC_TEST' and
                    (b.canonical_document_id,b.version_id,b.dataset_id,b.document_id,b.binding_revision) in registered_pairs):
                    accepted.append(b)
        bindings=tuple(accepted)
        revision=hashlib.sha256(json.dumps(sorted((b.binding_ref,b.binding_revision,b.version_id) for b in bindings)).encode()).hexdigest()
        grants=tuple(GrantPair(self.config['reader_role'],s['name'],a,'SHARED_'+s['name']+'_'+a.split('.')[-1])
            for s in spaces for a in ('knowledge.search','knowledge.evidence','knowledge.spaces','document.read'))
        return AuthoritySnapshot(state,(Client(self.config['portal_client_id']),),grants,tuple(s['name'] for s in spaces),
            bindings,tuple(sorted(allowed_datasets)),(),self.config['policy_revision'],revision,
            ProviderStamp('INTERNAL_SHARED_REFERENCE',self.config['policy_revision'],None),
            self.config['model_policy_ref'],True,tuple((s['name'],s['title']) for s in spaces))

class InternalSharedReferenceProvider(LegacyHbosPolicyProvider):
    provider_kind='INTERNAL_SHARED_REFERENCE'

    def authorize_download(self, actor, client, binding, source_sha256):
        """The one download decision, made by the server for this binding.

        Reading and searching still need their own grants; this is the separate
        ``document.download`` action. Under the configured
        ``shared_all_authenticated`` scope every normally enabled business user
        may take the original of a current published shared document without a
        per-file grant. Under ``department_scoped`` the same entry point consults
        IAM/department scope and legacy per-file grants instead. Withdrawal,
        publication state, the current version, an explicitly withheld original,
        synthetic bindings and original delivery being switched off are refused
        in both scopes, and the configuration is server-owned and reloaded with
        each HTTP request.
        """
        from .download_policy import (DEPARTMENT_SCOPED, SHARED_ALL_AUTHENTICATED,
                                      document_download_decision)
        from .execution_plan import validate_admission
        snapshot = self._current(actor, client)
        if binding not in snapshot.bindings:
            return False
        validate_admission(binding, self.environment, self.clock())
        cfg = self.repository.config
        scope = cfg.get('document_download_scope', SHARED_ALL_AUTHENTICATED)
        if not isinstance(scope, str):
            return False
        withheld = cfg.get('document_download_withheld_versions', [])
        if not isinstance(withheld, list) or len(withheld) > 500:
            return False
        approved = False
        if scope == DEPARTMENT_SCOPED:
            approvals = cfg.get('document_download_grants', [])
            if not isinstance(approvals, list) or len(approvals) > 100:
                return False
            for grant in approvals:
                if not isinstance(grant, dict) or set(grant) != {
                        'action', 'role_ref', 'subject_refs', 'space_id', 'document_id',
                        'version_id', 'source_sha256'}:
                    continue
                subjects = grant['subject_refs']
                if (not isinstance(subjects, list) or not subjects or len(subjects) > 20
                        or not all(isinstance(s, str) for s in subjects)):
                    continue
                if (grant['action'] == 'document.download'
                        and grant['role_ref'] in snapshot.actor_state.roles
                        and actor.user_ref in subjects
                        and grant['space_id'] == binding.space_id
                        and binding.space_id in snapshot.active_spaces
                        and binding.space_id not in snapshot.denied_spaces
                        and grant['document_id'] == binding.canonical_document_id
                        and grant['version_id'] == binding.version_id
                        and grant['source_sha256'] == source_sha256):
                    approved = True
                    break
        return document_download_decision(
            subject_enabled=actor.enabled, version_current=True, scope=scope,
            iam_allowed=approved, department_allowed=approved,
            delivery_enabled=cfg.get('document_delivery_enabled') is True,
            withheld=(binding.version_id in withheld
                      or binding.canonical_document_id in withheld),
            synthetic=binding.source_type == 'SYNTHETIC_TEST').allowed
