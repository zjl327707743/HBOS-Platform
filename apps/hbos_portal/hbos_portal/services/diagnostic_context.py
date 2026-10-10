"""Read-only user evaluation without changing the HTTP caller's session."""
from contextlib import contextmanager


@contextmanager
def diagnostic_user_context(subject):
    import frappe

    # Frappe set_user resets sid/data and permission caches. Preserve the
    # original session object, shared with session_obj, before HTTP persistence.
    session = frappe.local.session
    saved_session = dict(session)
    keys = ("cache", "form_dict", "jenv_restricted", "jenv_unrestricted",
            "role_permissions", "new_doc_templates", "user_perms")
    saved_context = {key: getattr(frappe.local, key, None) for key in keys}
    try:
        if subject != session.user:
            frappe.set_user(subject)
        yield
    finally:
        session.clear()
        session.update(saved_session)
        for key, value in saved_context.items():
            setattr(frappe.local, key, value)
