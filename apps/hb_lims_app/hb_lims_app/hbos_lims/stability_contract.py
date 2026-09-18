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

import datetime
from decimal import Decimal, ROUND_HALF_UP

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
NAMING_SAMPLE = "HBOS-STB-SMP-.YYYY.-"
NAMING_TIMEPOINT = "HBOS-STB-TPT-.YYYY.-"


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


# ===========================================================================
# M2-R8B：样品与时间点（方案 5.3 / 6.1 / 6.3.3 / 6.3.4 / 7.1 / 7.2 / 7.3）
# ===========================================================================

FLOW_STB_SAMPLE = "stability_sample"
FLOW_STB_TIMEPOINT = "stability_timepoint"
FLOW_STB_TIMEPOINT_DELAY = "stability_timepoint_delay"

# ---------------------------------------------------------------------------
# FLOW_STB_SAMPLE（方案 6.1；current_qty 单一写路径）
# ---------------------------------------------------------------------------

SAMPLE_IN_STORAGE = "在箱"
SAMPLE_PARTIAL = "部分取样"
SAMPLE_DEPLETED = "已取尽"
SAMPLE_PENDING_DISPOSAL = "待处理"
SAMPLE_DESTROYED = "已销毁"
SAMPLE_TRANSFERRED = "已转出"

SAMPLE_TRANSITIONS = {
	SAMPLE_IN_STORAGE: {SAMPLE_IN_STORAGE, SAMPLE_PARTIAL, SAMPLE_DEPLETED,
						SAMPLE_PENDING_DISPOSAL, SAMPLE_TRANSFERRED},
	SAMPLE_PARTIAL: {SAMPLE_PARTIAL, SAMPLE_DEPLETED,
					 SAMPLE_PENDING_DISPOSAL, SAMPLE_TRANSFERRED},
	SAMPLE_DEPLETED: {SAMPLE_PENDING_DISPOSAL, SAMPLE_TRANSFERRED},
	# 回退按 pre_disposal_status 快照恢复到三态之一（方案 P1-2）
	SAMPLE_PENDING_DISPOSAL: {SAMPLE_DESTROYED, SAMPLE_IN_STORAGE, SAMPLE_PARTIAL, SAMPLE_DEPLETED},
	SAMPLE_DESTROYED: set(),
	SAMPLE_TRANSFERRED: set(),
}

SAMPLE_TERMINAL_STATES = {SAMPLE_DESTROYED, SAMPLE_TRANSFERRED}

# 可进入「待处理」的源状态（方案 6.3.3 / 门禁 13）
SAMPLE_DISPOSAL_SOURCE_STATES = {SAMPLE_IN_STORAGE, SAMPLE_PARTIAL, SAMPLE_DEPLETED}
# 「待处理」可回退到的目标（即 pre_disposal_status 的取值域）
SAMPLE_PRE_DISPOSAL_STATES = SAMPLE_DISPOSAL_SOURCE_STATES

# ---------------------------------------------------------------------------
# FLOW_STB_TIMEPOINT（方案 6.1；逾期为纯派生，不进状态枚举）
# ---------------------------------------------------------------------------

TP_WAIT_SAMPLE = "待取样"
TP_WAIT_TEST = "待检测"
TP_TESTING = "检测中"
TP_DONE = "已完成"
TP_CANCELLED = "已取消"

TIMEPOINT_TRANSITIONS = {
	TP_WAIT_SAMPLE: {TP_WAIT_TEST, TP_CANCELLED},
	TP_WAIT_TEST: {TP_TESTING, TP_CANCELLED},
	TP_TESTING: {TP_DONE, TP_CANCELLED},
	# 唯一出口，仅系统动作 reopen_timepoint（由 R8C 的 void_result 同事务调用）
	TP_DONE: {TP_TESTING},
	TP_CANCELLED: set(),
}

TIMEPOINT_TERMINAL_STATES = {TP_CANCELLED}
# 可取消的状态（方案 6.3.4）
TIMEPOINT_CANCELLABLE_STATES = {TP_WAIT_SAMPLE, TP_WAIT_TEST, TP_TESTING}

# ---------------------------------------------------------------------------
# FLOW_STB_TIMEPOINT_DELAY（延期子表自身的状态机；方案 7.3）
# 子表不是主 DocType，但同样"每处转移都有动作"，故一并纳入转移覆盖断言。
# ---------------------------------------------------------------------------

DELAY_WAIT_APPROVE = "待批准"
DELAY_APPROVED = "已批准"
DELAY_REJECTED = "已驳回"

DELAY_TRANSITIONS = {
	DELAY_WAIT_APPROVE: {DELAY_APPROVED, DELAY_REJECTED},
	DELAY_APPROVED: set(),
	DELAY_REJECTED: set(),
}

DELAY_TYPES = ["取样延期", "检测延期"]
DELAY_REJECTED_STATES = {DELAY_APPROVED, DELAY_REJECTED}

STABILITY_FLOW_TRANSITIONS.update({
	FLOW_STB_SAMPLE: SAMPLE_TRANSITIONS,
	FLOW_STB_TIMEPOINT: TIMEPOINT_TRANSITIONS,
	FLOW_STB_TIMEPOINT_DELAY: DELAY_TRANSITIONS,
})

# ---------------------------------------------------------------------------
# 6.3.3 / 6.3.4 动作 → 转移（供门禁 10 断言）
# ---------------------------------------------------------------------------

ACTION_TRANSITIONS += [
	# 6.3.3 FLOW_STB_SAMPLE
	("record_sampling", FLOW_STB_SAMPLE, SAMPLE_IN_STORAGE, SAMPLE_IN_STORAGE),
	("record_sampling", FLOW_STB_SAMPLE, SAMPLE_IN_STORAGE, SAMPLE_PARTIAL),
	("record_sampling", FLOW_STB_SAMPLE, SAMPLE_IN_STORAGE, SAMPLE_DEPLETED),
	("record_sampling", FLOW_STB_SAMPLE, SAMPLE_PARTIAL, SAMPLE_PARTIAL),
	("record_sampling", FLOW_STB_SAMPLE, SAMPLE_PARTIAL, SAMPLE_DEPLETED),
	("return_sample", FLOW_STB_SAMPLE, SAMPLE_IN_STORAGE, SAMPLE_IN_STORAGE),
	("return_sample", FLOW_STB_SAMPLE, SAMPLE_PARTIAL, SAMPLE_PARTIAL),
	("mark_for_disposal", FLOW_STB_SAMPLE, SAMPLE_IN_STORAGE, SAMPLE_PENDING_DISPOSAL),
	("mark_for_disposal", FLOW_STB_SAMPLE, SAMPLE_PARTIAL, SAMPLE_PENDING_DISPOSAL),
	("mark_for_disposal", FLOW_STB_SAMPLE, SAMPLE_DEPLETED, SAMPLE_PENDING_DISPOSAL),
	("cancel_disposal", FLOW_STB_SAMPLE, SAMPLE_PENDING_DISPOSAL, SAMPLE_IN_STORAGE),
	("cancel_disposal", FLOW_STB_SAMPLE, SAMPLE_PENDING_DISPOSAL, SAMPLE_PARTIAL),
	("cancel_disposal", FLOW_STB_SAMPLE, SAMPLE_PENDING_DISPOSAL, SAMPLE_DEPLETED),
	("dispose_sample", FLOW_STB_SAMPLE, SAMPLE_PENDING_DISPOSAL, SAMPLE_DESTROYED),
	("transfer_out", FLOW_STB_SAMPLE, SAMPLE_IN_STORAGE, SAMPLE_TRANSFERRED),
	("transfer_out", FLOW_STB_SAMPLE, SAMPLE_PARTIAL, SAMPLE_TRANSFERRED),
	("transfer_out", FLOW_STB_SAMPLE, SAMPLE_DEPLETED, SAMPLE_TRANSFERRED),
	# 6.3.4 FLOW_STB_TIMEPOINT
	("complete_sampling", FLOW_STB_TIMEPOINT, TP_WAIT_SAMPLE, TP_WAIT_TEST),
	("import_zero_month_result", FLOW_STB_TIMEPOINT, TP_WAIT_SAMPLE, TP_WAIT_TEST),
	("start_testing", FLOW_STB_TIMEPOINT, TP_WAIT_TEST, TP_TESTING),
	("complete_testing", FLOW_STB_TIMEPOINT, TP_TESTING, TP_DONE),
	("reopen_timepoint", FLOW_STB_TIMEPOINT, TP_DONE, TP_TESTING),
	("cancel_timepoint", FLOW_STB_TIMEPOINT, TP_WAIT_SAMPLE, TP_CANCELLED),
	("cancel_timepoint", FLOW_STB_TIMEPOINT, TP_WAIT_TEST, TP_CANCELLED),
	("cancel_timepoint", FLOW_STB_TIMEPOINT, TP_TESTING, TP_CANCELLED),
	# 7.3 延期子表
	("approve_delay", FLOW_STB_TIMEPOINT_DELAY, DELAY_WAIT_APPROVE, DELAY_APPROVED),
	("reject_delay", FLOW_STB_TIMEPOINT_DELAY, DELAY_WAIT_APPROVE, DELAY_REJECTED),
]

# R8B 的建档 / 准入动作（状态不变或无源状态）
ACTION_ADMISSION_ONLY |= {
	"register_stability_sample", "review_sample_storage", "adjust_stock",
	"generate_timepoints", "apply_delay", "append_conditions", "approve_extra_sampling",
}

# 系统触发动作：角色豁免，但动作名不豁免（门禁 10 / 20）
SYSTEM_TRIGGERED_ACTIONS = {"complete_testing", "reopen_timepoint"}

# ---------------------------------------------------------------------------
# 7.1 时间点生成
# ---------------------------------------------------------------------------

CATEGORY_LONG_TERM_SERIES_DEFAULT = "default"       # 新产品/变更/其它：按年限递进
CATEGORY_YEARLY = "年度持续稳定性考察类"

# 各条件的固定时间点（天或月），按条件类型分派
CONDITION_POINTS = {
	"加速": {"unit": "月", "values": [0, 3, 6]},
	"中间": {"unit": "月", "values": [0, 6, 9, 12]},
	"影响因素-高温": {"unit": "天", "values": [0, 5, 10, 30]},
	"影响因素-高湿": {"unit": "天", "values": [5, 10]},
	# 影响因素-强光：按 Study Condition.exposure_days
}


def long_term_months(vd_months):
	"""长期条件的时间点（月）：第 1 年每 3 月、第 2 年每 6 月、之后每 12 月，直至 vd_months。

	末点口径：常规序列未落在 `vd_months` 上时，**补上 `vd_months` 本身**（方案 7.1「直至 vd_months」）。
	"""
	vd = int(vd_months or 0)
	if vd <= 0:
		return [0]
	points = {m for m in (0, 3, 6, 9, 12, 18, 24) if m <= vd}
	m = 36
	while m <= vd:
		points.add(m)
		m += 12
	points.add(vd)
	return sorted(points)


def yearly_study_months(vd_months):
	"""年度持续稳定性考察类：按 VD 分档（规程 4.3 表 B）。

	VD≤0.5Y → 0 / ⅔效期 / 效期；0.5–1Y → 0/6/效期；1–1.5Y → 0/6/12/效期；
	1.5–2Y → 0/12/18/效期；>2Y → 0/12/24/效期。2/3 效期 ROUND_HALF_UP，算出 0 月取 1 月。
	"""
	vd = int(vd_months or 0)
	if vd <= 0:
		return [0]
	if vd <= 6:
		two_thirds = half_up(Decimal(vd) * 2 / 3)
		two_thirds = max(two_thirds, 1)
		return sorted({0, two_thirds, vd})
	if vd <= 12:
		return sorted({0, 6, vd})
	if vd <= 18:
		return sorted({0, 6, 12, vd})
	if vd <= 24:
		return sorted({0, 12, 18, vd})
	return sorted({0, 12, 24, vd})


def condition_points(condition_type, exposure_days=None):
	"""单个条件的 (value, unit) 列表（方案 7.1）。"""
	if condition_type == "影响因素-强光":
		days = int(exposure_days or 0)
		return [(0, "天"), (days, "天")] if days else [(0, "天")]
	conf = CONDITION_POINTS.get(condition_type)
	if conf:
		return [(v, conf["unit"]) for v in conf["values"]]
	return []


def plan_timepoints(category, vd_months, conditions, room_temp_recovery_days=0):
	"""按 study_conditions 逐条件展开时间点清单（方案 7.1）。

	conditions 为 [{"condition_type":..., "condition_code":..., "exposure_days":...}, ...]
	返回 [{"condition_type","condition_code","value","unit","label","is_full_test","order"}, ...]
	不依赖 Frappe，日期在服务层按 7.2（relativedelta）计算。
	"""
	out = []
	for cond in conditions or []:
		ctype = cond.get("condition_type")
		ccode = cond.get("condition_code") or cond.get("storage_cond")
		if ctype == "长期":
			if category == CATEGORY_YEARLY:
				pairs = [(m, "月") for m in yearly_study_months(vd_months)]
			else:
				pairs = [(m, "月") for m in long_term_months(vd_months)]
		else:
			pairs = condition_points(ctype, cond.get("exposure_days"))
		for idx, (value, unit) in enumerate(pairs):
			out.append({
				"condition_type": ctype,
				"condition_code": ccode,
				"value": value,
				"unit": unit,
				"label": time_point_label(value, unit),
				# 首末点为全检（方案 5.3.2）
				"is_full_test": 1 if (idx == 0 or idx == len(pairs) - 1) else 0,
			})
	return out


def time_point_label(value, unit):
	"""展示标签（只读，代码生成）：`3月` / `10天`。"""
	return "{}{}".format(int(value or 0), unit)


def make_sample_cond_point_key(sample, condition_code, value, unit):
	"""时间点业务键（unique 单字段）：`{sample}#{condition_code}#{value}{unit}`。"""
	return "{}#{}#{}{}".format(sample or "", condition_code or "", int(value or 0), unit or "")


# ---------------------------------------------------------------------------
# 7.3 期限与延期
# ---------------------------------------------------------------------------

# 检测侧政策窗口（天）；委外按 outsourced_test_window_days（可空=不限制）
TEST_WINDOW_DAYS = 30
SAMPLE_DELAY_CAP_DAYS = 15


def _to_days(value, unit):
	"""时间点折算天数：`天` 直接用；`月` × 30（方案 11.3-4 采甲）。"""
	return int(value or 0) if unit == "天" else int(value or 0) * 30


def delay_limit_days(value, unit):
	"""取样延期上限（天）：`min(ROUND_HALF_UP(days × 0.1), 15)`。

	显式 decimal ROUND_HALF_UP，禁银行家舍入——影响因素 5 天 × 10% = 0.5 取 **1** 天。
	"""
	days = _to_days(value, unit)
	raw = (Decimal(days) * Decimal("0.1")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
	return min(int(raw), SAMPLE_DELAY_CAP_DAYS)


def policy_latest_due(planned_date, delay_type, delay_limit=None,
					  outsourced_test_window_days=None):
	"""政策最新截止日（硬上限）：取样 `planned + delay_limit_days`；检测 `planned + 30 天`。

	委外检测窗口留空 = 不限制（返回 None，表示不做上限拦截）。
	"""
	if delay_type == "取样延期":
		return _add_days(planned_date, delay_limit if delay_limit is not None else 0)
	window = (TEST_WINDOW_DAYS if outsourced_test_window_days is None
			  else outsourced_test_window_days)
	if window in (None, ""):
		return None
	return _add_days(planned_date, int(window))


def _add_days(d, days):
	if not d:
		return None
	if isinstance(d, str):
		d = datetime.date.fromisoformat(d[:10])
	return d + datetime.timedelta(days=int(days or 0))


def check_delay_apply(planned_due_date, requested_due_date, policy_latest_due_date):
	"""申请段日期链：`planned ≤ requested ≤ policy_latest`（方案 7.3 / P1-2 rev11）。

	返回 (ok, error_message)。
	"""
	planned = _as_date(planned_due_date)
	requested = _as_date(requested_due_date)
	latest = _as_date(policy_latest_due_date)
	if not requested:
		return False, "申请顺延日期必填。"
	if planned and requested < planned:
		return False, "申请顺延日期不得早于计划日期（{}）。".format(planned)
	if latest and requested > latest:
		return False, "申请顺延日期不得超出政策上限（{}）。".format(latest)
	return True, None


def check_delay_approve(planned_due_date, requested_due_date, approved_due_date,
						policy_latest_due_date):
	"""批准段日期链：`planned ≤ requested ≤ approved ≤ policy_latest`（方案 7.3 / 门禁 18）。"""
	ok, err = check_delay_apply(planned_due_date, requested_due_date, policy_latest_due_date)
	if not ok:
		return ok, err
	requested = _as_date(requested_due_date)
	approved = _as_date(approved_due_date)
	latest = _as_date(policy_latest_due_date)
	if not approved:
		return False, "批准允许日期必填。"
	if approved < requested:
		return False, "批准日期不得早于申请顺延日期（{}）。".format(requested)
	if latest and approved > latest:
		return False, "批准日期不得超出政策上限（{}）。".format(latest)
	return True, None


def _as_date(value):
	if not value:
		return None
	if isinstance(value, str):
		return datetime.date.fromisoformat(value[:10])
	if isinstance(value, datetime.datetime):
		return value.date()
	return value


def effective_due_date(delays, delay_type, fallback_policy_latest=None):
	"""有效截止日 = 最后一条**已批准**行的 `approved_due_date`（按 `approve_at` 降序），否则回退政策上限。

	多条已批准行不叠加、不累加、不取最大值（方案 7.3 通用规则）。
	delays 为 [{"delay_type","status","approve_at","approved_due_date"}, ...]
	"""
	rows = [d for d in (delays or [])
			if d.get("delay_type") == delay_type and d.get("status") == DELAY_APPROVED]
	if not rows:
		return _as_date(fallback_policy_latest)
	rows.sort(key=lambda d: str(d.get("approve_at") or ""), reverse=True)
	return _as_date(rows[0].get("approved_due_date"))


def check_approve_not_backwards(prev_approved_due, prev_approve_at,
								new_approved_due, new_approve_at):
	"""禁止批准时间/日期倒退（方案 7.3）：新批准行须 ≥ 上一条已批准行。"""
	prev_due = _as_date(prev_approved_due)
	new_due = _as_date(new_approved_due)
	if prev_due and new_due and new_due < prev_due:
		return False, "延期不得回退：批准日期（{}）早于上一条已批准（{}）。".format(new_due, prev_due)
	if prev_approve_at and new_approve_at and str(new_approve_at) < str(prev_approve_at):
		return False, "延期不得回退：批准时间早于上一条已批准时间。"
	return True, None


def check_sampling_not_late(actual_sample_date, effective_sample_due, policy_latest_sample_due):
	"""取样实际日期校验（方案 7.3）：`≤ effective_due` 且 `≤ policy_latest`（硬上限）。"""
	actual = _as_date(actual_sample_date)
	for label, due in (("有效截止日", effective_sample_due), ("政策硬上限", policy_latest_sample_due)):
		d = _as_date(due)
		if actual and d and actual > d:
			return False, "实际取样日期（{}）超过{}{}，须先提交并批准取样延期。".format(
				actual, label, "（{}）".format(d))
	return True, None


def check_test_dates(actual_test_date, actual_sample_date, plan_test_date,
					 effective_test_due, policy_latest_test_due, exempt_zero_month=False):
	"""提交结果时的日期硬校验（方案 7.3 校验 #1/#2/#3）。

	0 月点（来源为出厂全检/委外）豁免 #1/#2（免取样口径）。
	"""
	actual = _as_date(actual_test_date)
	sample = _as_date(actual_sample_date)
	plan_test = _as_date(plan_test_date)
	if not actual:
		return False, "实际检测日期必填。"
	if not exempt_zero_month:
		if plan_test and actual < plan_test:
			return False, "实际检测日期（{}）不得早于计划检测日期（{}）。".format(actual, plan_test)
		if sample and actual < sample:
			return False, "实际检测日期（{}）不得早于实际取样日期（{}）。".format(actual, sample)
	for label, due in (("有效截止日", effective_test_due), ("政策硬上限", policy_latest_test_due)):
		d = _as_date(due)
		if d and actual > d:
			return False, "实际检测日期（{}）超过{}{}，须先提交并批准检测延期。".format(
				actual, label, "（{}）".format(d))
	return True, None


ZERO_MONTH_SOURCES = {"出厂全检", "委外"}


def zero_month_exempt(is_zero_month, source):
	"""0 月免取样口径判定（方案 7.3 / P1-1）：`is_zero_month=1 且 source ∈ {出厂全检, 委外}`。"""
	return bool(is_zero_month) and (source in ZERO_MONTH_SOURCES)


# ---------------------------------------------------------------------------
# 7.2 日期推进（月末溢出用 relativedelta；此处在契约层给纯函数以便离线单测）
# ---------------------------------------------------------------------------

def add_time_point(start_date, value, unit):
	"""`start_date + (value, unit)`；`月` 用 relativedelta 收敛到目标月最后一天（方案 7.2）。

	不引入 dateutil 依赖，等价实现：先加月，若目标月天数不足则取该月最后一天。
	"""
	base = _as_date(start_date)
	if not base:
		return None
	if unit == "天":
		return base + datetime.timedelta(days=int(value or 0))
	months = int(value or 0)
	year = base.year + (base.month - 1 + months) // 12
	month = (base.month - 1 + months) % 12 + 1
	day = min(base.day, _days_in_month(year, month))
	return datetime.date(year, month, day)


def _days_in_month(year, month):
	if month == 12:
		nxt = datetime.date(year + 1, 1, 1)
	else:
		nxt = datetime.date(year, month + 1, 1)
	return (nxt - datetime.timedelta(days=1)).day


def half_up(value):
	"""显式 ROUND_HALF_UP 取整（方案 7.2 统一口径）。"""
	return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

