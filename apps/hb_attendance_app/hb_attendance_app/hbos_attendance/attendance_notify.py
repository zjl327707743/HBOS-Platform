"""考勤通知：把当日部门到岗统计渲染成群消息并（出站）推送。

本模块的渲染与请求体构造是纯函数（无 frappe / 无网络），便于离线测试；
发送与调度在 Task 5 追加，依赖 frappe 与 requests。
"""
import os  # noqa: F401  (Task 5 使用；本任务保持模块可独立导入)

TITLE_PREFIX = "【考勤到岗】"
EMPTY_HINT = "（今日暂无应出勤人员）"
NO_CARD_HINT = "（晚班 20:00 / 夜班 0:00 上班，未到班次时间不计入未打卡）"

_DEPT_COL = 20          # 部门名显示宽度（西文按 1，中文按 2 计算）
# 每个数字列比表头自身宽 1 格：否则中文表头正好填满，"应出勤已到岗未打卡迟到" 会连成一片
_NUM_COLS = [("应出勤", 7), ("已到岗", 7), ("未打卡", 7), ("迟到", 6)]


def _width(s):
    """中文按 2 个字符宽度计算，用于纯文本表格对齐。"""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in s)


def _pad(s, w):
    return s + " " * max(0, w - _width(s))


def render_report(date_str, hhmm, dept_stats):
    """渲染群消息文本；不含全厂汇总行（Owner 确认只看部门）。"""
    lines = ["%s%s %s" % (TITLE_PREFIX, date_str, hhmm), ""]
    rows = [d for d in dept_stats if (d.get("expected") or 0) > 0]
    if not rows:
        lines.append(EMPTY_HINT)
        return "\n".join(lines)
    header = _pad("部门", _DEPT_COL) + "".join(_pad(t, w) for t, w in _NUM_COLS)
    lines.append(header.rstrip())
    for d in rows:
        lines.append(
            _pad(d["dept"], _DEPT_COL)
            + _pad(str(d.get("expected", 0)), _NUM_COLS[0][1])
            + _pad(str(d.get("present", 0)), _NUM_COLS[1][1])
            + _pad(str(d.get("noCard", 0)), _NUM_COLS[2][1])
            + _pad(str(d.get("late", 0)), _NUM_COLS[3][1])
        )
    lines.append("")
    lines.append(NO_CARD_HINT)
    return "\n".join(lines)


def _to_snake(d):
    return {
        "dept": d.get("dept"),
        "total": d.get("total", 0),
        "expected": d.get("expected", 0),
        "present": d.get("present", 0),
        "no_card": d.get("noCard", 0),
        "out_only": d.get("outOnly", 0),
        "unknown_time": d.get("unknownTime", 0),
        "not_started": d.get("notStarted", 0),
        "late": d.get("late", 0),
        "absent": d.get("absent", 0),
        "leave": d.get("leave", 0),
    }


def _hhmm_of(generated_at):
    """从 "YYYY-MM-DD HH:MM:SS" 取 "HH:MM"；格式异常时回退空串（不抛）。"""
    try:
        parts = str(generated_at).split(" ")
        if len(parts) >= 2 and len(parts[1]) >= 5:
            return parts[1][:5]
    except Exception:
        pass
    return ""


def build_payload(date_str, generated_at, text, dept_stats):
    """构造待 POST 的 JSON 体。"""
    return {
        "type": "attendance_daily",
        "date": date_str,
        "generated_at": generated_at,
        "title": ("%s%s %s" % (TITLE_PREFIX, date_str, _hhmm_of(generated_at))).strip(),
        "text": text,
        "dept_stats": [_to_snake(d) for d in dept_stats],
    }


def should_send_now(now_bj):
    """仅北京时间 09:00-09:59 触发发送（cron 时刻不可信, 以守卫为准）。"""
    return now_bj.hour == 9


# ---- 以下依赖 frappe / requests ----

def _bj_now():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)


def _sent_key(date_str):
    return "hbos_notify_sent:%s" % date_str


def already_sent(date_str):
    import frappe
    return bool(frappe.cache.get_value(_sent_key(date_str)))


def mark_sent(date_str):
    import frappe
    frappe.cache.set_value(_sent_key(date_str), "1")


def post_to_webhook(url, token, payload):
    """POST 到 OpenClaw；永不抛异常，返回 (是否成功, 说明)。"""
    import requests
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer %s" % token
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if 200 <= r.status_code < 300:
            return True, "HTTP %s" % r.status_code
        return False, "HTTP %s: %s" % (r.status_code, (r.text or "")[:200])
    except Exception as e:
        return False, str(e)


def send_daily_report(force=False):
    """scheduler 入口：算当日部门统计 → 渲染 → 出站推送。

    守卫：北京时间 09:00-09:59（force=True 时跳过，供干跑验证）；
    幂等：同日已发送则跳过；未配 webhook 静默跳过；
    异常：只记 Error Log，不抛（不影响调度器）。
    """
    import frappe
    from hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data import get_data

    try:
        now = _bj_now()
        date_str = now.strftime("%Y-%m-%d")
        if not force and not should_send_now(now):
            return {"skipped": "not_9am_bj"}
        if not force and already_sent(date_str):
            return {"skipped": "already_sent"}

        data = get_data(department=None, date_str=date_str)
        dept_stats = data.get("dept_stats") or []
        text = render_report(date_str, now.strftime("%H:%M"), dept_stats)
        payload = build_payload(date_str, now.strftime("%Y-%m-%d %H:%M:%S"), text, dept_stats)

        dry = os.environ.get("HBOS_NOTIFY_DRY_RUN", "") == "1"
        url = os.environ.get("HBOS_NOTIFY_WEBHOOK_URL", "")
        if dry or not url:
            frappe.log_error(text, "HBOS考勤通知(未发送: %s)" % ("dry_run" if dry else "no_webhook"))
            if dry:
                mark_sent(date_str)
            return {"sent": False, "reason": "dry_run" if dry else "no_webhook", "text": text}

        ok, msg = post_to_webhook(url, os.environ.get("HBOS_NOTIFY_TOKEN", ""), payload)
        if ok:
            mark_sent(date_str)
            return {"sent": True, "detail": msg}
        frappe.log_error("%s\n%s" % (msg, text), "HBOS考勤通知发送失败")
        return {"sent": False, "reason": msg}
    except Exception as e:
        frappe.log_error(str(e), "HBOS考勤通知异常")
        return {"sent": False, "reason": str(e)}
