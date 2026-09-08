# -*- coding: utf-8 -*-
"""M2-R7 留样业务契约（零 Frappe 依赖，可离线单测）。

业务口径来自 JXH-SOP-LC-1-00-007-09《留样管理规程》（09 版）与
《M2-R7 留样管理板块开发方案》rev6 第四/五/七/九节：
- 分类与数量（2 倍 / <1g / 液体拦截 / 受托转出 / UOM 受控）
- 期限（留样期至 = 效期 + 3 年）
- 业务键（产品#批号#容器、留样#观察偏移）
- 库存锁内复核规则（7.3 表）
- Sample→留样来源映射（第九节 6 规则）
"""

# ---------------------------------------------------------------------------
# 留样生命周期状态（方案 6.1 rev6）
# ---------------------------------------------------------------------------

RET_IN_STOCK = "在库"
RET_PARTIAL_USED = "部分使用"
RET_EXHAUSTED = "已用尽"
RET_PENDING = "待处理"
RET_DESTROYED = "已销毁"
RET_TRANSFERRED = "已转出"

RETENTION_TRANSITIONS = {
	RET_IN_STOCK: {RET_PARTIAL_USED, RET_PENDING, RET_TRANSFERRED},
	RET_PARTIAL_USED: {RET_PARTIAL_USED, RET_EXHAUSTED, RET_PENDING, RET_TRANSFERRED},
	RET_EXHAUSTED: {RET_PENDING, RET_TRANSFERRED},
	# 回退按进入待处理前的状态快照恢复（rev6）：驳回退出 / 续留回写
	RET_PENDING: {RET_DESTROYED, RET_IN_STOCK, RET_PARTIAL_USED},
	RET_DESTROYED: set(),
	RET_TRANSFERRED: set(),
}

# ---------------------------------------------------------------------------
# UOM 受控枚举（方案 5.1 default_uom，全板块唯一权威）
# ---------------------------------------------------------------------------

UOM_OPTIONS = ["g", "kg", "mg", "mL", "L", "瓶", "支", "袋", "桶", "盒", "其他"]

# Sample→留样 来源映射（方案第九节）
# 白名单兼容实际主数据：HBOS Sample.sample_type 为 Link 到 HBOS Sample Type，
# 本环境原料类样品类型名为「原材料」（历史沿用），「原料」亦保留兼容（P1 修复）
SAMPLE_TYPE_WHITELIST = {"原料", "原材料", "成品"}  # 原料/原材料→关键物料、成品→成品（原料药）
SAMPLE_STATUS_WHITELIST = {"检验完成", "已放行"}
RECURSION_SAMPLE_SOURCE = "留样"  # 防递归：sample_source=留样 的样品不得再生成留样

# 类别映射
SAMPLE_TYPE_TO_CATEGORY = {"原料": "关键物料", "原材料": "关键物料", "成品": "成品（原料药）"}


def can_retention_transition(current, target):
	"""留样状态转移合法性。"""
	allowed = RETENTION_TRANSITIONS.get(current)
	return bool(allowed) and target in allowed


def uom_gate(full_test_qty_uom, default_uom):
	"""UOM 一致性闸（方案 4.1 rev4）：仅两 UOM 一致时允许自动计算 2 倍。

	返回 (allow_auto_calc, error_message)。
	"""
	if not full_test_qty_uom or not default_uom:
		return False, None  # 未填全检量单位 → 不自动算，也不报错（人工填写）
	if full_test_qty_uom == default_uom:
		return True, None
	return False, "全检量单位与产品默认单位不一致，请人工填写留样量（系统不做换算）。"


def calc_retention_qty(retention_qty_rule, full_test_qty, full_test_qty_uom, default_uom):
	"""留样量自动计算（方案 4.1）：全检量 2 倍，受 UOM 一致性闸约束。

	返回 (qty, error_message)——qty 为 None 表示不自动计算。
	"""
	if retention_qty_rule != "全检量 2 倍":
		return None, None
	if not full_test_qty:
		return None, None
	allow, err = uom_gate(full_test_qty_uom, default_uom)
	if not allow:
		return None, err
	return full_test_qty * 2, None


def min_qty_note(full_test_qty, full_test_qty_uom):
	"""全检量 < 1g 按 1g 计（非硬拦截，提示人工确认）。"""
	if full_test_qty is not None and full_test_qty < 1 and full_test_qty_uom == "g":
		return "全检量小于 1g，按规程以 1g 计，请人工复核留样量。"
	return None


def generate_product_batch_container_key(product_code, batch_no, container_no):
	"""业务键（方案 5.7）：{product_code}#{batch_no}#{container_no:02d}。"""
	return "{}#{}#{:02d}".format(product_code or "", batch_no or "", container_no or 1)


def generate_sample_period_key(retention_sample, obs_month):
	"""观察业务键（方案 5.7）：{retention_sample}#{obs_month:03d}。"""
	return "{}#{:03d}".format(retention_sample or "", obs_month or 0)


# ---------------------------------------------------------------------------
# 库存锁内复核规则（方案 7.3 rev6）
# ---------------------------------------------------------------------------

def check_confirm_stock(current_qty, reserved_qty, apply_qty):
	"""库存确认+预占：current_qty - reserved_qty >= apply_qty（锁内重读两值计算）。"""
	available = (current_qty or 0) - (reserved_qty or 0)
	if available < (apply_qty or 0):
		return False, "可用量不足（当前结存 {} - 预占 {} = {}，申请 {}）。".format(
			current_qty or 0, reserved_qty or 0, available, apply_qty or 0)
	return True, None


def check_execute_usage(current_qty, reserved_qty, apply_qty):
	"""使用执行（rev4 修正）：本单预占有效性 + 总量守恒，不用 available_qty 判本单。"""
	if (reserved_qty or 0) < (apply_qty or 0):
		return False, "本单预占已不在（预占 {} < 申请 {}），可能已被释放，请重新确认库存。".format(
			reserved_qty or 0, apply_qty or 0)
	if (current_qty or 0) < (reserved_qty or 0):
		return False, "结存不足以覆盖在途预占（结存 {} < 预占 {}），库存异常。".format(
			current_qty or 0, reserved_qty or 0)
	return True, None


def check_execute_disposal(qty, current_qty, reserved_qty):
	"""销毁执行：qty == current_qty 且 reserved_qty == 0（整批终结，数量不等于结存拒绝）。"""
	if (reserved_qty or 0) != 0:
		return False, "该留样存在在途预占，不得销毁。"
	if (qty or 0) != (current_qty or 0):
		return False, "销毁数量必须等于当前结存（申请 {}，结存 {}）。".format(
			qty or 0, current_qty or 0)
	return True, None


def check_transfer_out(reserved_qty):
	"""受托转出：有在途预占不得转出。"""
	if (reserved_qty or 0) != 0:
		return False, "该留样存在在途预占，不得转出。"
	return True, None


def check_adjust_stock(current_qty, reserved_qty, new_current_qty):
	"""手动调整（rev6 R7A 边界）：调整后不得低于预占量且不为负（预占相关用例在 R7C）。"""
	if (new_current_qty or 0) < 0:
		return False, "调整后结存不得为负。"
	if (new_current_qty or 0) < (reserved_qty or 0):
		return False, "调整后结存不得低于预占量（预占 {}）。".format(reserved_qty or 0)
	return True, None


def check_release_reservation(reserved_qty, apply_qty, from_state):
	"""释放预占（rev6 P1 修正）：本单必须已过库存确认才释放；聚合守卫仅防重复。

	from_state ∈ 待QC批准/待QA批准/待QM批准/已批准 = 本单持有预占；
	草稿/待库存确认 阶段的驳回与取消不触发释放。
	"""
	if from_state not in ("待QC批准", "待QA批准", "待QM批准", "已批准"):
		return False, None  # 本单未持有预占：不释放，也不报错（幂等跳过）
	if (reserved_qty or 0) < (apply_qty or 0):
		return False, "预占释放失败（预占 {} < 申请 {}），疑似重复释放。".format(
			reserved_qty or 0, apply_qty or 0)
	return True, None


# ---------------------------------------------------------------------------
# Sample→留样 来源映射（方案第九节 6 规则）
# ---------------------------------------------------------------------------

def check_sample_source_mapping(sample_type, sample_status, sample_source, material_code, product_exists):
	"""从 HBOS Sample 创建留样的前置校验，返回 (ok, error_message)。

	参数：
	- sample_type / sample_status / sample_source：HBOS Sample 三字段
	- material_code：HBOS Sample.material_code
	- product_exists：对应 Retention Product 是否已存在（不自动创建）
	"""
	if sample_type == "稳定性样品":
		return False, "稳定性考察样品不属于留样（规程范围界定），禁止生成留样。"
	if sample_type not in SAMPLE_TYPE_WHITELIST:
		return False, "样品类型「{}」不在留样白名单（原料 / 成品）内。".format(sample_type)
	if sample_status not in SAMPLE_STATUS_WHITELIST:
		return False, "样品状态须为 检验完成 / 已放行（当前：{}）。".format(sample_status)
	if sample_source == RECURSION_SAMPLE_SOURCE:
		return False, "动用留样产生的检验样品不得再生成留样（防递归）。"
	if not product_exists:
		return False, "物料 {} 未创建留样产品主数据，请先创建（系统不自动创建）。".format(material_code)
	return True, None


def map_sample_type_to_category(sample_type):
	"""原料/原材料→关键物料、成品→成品（原料药）（方案第九节规则 1）。"""
	return SAMPLE_TYPE_TO_CATEGORY.get(sample_type)


# ---------------------------------------------------------------------------
# R7B/R7C 契约纯函数（供 offline 单测）
# ---------------------------------------------------------------------------

OBS_REASON_ANNUAL = "年度观察批（每年 3 批）"
OBS_REASON_SALE = "外售产品每批"
OBS_REASON_OTHER = "其他"
OBS_ANNUAL_CAP = 3


def check_sod_sign(applicant, prev_signer, signer):
	"""两条 SoD 硬校验（方案 6.4）：申请人不得任一级签署；同一用户不得连续两级签署。

	返回 (ok, error_message)。prev_signer 为紧邻上一级签署人（无则 None）。
	"""
	if signer and applicant and signer == applicant:
		return False, "申请人（{}）不得担任本单审批签署人（SoD）。".format(applicant)
	if prev_signer and signer and prev_signer == signer:
		return False, "同一用户（{}）不得在同一单据连续两级签署（SoD）。".format(signer)
	return True, None


def release_requires(from_state):
	"""释放预占前置：仅已过库存确认（持有预占）的阶段才释放（rev6 P1）。"""
	return from_state in ("待QC批准", "待QA批准", "待QM批准", "已批准")
