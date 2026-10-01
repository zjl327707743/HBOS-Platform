from __future__ import annotations

from frappe.model.document import Document


class HBOSKnowledgeDocument(Document):
    """Metadata and publication state only; never stores source text or chunks."""
