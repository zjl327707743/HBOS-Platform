"""Same-source index replacement preserves business identity and sharing.

The existing replace operation performs the final compare-and-swap. This proof
does not authorize withdrawal, restoration, a new source, or a changed SOP.
"""
import hashlib
from .service_http import canonical
from .publication import PublicationConflict

FACT_FIELDS=('sha256','document_number','business_version','source_type','authority_status','legal_metadata')
PROOF_FIELDS=frozenset(('parent_version_id','parent_binding_revision','parent_document_id',
                        'parent_metadata_sha256','source_sha256'))

def metadata_digest(metadata):
    return hashlib.sha256(canonical(metadata).encode()).hexdigest()

def validate_same_source_reindex(item,current,parent_metadata,parent_binding,expected,space_id):
    preflight=item.get('native_text_preflight',{});proof=preflight.get('same_source_reindex')
    def require(ok,reason):
        if not ok:raise PublicationConflict(reason)
    require(isinstance(proof,dict) and set(proof)==PROOF_FIELDS,'Exact same-source reindex proof required')
    require(item.get('parser_input')=='VERIFIED_LOCAL_FULL_TEXT'
            and item.get('disposition')=='REPLACE_CURRENT','Reindex requires a new full-text replacement version')
    require(current and not current.get('withdrawn') and current.get('ingestion_status')=='published',
            'Reindex cannot restore or withdraw a publication')
    require(expected==proof['parent_version_id']==item.get('expected_current_version')
            and current.get('current_version') in (expected,item['version_id'])
            and item['version_id']!=expected,'Reindex current-version comparison failed')
    require(current.get('document_id')==item['canonical_document_id']==parent_binding.get('canonical_document_id')
            and parent_binding.get('version_id')==expected,'Reindex parent document identity changed')
    require(proof['parent_metadata_sha256']==metadata_digest(parent_metadata),
            'Reindex immutable parent metadata changed')
    require(all(item.get(k)==parent_metadata.get(k) for k in FACT_FIELDS),
            'Reindex cannot change original source or business facts')
    asset=preflight.get('original_asset',{})
    require(proof['source_sha256']==item['sha256']==current.get('source_hash')
            ==parent_metadata.get('sha256')==parent_metadata.get('upload_sha256')==asset.get('source_sha256'),
            'Reindex requires the identical retained native original')
    require(item['dataset_id']==current.get('dataset_id')==parent_binding.get('dataset_id')==asset.get('dataset_id')
            and space_id==parent_binding.get('space_id') and item.get('space_id')==space_id,
            'Reindex cannot change source dataset or sharing space')
    require(proof['parent_document_id']==parent_binding.get('document_id')==asset.get('document_id')
            and proof['parent_binding_revision']==parent_binding.get('binding_revision')
            and item['binding_revision']!=proof['parent_binding_revision']
            and item['ragflow_document_id']!=proof['parent_document_id'],
            'Reindex must preserve the old physical index and create a distinct binding')
    require(item.get('title')==parent_binding.get('title')
            and item.get('document_number')==parent_binding.get('document_number')
            and item.get('business_version')==parent_binding.get('business_version')
            and item.get('source_type')==parent_binding.get('source_type')
            and item.get('authority_status')==parent_binding.get('authority_status'),
            'Reindex cannot promote authority or change displayed document identity')
    require(item.get('owner_inclusion_confirmed') is True and item.get('internal_sharing_confirmed') is True
            and bool(item.get('approval_ref')) and item.get('upload_sha256')==preflight.get('text_sha256'),
            'Reindex requires approved exact derived text')
    return proof
