"""HBOS 规则看板静态数据（纯函数，无 Frappe 依赖，可离线测试）。

数据源单一: 名单/班次/配对参数全部 import 现有常量，不复制。
"""
from hb_attendance_app.hbos_attendance.pairing import (
    FOUR_SHIFT_NUMS, IN_TERMINAL_SNS, OUT_TERMINAL_SNS, SPECIAL_SHIFT_NUMS,
)
from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)
from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS


def builtin_shifts():
    """8 种内置默认班次。BUILTIN_SHIFTS 值元组: (上班, 下班, 迟到起算, 最小工时)。"""
    return [
        {"shift_type": k, "start_time": v[0], "end_time": v[1],
         "late_after": v[2], "min_hours": v[3]}
        for k, v in BUILTIN_SHIFTS.items()
    ]


def list_groups():
    """名单规则分组（卡片数据）。"""
    return [
        {"key": "ADMIN_NUMS", "title": "行政班名单",
         "desc": "固定 8:30-17:30；08:31 起算迟到；周末双休；名单人员短路规则表",
         "count": len(ADMIN_NUMS), "nums": sorted(ADMIN_NUMS)},
        {"key": "EXEMPT_NUMS", "title": "豁免名单",
         "desc": "管理层等不计入任何异常考勤（不判迟到/早退/缺勤）",
         "count": len(EXEMPT_NUMS), "nums": sorted(EXEMPT_NUMS)},
        {"key": "SPECIAL_SHIFT_NUMS", "title": "无菌/三班独立班次",
         "desc": "无菌早/晚 12h + 早/中/夜 8h 独立班次体系",
         "count": len(SPECIAL_SHIFT_NUMS), "nums": sorted(SPECIAL_SHIFT_NUMS)},
        {"key": "FOUR_SHIFT_NUMS", "title": "四班次倒班",
         "desc": "早/中/夜/8:30班四班次；工作满 8 小时算正常出勤",
         "count": len(FOUR_SHIFT_NUMS), "nums": sorted(FOUR_SHIFT_NUMS)},
        {"key": "SAFETY_NUMS", "title": "安全人员倒班",
         "desc": "早班 8:30 / 晚班 20:30，8:31 / 20:31 起算迟到",
         "count": len(SAFETY_NUMS), "nums": sorted(SAFETY_NUMS)},
        {"key": "FOOD_NUMS", "title": "食堂人员",
         "desc": "不判迟到早退",
         "count": len(FOOD_NUMS), "nums": sorted(FOOD_NUMS)},
        {"key": "IN_TERMINAL_SNS", "title": "上班打卡机",
         "desc": "分机规则（2026-08-15 起）上班卡设备 SN",
         "count": len(IN_TERMINAL_SNS), "nums": sorted(IN_TERMINAL_SNS)},
        {"key": "OUT_TERMINAL_SNS", "title": "下班打卡机",
         "desc": "分机规则（2026-08-15 起）下班卡设备 SN",
         "count": len(OUT_TERMINAL_SNS), "nums": sorted(OUT_TERMINAL_SNS)},
    ]


def pairing_params():
    """配对算法参数（静态描述，值来自 pairing.py / api.py 当前口径）。"""
    return [
        {"name": "打卡去重间隔", "value": "10 分钟",
         "desc": "相邻打卡间隔 < 10 分钟视为重复打卡，保留最早一条"},
        {"name": "最短班次", "value": "2 小时",
         "desc": "不足 2 小时的两张卡不配对，视为重复打卡"},
        {"name": "最长配对（通用）", "value": "16 小时",
         "desc": "超过 16 小时不配对，防漏下班卡导致的假超长班"},
        {"name": "最长配对（环保/质量控制部）", "value": "18 小时",
         "desc": "环保部、质量控制部配对上限放宽到 18h（Owner 2026-08-27）"},
        {"name": "跨天夜班优先锁定", "value": "上班 22:00-24:00 → 次日 04:00-10:00",
         "desc": "先锁定无歧义夜班对（时长 4-12h），避免下班卡被误判早班迟到"},
        {"name": "早晨卡向前配对", "value": "10:00 前卡向前一天 14:00 后上班卡",
         "desc": "倒班员工早晨卡优先向前配对（时长 2-12h）"},
        {"name": "零点夜班配对", "value": "0-4 点卡配当天 04:00-10:00 下班卡",
         "desc": "向前配对失败后尝试（时长 2-12h），迟到起算 00:01"},
        {"name": "分机实施起始日期", "value": "2026-08-15",
         "desc": "此日期起打卡方向按设备 SN 判定；之前回退配对推断"},
        {"name": "GPS/外勤打卡豁免", "value": "是",
         "desc": "当天存在 GPS/外勤打卡视为已出勤，不判缺勤"},
        {"name": "连续无打卡缺勤门槛", "value": "3 天起判",
         "desc": "连续无打卡 1-2 天不判缺勤，连续 3 天及以上判缺勤"},
        {"name": "行政班周末双休", "value": "周六/周日",
         "desc": "行政班名单人员周末无打卡不算缺勤"},
        {"name": "四班次 8 小时口径", "value": "满 8 小时算正常",
         "desc": "四班次人员工作满 8 小时算正常出勤，不足 8 小时置早退标记"},
    ]


def priority_chain():
    """考勤判定优先级链（升序）。"""
    return [
        {"step": 1, "name": "排班表",
         "desc": "HBOS Employee Schedule 指定当天的班次/休息/请假，优先级最高"},
        {"step": 2, "name": "固定班次绑定",
         "desc": "HBOS Employee Shift（多绑定）/ Employee.hbos_fixed_shift，按打卡时间自动匹配"},
        {"step": 3, "name": "部门 / 全局规则",
         "desc": "HBOS Shift Rule：部门专属优先，其次「全部部门」全局规则"},
        {"step": 4, "name": "名单短路",
         "desc": "行政班名单人员短路规则表（08:31 起算迟到等）"},
        {"step": 5, "name": "硬编码兜底",
         "desc": "内置班次时间判定兜底"},
    ]
