# -*- coding: utf-8 -*-
"""M2 审计锚定（L10-P0-02）：把审计历史的整体摘要写到**数据库之外**的 append-only 文件。

新 v2 锚点直接绑定其建立时点所见的原始审计载荷、行身份和指纹版本。旧无版本锚点
仍按原 v1 编码校验（只绑定 name/created_at/checksum，且不绑定锚定时间 at）。
旧行和旧文件不重写；为旧行建立新快照不能追溯证明旧载荷从未被改变。

不能证明什么（不得据此宣称强防篡改）：
- 主机级权限（root / 容器）可同时改 DB 与锚定文件；
- 锚定文件是本机文件，不是远端存证；锚点建立后的新增行尚未被该锚覆盖；
- 锚定只覆盖"点"，两点之间的改动要靠下一行的链与摘要比对收敛。
"""

import fcntl
import hashlib
import json
import os

import frappe

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.lims_service import CHECKSUM_V2_FIELDS, _audit_checksum_version

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


def _history_snapshot(limit=None, version=1):
	if str(version) not in {"1", "2"}:
		raise ValueError("未知锚定版本：{}".format(version))
	version = int(version)
	fields = ["name", "created_at", "checksum", "checksum_version"]
	if version == 2:
		fields = list(dict.fromkeys(fields + list(CHECKSUM_V2_FIELDS)))
	digest = hashlib.sha256(b"hbos-audit-history-v1" if version == 1 else b"hbos-audit-history-v2\n")
	versions = {"1": 0, "2": 0, "3": 0}
	offset = 0
	while limit is None or offset < limit:
		batch = _CHUNK if limit is None else min(_CHUNK, limit - offset)
		rows = frappe.get_all("HBOS Audit Log",
							  fields=fields,
							  order_by="created_at asc, name asc",
							  limit_start=offset, limit_page_length=batch)
		if not rows:
			break
		for row in rows:
			versions[_audit_checksum_version(row.get("checksum_version"))] += 1
			if version == 1:
				# Preserve the original bytes, including its limited coverage.
				digest.update("{}|{}|{}".format(
					row.name, row.created_at or "", row.checksum or "").encode("utf-8"))
			else:
				# Stored values are read on both sides; keep null distinct from
				# empty text and JSON-frame each row, including embedded newlines.
				payload = {field: row.get(field) for field in fields}
				digest.update(json.dumps(payload, ensure_ascii=False, sort_keys=True,
					separators=(",", ":"), default=str, allow_nan=False).encode("utf-8") + b"\n")
		offset += len(rows)
		if len(rows) < batch:
			break
	return {"digest": digest.hexdigest(), "rows": offset, "versions": versions}


def history_digest(limit=None, version=1):
	"""Stable prefix digest; omitted version retains the historical v1 API."""
	return _history_snapshot(limit=limit, version=version)["digest"]


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


def _anchor_version(line):
	version = str(line["version"]) if "version" in line else "1"
	if version not in {"1", "2"}:
		raise ValueError("未知锚定版本：{}".format(version))
	return int(version)


def _anchor_hash(prev_hash, rows, digest, source, *, version=1, at=None):
	if str(version) == "1":
		return hashlib.sha256("|".join(
			[prev_hash, str(rows), digest, source]).encode("utf-8")).hexdigest()
	if str(version) != "2":
		raise ValueError("未知锚定版本：{}".format(version))
	payload = {"version": 2, "at": at, "prev": prev_hash, "rows": rows,
			   "digest": digest, "source": source}
	return hashlib.sha256(("hbos-audit-anchor-v2|" + json.dumps(payload,
		ensure_ascii=False, sort_keys=True, separators=(",", ":"))).encode("utf-8")).hexdigest()


def write_anchor_at(path=None, source="scheduled"):
	"""追加一行锚定记录（时间、来源、行数、整体摘要、前一锚定哈希、本行锚定哈希）。

	锚定行之间也串链：改动历史锚定行会破坏链。`path` 仅供测试指定；生产走默认路径。
	"""
	path = path or anchor_path()
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "a+", encoding="utf-8") as handle:
		fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
		try:
			previous = _read_anchor_lines(path)
			if previous:
				verdict = verify_anchor_at(path)
				if not verdict["ok"]:
					raise ValueError("已有锚定前缀不一致，禁止追加或重新锚定：" + verdict["reason"])
			# Read after acquiring the append lock. An earlier snapshot must not
			# follow another writer's newer/larger anchor and shrink its coverage.
			rows = frappe.db.count("HBOS Audit Log")
			if previous and rows < previous[-1]["rows"]:
				raise ValueError("锚定覆盖行数不得倒退。")
			snapshot = _history_snapshot(limit=rows, version=2)
			if snapshot["rows"] != rows:
				raise ValueError("审计行数在读取期间变化，拒绝建立不一致锚点。")
			prev_hash = previous[-1]["anchor"] if previous else _ANCHOR_GENESIS
			line = {"version": 2, "at": str(frappe.utils.now()), "source": source,
					"rows": rows, "digest": snapshot["digest"], "prev": prev_hash}
			line["anchor"] = _anchor_hash(prev_hash, rows, line["digest"], source,
				version=2, at=line["at"])
			handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
			handle.flush()
		finally:
			fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
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
	previous_rows = 0
	for index, line in enumerate(lines, 1):
		try:
			if not isinstance(line, dict):
				raise ValueError("锚定行必须是对象。")
			version = _anchor_version(line)
			if type(line.get("rows")) is not int or line["rows"] < 0:
				raise ValueError("锚定行数必须是非负整数。")
			if line["rows"] < previous_rows:
				raise ValueError("锚定覆盖行数不得倒退。")
			expected = _anchor_hash(line.get("prev"), line["rows"], line.get("digest", ""),
				line.get("source", ""), version=version, at=line.get("at"))
		except (ValueError, TypeError) as exc:
			return {"ok": False, "anchors": len(lines), "reason": "锚定记录第 {} 行无效：{}".format(index, exc)}
		if line.get("prev") != prev_hash:
			return {"ok": False, "anchors": len(lines),
					"reason": "锚定链在第 {} 行断裂（历史锚定记录被改动或缺失）。".format(index)}
		if line.get("anchor") != expected:
			return {"ok": False, "anchors": len(lines),
					"reason": "锚定记录第 {} 行的哈希不符（该行被改动）。".format(index)}
		prev_hash = line["anchor"]
		previous_rows = line["rows"]

	last = lines[-1]
	anchored_rows = last["rows"]
	current_rows = frappe.db.count("HBOS Audit Log")
	if current_rows < anchored_rows:
		return {"ok": False, "anchors": len(lines), "last_at": last.get("at"),
				"anchored_rows": anchored_rows, "current_rows": current_rows,
				"reason": "审计行数比锚定更少（存在删除）。"}
	version = _anchor_version(last)
	try:
		snapshot = _history_snapshot(limit=anchored_rows, version=version)
	except ValueError as exc:
		return {"ok": False, "anchors": len(lines), "last_at": last.get("at"),
				"anchored_rows": anchored_rows, "current_rows": current_rows, "reason": str(exc)}
	ok = snapshot["rows"] == anchored_rows and snapshot["digest"] == last.get("digest")
	return {"ok": ok, "anchors": len(lines), "last_at": last.get("at"),
			"anchored_rows": anchored_rows, "current_rows": current_rows,
			"anchor_version": version, "versions": snapshot["versions"],
			"weak_legacy": snapshot["versions"]["1"] + snapshot["versions"]["2"],
			"payload_coverage": "snapshot_v2" if version == 2 else "legacy_checksum_only",
			"coverage_note": ("仅绑定新锚建立时点所见的载荷；旧 v1/v2 行未重算，不能追溯证明其原始内容。"
				if version == 2 else "历史锚仅覆盖 name/created_at/checksum，不覆盖完整载荷或锚定时间；旧记录未升级。"),
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
