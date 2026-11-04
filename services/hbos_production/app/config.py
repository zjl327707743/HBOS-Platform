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

#: 并发拉表的线程数。
#:
#: 看板要拉 13 张表，其中 7 张明细表各有 1500~2000 行（翻 3~4 页，单张 8~10 秒）。
#: **串行实测 57 秒**（点一次刷新要等这么久），并发后压到 ~19 秒。
#:
#: 定 5 而不是更高：实测 5 与 8 的用时几乎一样（18.9s vs 18.0s）—— 总时长由
#: 最慢的那张表决定，再高的并发不缩短它，白白多撞飞书节流。
#: 设 1 = 退回串行（保留开关，便于排查是不是并发引起的问题）。
FETCH_WORKERS = int(os.environ.get("HBOS_PRODUCTION_FETCH_WORKERS", "5"))

#: 服务间令牌 —— HBOS 受控后端调用本服务时必须带 `X-HBOS-Service-Token`。
#:
#: 本服务不再由浏览器直连（改为 `Portal → HBOS 受控后端 → 本服务`），
#: 所有数据端点都要求该请求头与本值一致。
#:
#: **留空 = 拒绝所有数据请求**（默认拒绝）——
#: 不允许「没配令牌就跑匿名」，那样等于把生产数据裸奔。
#: 与后端 `frappe.conf` 的 `hbos_production_service_token` 必须一致。
SERVICE_TOKEN = os.environ.get("HBOS_PRODUCTION_SERVICE_TOKEN", "")

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
