"""HBOS 班次人员归类纯函数。

人员名单来自数据库-backed PolicySet；代码只定义分类优先级。
"""
from hb_attendance_app.hbos_attendance.pairing import (
    FOUR_SHIFT_NUMS, SPECIAL_SHIFT_NUMS,
)
from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)

LIST_SYSTEMS = (
    (SPECIAL_SHIFT_NUMS, "无菌倒班"),
    (FOUR_SHIFT_NUMS, "四班次倒班"),
    (ADMIN_NUMS, "行政班"),
    (SAFETY_NUMS, "安全倒班"),
    (FOOD_NUMS, "食堂"),
)


def classify(emp_num, bound_shift_type="", policies=None):
    """返回员工在主表中的班次体系；豁免返回空字符串。

    policies 仅用于纯单测/离线规则验证；运行态默认读取数据库 PolicySet。
    """
    exempt = EXEMPT_NUMS if policies is None else policies.get("EXEMPT", set())
    systems = LIST_SYSTEMS if policies is None else (
        (policies.get("SPECIAL_SHIFT", set()), "无菌倒班"),
        (policies.get("FOUR_SHIFT", set()), "四班次倒班"),
        (policies.get("ADMIN", set()), "行政班"),
        (policies.get("SAFETY", set()), "安全倒班"),
        (policies.get("FOOD", set()), "食堂"),
    )
    if emp_num in exempt:
        return ""
    if bound_shift_type:
        return bound_shift_type
    for nums, label in systems:
        if emp_num in nums:
            return label
    return "通用倒班"
