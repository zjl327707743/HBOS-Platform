"""Explicit real internal-reference profile using native Frappe identity."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
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

# The registry projection (which version, dataset and binding revision were
# quality-passed and share-confirmed) is the same for every reader, and it was
# rebuilt on every request by parsing all import batches. That work belongs to
# the registry, not to a reader: it is cached under a key made of the site, the
# projection schema, the approved-config revision and the batch table's own
# revision (count plus newest modification). A batch write updates `modified`,
# so a new registration cannot be served from a stale key. The cache holds no
# per-actor conclusion - bindings, withdrawals and roles are still read from the
# database on every request and every accepted binding is matched against these
# pairs.
_REGISTRY_SCHEMA='registry-v1'

def _registry_revision(cur):
    from .shared_reference import rows as _rows  # module-level helper
    try:
        probe=_rows(cur,'SELECT COUNT(*) AS n,COALESCE(MAX(modified),\'\') AS m FROM `tabHBOS Knowledge Import Batch`')[0]
        return f"{probe['n']}:{probe['m']}"
    except Exception:
        return None

def _registry_pairs(cur,config,rows_fn):
    """Registry pairs for this request.

    The cross-request cache was removed rather than tuned: COUNT(*) plus
    MAX(modified) cannot prove that a registry row changed from Passed to
    Rejected or lost its sharing confirmation, because such an update can keep
    both aggregates identical, and the registry does take part in authorization.
    Until a revision maintained in the same transaction as every registry write
    exists, the projection is rebuilt once per request - which measured 107 ms
    and therefore was never the source of the six-second wait.
    """
    from .maintenance_contract import registered
    import frappe
    cached=getattr(frappe.local,'_hbos_registry_value',None)
    if cached is not None:
        return cached
    pairs=set();datasets=set()
    batches=rows_fn(cur,'SELECT frozen_json,state_json,quality_json FROM `tabHBOS Knowledge Import Batch`')
    for entry in batches:
        try:
            frozen=json.loads(entry['frozen_json']);batch_state=json.loads(entry['state_json']);quality=json.loads(entry['quality_json'] or '{}')
            registered(frozen,batch_state)
            for item in batch_state['items']:
                q=quality.get(item['version_id'],{})
                if (item['status']=='parsed/indexed' and item.get('disposition')!='SAME_CONTENT_SKIP' and
                    item.get('internal_sharing_confirmed') is True and item.get('owner_inclusion_confirmed') is True and
                    q.get('status')=='Passed' and q.get('source_sha256')==item['sha256'] and
                    q.get('upload_sha256')==item.get('upload_sha256')):
                    pairs.add((item['canonical_document_id'],item['version_id'],item['dataset_id'],item['ragflow_document_id'],item['binding_revision']))
                    datasets.add(item['dataset_id'])
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
            spaces=rows(cur,'SELECT name,title,required_role FROM `tabHBOS Knowledge Space` WHERE enabled=1')
            spaces=[s for s in spaces if s['name'] in self.config['approved_space_ids'] and s['required_role']==self.config['reader_role']]
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
                if (b.space_id in {s['name'] for s in spaces} and b.dataset_id in self.config['approved_dataset_ids']
                    and b.canonical_document_id in allowed_documents and b.source_type!='SYNTHETIC_TEST') or (
                    b.space_id in {s['name'] for s in spaces} and b.source_type!='SYNTHETIC_TEST' and
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
        """A narrow document.download extension of this same policy provider.

        Reader/search grants never imply this action. Candidate grants name an
        existing role, subject, space, immutable version and original hash. A
        future IAM provider can implement the same port without another IAM DB.
        The configuration is server-owned and reloaded with each HTTP request.
        """
        from .download_policy import document_download_decision
        from .execution_plan import validate_admission
        snapshot = self._current(actor, client)
        if binding not in snapshot.bindings:
            return False
        validate_admission(binding, self.environment, self.clock())
        cfg = self.repository.config
        approvals = cfg.get('document_download_grants', [])
        if not isinstance(approvals, list) or len(approvals) > 100:
            return False
        allowed = False
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
                allowed = True
                break
        return document_download_decision(
            subject_enabled=actor.enabled, version_current=True,
            iam_allowed=allowed, department_allowed=allowed,
            delivery_enabled=cfg.get('document_delivery_enabled') is True).allowed
