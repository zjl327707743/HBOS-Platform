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
    if operation not in {"publish", "replace", "restore"}:
        raise PublicationConflict("Unknown publication operation")
    withdrawn = bool(current and (current.get("withdrawn") or current.get("ingestion_status") == "retired"))
    version = current.get("current_version") if current else None
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
    state = {"current_version": expected, "withdrawn": operation == "restore"}
    identity = [batch, item["canonical_document_id"], operation, state,
                item["version_id"], item["sha256"], item["binding_revision"], intent_ref]
    return "PUB_" + hashlib.sha256(canonical(identity).encode()).hexdigest()
