"""调休纯逻辑：飞书字段映射、调休日展开、加班日解析与核实判定。

纯标准库模块，无 frappe / requests 依赖，可离线单测（与 board_stats.py 同模式）。
判定规则见 docs/superpowers/specs/2026-09-21-调休接入考勤判定设计.md §4。
"""
import re
from datetime import datetime, timedelta, timezone

# 飞书毫秒时间戳按北京时间转日期；用固定 +8 而非容器本地时区，
# 避免容器为 UTC 时把「当日」算成前一天（与 api.py DELICLOUD_TZ 同基准）。
_TZ = timezone(timedelta(hours=8))

REST_LEAVE_APP_TOKEN = "XLD0bPiGXaP0JTsicHCcSLA4nlQ"
REST_LEAVE_TABLE_ID = "tblYHBgNJdvVCiFM"
ID_PREFIX = "feishu-bitable-restleave-"

# 状态机：待解析 → 待核实 → 已核实 / 核实不通过；解析不出加班日 → 解析失败
PARSE_PENDING = "待解析"
VERIFY_PENDING = "待核实"
VERIFY_OK = "已核实"
VERIFY_FAIL = "核实不通过"
VERIFY_PARSE_FAIL = "解析失败"
ALL_STATUSES = (PARSE_PENDING, VERIFY_PENDING, VERIFY_OK, VERIFY_FAIL, VERIFY_PARSE_FAIL)


def ts_to_date(ms):
    """飞书毫秒时间戳 → "YYYY-MM-DD"；空/0/异常返回 None。"""
    try:
        if not ms:
            return None
        return datetime.fromtimestamp(int(ms) / 1000, tz=_TZ).strftime("%Y-%m-%d")
    except Exception:
        return None


def _safe_float(v):
    """调休天数是 Text 字段（实测 115/115 返回 str），脏值回落 0 且不抛异常。

    原实现直接 float()，一条脏值即抛异常并中断整次同步（全批数据丢失）。
    """
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return 0.0


def rest_leave_fields(fields):
    """调休记录 → 待写入字段；缺人员或缺开始日期时返回 None。"""
    num = str(fields.get("调休人员_工号") or "").strip()
    name = str(fields.get("调休人员_姓名") or "").strip()
    start = ts_to_date(fields.get("调休人员_开始时间"))
    if not (num or name) or not start:
        return None
    return {
        "employee_number": num,
        "employee_name": name,
        "start_date": start,
        "end_date": ts_to_date(fields.get("调休人员_结束时间")) or start,
        "rest_days": _safe_float(fields.get("调休人员_调休天数")),
        "remarks": str(fields.get("说明") or ""),
    }
    # 注意：不返回「调休人员_联系电话」——与考勤无关的 PII，不抄第二份。


def expand_dates(start, end):
    """调休日 = [start, end] 闭区间逐日展开；异常输入返回 []。

    刻意不使用「调休天数」字段：实测 104 条中 16 条天数与日期跨度不符
    （如 09-06→09-11 跨 6 天只申报 1 天），用区间可解释、可复核。
    """
    try:
        d = datetime.strptime(str(start)[:10], "%Y-%m-%d").date()
        e = datetime.strptime(str(end or start)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return []
    if e < d:
        d, e = e, d
    out, cur = [], d
    while cur <= e:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out


_PROMPT_HEAD = (
    "你是海滨考勤助理。下面是一条【调休申请】的说明原文。\n"
    "请只提取「该员工本人」在这条申请里申报的【加班日期】。\n"
    "规则：\n"
    "1. 说明可能同时列出多个人的加班（含姓名），只取与【本人姓名】一致的那些；\n"
    "2. 若说明未出现任何姓名，视为本人；\n"
    "3. 日期可能写作「8月2日」「08.02」「8/2」等，一律换算成 YYYY-MM-DD；\n"
    "4. 年份以【申请年】为准；\n"
    "5. 找不到任何日期就只输出「无」；\n"
    "6. 只输出日期，一行一个，不要任何解释文字。\n"
    "注意：说明里提到「调休到 X 号」的日期是休息日，不是加班日，不要输出。\n"
)


def build_overtime_prompt(emp_name, emp_num, remarks, year):
    """构造提取加班日的 prompt。"""
    return (
        _PROMPT_HEAD
        + f"\n【本人姓名】{emp_name}\n【本人工号】{emp_num}\n【申请年】{year}\n"
        + f"【说明原文】\n{remarks}\n\n输出："
    )


def parse_overtime_dates(text, year):
    """解析 LLM 输出 → ["YYYY-MM-DD", ...]；无法解析返回 []。

    只认严格日期，不做模糊匹配——解析不出即「解析失败」，转人工，
    宁可漏判也不猜（猜错会把没加过的班认成加班）。
    """
    if not text:
        return []
    out = []
    for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})", str(text)):
        s = m.group(0)
        if s not in out:
            out.append(s)
    if out:
        return out
    # 容错：模型只回了 M月D日
    for m in re.finditer(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", str(text)):
        s = "%04d-%02d-%02d" % (int(year), int(m.group(1)), int(m.group(2)))
        if s not in out:
            out.append(s)
    return out


def verify_status_for(overtime_dates, paired_dates):
    """加班日是否都有完整配对 → 核实结论。

    paired_dates 由调用方提供（该员工当天存在完整上下班配对的日期集合，
    取自系统已生成的 Attendance）。任一加班日缺失即「核实不通过」。
    """
    if not overtime_dates:
        return VERIFY_PARSE_FAIL
    paired = paired_dates or set()
    return VERIFY_OK if all(d in paired for d in overtime_dates) else VERIFY_FAIL
