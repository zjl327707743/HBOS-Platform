"""生产看板取数服务的配置——全部来自环境变量。

同 `services/hbos_ocr/app/config.py` 的做法：部署时改环境，不改代码。

**飞书凭据只存在于服务端**。前端永远拿不到 `app_secret`
（见 `docs/frontend/P4_生产看板_取数架构方案对比.md` §2 方案 A 的否决理由）。
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """自动加载服务目录下的 `.env`（若存在）。

    同 `services/hbos_production_ai/app/config.py` 的做法。加这个是因为定时
    预热脚本 `python -m app.warm` 里没有人给它传 `--env-file` —— 没有它就会
    报「飞书凭据未配置」，看起来像配置写错了，实际是环境没进来。

    **已存在的环境变量优先**（真实环境 > .env），所以 uvicorn 的
    `--env-file` 或外面 export 都能覆盖它。不引第三方依赖。
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

#: 结果缓存秒数。**默认 12 小时**（Owner 2026-10-20：一天更新一两次就够）。
#:
#: 早先是 5 分钟 —— 那是按「数据可能在变」设的，但实测上游都是按天更新的：
#: 产量明细按批录入、QC 按天出结论、计划/目标一个月才动一次。5 分钟一刷的
#: 唯一效果是**每隔几分钟撞一次飞书限流**（1254607），把简单的一次打开
#: 拖成几十秒。
#:
#: 12 小时 = 一天最多两次自然过期。另有两道保险：
#:
#:   - `built_on` 跨天必失效 —— 过了零点再访问一定重算（「昨日入库」「本月已过
#:     N 天」是按当天算的，不能沿用昨天的缓存）
#:   - 前端「刷新」按钮仍会 `?refresh=1` 强制重取（那是用户显式要求，属于
#:     「最多两次」里的第二次）
CACHE_TTL_SECONDS = int(os.environ.get("HBOS_PRODUCTION_CACHE_TTL", str(12 * 3600)))

#: 质量合格率的缓存秒数。**默认一天**。
#:
#: 为什么比看板还长：QC 那 4 张表 1000~1200 行，即便并发拉也要 ~50 秒，是冷
#: 缓存总时长的大头；而**质量结论一天最多变一次**（QC 按天录入）。
#:
#: 点「刷新」**不会**重拉它 —— 用户要的是产量/收率/异常的最新值，为一次刷新
#: 多等 50 秒去拉几个月才动一次的数据不划算。当天新录入的 QC 结果会在过期后
#: 出现，`built_on` 保证跨天必重拉，不会连着两天用同一份。
QUALITY_CACHE_TTL_SECONDS = int(
    os.environ.get("HBOS_PRODUCTION_QUALITY_CACHE_TTL", str(24 * 3600))
)

#: 并发拉表的线程数。
#:
#: 看板要拉 14 张表，其中 7 张明细表各有 1500~2000 行（翻 3~4 页，单张 8~10 秒）。
#: **串行实测 57 秒**（点一次刷新要等这么久），并发后压到 ~19 秒。
#:
#: 2026-10-20 从 5 提到 8：接入 QC 表后 `_fetch_all` 实测 39.2s(5) vs 41.1s(8) ——
#: **没有改善**，差异在噪声范围内。原因是总时长由最慢的那几张明细表决定，
#: 再加并发不缩短它们，只会多撞飞书节流（1254607）。留着 8 是因为它不更差，
#: 且表数从 13 涨到 14 后并行度稍高一点更稳；真要提速得减表或做分层缓存。
#: 设 1 = 退回串行（保留开关，便于排查是不是并发引起的问题）。
FETCH_WORKERS = int(os.environ.get("HBOS_PRODUCTION_FETCH_WORKERS", "8"))

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


#: 缓存落盘目录。
#:
#: 内存缓存在**服务重启后就没了** —— 而重启是常事（改代码、机器休眠唤醒）。
#: 每次重启后的第一次访问都要重新拉 18 张飞书表、等 100 秒，这是目前最大的
#: 体验问题。把缓存写一份到磁盘，重启后直接读回来：
#:
#:   - 缓存还新鲜 → 秒开，连后台刷新都不用
#:   - 已过期（跨天）→ **先给旧值秒开**，同时后台刷新（见 `_cached`）
#:
#: 目录默认 `.cache/`（在服务目录下，已在 .gitignore 里）。设空字符串可关闭落盘。
CACHE_DIR = Path(os.environ.get("HBOS_PRODUCTION_CACHE_DIR", ".cache"))
