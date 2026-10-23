"""Non-transferable lease for the one new private import source File."""
from contextlib import contextmanager
from contextvars import ContextVar

_current = ContextVar('attendance_import_file', default=None)


def authorizes_new_file(doc, method):
    value = _current.get()
    if not value or method not in {'before_insert', 'before_validate'} or not doc.is_new():
        return False
    import frappe
    return ((doc.attached_to_doctype, doc.attached_to_name) == value['target']
            and doc.is_private in (1, True, '1') and doc.owner == value['actor'] == frappe.session.user)


@contextmanager
def new_file(actor, target):
    if target[0] != 'HBOS Attendance Import Log' and target != ('Page', 'hbos-shift-management'):
        raise ValueError('Unknown import attachment')
    token = _current.set(dict(actor=actor, target=target))
    try:
        yield
    finally:
        _current.reset(token)
