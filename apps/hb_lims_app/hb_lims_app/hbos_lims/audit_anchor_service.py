# -*- coding: utf-8 -*-
"""M2 审计锚定（L10-P0-02）：把审计历史的整体摘要写到**数据库之外**的 append-only 文件。

为什么需要：`HBOS Audit Log` 的 checksum 与内容同库同行，具备 DB 直写权限的人可以同时
改写两者 —— 单靠 checksum 只能检出应用级误改。把「全量行数 + 整体摘要」写到 DB 之外的
文件后，删行 / 改行都会在下次对账时暴露（改内容必然改逐行 checksum，进而改整体摘要）。

能证明什么：**锚定点之前**的审计历史未被整体改动 —— 行数变少（删除）或任一行的
name/created_at/checksum 变化（改写、插入、重排）都会使重算摘要与锚定不符。

不能证明什么（不得据此宣称强防篡改）：
- 主机级权限（root / 容器）可同时改 DB 与锚定文件；
- 锚定文件是本机文件，不是远端存证；最新一行与其后的新增行尚未被锚定；
- 锚定只覆盖"点"，两点之间的改动要靠下一行的链与摘要比对收敛。
"""

import hashlib
import json
import os

import frappe

from hb_lims_app.hbos_lims import workflow_contract as wf

ANCHOR_FILENAME = "hbos_audit_anchor.log"
_ANCHOR_GENESIS = "genesis"
_CHUNK = 2000


def _user():
	return frappe.session.user


def _check_action(action):
	roles = frappe.get_roles(_user())
	if not any(wf.action_allowed(action, role) for role in roles):
		frappe.throw("当前用户（{}）没有执行「{}」的权限。".format(_user(), action))


def anchor_path():
	"""锚定文件路径：bench 的 `logs/` 目录（独立于数据库的卷）。"""
	return os.path.join(frappe.utils.get_bench_path(), "logs", ANCHOR_FILENAME)


def history_digest(limit=None):
	"""全量审计历史的整体指纹（分块计算，结果与分块方式无关）。

	按 `(created_at, name)` 升序逐行累加 `name|created_at|checksum`。`limit` 限定只
	累积前 N 行 —— 对账时用它重算"锚定点之前"的那一段，从而不受锚定之后新增行影响。
	"""
	digest = hashlib.sha256(b"hbos-audit-history-v1")
	offset = 0
	while limit is None or offset < limit:
		batch = _CHUNK if limit is None else min(_CHUNK, limit - offset)
		rows = frappe.get_all("HBOS Audit Log",
							  fields=["name", "created_at", "checksum"],
							  order_by="created_at asc, name asc",
							  limit_start=offset, limit_page_length=batch)
		if not rows:
			break
		for row in rows:
			digest.update("{}|{}|{}".format(
				row.name, row.created_at or "", row.checksum or "").encode("utf-8"))
		offset += len(rows)
		if len(rows) < batch:
			break
	return digest.hexdigest()


def _read_anchor_lines(path):
	"""读取锚定行；忽略空行与无法解析的行（解析失败的行由链校验暴露为断裂）。"""
	lines = []
	if not os.path.exists(path):
		return lines
	with open(path, encoding="utf-8") as handle:
		for raw in handle:
			raw = raw.strip()
			if not raw:
				continue
			try:
				lines.append(json.loads(raw))
			except ValueError:
				lines.append({"_unparsable": raw})
	return lines


def _anchor_hash(prev_hash, rows, digest, source):
	return hashlib.sha256("|".join(
		[prev_hash, str(rows), digest, source]).encode("utf-8")).hexdigest()


def write_anchor_at(path=None, source="scheduled"):
	"""追加一行锚定记录（时间、来源、行数、整体摘要、前一锚定哈希、本行锚定哈希）。

	锚定行之间也串链：改动历史锚定行会破坏链。`path` 仅供测试指定；生产走默认路径。
	"""
	path = path or anchor_path()
	previous = _read_anchor_lines(path)
	prev_hash = previous[-1].get("anchor", _ANCHOR_GENESIS) if previous else _ANCHOR_GENESIS
	rows = frappe.db.count("HBOS Audit Log")
	digest = history_digest()
	line = {
		"at": str(frappe.utils.now()),
		"source": source,
		"rows": rows,
		"digest": digest,
		"prev": prev_hash,
		"anchor": _anchor_hash(prev_hash, rows, digest, source),
	}
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "a", encoding="utf-8") as handle:
		handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
	return dict(line, path=path)


def verify_anchor_at(path=None):
	"""对账（可指定路径，供测试）：锚定链完整 + 锚定点之前的历史未被改动。

	返回 {"ok", "anchors", "last_at", "anchored_rows", "current_rows", "reason"}。
	新增行不影响结论（只重算锚定点之前那一段）；行数变少或该段摘要不符即为不一致。
	"""
	path = path or anchor_path()
	lines = _read_anchor_lines(path)
	if not lines:
		return {"ok": False, "anchors": 0, "last_at": None, "anchored_rows": None,
				"current_rows": frappe.db.count("HBOS Audit Log"),
				"reason": "尚无锚定记录（未执行过锚定）。"}

	prev_hash = _ANCHOR_GENESIS
	for index, line in enumerate(lines, 1):
		if line.get("prev") != prev_hash:
			return {"ok": False, "anchors": len(lines),
					"reason": "锚定链在第 {} 行断裂（历史锚定记录被改动或缺失）。".format(index)}
		expected = _anchor_hash(line.get("prev"), line.get("rows"),
								line.get("digest", ""), line.get("source", ""))
		if line.get("anchor") != expected:
			return {"ok": False, "anchors": len(lines),
					"reason": "锚定记录第 {} 行的哈希不符（该行被改动）。".format(index)}
		prev_hash = line["anchor"]

	last = lines[-1]
	anchored_rows = int(last.get("rows") or 0)
	current_rows = frappe.db.count("HBOS Audit Log")
	if current_rows < anchored_rows:
		return {"ok": False, "anchors": len(lines), "last_at": last.get("at"),
				"anchored_rows": anchored_rows, "current_rows": current_rows,
				"reason": "审计行数比锚定更少（存在删除）。"}
	ok = history_digest(limit=anchored_rows) == last.get("digest")
	return {"ok": ok, "anchors": len(lines), "last_at": last.get("at"),
			"anchored_rows": anchored_rows, "current_rows": current_rows,
			"reason": "" if ok else "锚定点之前的历史与锚定摘要不一致（存在改写 / 插入 / 重排）。"}


@frappe.whitelist()
def verify_audit_anchor():
	"""对账入口（只读）：见 `verify_anchor_at` 的语义与局限。"""
	_check_action("verify_audit_anchor")
	return verify_anchor_at()


def scheduler_scan():
	"""每日调度：追加一行锚定（系统触发，不做角色判定）。"""
	try:
		write_anchor_at(source="scheduled")
	except Exception as exc:  # 锚定失败不得影响其它调度任务
		if hasattr(frappe, "log_error"):
			frappe.log_error("审计锚定写入失败：{}".format(exc), "HBOS 审计锚定")
