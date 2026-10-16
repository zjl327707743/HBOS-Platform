"""Publication decisions are state transitions, never a reusable restore grant."""
import hashlib
from .service_http import canonical


class PublicationConflict(ValueError):
    pass


FROZEN_PUBLICATION_FIELDS = (
    "canonical_document_id", "version_id", "sha256", "upload_sha256",
    "binding_revision", "dataset_id", "ragflow_document_id", "department_key",
    "title", "document_number", "business_version", "source_type", "authority_status",
    "owner_inclusion_confirmed", "internal_sharing_confirmed", "approval_ref",
)


def select_publication_items(state, selected_document_ids=None):
    eligible=[item for item in state['items'] if item['status']=='parsed/indexed'
              and item.get('owner_inclusion_confirmed') is True and item.get('internal_sharing_confirmed') is True
              and item.get('disposition') not in {'SAME_CONTENT_SKIP','ALIAS'}]
    if selected_document_ids is None:return eligible
    if (not isinstance(selected_document_ids,list) or not 1<=len(selected_document_ids)<=512
            or any(not isinstance(v,str) or not v for v in selected_document_ids)
            or len(set(selected_document_ids))!=len(selected_document_ids)):
        raise PublicationConflict('Publication subset must contain distinct explicit document identities')
    if set(selected_document_ids)-{item['canonical_document_id'] for item in eligible}:
        raise PublicationConflict('Publication subset includes an unverified or unknown item')
    return [item for item in eligible if item['canonical_document_id'] in selected_document_ids]


def verify_frozen_target(item, approved, department):
    if not isinstance(approved, dict) or any(k not in approved for k in FROZEN_PUBLICATION_FIELDS):
        raise PublicationConflict("Complete frozen publication target is required")
    if any(item.get(k) != approved[k] for k in FROZEN_PUBLICATION_FIELDS):
        raise PublicationConflict("Item differs from approved frozen target")
    if item.get("department_key") != department:
        raise PublicationConflict("Frozen department differs from publication space")


def decide(current, target, operation="publish", expected=None):
    if operation not in {"publish", "replace", "restore", "repair"}:
        raise PublicationConflict("Unknown publication operation")
    withdrawn = bool(current and (current.get("withdrawn") or current.get("ingestion_status") == "retired"))
    version = current.get("current_version") if current else None
    if operation == "repair":
        if not current or not expected or target == expected:
            raise PublicationConflict("Technical repair requires an explicit distinct version")
        if version == target and not withdrawn and current.get("ingestion_status") == "published":
            return "RECEIPT_REQUIRED"
        if not withdrawn or version != expected:
            raise PublicationConflict("Technical repair requires the exact withdrawn current version")
        return "REPAIRED"
    if withdrawn and operation != "restore":
        return "SKIPPED_WITHDRAWN"
    if operation == "publish":
        if version and version != target:
            raise PublicationConflict("CONFLICT: current version differs from batch")
        if version == target:
            if current.get("ingestion_status") != "published":
                raise PublicationConflict("CONFLICT: publication state changed")
            return "NOOP"
        return "PUBLISHED"
    if not current or not expected:
        raise PublicationConflict("Explicit operation requires an expected current version")
    if operation == "restore" and target != expected:
        raise PublicationConflict("Restore must retain the withdrawn current version")
    # A committed retry can return its receipt only while target remains current.
    if version == target and current.get("ingestion_status") == "published" and not withdrawn:
        return "RECEIPT_REQUIRED"
    if version != expected:
        raise PublicationConflict("CONFLICT: expected current version does not match")
    if operation == "restore":
        if not withdrawn or target != expected:
            raise PublicationConflict("Restore must retain the withdrawn current version")
        return "RESTORED"
    if target == expected:
        raise PublicationConflict("Replace requires a distinct target version")
    return "REPLACED"


def receipt_id(batch, item, operation, expected, intent_ref=None):
    state = {"current_version": expected, "withdrawn": operation in {"restore", "repair"}}
    identity = [batch, item["canonical_document_id"], operation, state,
                item["version_id"], item["sha256"], item["binding_revision"], intent_ref]
    return "PUB_" + hashlib.sha256(canonical(identity).encode()).hexdigest()


TECHNICAL_REPAIR_FIELDS = frozenset((
    'parent_version_id','parent_batch_sha256','parent_source_sha256',
    'withdrawal_receipt_id','withdrawal_reason_sha256','approval_ref','reason_code'))

def validate_technical_repair(item,parent,expected):
    """A technical derivative cannot change the business document or its grants."""
    import re
    proof=item.get('technical_correction')
    if not isinstance(proof,dict) or set(proof)!=TECHNICAL_REPAIR_FIELDS:
        raise PublicationConflict('Exact technical recovery proof is required')
    if (proof['reason_code']!='PARSE_DELIMITER_PRESERVATION'
        or not isinstance(proof['approval_ref'],str) or not proof['approval_ref'].strip()
        or proof['parent_version_id']!=expected or parent.get('version_id')!=expected
        or item.get('version_id')==expected
        or any(not isinstance(proof[k],str) or not re.fullmatch(r'[0-9a-f]{64}',proof[k])
               for k in ('parent_batch_sha256','parent_source_sha256','withdrawal_reason_sha256'))
        or not isinstance(proof['withdrawal_receipt_id'],str) or not proof['withdrawal_receipt_id'].startswith('PUB_')):
        raise PublicationConflict('Invalid technical recovery proof')
    from .maintenance_contract import normalized_department
    if normalized_department(item.get('department_key',''))!=normalized_department(parent.get('department_key','')):
        raise PublicationConflict('Technical repair cannot change the department')
    for field in ('canonical_document_id','sha256','business_version','document_number','source_type','authority_status'):
        if item.get(field)!=parent.get(field):
            raise PublicationConflict('Technical repair cannot change source, identity or authority')
    if proof['parent_source_sha256']!=item.get('sha256'):
        raise PublicationConflict('Technical repair requires an identical original source')
    if not all(parent.get(k) is True and item.get(k) is True for k in ('owner_inclusion_confirmed','internal_sharing_confirmed')):
        raise PublicationConflict('Technical repair cannot acquire sharing approval')
    if not parent.get('approval_ref') or not item.get('approval_ref'):
        raise PublicationConflict('Technical repair requires original and current sharing approval')
    from knowledge_service.ingestion import approved_parser_profile,NATIVE_TEXT_NEWLINE_PROFILE
    try:profile=approved_parser_profile(item)
    except (TypeError,ValueError):raise PublicationConflict('Technical repair parser proof is invalid') from None
    if profile!=NATIVE_TEXT_NEWLINE_PROFILE:
        raise PublicationConflict('Technical repair requires the verified new text profile')
    return proof
