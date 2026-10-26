"""测试全局隔离 —— **别让测试写真实缓存目录**。

踩过的坑（2026-10-26）：`board.json` 里出现 `{"rows": [], "anomaly": {}}`、
`built_on: "2026-10-12"` —— 那是测试造的假数据被**落盘**了。

后果不是测试失败，而是**看板白屏**：
服务启动时 `_restore()` 把这个假缓存读回内存，`rows` 是空数组 → 前端
`board.rows.length` 为 0；`anomaly` 是 `{}` → `anomaly.windowStart.slice(0,7)`
抛 `Cannot read properties of undefined`，整个页面卡在「正在取生产数据」。

而且它**看起来完全像服务的问题**（重启也没用 —— 缓存是从磁盘读回来的），
排查方向会被带偏很久。

所以这条隔离放在 conftest 里，对所有用例生效：任何测试都不许写
`services/hbos_production/.cache/`。要测落盘行为的用例自己 monkeypatch
到 tmp_path（见 test_cache_persist.py / test_warm.py）。
"""

from __future__ import annotations

import pytest

from app import config


@pytest.fixture(autouse=True)
def _no_real_cache_dir(tmp_path, monkeypatch):
    """把缓存目录指向临时目录，并清空内存缓存。

    autouse：**所有**用例都套用。落盘是后台线程，任何一个用例碰到
    `_store` 都会写盘 —— 逐个用例记得加隔离不现实。

    ⚠️ **两个都要设**：`test_board_freshness._client` 里有
    `importlib.reload(config)` —— 模块重载会把 `CACHE_DIR` 从环境变量
    重新读一遍，只 monkeypatch 属性会被重置回 `.cache`（实测：加了
    fixture 之后测试仍照写不误）。所以环境变量也必须指到 tmp_path。
    """
    monkeypatch.setenv("HBOS_PRODUCTION_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)

    from app import main

    main._CACHE.clear()
    yield
    main._CACHE.clear()
