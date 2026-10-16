from __future__ import annotations
import hmac
import hashlib
import secrets

class SafeAudit:
    """No request text/fingerprint, excerpt, credentials, physical IDs or traceback."""
    test_only = True
    def __init__(self):
        self._key = secrets.token_bytes(32)
        self.events = []

    def record(self, subject: str, operation: str, code: str, count: int = 0):
        if operation not in {"search", "evidence", "contract", "ask"} or type(count) is not int:
            raise ValueError("audit shape")
        actor_key = hmac.new(self._key, subject.encode(), hashlib.sha256).hexdigest()[:16]
        self.events.append({"actor_key": actor_key, "operation": operation, "code": code, "count": count})
