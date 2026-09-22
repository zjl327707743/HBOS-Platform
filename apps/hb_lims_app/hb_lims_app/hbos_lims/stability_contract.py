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

# 业务样品来源别名。前端使用“稳定性取样”提升可读性，DocType 数据层保留既有
# 受控枚举“稳定性”；两者在登记入口统一归一，避免同一业务出现两种来源值。
STABILITY_SAMPLE_SOURCE = "稳定性"
STABILITY_SAMPLE_SOURCE_ALIASES = {STABILITY_SAMPLE_SOURCE, "稳定性取样"}


def normalize_sample_source(value):
	"""归一化业务样品来源，返回稳定性板块使用的受控枚举值。"""
	source = str(value or "").strip()
	return STABILITY_SAMPLE_SOURCE if source in STABILITY_SAMPLE_SOURCE_ALIASES else source


def is_stability_sample_source(value):
	"""判断样品来源是否代表稳定性检测样品。"""
	return normalize_sample_source(value) == STABILITY_SAMPLE_SOURCE


def validate_stability_binding(sample_source, stability_timepoint):
	"""校验样品来源与稳定性时间点的一致性，返回 (ok, error_message)。"""
	is_stability = is_stability_sample_source(sample_source)
	if is_stability and not str(stability_timepoint or "").strip():
		return False, "样品来源为稳定性取样时，必须绑定稳定性时间点。"
	if not is_stability and str(stability_timepoint or "").strip():
		return False, "仅稳定性取样样品可以绑定稳定性时间点。"
	return True, None


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



# ===========================================================================
# M2-R8C：结果与报告（方案 5.4 / 6.1 / 6.3.5 / 6.3.6 / 7.4 / 7.5 / 7.6 / 7.7）
# ===========================================================================

from hb_lims_app.hbos_lims import result_contract as rc

FLOW_STB_RESULT = "stability_result"
FLOW_STB_REPORT = "stability_report"

# ---------------------------------------------------------------------------
# FLOW_STB_RESULT（方案 6.1；版本链与生效指针见 7.7）
# ---------------------------------------------------------------------------

RESULT_DRAFT = "草稿"
RESULT_SUBMITTED = "已提交"
RESULT_REVIEWED = "已复核"
RESULT_APPROVED = "已批准"
RESULT_REVISED = "已修订"
RESULT_VOIDED = "已作废"

RESULT_TRANSITIONS = {
	RESULT_DRAFT: {RESULT_SUBMITTED, RESULT_VOIDED},
	RESULT_SUBMITTED: {RESULT_REVIEWED, RESULT_DRAFT, RESULT_VOIDED},
	RESULT_REVIEWED: {RESULT_APPROVED, RESULT_SUBMITTED, RESULT_VOIDED},
	RESULT_APPROVED: {RESULT_REVISED, RESULT_VOIDED},
	RESULT_REVISED: set(),
	RESULT_VOIDED: set(),
}

RESULT_TERMINAL_STATES = {RESULT_REVISED, RESULT_VOIDED}
# 在途（未批准）状态：同一 (时间点, 项目) 至多一条
RESULT_INFLIGHT_STATES = {RESULT_DRAFT, RESULT_SUBMITTED, RESULT_REVIEWED}

# ---------------------------------------------------------------------------
# FLOW_STB_CHANGE（方案 6.1 / 6.3.7；P1-9 修订）
# ---------------------------------------------------------------------------

FLOW_STB_CHANGE = "stability_change"
FLOW_STB_FAULT = "stability_fault"

CHANGE_DRAFT = "草稿"
CHANGE_WAIT_QA = "待QA审核"
CHANGE_WAIT_QAM = "待QA经理批准"
CHANGE_WAIT_QP = "待QP批准"
CHANGE_APPROVED = "已批准"
CHANGE_IMPLEMENTED = "已实施"
CHANGE_ASSESSED = "已评估完成"
CHANGE_ASSESS_FAILED = "后评估不通过"
CHANGE_REJECTED = "已驳回"
CHANGE_CANCELLED = "已取消"

CHANGE_TRANSITIONS = {
	CHANGE_DRAFT: {CHANGE_WAIT_QA, CHANGE_CANCELLED},
	# review_change 按 change_level 分流：一般 → 待QA经理批准；重大 → 待QP批准
	CHANGE_WAIT_QA: {CHANGE_WAIT_QAM, CHANGE_WAIT_QP, CHANGE_REJECTED},
	CHANGE_WAIT_QAM: {CHANGE_APPROVED, CHANGE_REJECTED},
	CHANGE_WAIT_QP: {CHANGE_APPROVED, CHANGE_REJECTED},
	CHANGE_APPROVED: {CHANGE_IMPLEMENTED},
	CHANGE_IMPLEMENTED: {CHANGE_ASSESSED, CHANGE_ASSESS_FAILED},
	# 后评估不通过为终态（P1-3）：本单停留，纠正须另立新单（supersedes 指向本单）
	CHANGE_ASSESS_FAILED: set(),
	CHANGE_ASSESSED: set(),
	CHANGE_REJECTED: set(),
	CHANGE_CANCELLED: set(),
}

CHANGE_TERMINAL_STATES = {CHANGE_ASSESS_FAILED, CHANGE_ASSESSED, CHANGE_REJECTED, CHANGE_CANCELLED}

# 变更落点（方案 7.9）与 change_level
CHANGE_SCOPES = ["涉方案", "涉通知单", "涉条件与时间点", "涉样品"]
CHANGE_LEVELS = ["一般", "重大"]
APPLICANT_DEPTS = ["研发部门", "生产部门", "质量控制部门", "质量保证部门"]

# ---------------------------------------------------------------------------
# FLOW_STB_FAULT（方案 6.1 / 6.3.8）
# ---------------------------------------------------------------------------

FAULT_PENDING = "待处理"
FAULT_HANDLING = "处理中"
FAULT_WAIT_ASSESS = "待评估"
FAULT_CLOSED = "已关闭"

FAULT_TRANSITIONS = {
	FAULT_PENDING: {FAULT_HANDLING, FAULT_CLOSED},
	FAULT_HANDLING: {FAULT_WAIT_ASSESS, FAULT_CLOSED},
	FAULT_WAIT_ASSESS: {FAULT_CLOSED, FAULT_HANDLING},
	FAULT_CLOSED: set(),
}

FAULT_TERMINAL_STATES = {FAULT_CLOSED}

# Room Log / Equipment / Fault Ticket 受控枚举（方案 5.5.2~5.5.4）
LOG_PERIODS = ["上午", "下午"]
EQUIPMENT_TYPES = ["恒温恒湿箱", "医用冷藏箱", "强光照射试验箱", "其它"]
QUALIFICATION_STATUSES = ["已确认", "待确认", "过期"]
EQUIPMENT_STATUSES = ["在用", "停用", "维修中"]

NAMING_CHANGE = "HBOS-STB-CHG-.YYYY.-"
NAMING_ROOM_LOG = "HBOS-STB-RML-.YYYY.-"
NAMING_EQUIPMENT = "HBOS-STB-EQP-"
NAMING_FAULT = "HBOS-STB-FLT-.YYYY.-"


def make_room_log_key(room, log_date, period):
	"""温湿度记录业务键（unique 单字段）：`{room}#{log_date}#{period}`（方案 5.5.2）。"""
	return "{}#{}#{}".format(room or "", log_date or "", period or "")

# ---------------------------------------------------------------------------
# FLOW_STB_REPORT（方案 6.1）
# ---------------------------------------------------------------------------

REPORT_DRAFT = "草稿"
REPORT_WAIT_QA = "待QA审核"
REPORT_APPROVED = "已批准"
REPORT_REJECTED = "已驳回"
REPORT_VOIDED = "已作废"

REPORT_TRANSITIONS = {
	REPORT_DRAFT: {REPORT_WAIT_QA, REPORT_VOIDED},
	REPORT_WAIT_QA: {REPORT_APPROVED, REPORT_REJECTED},
	REPORT_APPROVED: {REPORT_VOIDED},
	REPORT_REJECTED: set(),
	REPORT_VOIDED: set(),
}

REPORT_TERMINAL_STATES = {REPORT_REJECTED, REPORT_VOIDED}

STABILITY_FLOW_TRANSITIONS.update({
	FLOW_STB_RESULT: RESULT_TRANSITIONS,
	FLOW_STB_REPORT: REPORT_TRANSITIONS,
	FLOW_STB_CHANGE: CHANGE_TRANSITIONS,
	FLOW_STB_FAULT: FAULT_TRANSITIONS,
})

ACTION_TRANSITIONS += [
	# 6.3.5 FLOW_STB_RESULT
	("submit_result", FLOW_STB_RESULT, RESULT_DRAFT, RESULT_SUBMITTED),
	("review_result", FLOW_STB_RESULT, RESULT_SUBMITTED, RESULT_REVIEWED),
	("return_result", FLOW_STB_RESULT, RESULT_SUBMITTED, RESULT_DRAFT),
	("return_result", FLOW_STB_RESULT, RESULT_REVIEWED, RESULT_SUBMITTED),
	("approve_result", FLOW_STB_RESULT, RESULT_REVIEWED, RESULT_APPROVED),
	("mark_superseded", FLOW_STB_RESULT, RESULT_APPROVED, RESULT_REVISED),
	("void_result", FLOW_STB_RESULT, RESULT_DRAFT, RESULT_VOIDED),
	("void_result", FLOW_STB_RESULT, RESULT_SUBMITTED, RESULT_VOIDED),
	("void_result", FLOW_STB_RESULT, RESULT_REVIEWED, RESULT_VOIDED),
	("void_result", FLOW_STB_RESULT, RESULT_APPROVED, RESULT_VOIDED),
	# 6.3.6 FLOW_STB_REPORT
	("submit_report", FLOW_STB_REPORT, REPORT_DRAFT, REPORT_WAIT_QA),
	("approve_report", FLOW_STB_REPORT, REPORT_WAIT_QA, REPORT_APPROVED),
	("reject_report", FLOW_STB_REPORT, REPORT_WAIT_QA, REPORT_REJECTED),
	("void_report", FLOW_STB_REPORT, REPORT_DRAFT, REPORT_VOIDED),
	("void_report", FLOW_STB_REPORT, REPORT_APPROVED, REPORT_VOIDED),
	# 6.3.7 FLOW_STB_CHANGE
	("submit_change", FLOW_STB_CHANGE, CHANGE_DRAFT, CHANGE_WAIT_QA),
	("review_change", FLOW_STB_CHANGE, CHANGE_WAIT_QA, CHANGE_WAIT_QAM),
	("review_change", FLOW_STB_CHANGE, CHANGE_WAIT_QA, CHANGE_WAIT_QP),
	("approve_change_general", FLOW_STB_CHANGE, CHANGE_WAIT_QAM, CHANGE_APPROVED),
	("approve_change_major", FLOW_STB_CHANGE, CHANGE_WAIT_QP, CHANGE_APPROVED),
	("reject_change", FLOW_STB_CHANGE, CHANGE_WAIT_QA, CHANGE_REJECTED),
	("reject_change", FLOW_STB_CHANGE, CHANGE_WAIT_QAM, CHANGE_REJECTED),
	("reject_change", FLOW_STB_CHANGE, CHANGE_WAIT_QP, CHANGE_REJECTED),
	("cancel_change", FLOW_STB_CHANGE, CHANGE_DRAFT, CHANGE_CANCELLED),
	("implement_change", FLOW_STB_CHANGE, CHANGE_APPROVED, CHANGE_IMPLEMENTED),
	("assess_change", FLOW_STB_CHANGE, CHANGE_IMPLEMENTED, CHANGE_ASSESSED),
	("assess_change", FLOW_STB_CHANGE, CHANGE_IMPLEMENTED, CHANGE_ASSESS_FAILED),
	# 6.3.8 FLOW_STB_FAULT
	("start_fault_handling", FLOW_STB_FAULT, FAULT_PENDING, FAULT_HANDLING),
	("close_fault_ticket", FLOW_STB_FAULT, FAULT_PENDING, FAULT_CLOSED),
	("submit_fault_assessment", FLOW_STB_FAULT, FAULT_HANDLING, FAULT_WAIT_ASSESS),
	("return_fault_handling", FLOW_STB_FAULT, FAULT_WAIT_ASSESS, FAULT_HANDLING),
	("close_fault_ticket", FLOW_STB_FAULT, FAULT_HANDLING, FAULT_CLOSED),
	("close_fault_ticket", FLOW_STB_FAULT, FAULT_WAIT_ASSESS, FAULT_CLOSED),
]

ACTION_ADMISSION_ONLY |= {
	"record_result", "revise_result", "create_stability_report", "review_report", "eval_trend",
}
SYSTEM_TRIGGERED_ACTIONS |= {"mark_superseded"}
# R8D 准入动作：review_change 状态不变（审核落分流由服务内决定）；open_fault_ticket 为
# 创建（无源状态，R8C 的 record_result / create_stability_report 同口径不进转移表）；
# log_room_env / manage_equipment 为记录/台账类动作（FLOW 无状态机）
ACTION_ADMISSION_ONLY |= {"review_change", "open_fault_ticket", "log_room_env", "manage_equipment"}

# ---------------------------------------------------------------------------
# 业务键（方案 5.4.1 / 5.4.2；分隔符 `#`，入键成分禁 `#`）
# ---------------------------------------------------------------------------

NAMING_RESULT = "HBOS-STB-RES-.YYYY.-"
NAMING_REPORT = "HBOS-STB-RPT-.YYYY.-"

REPORT_TYPES = ["年度趋势分析报告", "工艺验证稳定性报告", "专项（客户要求）", "APQR 年度稳定性汇总"]
REPORT_TYPE_SPECIAL = "专项（客户要求）"

# report_type ↔ source_doctype 允许集合（方案 5.4.2 映射表）
REPORT_SOURCE_MAP = {
	"工艺验证稳定性报告": {"HBOS Stability Protocol"},
	"年度趋势分析报告": {"HBOS Stability Notice"},
	"APQR 年度稳定性汇总": {None, ""},
	"专项（客户要求）": {"HBOS Stability Protocol", "HBOS Stability Sample", None, ""},
}

BASELINE_REFS = ["0月", "出厂全检", "首点"]
BASELINE_SOURCE_MAP = {
	"0月": {"HBOS Test Result", "HBOS COA", "HBOS Stability Result"},
	"出厂全检": {"HBOS Test Result", "HBOS COA"},
	"首点": {"HBOS Stability Result"},
}

RESULT_SOURCES = ["自检", "出厂全检", "委外"]


def make_result_version_key(timepoint, item_code, revision_no):
	"""结果版本键（unique 单字段）：`{timepoint}#{item_code}#{revision_no:02d}`。"""
	return "{}#{}#{:02d}".format(timepoint or "", item_code or "", int(revision_no or 1))


def make_report_period_key(product_code, year, report_type, source_doctype=None,
						   source_name=None, client_code=None, seq=None):
	"""报告防重键（方案 5.4.2）。

	常规：`{product_code}#{year}#{report_type}#{source_doctype or '-'}#{source_name or '-'}`
	专项：`…#专项#{source_doctype or '-'}#{source_name or '-'}#{client_code}#{seq:02d}`
	"""
	base = "{}#{}#{}#{}#{}".format(
		product_code or "", int(year or 0), report_type or "",
		source_doctype or "-", source_name or "-")
	if report_type == REPORT_TYPE_SPECIAL:
		return "{}#{}#{:02d}".format(base, client_code or "", int(seq or 0))
	return base


def check_report_key_parts(product_code, source_name=None, client_code=None):
	"""入键成分禁 `#` 且长度受限（方案 P2 rev14）。返回 (ok, error)。"""
	for value, label in ((product_code, "产品编码"), (source_name, "来源单据编号"),
						 (client_code, "客户编码")):
		if value is None or value == "":
			continue
		if "#" in str(value):
			return False, "{}不得包含 `#`（业务键分隔符）。".format(label)
		if len(str(value)) > 40:
			return False, "{}不得超过 40 个字符。".format(label)
	return True, None


CUSTOMER_CODE_PATTERN = r"^[A-Z0-9_-]{1,40}$"


def check_customer_code(code):
	"""Customer 文档名命名规范（方案 5.4.2 ②）：大写字母/数字/`-`/`_`，≤40，禁 `#`。"""
	import re
	text = (code or "").strip()
	if not text:
		return False, "客户编码不得为空。"
	if not re.match(CUSTOMER_CODE_PATTERN, text):
		return False, ("客户编码「{}」不符合命名规范：仅允许大写字母、数字、`-`、`_`，"
					   "长度 ≤ 40，且不得含 `#`。请修正 ERPNext Customer 文档名后重试。").format(text)
	return True, None


def check_report_scope(report_type, source_doctype, customer, client_code, seq):
	"""报告范围校验（方案 5.4.2 映射表 + P2 rev14）。返回 (ok, error)。"""
	if report_type not in REPORT_TYPES:
		return False, "报告类型「{}」不在受控枚举内。".format(report_type)
	allowed = REPORT_SOURCE_MAP.get(report_type, set())
	if (source_doctype or None) not in allowed and (source_doctype or "") not in allowed:
		return False, "报告类型「{}」不允许来源单据类型「{}」。".format(report_type, source_doctype or "空")
	if report_type == REPORT_TYPE_SPECIAL:
		if not customer or not client_code:
			return False, "专项报告必须指定客户（customer）并带出客户编码。"
		if not seq or int(seq) <= 0:
			return False, "专项报告必须分配序号（seq）。"
		ok, err = check_customer_code(client_code)
		if not ok:
			return False, err
	else:
		if customer or client_code or seq:
			return False, "非专项报告不得填写客户、客户编码与序号（防键语义漂移）。"
	return True, None


# ---------------------------------------------------------------------------
# 7.4 显著变化判定（配置驱动）
# ---------------------------------------------------------------------------

SIG_RELATIVE = "相对变化超阈值"
SIG_OVER_LIMIT = "超规格限度"
SIG_QUALITATIVE = "定性不符标准"
SIG_SKIP = "不参与判定"

DEFAULT_CHANGE_THRESHOLD = 5.0

QUALITATIVE_PASS_WORDS = {"符合规定", "符合", "符合标准", "合格", "正常"}


def check_significant_change(rule, result_value, baseline=None, threshold=None,
							 limits_type=None, lower=None, upper=None,
							 result_type="数值型"):
	"""显著变化判定（方案 7.4）。返回 (is_significant, basis_text)。

	规则由 `HBOS Stability Test Item.significant_change_rule` 配置驱动，不硬编码。
	"""
	if rule == SIG_SKIP:
		return False, "规则为「不参与判定」，仅记录结果"
	if result_value is None or str(result_value).strip() == "":
		return False, "结果缺失，不判定（完备性进看板提示）"

	if rule == SIG_RELATIVE:
		if result_type != "数值型":
			return False, "非数值结果不做相对变化计算（结果类型：{}）".format(result_type)
		if baseline is None or str(baseline).strip() == "":
			return False, "无可用基线，不做相对判定"
		try:
			r = float(result_value)
			b = float(baseline)
		except (TypeError, ValueError):
			return False, "结果或基线非数值，不做相对判定"
		if b <= 0:
			return False, "基线 ≤ 0，不做相对判定（除零保护）"
		th = float(threshold) if threshold not in (None, "") else DEFAULT_CHANGE_THRESHOLD
		change = abs(r - b) / b * 100
		if change >= th:
			return True, "相对基线变化 {:.1f}% ≥ {:.0f}%（基线 {}）".format(change, th, b)
		return False, "相对基线变化 {:.1f}% < {:.0f}%".format(change, th)

	if rule == SIG_OVER_LIMIT:
		verdict = rc.judge_result(result_value, limits_type or rc.LIMITS_RECORD, lower, upper)
		limit_text = _limit_text(limits_type, lower, upper)
		if verdict == rc.VERDICT_FAIL:
			return True, "超出规格限度（{}）".format(limit_text)
		if verdict == rc.VERDICT_UNDETERMINED:
			return False, "结果无法判定（{}）".format(limit_text)
		return False, "在规格限度内（{}）".format(limit_text)

	if rule == SIG_QUALITATIVE:
		text = str(result_value).strip()
		if text in QUALITATIVE_PASS_WORDS:
			return False, "定性判定符合标准（{}）".format(text)
		return True, "定性判定不符标准：{}".format(text)

	return False, "未识别的判定规则：{}".format(rule)


def _limit_text(limits_type, lower, upper):
	if limits_type == rc.LIMITS_UP:
		return "上限 {}".format(upper)
	if limits_type == rc.LIMITS_DOWN:
		return "下限 {}".format(lower)
	if limits_type == rc.LIMITS_RANGE:
		return "{} ~ {}".format(lower, upper)
	return "记录型（不判定）"


# ---------------------------------------------------------------------------
# 7.5 趋势（仅规格限 + 折线 + 线性趋势线；**不计算统计控制限**）
# ---------------------------------------------------------------------------

def fit_trend_line(points):
	"""最小二乘线性拟合。points = [(x, y), ...]；点数 < 2 或退化时返回 None。"""
	pts = []
	for x, y in (points or []):
		if x is None or y is None or str(y).strip() == "":
			continue
		try:
			pts.append((float(x), float(y)))
		except (TypeError, ValueError):
			continue
	if len(pts) < 2:
		return None
	n = len(pts)
	sx = sum(p[0] for p in pts)
	sy = sum(p[1] for p in pts)
	sxx = sum(p[0] * p[0] for p in pts)
	sxy = sum(p[0] * p[1] for p in pts)
	den = n * sxx - sx * sx
	if abs(den) < 1e-12:
		return None
	slope = (n * sxy - sx * sy) / den
	intercept = (sy - slope * sx) / n
	mean_y = sy / n
	ss_tot = sum((p[1] - mean_y) ** 2 for p in pts)
	ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in pts)
	r2 = 1.0 if ss_tot < 1e-12 else max(0.0, 1 - ss_res / ss_tot)
	return {
		"slope": round(slope, 6),
		"intercept": round(intercept, 6),
		"r2": round(r2, 4),
		"n": n,
	}


# ---------------------------------------------------------------------------
# 7.6 ICH Q1E 有效期外推（仅建议不定值）
#
# 方案列出五种情形；多情形同时成立时的**优先级**方案未指定，本实现按
# 「不能外推 > 长期数据充分 > 相关性支持 > 6 月加速显著变化 > 均微小变化」取值。
# ---------------------------------------------------------------------------

VALIDITY_TYPES = ["有效期", "复检期"]


def advise_validity(x_months, sig_change_3m=False, sig_change_6m=False,
					intermediate_ok=False, correlated=False,
					long_term_sufficient=False, refrigerated=False):
	"""ICH Q1E 外推建议（方案 7.6）。返回 (months|None, branch, basis)。"""
	x = int(x_months or 0)
	if x <= 0:
		return None, "数据不足", "无长期数据覆盖，无法外推"
	if sig_change_3m:
		return None, "3 月加速显著变化", \
			"不能外推；应缩短再检测日期/保质期，长期数据有变异性时需统计分析"
	if long_term_sufficient:
		if refrigerated:
			y = min(int(x * 1.5), x + 6)
			return y, "长期数据充分支持（冷藏）", "Y ≤ 1.5X 且 ≤ X+6 月（X={} 月）".format(x)
		y = min(int(x * 2), x + 12)
		return y, "长期数据充分支持", "Y ≤ 2X 且 ≤ X+12 月（X={} 月）".format(x)
	if correlated:
		y = min(x + 3, int(x * 2))
		return y, "有相关性数据支持", "Y ≤ X+3 月（X={} 月）".format(x)
	if sig_change_6m:
		if intermediate_ok:
			y = min(int(x * 1.5), x + 6)
			return y, "6 月加速显著变化 + 中间条件支持", "Y ≤ 1.5X 且 ≤ X+6 月（X={} 月）".format(x)
		return None, "6 月加速显著变化", "中间条件结果不充分，不能外推"
	y = min(int(x * 1.5), x + 6)
	return y, "长期与加速均微小变化且有统计分析支持", "Y ≤ 1.5X 且 ≤ X+6 月（X={} 月）".format(x)


# ---------------------------------------------------------------------------
# 工作日（趋势评估 5 个工作日；依 Holiday List，缺配置时退化为自然日）
# ---------------------------------------------------------------------------

def add_working_days(start_date, days, holidays=None):
	"""自 `start_date` 起加 `days` 个工作日（跳过周末与 holidays）。"""
	base = _as_date(start_date)
	if not base:
		return None
	holidays = set(holidays or [])
	added = 0
	cur = base
	while added < int(days or 0):
		cur = cur + datetime.timedelta(days=1)
		if cur.weekday() >= 5 or cur in holidays:
			continue
		added += 1
	return cur
