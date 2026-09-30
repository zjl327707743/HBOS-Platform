from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit


STATE_TTL_SECONDS = 8 * 60
STATE_PREFIX = "hbos:p1:feishu:oauth-state:"


class OAuthStateError(ValueError):
    pass


def validate_redirect_target(value: str | None) -> str:
    target = str(value or "/hbos").strip() or "/hbos"
    for _ in range(4):
        decoded = unquote(target)
        if decoded == target:
            break
        target = decoded
    else:
        raise OAuthStateError("redirect target is over-encoded")

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise OAuthStateError("redirect target must be same-origin")
    if not (parsed.path == "/hbos" or parsed.path.startswith("/hbos/")) or parsed.path.startswith("//"):
        raise OAuthStateError("redirect target must stay inside /hbos")
    if "\\" in parsed.path:
        raise OAuthStateError("redirect target contains a backslash")
    segments = [segment for segment in parsed.path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise OAuthStateError("redirect target contains traversal")
    return urlunsplit(("", "", parsed.path, parsed.query, ""))


def _nonce_digest(nonce: str) -> str:
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


def _encode_record(record: dict[str, object]) -> str:
    raw = json.dumps(record, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_record(value: str) -> dict[str, Any]:
    padding = "=" * ((4 - len(value) % 4) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    result = json.loads(decoded)
    if not isinstance(result, dict):
        raise OAuthStateError("invalid state record")
    return result


@dataclass(frozen=True)
class OAuthStateRecord:
    redirect_to: str
    created_at: int
    code_verifier: str | None = None
    intent: str = "login"
    user: str | None = None
    session_digest: str | None = None
    security_epoch: int = 0
    verified_at: int = 0


class RedisOAuthStateStore:
    """Atomic, site-namespaced OAuth state store backed by Frappe Redis."""

    _CONSUME_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if not value then return nil end
if string.sub(value, 1, 64) ~= ARGV[1] then return false end
redis.call('DEL', KEYS[1])
return value
"""

    def __init__(self, redis_client: Any, *, ttl_seconds: int = STATE_TTL_SECONDS) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    def _key(self, state: str) -> bytes:
        return self.redis.make_key(f"{STATE_PREFIX}{state}")

    def create(
        self,
        *,
        redirect_to: str,
        code_verifier: str | None = None,
        intent: str = "login",
        user: str | None = None,
        session_digest: str | None = None,
        security_epoch: int = 0,
        verified_at: int = 0,
    ) -> tuple[str, str]:
        state = secrets.token_urlsafe(32)
        browser_nonce = secrets.token_urlsafe(32)
        record = OAuthStateRecord(
            redirect_to=validate_redirect_target(redirect_to),
            created_at=int(time.time()),
            code_verifier=code_verifier,
            intent=intent,
            user=user,
            session_digest=session_digest,
            security_epoch=security_epoch,
            verified_at=verified_at,
        )
        value = f"{_nonce_digest(browser_nonce)}.{_encode_record(asdict(record))}"
        created = self.redis.set(
            self._key(state),
            value,
            ex=self.ttl_seconds,
            nx=True,
        )
        if not created:
            raise OAuthStateError("could not allocate OAuth state")
        return state, browser_nonce

    def consume(self, *, state: str, browser_nonce: str) -> OAuthStateRecord:
        if not state or len(state) > 256 or not browser_nonce or len(browser_nonce) > 256:
            raise OAuthStateError("invalid OAuth state")
        result = self.redis.eval(
            self._CONSUME_SCRIPT,
            1,
            self._key(state),
            _nonce_digest(browser_nonce),
        )
        if not result:
            raise OAuthStateError("OAuth state is missing, expired, or browser-bound elsewhere")
        if isinstance(result, bytes):
            result = result.decode("utf-8")
        stored_digest, separator, encoded = str(result).partition(".")
        if not separator or not secrets.compare_digest(stored_digest, _nonce_digest(browser_nonce)):
            raise OAuthStateError("invalid browser binding")
        raw = _decode_record(encoded)
        record = OAuthStateRecord(
            redirect_to=validate_redirect_target(str(raw.get("redirect_to") or "/hbos")),
            created_at=int(raw.get("created_at") or 0),
            code_verifier=str(raw.get("code_verifier") or "") or None,
            intent=str(raw.get("intent") or "login"),
            user=raw.get("user"),
            session_digest=raw.get("session_digest"),
            security_epoch=int(raw.get("security_epoch") or 0),
            verified_at=int(raw.get("verified_at") or 0),
        )
        if record.created_at + self.ttl_seconds < int(time.time()):
            raise OAuthStateError("OAuth state expired")
        return record
