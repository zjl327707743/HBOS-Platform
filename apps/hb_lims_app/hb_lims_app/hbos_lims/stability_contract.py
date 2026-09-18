# -*- coding: utf-8 -*-
"""M2-R8A 稳定性业务契约（零 Frappe 依赖，可离线单测）。

业务口径来自《稳定性管理》SOP-LC-1-00-019 v9.0（Owner 2026-09-16 确认已正式生效）
与《M2-R8 稳定性管理板块开发方案》rev15 第四/五/六节：
- 考察分类与批次规则（4.1）
- 通知单/方案状态机（6.1 FLOW_STB_NOTICE / FLOW_STB_PROTOCOL）
- 冻结快照与版本链（7.7）
- 业务键与命名（5.8）

本模块只放纯函数与常量，Frappe 相关读写一律在 stability_service.py。
R8B~R8D 的流程（Sample / Timepoint / Result / Report / Change / Fault）按子轮增量补入，
不预先声明未实现的动作（对齐 R7A→R7B→R7C 的增量做法）。
"""

# ---------------------------------------------------------------------------
# 状态机（方案 6.1）
# ---------------------------------------------------------------------------

FLOW_STB_NOTICE = "stability_notice"
FLOW_STB_PROTOCOL = "stability_protocol"

# FLOW_STB_NOTICE
NOTICE_DRAFT = "草稿"
NOTICE_WAIT_QC = "待QC经理确认"
NOTICE_WAIT_APPROVE = "待批准"
NOTICE_APPROVED = "已批准"
NOTICE_REJECTED = "已驳回"
NOTICE_CLOSED = "已关闭"
NOTICE_CANCELLED = "已取消"

NOTICE_TRANSITIONS = {
	NOTICE_DRAFT: {NOTICE_WAIT_QC, NOTICE_CANCELLED},
	NOTICE_WAIT_QC: {NOTICE_WAIT_APPROVE, NOTICE_REJECTED},
	NOTICE_WAIT_APPROVE: {NOTICE_APPROVED, NOTICE_REJECTED},
	NOTICE_APPROVED: {NOTICE_CLOSED},          # 前置：该 Notice 下全部 Timepoint 均达终态（R8B 起生效）
	NOTICE_REJECTED: set(),
	NOTICE_CLOSED: set(),
	NOTICE_CANCELLED: set(),
}

# FLOW_STB_PROTOCOL
PROTOCOL_DRAFT = "草稿"
PROTOCOL_WAIT_QA = "待QA审核"
PROTOCOL_APPROVED = "已批准"
PROTOCOL_REJECTED = "已驳回"
PROTOCOL_VOIDED = "已作废"

PROTOCOL_TRANSITIONS = {
	PROTOCOL_DRAFT: {PROTOCOL_WAIT_QA, PROTOCOL_VOIDED},
	PROTOCOL_WAIT_QA: {PROTOCOL_APPROVED, PROTOCOL_REJECTED},
	PROTOCOL_APPROVED: {PROTOCOL_VOIDED},
	PROTOCOL_REJECTED: set(),
	PROTOCOL_VOIDED: set(),
}

STABILITY_FLOW_TRANSITIONS = {
	FLOW_STB_NOTICE: NOTICE_TRANSITIONS,
	FLOW_STB_PROTOCOL: PROTOCOL_TRANSITIONS,
}

# 终态集合（Notice 的 close_notice 前置依赖；R8B 追加 Timepoint 终态集）
NOTICE_TERMINAL_STATES = {NOTICE_REJECTED, NOTICE_CLOSED, NOTICE_CANCELLED}
PROTOCOL_TERMINAL_STATES = {PROTOCOL_REJECTED, PROTOCOL_VOIDED}


def can_stability_transition(flow, current, target):
	"""稳定性流程状态转移合法性。"""
	table = STABILITY_FLOW_TRANSITIONS.get(flow)
	if not table:
		return False
	allowed = table.get(current)
	return bool(allowed) and target in allowed


# ---------------------------------------------------------------------------
# 主数据枚举（方案 5.1）
# ---------------------------------------------------------------------------

DOSAGE_FORMS = ["原料药", "片剂", "胶囊剂", "注射剂", "吸入粉雾剂", "口服混悬剂", "中间体", "其它"]

CATEGORIES = ["新产品/工艺验证类", "变更类", "年度持续稳定性考察类", "其它类"]

CONDITION_TYPES = ["长期", "加速", "中间", "影响因素-高温", "影响因素-高湿", "影响因素-强光"]

# UOM 受控枚举：与 HBOS Retention Product.default_uom 同一权威口径（方案 5.1.1）
UOM_OPTIONS = ["g", "kg", "mg", "mL", "L", "瓶", "支", "袋", "桶", "盒", "其他"]

CLIMATE_ZONES = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳa", "Ⅳb", "N/A"]

RESULT_TYPES = ["数值型", "定性型", "文本型"]

SIGNIFICANT_CHANGE_RULES = ["相对变化超阈值", "超规格限度", "定性不符标准", "不参与判定"]

TEST_ITEM_CATEGORIES = [
	"性状", "含量", "有关物质", "水分", "熔点", "吸湿性", "pH", "溶出度", "释放度",
	"崩解时限", "可见异物", "不溶性微粒", "无菌", "沉降体积比", "再分散性", "其他",
]

# ---------------------------------------------------------------------------
# 4.1 考察分类与批次规则
# ---------------------------------------------------------------------------

# 每类别最少批次数（方案 4.1「批次要求」）
CATEGORY_MIN_BATCHES = {
	"新产品/工艺验证类": 3,     # 原则 ≥3 批
	"变更类": 1,                # 依变更评估 + 法规要求定批（不设 3 批硬下限）
	"年度持续稳定性考察类": 1,   # 每种规格和包装形式 ≥1 批
	"其它类": 1,
}

# 每类别「至少包含条件」（方案 4.1「至少包含条件」）
CATEGORY_REQUIRED_CONDITION_TYPES = {
	"新产品/工艺验证类": {"长期", "加速"},
	"变更类": {"长期"},
	"年度持续稳定性考察类": {"长期"},
	"其它类": {"长期"},
}

# 委托生产产品参照客户要求，不做本表硬校验；影响因素单独按 1 批（4.1 基本要求）
OUTSOURCE_CATEGORY_EXEMPT = True

# 多条件复核触发阈值（方案 4.1）：条件 > 2 个时 extra_condition_reason 必填 + register_review 强制
MULTI_CONDITION_THRESHOLD = 2


def check_product_code(product_code):
	"""产品编码校验（方案 5.1.1 P2 rev14）：必填、≤40、禁含 `#`。

	`#` 为 report_period_key 及各业务键分隔符，含 `#` 会破坏键解析。
	返回 (ok, error_message)。
	"""
	code = (product_code or "").strip()
	if not code:
		return False, "产品编码必填。"
	if len(code) > 40:
		return False, "产品编码不得超过 40 个字符（当前 {}）。".format(len(code))
	if "#" in code:
		return False, "产品编码不得包含 `#`（`#` 为业务键分隔符，会破坏键解析）。"
	return True, None


def check_notice_conditions(category, conditions):
	"""通知单条件校验：条件数 > 2 需补充原因，且须至少包含该类别的必备条件。

	conditions 为 [{"condition_type": ..., ...}, ...]
	返回 (ok, error_message)。
	"""
	types = [c.get("condition_type") for c in (conditions or [])]
	if not types:
		return False, "至少填写一个试验条件。"
	required = CATEGORY_REQUIRED_CONDITION_TYPES.get(category)
	if required:
		missing = sorted(required - set(types))
		if missing:
			return False, "考察分类「{}」至少须包含条件：{}（当前缺少 {}）。".format(
				category, " / ".join(sorted(required)), " / ".join(missing))
	return True, None


def check_multi_condition_review(conditions_count, extra_condition_reason, register_review_by):
	"""多条件复核（方案 4.1）：> 2 个条件时须填补充原因并经注册人员复核。

	返回 (ok, error_message)。
	"""
	if (conditions_count or 0) > MULTI_CONDITION_THRESHOLD:
		if not (extra_condition_reason or "").strip():
			return False, "考察条件超过 {} 个时，必须填写补充原因。".format(MULTI_CONDITION_THRESHOLD)
		if not register_review_by:
			return False, "考察条件超过 {} 个时，必须经注册人员复核（register_review）。".format(
				MULTI_CONDITION_THRESHOLD)
	return True, None


def check_batch_count(category, batch_count):
	"""批次数量校验（方案 4.1 / 5.2.2「≥3 批（按类别校验）」）。"""
	if OUTSOURCE_CATEGORY_EXEMPT and category == "委托生产":
		return True, None
	minimum = CATEGORY_MIN_BATCHES.get(category, 1)
	if (batch_count or 0) < minimum:
		return False, "考察分类「{}」的考察批次不得少于 {} 批（当前 {} 批）。".format(
			category, minimum, batch_count or 0)
	return True, None


def check_year_long_study_no_protocol(category):
	"""年度持续稳定性考察类不建方案单（方案 4.2.5）。返回 True 表示该类无需 Protocol。"""
	return category == "年度持续稳定性考察类"


# ---------------------------------------------------------------------------
# 冻结快照与版本链（方案 7.7）
# ---------------------------------------------------------------------------

# 批准后冻结的字段（置 snapshot_frozen=1 后只读）
SNAPSHOT_FIELDS_NOTICE = [
	"spec_ref", "spec_version", "method_version", "limits_snapshot", "vd_months_snapshot",
]
SNAPSHOT_FIELDS_PROTOCOL = [
	"spec_ref", "spec_version", "test_method_ref", "method_version", "vd_months_snapshot",
]


def check_snapshot_frozen(before_doc, after_dict, frozen_flag_field="snapshot_frozen"):
	"""冻结快照字段只读校验（方案 7.7 / 11.2 门禁 2）。

	before_doc 为保存前文档（dict 或 Document），after_dict 为本次提交值。
	返回 (ok, error_message, changed_field)。
	"""
	if not before_doc:
		return True, None, None
	if not _get(before_doc, frozen_flag_field):
		return True, None, None
	for field in SNAPSHOT_FIELDS_NOTICE + SNAPSHOT_FIELDS_PROTOCOL:
		if str(_get(before_doc, field) or "") != str(after_dict.get(field) or ""):
			return False, "字段「{}」已冻结（快照锁定），批准后不可修改；如需变更请生成新版本。".format(field), field
	return True, None, None


def _get(doc, field):
	if isinstance(doc, dict):
		return doc.get(field)
	return doc.get(field)


def next_version(current_version):
	"""版本号递增（方案 5.2.1 / 5.2.2）。"""
	return int(current_version or 0) + 1


# ---------------------------------------------------------------------------
# 业务键与命名（方案 5.8）
# ---------------------------------------------------------------------------

# 命名系列：Frappe 在 set_name_by_naming_series 中无条件追加 ".#####"
# （frappe/model/naming.py），故系列本身不得含 "#"——否则会生成
# `HBOS-STB-NOT-2026-####00009` 这类畸形单号（R8G 修复）。
# 与既有 HBOS-SMP- / HBOS-RET- 同一约定。
NAMING_NOTICE = "HBOS-STB-NOT-.YYYY.-"
NAMING_PROTOCOL = "HBOS-STB-PRO-.YYYY.-"


def make_notice_version_key(notice_name, version):
	"""通知单版本键（版本链可追溯）。"""
	return "{}#V{}".format(notice_name or "", version or 1)


def make_protocol_version_key(protocol_name, version):
	"""方案版本键。"""
	return "{}#V{}".format(protocol_name or "", version or 1)


# ---------------------------------------------------------------------------
# 动作 → 状态转移（供离线契约断言「每处转移都有对应动作」，方案 11.2 门禁 10）
#
# 角色表不放这里，唯一来源是 workflow_contract.ACTION_ROLES（避免双源漂移）。
# 同一动作可覆盖多条转移（如 reject_notice 覆盖 待QC经理确认/待批准 两个来源态）。
# ---------------------------------------------------------------------------

ACTION_TRANSITIONS = [
	# FLOW_STB_NOTICE（方案 6.3.1）
	("submit_notice", FLOW_STB_NOTICE, NOTICE_DRAFT, NOTICE_WAIT_QC),
	("confirm_notice_qc", FLOW_STB_NOTICE, NOTICE_WAIT_QC, NOTICE_WAIT_APPROVE),
	("approve_notice", FLOW_STB_NOTICE, NOTICE_WAIT_APPROVE, NOTICE_APPROVED),
	("reject_notice", FLOW_STB_NOTICE, NOTICE_WAIT_QC, NOTICE_REJECTED),
	("reject_notice", FLOW_STB_NOTICE, NOTICE_WAIT_APPROVE, NOTICE_REJECTED),
	("cancel_notice", FLOW_STB_NOTICE, NOTICE_DRAFT, NOTICE_CANCELLED),
	("close_notice", FLOW_STB_NOTICE, NOTICE_APPROVED, NOTICE_CLOSED),
	# FLOW_STB_PROTOCOL（方案 6.3.2）
	("submit_protocol", FLOW_STB_PROTOCOL, PROTOCOL_DRAFT, PROTOCOL_WAIT_QA),
	("approve_protocol", FLOW_STB_PROTOCOL, PROTOCOL_WAIT_QA, PROTOCOL_APPROVED),
	("reject_protocol", FLOW_STB_PROTOCOL, PROTOCOL_WAIT_QA, PROTOCOL_REJECTED),
	("void_protocol", FLOW_STB_PROTOCOL, PROTOCOL_DRAFT, PROTOCOL_VOIDED),
	("void_protocol", FLOW_STB_PROTOCOL, PROTOCOL_APPROVED, PROTOCOL_VOIDED),
]

# 状态不变（准入行）的动作，不参与转移覆盖断言
ACTION_ADMISSION_ONLY = {"register_review", "review_protocol", "manage_stability_master"}
