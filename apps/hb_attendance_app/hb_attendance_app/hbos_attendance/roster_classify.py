"""HBOS 班次人员归类纯函数（无 Frappe 依赖，可离线测试）。

归行优先级（班次人员维护表导出设计文档 §三）：豁免 > 绑定班次 > 名单 > 通用倒班。
"""
from hb_attendance_app.hbos_attendance.pairing import (
    FOUR_SHIFT_NUMS, SPECIAL_SHIFT_NUMS,
)
from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)

# 名单 → 主表班次体系（按优先级 2-6 排序）
LIST_SYSTEMS = (
    (SPECIAL_SHIFT_NUMS, "无菌倒班"),
    (FOUR_SHIFT_NUMS, "四班次倒班"),
    (ADMIN_NUMS, "行政班"),
    (SAFETY_NUMS, "安全倒班"),
    (FOOD_NUMS, "食堂"),
)


def classify(emp_num, bound_shift_type=""):
    """返回员工在主表中的班次体系；豁免返回 ""（不进主表）。

    优先级: 豁免 > 绑定班次(bound_shift_type) > 名单 > 通用倒班。
    bound_shift_type 由调用方从绑定规则解析（如 早班/行政班/8:30班/晚班）。
    """
    if emp_num in EXEMPT_NUMS:
        return ""
    if bound_shift_type:
        return bound_shift_type
    for nums, label in LIST_SYSTEMS:
        if emp_num in nums:
            return label
    return "通用倒班"
