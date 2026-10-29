"""A dedicated native maintenance role, separate from employee document APIs."""
from .errors import KnowledgeError

ROLE = 'HBOS Knowledge Maintainer'

def permitted(user=None):
    import frappe
    user = user or frappe.session.user
    if user in ('Guest','Administrator'):return False
    from .shared_reference import configuration
    from .frappe_authority import committed_view
    from .connections import _user
    try:
        with committed_view() as cur:roles,_=_user(cur,user,configuration())
        return ROLE in roles
    except KnowledgeError:return False

def require():
    if not permitted():
        raise KnowledgeError('SCOPE_REJECTED')
    from .runtime import load_runtime
    runtime=load_runtime()
    runtime.provider._current(runtime.actor(),runtime.client)
