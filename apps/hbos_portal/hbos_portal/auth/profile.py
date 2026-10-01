"""Optional profile data from a verified provider response; never credentials."""
from urllib.parse import parse_qs, urlsplit


def normalized_avatar_url(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048 or any(c.isspace() for c in value):
        return ''
    try:
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            return ''
        if parsed.hostname in {'localhost', '127.0.0.1', '::1'} or parsed.hostname.endswith('.localhost'):
            return ''
        if any(key.lower() in {'access_token', 'refresh_token', 'client_secret', 'code'} for key in parse_qs(parsed.query)):
            return ''
        return value
    except ValueError:
        return ''


def sync_verified_avatar(user: str, identity: dict) -> None:
    """Call only after binding/tenant/account and any required MFA are verified.

    No HTTP fetch is performed here. A missing/invalid picture preserves the
    existing profile; picture failures cannot block a successful account flow.
    """
    avatar = normalized_avatar_url(identity.get('avatar_url'))
    if not avatar:
        return
    import frappe
    frappe.db.savepoint('hbos_avatar_sync')
    try:
        frappe.db.set_value('User', user, 'user_image', avatar, update_modified=False)
        frappe.clear_cache(user=user)
    except Exception:
        frappe.db.rollback(save_point='hbos_avatar_sync')
