"""Present current, visually reviewed source excerpts to authorized employees."""

from dataclasses import replace

from knowledge_service.hbos_gateway.response_projection import public_evidence as project
from knowledge_service.hbos_gateway.reviewed_excerpts import has_review, reviewed_presentation


def public_evidence(record, evidence_id, *, environment):
    binding = record.binding
    if environment == 'production' and has_review(binding):
        from .document_assets import current_source_hash
        excerpt,page = reviewed_presentation(binding,record.excerpt,source_sha256=current_source_hash(binding))
        page = record.page_number if record.page_number is not None else page
        if excerpt != record.excerpt or page != record.page_number:
            record = replace(record,excerpt=excerpt,page_number=page)
    return project(record, evidence_id, environment=environment)
