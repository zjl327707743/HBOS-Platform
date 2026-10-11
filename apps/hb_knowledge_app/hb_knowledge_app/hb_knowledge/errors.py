from __future__ import annotations

# Messages are fixed. Exception details, IDs, paths and upstream bodies never escape.
ERRORS = {
    "MODEL_UNAVAILABLE": (503,"所选模型配置尚未核验或已撤销，暂不可用。未自动切换其他模型。",False),
    "MODEL_REQUEST_INVALID": (502,"模型服务拒绝了请求格式；请联系维护人核对模型协议。",False),
    "MODEL_AUTH_FAILED": (502,"模型服务认证或授权失败；请联系维护人核对服务端配置。",False),
    "MODEL_RATE_LIMITED": (429,"所选模型当前限流，请稍后重新提交。未自动重试或切换模型。",True),
    "MODEL_SERVICE_FAILED": (503,"所选模型服务故障，请稍后重新提交。未自动重试或切换模型。",True),
    "IMPORT_BUSY": (409,"该批次正在处理，请等待本次完成。",True),
    "IDENTITY_CONFLICT": (409,"文件与现有身份或当前版本冲突，请选择明确的换版关系。",False),
    "QUALITY_REQUIRED": (409,"请先完成本版本的质量核对。",False),
    "IMPORT_BUDGET_BLOCKED": (503,"解析费用待核验或预算不可用，解析已暂停；质量核对、发布和下架仍可操作。",False),
    "INVALID_REQUEST": (400, "请求格式无效。", False),
    "AUTHENTICATION_REQUIRED": (401, "需要有效登录。", False),
    "CLIENT_AUTH_FAILED": (401, "客户端认证无效。", False),
    "SCOPE_REJECTED": (403, "当前请求不可访问。", False),
    "ORIGINAL_ACCESS_DENIED": (403, "不能提供未授权资料或原件。请只查询已共享且有权查阅的资料。", False),
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
    "ANSWER_MODEL_UNAVAILABLE": (503, "回答模型暂时不可用或未通过依据校验。请稍后重试；检索和记录仍可使用。", True),
    "ANSWER_BUDGET_BLOCKED": (503, "回答费用待核验或预算不可用，回答已暂停；目录、来源和个人记录仍可查看。", False),
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
