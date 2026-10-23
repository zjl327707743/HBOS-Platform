from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely
from hbos_portal.services.access import require_authenticated_user


@frappe.whitelist(methods=["GET"])
def get_token() -> dict[str, object]:
    """Return the current Session CSRF token to the same-origin Portal client."""

    def _load() -> dict[str, str]:
        require_authenticated_user()
        # Website Users do not render Desk, so their fresh Session may not yet
        # have a token. Use Frappe's generator instead of reading the field
        # directly; the normal request finalizer persists it in the Session.
        token = str(frappe.sessions.get_csrf_token() or "")
        if not token:
            frappe.throw("Session CSRF token is unavailable", frappe.AuthenticationError)
        frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"
        return {"csrf_token": token}

    return call_safely(_load)
