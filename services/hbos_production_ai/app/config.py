"""AI 分析服务的配置——全部来自环境变量。

**本服务有自己的 `.env`**（Owner 2026-10-02 选 B），与仓库根 `.env` 的
`HBOS_AI_*`（考勤模块用）**不共用** —— 两者互不影响。

变量名沿用仓库既有约定（`HBOS_AI_*`，见根 `.env.example`），只是值各存一份。
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """自动加载服务目录下的 `.env`（若存在）。

    加这个是因为踩过一次：直接 `python -m app.main` 时环境变量没进来，
    报的是「模型未配置」—— 看起来像配置写错了，实际是没带 `--env-file`。

    **已存在的环境变量优先**（真实环境 > .env），所以 launchd 传
    `--env-file` 或外面 export 都能覆盖它。不引第三方依赖 —— 格式简单，
    hand-rolled 足够（只认 `KEY=VALUE`、`#` 注释、成对引号）。
    """
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ---------------------------------------------------------------------------
# 模型（OpenAI 兼容端点）
# ---------------------------------------------------------------------------

#: 服务启用开关。默认关 —— 分析会花 token，不该在没打算跑的时候偷跑。
AI_ENABLED = os.environ.get("HBOS_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}

#: 端点基址（形如 `https://xxx/v1`）。
AI_BASE_URL = (os.environ.get("HBOS_AI_BASE_URL") or "").rstrip("/")

#: 密钥。**绝不进仓库**。
AI_API_KEY = os.environ.get("HBOS_AI_API_KEY") or ""

#: 模型名。**不硬编码** —— 历史上有过模型被上游下线、名字失效的先例
#: （见 docs/milestones/M1_FIX_F_调休模块第一阶段落地记录.md:218）。
AI_MODEL = os.environ.get("HBOS_AI_MODEL") or ""

#: 单次请求超时（秒）。台账可能上百字段，prompt 很长，给足。
AI_TIMEOUT = int(os.environ.get("HBOS_AI_TIMEOUT", "180"))

#: 单产品分析的最大重试次数。
AI_RETRIES = int(os.environ.get("HBOS_AI_RETRIES", "2"))

#: 采样温度。**默认不发**（None）—— 推理模型（如 gpt-5.6-sol）不接受这个参数，
#: 传了会被上游直接 400。要用非推理模型时可显式设：
#:   HBOS_AI_TEMPERATURE=0.2
_t = (os.environ.get("HBOS_AI_TEMPERATURE") or "").strip()
AI_TEMPERATURE: float | None = float(_t) if _t else None

# ---------------------------------------------------------------------------
# 飞书
# ---------------------------------------------------------------------------

FEISHU_APP_ID = os.environ.get("HBOS_FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("HBOS_FEISHU_APP_SECRET", "")
FEISHU_BASE = os.environ.get("HBOS_FEISHU_BASE", "https://open.feishu.cn")
FEISHU_TIMEOUT = int(os.environ.get("HBOS_FEISHU_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# 分析范围
# ---------------------------------------------------------------------------

#: 只分析这些产品（逗号分隔）。**第一版只跑 4BMA**（Owner 2026-10-02 定）。
#:
#: 留空 = 分析全部在产产品。放开前应先验证输出质量 ——
#: AI 结论会直接进看板给车间经理看，且**不做人工确认**。
AI_PRODUCTS = [
    p.strip() for p in os.environ.get("HBOS_AI_PRODUCTS", "4BMA").split(",") if p.strip()
]

#: 喂给模型的最大台账批数（取最近的 N 批）。
#: 台账有 1200+ 行，全喂会撑爆上下文且没必要 —— 分析看的是近期工艺稳定性。
AI_MAX_BATCHES = int(os.environ.get("HBOS_AI_MAX_BATCHES", "30"))

# ---------------------------------------------------------------------------
# 其他
# ---------------------------------------------------------------------------

LOG_LEVEL = os.environ.get("HBOS_AI_LOG_LEVEL", "INFO")

#: 只跑不写。用于验证输出质量时避免污染结果表。
DRY_RUN = os.environ.get("HBOS_AI_DRY_RUN", "0").strip().lower() in {"1", "true", "yes", "on"}


def llm_configured() -> bool:
    return bool(AI_BASE_URL and AI_API_KEY and AI_MODEL)


def feishu_configured() -> bool:
    return bool(FEISHU_APP_ID and FEISHU_APP_SECRET)
