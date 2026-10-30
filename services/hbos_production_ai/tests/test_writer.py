"""写回结果表的单测 —— 幂等 + 清理失效行。

幂等那部分（不重复追加）是 openclaw 踩过的坑；清理那部分是 2026-10-27 补的：
工序改名/拆分/合并/从工艺描述删除后，旧行会一直留在表里被看板读出来，
展示已废止工序的评级和建议。

全部用假的飞书客户端，不打网络。
"""

from __future__ import annotations

import pytest

from app import feishu, writer


@pytest.fixture
def fake_table(monkeypatch):
    """内存版结果表：`record_id -> fields`，按创建顺序保存。"""
    table: dict[str, dict] = {}
    seq = {"n": 0}
    calls: list[tuple[str, str, str]] = []

    def list_records(base, tid, page_size=500):
        return [
            {"record_id": rid, "fields": dict(fields)}
            for rid, fields in table.items()
        ]

    def create_record(base, tid, fields):
        seq["n"] += 1
        rid = f"rec{seq['n']}"
        table[rid] = dict(fields)
        calls.append(("create", rid, fields.get("工序", "")))
        return rid

    def update_record(base, tid, rid, fields):
        table[rid] = dict(fields)
        calls.append(("update", rid, fields.get("工序", "")))

    def delete_record(base, tid, rid):
        table.pop(rid, None)
        calls.append(("delete", rid, ""))

    monkeypatch.setattr(feishu, "list_records", list_records)
    monkeypatch.setattr(feishu, "create_record", create_record)
    monkeypatch.setattr(feishu, "update_record", update_record)
    monkeypatch.setattr(feishu, "delete_record", delete_record)
    return table, calls


def _record(process: str, fp: str = "fp1", product: str = "4BMA") -> dict:
    return {"产品": product, "工序": process, "数据指纹": fp, "结论摘要": "x"}


def test_second_run_with_same_fingerprint_skips(fake_table):
    table, calls = fake_table
    writer.write_results([_record("活化"), _record("精制")], "fp1")
    result = writer.write_results([_record("活化"), _record("精制")], "fp1")

    assert result["created"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 2
    assert len(table) == 2


def test_changed_fingerprint_updates_in_place(fake_table):
    table, _ = fake_table
    writer.write_results([_record("活化")], "fp1")
    writer.write_results([_record("活化", fp="fp2")], "fp2")

    assert len(table) == 1, "同一 (产品, 工序) 不该新增第二行"
    assert next(iter(table.values()))["数据指纹"] == "fp2"


def test_stale_process_is_removed_when_process_list_shrinks(fake_table):
    """工序改名/删除后，旧行必须清理 —— 否则看板一直展示已废止工序。"""
    table, calls = fake_table
    writer.write_results(
        [_record("活化"), _record("精制"), _record("结晶")],
        "fp1",
        valid_processes=["活化", "精制", "结晶"],
    )
    assert len(table) == 3

    result = writer.write_results(
        [_record("活化"), _record("精制")],
        "fp2",
        valid_processes=["活化", "精制"],
    )

    assert result["removed"] == 1
    assert sorted(f["工序"] for f in table.values()) == ["活化", "精制"]
    assert ("delete", "rec3", "") in calls


def test_stale_cleanup_only_touches_current_products(fake_table):
    """清理只针对本次分析的产品 —— 别把别的产品的行删了。"""
    table, _ = fake_table
    writer.write_results(
        [_record("活化"), _record("精制", product="F9")],
        "fp1",
        valid_processes=["活化", "精制"],
    )
    writer.write_results([_record("活化")], "fp2", valid_processes=["活化"])

    remaining = sorted((f["产品"], f["工序"]) for f in table.values())
    assert remaining == [("4BMA", "活化"), ("F9", "精制")]


def test_duplicate_rows_are_collapsed(fake_table):
    table, calls = fake_table
    # 模拟历史上被追加出来的重复行
    table["recA"] = {"产品": "4BMA", "工序": "活化", "数据指纹": "old", "结论摘要": "old-A"}
    table["recB"] = {"产品": "4BMA", "工序": "活化", "数据指纹": "old", "结论摘要": "old-B"}

    result = writer.write_results([_record("活化", fp="fp9")], "fp9", valid_processes=["活化"])

    assert len(table) == 1, "重复行必须收敛成一条"
    assert result["removed"] == 1
    # **留下的必须是新写的那条**，不是最旧的副本。
    # 踩过：`keys` 指向最后一条（被更新），`duplicates` 却收「除第一条外的全部」
    # —— 最后一条同时被更新又删除，留下的是最旧的 old-A，而报告说 updated=1。
    survivor = next(iter(table.values()))
    assert survivor["数据指纹"] == "fp9", f"留下的仍是旧指纹：{survivor}"
    assert survivor["结论摘要"] == "x", f"留下的仍是旧摘要：{survivor}"


def test_three_duplicates_keep_the_newest(fake_table):
    """三条重复时，保留更新的那条，删掉另外两条。"""
    table, _ = fake_table
    for i, rid in enumerate(("recA", "recB", "recC")):
        table[rid] = {"产品": "4BMA", "工序": "活化", "数据指纹": "old", "结论摘要": f"old-{i}"}

    result = writer.write_results([_record("活化", fp="new")], "new", valid_processes=["活化"])

    assert result["removed"] == 2
    assert len(table) == 1
    survivor = next(iter(table.values()))
    assert survivor["数据指纹"] == "new"
    assert survivor["结论摘要"] == "x"


def test_duplicate_cleanup_skipped_when_fingerprint_unchanged(fake_table):
    """指纹没变时不重写，但重复行仍要收敛，且留下的那条指纹不变。"""
    table, _ = fake_table
    table["recA"] = {"产品": "4BMA", "工序": "活化", "数据指纹": "same", "结论摘要": "keep"}
    table["recB"] = {"产品": "4BMA", "工序": "活化", "数据指纹": "same", "结论摘要": "keep"}

    result = writer.write_results(
        [_record("活化", fp="same")], "same", valid_processes=["活化"]
    )

    assert result["skipped"] == 1
    assert result["updated"] == 0
    assert result["removed"] == 1
    assert len(table) == 1


def test_duplicate_cleanup_in_dry_run_deletes_nothing(fake_table):
    table, calls = fake_table
    table["recA"] = {"产品": "4BMA", "工序": "活化", "数据指纹": "old"}
    table["recB"] = {"产品": "4BMA", "工序": "活化", "数据指纹": "old"}

    result = writer.write_results(
        [_record("活化", fp="new")], "new", dry_run=True, valid_processes=["活化"]
    )

    assert result["removed"] == 1
    assert len(table) == 2, "dry-run 不许删"
    assert not [c for c in calls if c[0] == "delete"]


def test_dry_run_deletes_nothing(fake_table):
    table, calls = fake_table
    writer.write_results([_record("活化"), _record("精制")], "fp1", valid_processes=["活化", "精制"])
    before = dict(table)

    result = writer.write_results([_record("活化", fp="fp2")], "fp2", dry_run=True, valid_processes=["活化"])

    assert table == before, "dry-run 不许真删"
    assert result["removed"] == 1, "但统计上要报出会删几条"
    assert not [c for c in calls if c[0] == "delete"]


def test_delete_failure_does_not_abort_the_run(fake_table, monkeypatch):
    """清理失败不该让整轮失败 —— 结果已经写进去了。"""
    table, _ = fake_table
    writer.write_results([_record("活化"), _record("精制")], "fp1", valid_processes=["活化", "精制"])

    def boom(*a, **kw):
        raise feishu.FeishuError(1254000, "cannot delete")

    monkeypatch.setattr(feishu, "delete_record", boom)

    result = writer.write_results([_record("活化", fp="fp2")], "fp2", valid_processes=["活化"])
    assert result["removed"] == 0
    assert any(f["工序"] == "活化" for f in table.values())


def test_cleanup_failure_is_reported(fake_table, monkeypatch):
    """失效行删不掉时必须**上报**，不能只记日志。

    踩过（复审 2026-10-27）：删除失败只 `log.warning`，`write_results` 仍返回
    正常统计、`analyze_product` 仍返回 `ok`，退出码 0 —— 废行继续留在结果表里
    被看板读到，而调度系统显示整轮成功。
    """
    table, _ = fake_table
    writer.write_results([_record("活化"), _record("精制")], "fp1", valid_processes=["活化", "精制"])

    def boom(*a, **kw):
        raise feishu.FeishuError(1254000, "cannot delete")

    monkeypatch.setattr(feishu, "delete_record", boom)

    result = writer.write_results([_record("活化", fp="fp2")], "fp2", valid_processes=["活化"])
    assert result["removed"] == 0
    assert len(result["cleanupFailed"]) == 1
    entry = result["cleanupFailed"][0]
    assert entry["process"] == "精制"
    assert entry["recordId"]
