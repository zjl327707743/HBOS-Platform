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
            accepted=[]
            for row in data:
                try:b=binding_from_row(row)
                except KnowledgeError:continue
                if (b.space_id in {s['name'] for s in spaces} and b.dataset_id in self.config['approved_dataset_ids']
                    and b.canonical_document_id in self.config['approved_document_ids'] and b.source_type!='SYNTHETIC_TEST'):
                    accepted.append(b)
        bindings=tuple(accepted)
        revision=hashlib.sha256(json.dumps(sorted((b.binding_ref,b.binding_revision,b.version_id) for b in bindings)).encode()).hexdigest()
        grants=tuple(GrantPair(self.config['reader_role'],s['name'],a,'SHARED_'+s['name']+'_'+a.split('.')[-1])
            for s in spaces for a in ('knowledge.search','knowledge.evidence','knowledge.spaces'))
        return AuthoritySnapshot(state,(Client(self.config['portal_client_id']),),grants,tuple(s['name'] for s in spaces),
            bindings,tuple(self.config['approved_dataset_ids']),(),self.config['policy_revision'],revision,
            ProviderStamp('INTERNAL_SHARED_REFERENCE',self.config['policy_revision'],None),
            self.config['model_policy_ref'],True,tuple((s['name'],s['title']) for s in spaces))

class InternalSharedReferenceProvider(LegacyHbosPolicyProvider):
    provider_kind='INTERNAL_SHARED_REFERENCE'
