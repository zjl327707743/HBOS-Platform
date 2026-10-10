"""生产看板取数服务的配置——全部来自环境变量。

同 `services/hbos_ocr/app/config.py` 的做法：部署时改环境，不改代码。

**飞书凭据只存在于服务端**。前端永远拿不到 `app_secret`
（见 `docs/frontend/P4_生产看板_取数架构方案对比.md` §2 方案 A 的否决理由）。
"""

from __future__ import annotations

import os

#: 监听地址与端口。
#: 默认绑 **127.0.0.1** —— 只允许本机访问，不开外网。
#: 8100 已被 hbos_ocr 占用，本服务用 8101。
HOST = os.environ.get("HBOS_PRODUCTION_HOST", "127.0.0.1")
PORT = int(os.environ.get("HBOS_PRODUCTION_PORT", "8101"))

#: 飞书自建应用凭据。**绝不进仓库**（`.env` 已 gitignore）。
FEISHU_APP_ID = os.environ.get("HBOS_FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("HBOS_FEISHU_APP_SECRET", "")

#: 飞书 OpenAPI 基址。
FEISHU_BASE = os.environ.get("HBOS_FEISHU_BASE", "https://open.feishu.cn")

#: 上游请求超时（秒）。
TIMEOUT_SECONDS = int(os.environ.get("HBOS_PRODUCTION_TIMEOUT", "30"))

#: 结果缓存秒数。看板是「看一眼就走」的场景，不需要每次请求都打飞书。
#: 默认 300 秒（5 分钟）—— 比数据本身的更新频率（天）细得多，不会读到过期数据。
CACHE_TTL_SECONDS = int(os.environ.get("HBOS_PRODUCTION_CACHE_TTL", "300"))

#: 日志级别。日志**不记录凭据**。
LOG_LEVEL = os.environ.get("HBOS_PRODUCTION_LOG_LEVEL", "INFO")

#: 允许跨源访问的前端源（逗号分隔）。
#:
#: 开发默认只放本机 Vite 端口。**部署到服务器时必须改** ——
#: 改成看板的实际域名，否则浏览器会因 CORS 拦掉请求。
#: 例：HBOS_PRODUCTION_CORS_ORIGINS=https://hbos.example.com
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "HBOS_PRODUCTION_CORS_ORIGINS",
        "http://127.0.0.1:5178,http://127.0.0.1:5179,http://localhost:5178,http://localhost:5179",
    ).split(",")
    if o.strip()
]


def feishu_configured() -> bool:
    """凭据是否齐备。未配置时接口返回 503 —— 而不是编造数据。"""
    return bool(FEISHU_APP_ID and FEISHU_APP_SECRET)
