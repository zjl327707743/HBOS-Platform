from __future__ import annotations

# Messages are fixed. Exception details, IDs, paths and upstream bodies never escape.
ERRORS = {
    "INVALID_REQUEST": (400, "请求格式无效。", False),
    "AUTHENTICATION_REQUIRED": (401, "需要有效登录。", False),
    "CLIENT_AUTH_FAILED": (401, "客户端认证无效。", False),
    "SCOPE_REJECTED": (403, "当前请求不可访问。", False),
    "EMPTY_SCOPE": (403, "当前没有可用授权资料。", False),
    "DECISION_EXPIRED": (409, "授权决定已失效，请重新请求。", True),
    "REPLAY_REJECTED": (409, "请求标识已用于其他请求。", False),
    "EVIDENCE_UNAVAILABLE": (404, "该证据不可用或已失效。", False),
    "POLICY_UNAVAILABLE": (503, "授权服务暂时不可用。", True),
    "SCOPE_FILTER_UNSUPPORTED": (503, "授权过滤暂时不可用。", True),
    "UPSTREAM_UNAVAILABLE": (503, "检索服务暂不可用，目录与个人记录仍可查看。", True),
    "UPSTREAM_SCOPE_VIOLATION": (502, "知识服务权限校验失败。", False),
    "UPSTREAM_INVALID_RESULT": (502, "知识服务返回无效。", False),
    "MODEL_NOT_APPROVED": (503, "回答能力尚未获准。", False),
    "RATE_LIMITED": (429, "请求较频繁，请稍后重试。", True),
    "EXTRACTION_LIMITED": (429, "本时段可展示的摘录已达上限。", True),
    "SERVICE_ERROR": (503, "知识服务暂时不可用。", True),
}

class KnowledgeError(Exception):
    def __init__(self, code: str, public_message: str | None = None, retryable: bool | None = None):
        if code not in ERRORS:
            code = "SERVICE_ERROR"
        self.code = code
        self.status, self.public_message, self.retryable = ERRORS[code]
        super().__init__(self.public_message)

def error_payload(error: KnowledgeError, request_id: str = "request-unavailable") -> dict:
    return {"ok": False, "error": {"code": error.code, "message": error.public_message,
            "retryable": error.retryable, "request_id": request_id}}
