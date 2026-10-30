"""缓存结构校验的单测 —— `_plausible()` 是白屏的守门人。

背景：缓存落盘后，**任何写进 `.cache/` 的东西下次启动都会被读回内存**。
一份形状不对的缓存（测试造的假数据、手改坏的文件）会让前端崩在
`undefined.slice()` 上，整页白屏且重启不恢复。

所以落盘和恢复前都要过这道校验。校验本身写错，等于这道门不存在。
"""

from __future__ import annotations

import pytest

from app import contract, main


def _row(label: str, **overrides) -> dict:
    row = {
        "label": label,
        "done": 1,
        "target": 2,
        "yieldRate": 0.9,
        "targetYieldRate": 0.91,
        "yesterdayInbound": 12.5,
    }
    row.update(overrides)
    return row


def _rows() -> list[dict]:
    return [_row(label) for label in contract.ROW_MEMBERS]


def _board(**overrides) -> dict:
    value = {"rows": _rows(), "anomaly": {"byWorkshop": [], "windowStart": "2026-10-01"}}
    value.update(overrides)
    return value


# --- 各 key 的正常形状 -------------------------------------------------------


def test_board_accepts_real_shape():
    assert main._plausible("board", _board())


def test_board_rejects_empty_rows():
    """`rows: []` 正是「看板 0 个产品」那个坏缓存的形态。

    早先这条测试把它断言成**合法**（`test_board_accepts_real_shape` 用空数组），
    等于把错误形状固化成正常。真实 `build_rows()` 恒返回六个固定行。
    """
    assert not main._plausible("board", _board(rows=[]))


def test_board_rejects_wrong_label_set():
    rows = _rows()[:-1]           # 少一行
    assert not main._plausible("board", _board(rows=rows))
    rows = _rows() + [_row("不存在")]   # 多一行
    assert not main._plausible("board", _board(rows=rows))


def test_board_rejects_bad_cell_types():
    """任意对象列表不该过关 —— 前端算术拿到 undefined 会算出 NaN。"""
    rows = _rows()
    rows[0]["done"] = "36"
    assert not main._plausible("board", _board(rows=rows))

    rows = _rows()
    rows[1]["target"] = None
    assert not main._plausible("board", _board(rows=rows))

    rows = _rows()
    rows[2]["yieldRate"] = "0.9"
    assert not main._plausible("board", _board(rows=rows))

    rows = _rows()
    rows[3]["yesterdayInbound"] = float("nan")
    assert not main._plausible("board", _board(rows=rows))


def test_board_allows_null_optional_numbers():
    """收率/昨日入库确实可能没有 —— null 是合法值，不能当成坏形状。"""
    rows = _rows()
    rows[0].update({"yieldRate": None, "targetYieldRate": None, "yesterdayInbound": None})
    assert main._plausible("board", _board(rows=rows))


def test_board_rejects_missing_anomaly():
    # 这就是那次白屏的元凶：rows 有、anomaly 是 {} —— 前端 windowStart 为 undefined
    assert not main._plausible("board", {"rows": _rows()})
    assert not main._plausible("board", _board(anomaly="x"))
    # `{}` 也是 dict —— 只判 isinstance 挡不住它（这一条钉住那个坑）
    assert not main._plausible("board", _board(anomaly={}))


def test_quality_accepts_real_shape():
    assert main._plausible("quality", {"byLabel": [], "rate": 1.0})


def test_quality_rejects_missing_bylabel():
    assert not main._plausible("quality", {"rate": 1.0})


def test_ai_accepts_list_of_records():
    """**AI 的缓存值是列表，不是 dict** —— 这条单独立一个用例。

    踩过：`_plausible` 开头写 `if not isinstance(value, dict): return False`，
    `ai` 分支排在后面永远到不了 —— 于是每一轮都判「结构异常」，
    既不恢复也不落盘，这个缓存从头到尾没生效过（日志里反复刷告警才看出来）。
    """
    assert main._plausible("ai", [])
    assert main._plausible("ai", [{"fields": {"产品": "4BMA"}}])


def test_ai_rejects_non_list():
    """AI 缓存若被写成 dict（比如误存成 `{"rows": [...]}`），必须拒。"""
    assert not main._plausible("ai", {"rows": []})
    assert not main._plausible("ai", None)


def test_unknown_key_is_permissive():
    # 未来新增的 key 不该被这条校验误杀
    assert main._plausible("something-new", {"any": "shape"})


# --- 端到端：坏缓存不许落盘、不许恢复 ---------------------------------------


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HBOS_PRODUCTION_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(main.config, "CACHE_DIR", tmp_path)
    main._CACHE.clear()
    yield tmp_path
    main._CACHE.clear()


def test_broken_board_cache_is_not_persisted(cache_dir):
    """形状不对就别写盘 —— 写进去下次启动会读回来，白屏就是这么来的。"""
    main._CACHE["board"] = {
        "value": {"rows": []},          # 缺 anomaly
        "stale_at": 9e18,
        "built_at": 1.0,
        "built_on": None,
    }
    main._persist("board")
    assert not (cache_dir / "board.json").exists()


def test_broken_board_cache_is_not_restored(cache_dir):
    import json
    import time
    from datetime import date

    (cache_dir / "board.json").write_text(
        json.dumps(
            {
                "value": {"rows": [], "anomaly": {}},
                "stale_at": time.time() + 3600,
                "built_at": time.time(),
                "built_on": date.today().isoformat(),
            }
        ),
        encoding="utf-8",
    )
    main._restore("board")
    assert "board" not in main._CACHE, "形状不对的缓存必须丢弃，重新取数"


def test_ai_cache_survives_persist_and_restore(cache_dir):
    """`ai` 走一遍落盘 → 恢复必须通 —— 这是它有没有真正生效的唯一判据。"""
    import time
    from datetime import date

    main._CACHE["ai"] = {
        "value": [{"fields": {"产品": "4BMA"}}],
        "stale_at": time.time() + 3600,
        "built_at": time.time(),
        "built_on": date.today(),
    }
    main._persist("ai")
    assert (cache_dir / "ai.json").exists(), "ai 缓存应当落盘"

    main._CACHE.clear()
    main._restore("ai")
    assert "ai" in main._CACHE
    assert main._CACHE["ai"]["value"][0]["fields"]["产品"] == "4BMA"


def test_restore_rejects_non_numeric_time_fields(cache_dir):
    """`stale_at` 是字符串时必须丢弃 —— 否则 `now >= "x"` 会在请求路径上抛 TypeError。"""
    import json
    from datetime import date

    (cache_dir / "quality.json").write_text(
        json.dumps(
            {
                "value": {"byLabel": [], "rate": 1.0},
                "stale_at": "later",          # 坏类型
                "built_at": 1.0,
                "built_on": date.today().isoformat(),
            }
        ),
        encoding="utf-8",
    )
    main._restore("quality")
    assert "quality" not in main._CACHE


def test_board_cache_survives_persist_and_restore(cache_dir):
    """真实形状必须能落盘并读回 —— 收紧校验不能把正常缓存也挡了。"""
    import time
    from datetime import date

    main._CACHE["board"] = {
        "value": _board(),
        "stale_at": time.time() + 3600,
        "built_at": time.time(),
        "built_on": date.today(),
    }
    main._persist("board")
    assert (cache_dir / "board.json").exists()

    main._CACHE.clear()
    main._restore("board")
    assert "board" in main._CACHE
    assert len(main._CACHE["board"]["value"]["rows"]) == len(contract.ROW_MEMBERS)


def test_plausible_does_not_raise_on_mixed_label_types():
    """坏行里的 `label` 是 None/数字时**必须返回 False，不能抛异常**。

    踩过（复审 2026-10-27）：早先直接 `sorted(labels)`，混入 `None` 时抛
    `TypeError: '<' not supported between 'str' and 'NoneType'` ——
    而 `_persist()` 只捕获 `OSError`，异常会打穿到落盘的 daemon 线程。
    """
    bad = _board(rows=[{"label": None}, {"label": "4BMA"}])
    assert main._plausible("board", bad) is False

    bad = _board(rows=[{"label": 123} for _ in range(len(contract.ROW_MEMBERS))])
    assert main._plausible("board", bad) is False

    bad = _board(rows=["not-a-dict"] * len(contract.ROW_MEMBERS))
    assert main._plausible("board", bad) is False


def test_persist_survives_malformed_cache(tmp_path, monkeypatch):
    """落盘遇到结构异常时只记日志 —— 不能把异常抛到后台线程。"""
    monkeypatch.setattr(main.config, "CACHE_DIR", tmp_path)
    main._CACHE["board"] = {
        "value": {"rows": [{"label": None}], "anomaly": {"byWorkshop": [], "windowStart": "x"}},
        "stale_at": 9e18,
        "built_at": 1.0,
        "built_on": None,
    }
    main._persist("board")          # 不抛
    assert not (tmp_path / "board.json").exists()
