"""调休/换班飞书记录 → HBOS 字段的映射（纯模块，无 frappe 依赖，可离线测试）。

列名以飞书表实读结果为准（Owner 2026-09-11）：
  调休: 调休人员_姓名/工号/开始时间/结束时间/调休天数, 说明
  换班: 明细_申请人/申请人工号/替班人/替班人工号/换班日期/还班日期, 说明
本模块只做映射与校验，不查库、不发请求。
"""
from datetime import datetime, timedelta, timezone

# 飞书毫秒时间戳按北京时间转日期；用固定 +8 而非容器本地时区，
# 避免容器为 UTC 时把「当日」算成前一天（与 api.py DELICLOUD_TZ 同基准）。
_TZ = timezone(timedelta(hours=8))

# 换班表链接是 /wiki/ 形式，其 app_token 为 wiki 节点，需先解析真实 obj_token；
# 该常量放在此处便于同步脚本与测试共用。
SWAP_WIKI_NODE = "QVUMwYsggiYGK8kdt0CcJifmnvf"
SWAP_TABLE_ID = "tbltVlpHx6NzG6WG"
REST_LEAVE_APP_TOKEN = "XLD0bPiGXaP0JTsicHCcSLA4nlQ"
REST_LEAVE_TABLE_ID = "tblYHBgNJdvVCiFM"


def ts_to_date(ms):
    """飞书毫秒时间戳 → "YYYY-MM-DD"；空/0/异常返回 None。"""
    try:
        if not ms:
            return None
        return datetime.fromtimestamp(int(ms) / 1000, tz=_TZ).strftime("%Y-%m-%d")
    except Exception:
        return None


def _num(fields, key):
    return str(fields.get(key) or "").strip()


def rest_leave_fields(fields):
    """调休记录 → 待写入字段；缺人员或缺开始日期时返回 None。"""
    num = _num(fields, "调休人员_工号")
    name = _num(fields, "调休人员_姓名")
    start = ts_to_date(fields.get("调休人员_开始时间"))
    if not (num or name) or not start:
        return None
    return {
        "employee_number": num,
        "employee_name": name,
        "start_date": start,
        "end_date": ts_to_date(fields.get("调休人员_结束时间")) or start,
        "rest_days": float(fields.get("调休人员_调休天数") or 0),
        "remarks": str(fields.get("说明") or ""),
    }


def swap_fields(fields):
    """换班记录 → 待写入字段；缺任一方人员或缺换班日期时返回 None。"""
    anum = _num(fields, "明细_申请人工号")
    aname = _num(fields, "明细_申请人")
    snum = _num(fields, "明细_替班人工号")
    sname = _num(fields, "明细_替班人")
    swap_date = ts_to_date(fields.get("明细_换班日期"))
    if not (anum or aname) or not (snum or sname) or not swap_date:
        return None
    return {
        "applicant_number": anum,
        "applicant_name": aname,
        "substitute_number": snum,
        "substitute_name": sname,
        "swap_date": swap_date,
        "repay_date": ts_to_date(fields.get("明细_还班日期")),
        "remarks": str(fields.get("说明") or ""),
    }
