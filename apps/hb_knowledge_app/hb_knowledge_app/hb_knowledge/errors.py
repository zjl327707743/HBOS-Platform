from __future__ import annotations

# Messages are fixed. Exception details, IDs, paths and upstream bodies never escape.
ERRORS = {
    "MODEL_TRANSPORT_FAILURE": (503,"回答服务连接失败，请稍后重新提交。检索和个人记录仍可使用。",True),
    "MODEL_REQUEST_FORMAT": (502,"回答服务未接受请求格式，请联系维护人。",False),
    "ANSWER_SCHEMA_INVALID": (502,"回答格式未通过校验，本次未展示回答。请重新提交或查阅来源。",True),
    "CITATION_SUPPORT_FAILED": (422,"回答未通过来源支持校验，本次未展示回答。请查阅来源或调整问题。",True),
    "RETRIEVAL_EMPTY": (404,"没有找到可核实的公司依据，请调整关键词或资料范围。",False),
    "RETRIEVAL_UPSTREAM_FAILED": (503,"资料检索暂时失败，请稍后重试；目录和个人记录仍可查看。",True),
    "SOURCE_VERSION_STALE": (409,"来源已换版、下架或授权变化，请重新检索并核对当前来源。",True),
    # One display-unsafe source excerpt is skipped per record; this code is only
    # returned when every candidate source fails the safety projection, so it is
    # never confused with an upstream outage or "no content".
    "SOURCE_CONTENT_UNSAFE": (502,"部分来源内容未通过安全展示检查，可联系维护者复核。",False),
    "MODEL_UNAVAILABLE": (503,"所选模型配置尚未核验或已撤销，暂不可用。未自动切换其他模型。",False),
    "MODEL_REQUEST_INVALID": (502,"模型服务拒绝了请求格式；请联系维护人核对模型协议。",False),
    "MODEL_AUTH_FAILED": (502,"模型服务认证或授权失败；请联系维护人核对服务端配置。",False),
    "MODEL_RATE_LIMITED": (429,"所选模型当前限流，请稍后重新提交。未自动重试或切换模型。",True),
    "MODEL_SERVICE_FAILED": (503,"所选模型服务故障，请稍后重新提交。未自动重试或切换模型。",True),
    "IMPORT_BUSY": (409,"该批次正在处理，请等待本次完成。",True),
    # Batch planning/submission keeps the preview and the frozen batch distinct:
    # a preview that still has conflicts cannot enqueue, and a preview whose
    # registry evidence has drifted cannot silently freeze old decisions.
    "BATCH_PLAN_BLOCKED": (409,"预演清单仍有冲突、异常或不可编排项，请修正后重新预演。",False),
    "BATCH_PLAN_STALE": (409,"预演与当前资料状态已不一致，请重新预演后再提交。",True),
    "BATCH_DERIVATIVE_ROOT_UNCONFIGURED": (503,"批量入库的派生文件共享目录尚未配置，提交未执行。",False),
    # File/plan size limits are separate decisions: a source-file limit is not
    # a reverse-proxy body limit and not the manifest body limit.
    "SOURCE_SIZE_LIMIT_EXCEEDED": (413,"资料原件超过当前允许的单文件上限，请按配置上限处理后重试。",False),
    "BATCH_SOURCE_SIZE_LIMIT_EXCEEDED": (413,"本批原件的总字节数超过批量上限，请拆分为更小的批次。",False),
    "MANIFEST_SIZE_LIMIT_EXCEEDED": (413,"清单文件体量超过独立上限，请拆分清单；该上限与原件尺寸无关。",False),
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
    "ANSWER_MODEL_UNAVAILABLE": (503, "回答服务暂时不可用，请稍后重试；检索和个人记录仍可使用。", True),
    "ANSWER_BUDGET_BLOCKED": (503, "回答费用待核验或预算不可用，回答已暂停；目录、来源和个人记录仍可查看。", False),
    "RATE_LIMITED": (429, "请求较频繁，请稍后重试。", True),
    "EXTRACTION_LIMITED": (429, "本时段可展示的摘录已达上限。", True),
    "SERVICE_ERROR": (503, "知识服务暂时不可用。", True),
    # A separate controlled use case from the 500-codepoint evidence excerpt.
    # The public message is fixed; the optional ``state`` names only an
    # enumerated, non-sensitive reason (never an id, path or upstream address).
    "DOCUMENT_READ_UNAVAILABLE": (404, "该资料暂不可阅读或授权已变化，请重新检索。", False),
    "DOCUMENT_READ_PAGE_OUT_OF_RANGE": (400, "页码超出该资料的可阅读范围。", False),
    "DOCUMENT_DELIVERY_UNAVAILABLE": (403, "该资料暂不可预览或下载，请核对权限、版本或稍后重试。", False),
    "DOCUMENT_RANGE_NOT_SATISFIABLE": (416, "请求的文件范围无效或超过单次上限。", False),
}

class KnowledgeError(Exception):
    def __init__(self, code: str, public_message: str | None = None,
                 retryable: bool | None = None, *, state: str | None = None):
        if code not in ERRORS:
            code = "SERVICE_ERROR"
        self.code = code
        self.status, self.public_message, self.retryable = ERRORS[code]
        # Enumerated safe reason for the client's wording choice only.
        self.state = state
        super().__init__(self.public_message)

def error_payload(error: KnowledgeError, request_id: str = "request-unavailable") -> dict:
    payload = {"ok": False, "error": {"code": error.code, "message": error.public_message,
               "retryable": error.retryable, "request_id": request_id}}
    if getattr(error, "state", None) is not None:
        payload["error"]["state"] = error.state
    return payload
