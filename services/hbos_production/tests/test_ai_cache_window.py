"""AI 结果缓存的过期时刻 —— 不是固定 TTL，是「下一个 16:35」。

## 为什么不用固定 TTL

AI 结果表**只在每天 16:30 那轮定时任务里变**，其余时间一动不动。
按固定间隔算 TTL 两头都不对：

    30 分钟 → 一天过期 48 次，其中 47 次拿到一模一样的数据（白拉）
    12 小时 → 16:30 写进去的新结论当天看不到（要等次日凌晨）

正确做法：缓存活到**下一个 16:35**（16:30 开跑，跑一轮 ~24 分钟，留 5 分钟余量）。
10:00 建的缓存活 6.5 小时；16:40 建的缓存活 24 小时。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app import config


def _ts(y, mo, d, h, mi, s=0) -> float:
    return datetime(y, mo, d, h, mi, s).timestamp()


@pytest.fixture(autouse=True)
def _fixed_refresh_time(monkeypatch):
    monkeypatch.setattr(config, "AI_REFRESH_HOUR", 16)
    monkeypatch.setattr(config, "AI_REFRESH_MINUTE", 35)


def test_before_refresh_expires_today():
    """10:00 建的缓存 → 当天 16:35 失效（约 6.6 小时）。"""
    now = _ts(2026, 10, 27, 10, 0)
    left = config.seconds_until_ai_refresh(now)
    assert left == pytest.approx(6.6 * 3600, abs=120)


def test_after_refresh_expires_tomorrow():
    """16:40 建的缓存 → 次日 16:35 失效（约 24 小时，不是 23），
    这样第二天 16:30 跑完、16:35 之后才是新结论。"""
    now = _ts(2026, 10, 27, 16, 40)
    left = config.seconds_until_ai_refresh(now)
    assert left == pytest.approx(23 * 3600 + 55 * 60, abs=120)


def test_exactly_at_refresh_time_rolls_to_tomorrow():
    """正好 16:35:00 建的缓存 → 活到次日 16:35，不能算出 0 秒。"""
    now = _ts(2026, 10, 27, 16, 35, 0)
    left = config.seconds_until_ai_refresh(now)
    assert left >= 23 * 3600


def test_never_returns_too_small():
    """任何时刻都不该给出很短的值 —— 否则建完立刻过期，每次请求都重拉。

    这是 CLAUDE 里那条 `max(60.0, ...)` 的下限保护。
    """
    for minute in (34, 35, 36):
        now = _ts(2026, 10, 27, 16, minute)
        assert config.seconds_until_ai_refresh(now) >= 60


def test_custom_refresh_time_is_respected(monkeypatch):
    """定时任务改时刻时，只改配置就能跟上（不用改代码）。"""
    monkeypatch.setattr(config, "AI_REFRESH_HOUR", 8)
    monkeypatch.setattr(config, "AI_REFRESH_MINUTE", 0)
    now = _ts(2026, 10, 27, 7, 0)
    assert config.seconds_until_ai_refresh(now) == pytest.approx(3600, abs=60)


def test_refresh_time_matches_launchd_schedule():
    """默认值必须与定时任务的实际时刻对得上，否则缓存过期点会错位。

    `services/hbos_production_ai/launchd/*.plist` 里是 16:30 跑。
    这里断言 16:3x —— 改了 plist 就要同步改 config，这条会挡住忘记改的情况。
    """
    assert config.AI_REFRESH_HOUR == 16
    assert 30 <= config.AI_REFRESH_MINUTE <= 40, "应比 plist 晚几分钟（等写完）"
