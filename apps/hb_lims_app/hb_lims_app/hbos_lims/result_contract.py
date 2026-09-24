# -*- coding: utf-8 -*-
"""LIMS 结果判定与修约契约（零 Frappe 依赖，可离线单测）。

业务口径来自《海滨药业LIMS系统开发方案》模块 2/3：
- 检验项目定义限度（上限 / 下限 / 区间 / 记录型）与有效位数
- 结果自动判定（合格 / 不合格 / OOS 候选 / 不适用）
- 修约采用中国药典四舍六入五成双（ROUND_HALF_EVEN）
"""

from decimal import Decimal
from decimal import ROUND_HALF_EVEN

# 限度模式
LIMITS_UP = "上限"
LIMITS_DOWN = "下限"
LIMITS_RANGE = "区间"
LIMITS_RECORD = "记录型"

# 判定结果
VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_OOS = "oos_candidate"
VERDICT_NA = "not_applicable"
VERDICT_UNDETERMINED = "undetermined"

VERDICT_LABELS = {
    VERDICT_PASS: "合格",
    VERDICT_FAIL: "不合格",
    VERDICT_OOS: "OOS候选",
    VERDICT_NA: "不适用",
    VERDICT_UNDETERMINED: "无法判定",
}

# 公式类型
FORMULA_CONTENT_PERCENT = "含量%内置模板"


class FormulaError(ValueError):
	"""计算公式执行失败（参数缺失、非法或除零）。"""


def judge_result(value, limits_type, lower=None, upper=None):
	"""按限度模式自动判定结果。

	- 记录型：返回 not_applicable（结果以文字记录，如"符合规定"）
	- 值为空 / None：返回 undetermined（无法判定，需人工确认）
	- 上限模式：value <= upper -> pass，否则 fail
	- 下限模式：value >= lower -> pass，否则 fail
	- 区间模式：lower <= value <= upper -> pass，否则 fail
	- fail 语义 = 不合格 = OOS 候选（由调用方置位锁定，参考 OOS 触发接口）

	:param value: 结果数值（数字或可转 Decimal 的字符串）
	:param limits_type: LIMITS_UP / LIMITS_DOWN / LIMITS_RANGE / LIMITS_RECORD
	:param lower: 下限（下限 / 区间模式必需）
	:param upper: 上限（上限 / 区间模式必需）
	"""
	if limits_type == LIMITS_RECORD:
		return VERDICT_NA
	if value is None or value == "":
		return VERDICT_UNDETERMINED
	try:
		v = Decimal(str(value))
		lo = Decimal(str(lower)) if lower not in (None, "") else None
		hi = Decimal(str(upper)) if upper not in (None, "") else None
	except Exception:
		return VERDICT_UNDETERMINED
	if limits_type == LIMITS_UP:
		return VERDICT_UNDETERMINED if hi is None else (VERDICT_PASS if v <= hi else VERDICT_FAIL)
	if limits_type == LIMITS_DOWN:
		return VERDICT_UNDETERMINED if lo is None else (VERDICT_PASS if v >= lo else VERDICT_FAIL)
	if limits_type == LIMITS_RANGE:
		if lo is None or hi is None:
			return VERDICT_UNDETERMINED
		return VERDICT_PASS if lo <= v <= hi else VERDICT_FAIL
	raise ValueError("未知限度模式: %s" % limits_type)


def round_significant(value, digits):
	"""四舍六入五成双修约（中国药典惯例，ROUND_HALF_EVEN）。

	:param digits: 小数位数（如 2 表示修约到小数点后 2 位）
	示例：0.125 -> 0.12；0.135 -> 0.14；1.245 -> 1.24；1.235 -> 1.24
	"""
	d = Decimal(str(value))
	return float(d.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_EVEN))


def apply_formula(raw_params, formula_type):
	"""按公式类型计算结果（当前支持含量 % 内置模板）。

	含量 %：result = A样 × C对 × D稀释 / (A对 × W样) × 100
	参数：a_sample（样品峰面积）、c_standard（对照浓度）、
	      dilution（稀释倍数）、a_standard（对照峰面积）、w_sample（称样量）

	参数缺失 / 非法或分母为 0 -> FormulaError
	"""
	if formula_type == FORMULA_CONTENT_PERCENT:
		try:
			a_sample = Decimal(str(raw_params["a_sample"]))
			c_standard = Decimal(str(raw_params["c_standard"]))
			dilution = Decimal(str(raw_params["dilution"]))
			a_standard = Decimal(str(raw_params["a_standard"]))
			w_sample = Decimal(str(raw_params["w_sample"]))
		except (KeyError, TypeError, ValueError):
			raise FormulaError("含量%%公式缺少或非法参数: %s" % sorted(raw_params.keys()))
		if a_standard == 0 or w_sample == 0:
			raise FormulaError("含量%%公式分母为 0（对照峰面积或称样量）")
		# 全程 Decimal 计算，API 边界保持兼容的 float 返回。
		return float((a_sample * c_standard * dilution) / (a_standard * w_sample) * Decimal("100"))
	raise ValueError("未知公式类型: %s" % formula_type)


def verdict_to_label(verdict):
	"""判定结果中文映射（合格 / 不合格 / OOS候选 / 不适用 / 无法判定）。"""
	return VERDICT_LABELS.get(verdict, str(verdict))
