"""Reviewed legal identity. Folder names never establish current effectiveness."""
from datetime import date
from .errors import KnowledgeError
from .public_strings import safe_string

LAW_SPACE='DEPT_PUBLIC_LAW'
LAW_CATEGORIES=('国家法律法规','GMP与药品监管','药典与技术标准','地方政策','安全环保','待分类')
EFFECTIVE_STATUSES=('待核','现行有效','已废止')
FIELDS=('category','level','issuer','published_date','region','applicability','effective_status')

def legal_metadata(value):
    if not isinstance(value,dict) or set(value)-set(FIELDS):raise KnowledgeError('INVALID_REQUEST')
    if value.get('category') not in LAW_CATEGORIES or value.get('effective_status') not in EFFECTIVE_STATUSES:
        raise KnowledgeError('INVALID_REQUEST')
    result={key:value.get(key) for key in FIELDS}
    for key in ('level','issuer','region','applicability'):
        if result[key] is not None:result[key]=safe_string(result[key],160).strip() or None
    if result['published_date'] is not None:
        try:
            if date.fromisoformat(result['published_date']).isoformat()!=result['published_date']:raise ValueError()
        except (TypeError,ValueError):raise KnowledgeError('INVALID_REQUEST') from None
    return result

def for_version(version_id):
    # This is called only after the catalog's live read authorization. A version
    # lookup cannot introduce a document that is absent from that authorized set.
    import json,frappe
    raw=frappe.db.get_value('HBOS Knowledge Version',version_id,'version_json')
    try:value=json.loads(raw or '{}').get('legal_metadata')
    except (TypeError,ValueError):raise KnowledgeError('POLICY_UNAVAILABLE') from None
    return legal_metadata(value or {'category':'待分类','effective_status':'待核'})
