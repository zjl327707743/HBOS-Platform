"""考勤通知：把当日部门到岗统计渲染成群消息并（出站）推送。

本模块的渲染与请求体构造是纯函数（无 frappe / 无网络），便于离线测试；
发送与调度在 Task 5 追加，依赖 frappe 与 requests。
"""
import os  # noqa: F401  (Task 5 使用；本任务保持模块可独立导入)

TITLE_PREFIX = "【考勤到岗】"
EMPTY_HINT = "（今日暂无应出勤人员）"
NO_CARD_HINT = "（晚班 20:00 / 夜班 0:00 上班，未到班次时间不计入未打卡）"
MAX_NAMES_PER_DEPT = 6      # 单个部门最多显示的人名数，超出收成「等 N 人」
MAX_EXCEPTION_DEPTS = 10    # 卡片最多列出的异常部门数，超出收成「另有 N 个部门」

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


def build_feishu_payload(card):
    """飞书卡片报文（msg_type=interactive）。

    Owner 2026-09-11：纯文本 + 空格补位在飞书比例字体下必然错列，改发卡片由组件负责对齐。
    """
    return {"msg_type": "interactive", "content": card}


def build_text_payload(text):
    """纯文本报文；卡片渲染失败时降级使用。"""
    return {"msg_type": "text", "content": {"text": text}}


def feishu_result(status_code, body_text):
    """判定飞书响应是否真的成功，返回 (是否成功, 说明)。

    飞书在失败时也可能返回 HTTP 200（如签名不匹配、被限流），错误码在 body 里，
    故不能只看状态码。成功判据：2xx 且 body 的 code / StatusCode 为 0 或缺失。
    body 非 JSON（例如自建网关返回纯文本）时，2xx 即视为成功。
    """
    if not (200 <= status_code < 300):
        return False, "HTTP %s: %s" % (status_code, (body_text or "")[:200])
    try:
        import json
        data = json.loads(body_text or "{}")
    except Exception:
        return True, "HTTP %s" % status_code
    code = data.get("code", data.get("StatusCode")) if isinstance(data, dict) else None
    if code in (0, None):
        return True, "HTTP %s" % status_code
    return False, "HTTP %s code=%s: %s" % (status_code, code, (body_text or "")[:200])


def should_send_now(now_bj):
    """仅北京时间 09:00-09:59 触发发送（cron 时刻不可信, 以守卫为准）。"""
    return now_bj.hour == 9


def collect_exceptions(rows):
    """挑出未打卡 / 迟到的人，按部门聚合。

    归桶不重写规则：对每行调一次 board_stats.summarize_rows([r])，直接取它的
    late / noCard 计数作为该行的归桶判定 —— 与统计口径字面同源，board_stats.py 不改。
    返回只含至少一项异常的部门，部门顺序与 dept_summary 一致（未打卡+迟到降序）。
    """
    from hb_attendance_app.hbos_attendance import board_stats as bs

    buckets = {}
    for r in rows:
        # anomaly_hidden 的行不进任何桶（与看板、统计一致，如设备动力部）
        if r.get("anomaly_hidden"):
            continue
        # 单行统计即该行的归桶判定。expected 为假的行（豁免/休息/请假/班次未定/非班次）
        # 一律不算异常——注意这里不能改用 bs.is_late(r) 单独判迟到，
        # 那会把「非应出勤行 + 迟到标签」也算进来，而 summarize_rows 不计，两处数字就会漂移。
        s = bs.summarize_rows([r])
        if not s["expected"] or not (s["late"] or s["noCard"]):
            continue
        dept = r.get("dept") or "未分组"
        b = buckets.setdefault(dept, {"dept": dept, "noCard": [], "late": []})
        person = {"name": r.get("name") or "", "num": r.get("num") or ""}
        if s["late"]:
            b["late"].append(person)
        if s["noCard"]:
            b["noCard"].append(person)

    order = {s["dept"]: i for i, s in enumerate(bs.dept_summary(rows))}
    out = sorted(buckets.values(), key=lambda b: order.get(b["dept"], len(order)))
    for b in out:
        b["noCard"].sort(key=lambda p: p["num"])
        b["late"].sort(key=lambda p: p["num"])
    return out


CARD_TITLE_PREFIX = "考勤到岗 · "


def _md(content):
    """卡片文本元素（lark_md 支持 **粗体** 与换行）。"""
    return {"tag": "div", "text": {"tag": "lark_md", "content": content}}


def _fmt_names(people):
    """人名串；超过 MAX_NAMES_PER_DEPT 人时收成「等 N 人」，N 必须显式写出。"""
    names = [p["name"] for p in people]
    if len(names) > MAX_NAMES_PER_DEPT:
        return " · ".join(names[:MAX_NAMES_PER_DEPT]) + " 等 %d 人" % (
            len(names) - MAX_NAMES_PER_DEPT)
    return " · ".join(names)


def _counts_text(exc):
    """部门行的计数：只写非零项，不出现「迟到 0」。"""
    parts = []
    if exc["noCard"]:
        parts.append("未打卡 %d" % len(exc["noCard"]))
    if exc["late"]:
        parts.append("迟到 %d" % len(exc["late"]))
    return "　".join(parts)


def _dept_block(exc):
    """一个异常部门：标题行 + 人名行。两类都有时给人名加标签，只有一类时省略标签。"""
    lines = ["**%s**　%s" % (exc["dept"], _counts_text(exc))]
    no_card, late = exc["noCard"], exc["late"]
    if no_card and late:
        lines.append("未打卡：%s" % _fmt_names(no_card))
        lines.append("迟到：%s" % _fmt_names(late))
    elif no_card:
        lines.append(_fmt_names(no_card))
    elif late:
        lines.append(_fmt_names(late))
    return "\n".join(lines)


def _factory_line(stats):
    """全厂汇总：应出勤与已到岗恒显示，未打卡 / 迟到为 0 时省略。"""
    parts = ["应出勤 %d" % stats.get("expected", 0),
             "已到岗 %d" % stats.get("present", 0)]
    if stats.get("noCard"):
        parts.append("未打卡 %d" % stats["noCard"])
    if stats.get("late"):
        parts.append("迟到 %d" % stats["late"])
    return "**全厂**　" + " · ".join(parts)


def _needs_note(stats):
    """有「未到上班时间 / 仅下班卡 / 班次未定」的人时，才需要附口径说明。"""
    return bool(stats.get("notStarted") or stats.get("outOnly") or stats.get("unknownTime"))


def render_card(date_str, hhmm, stats, dept_stats, exceptions):
    """渲染飞书卡片 JSON（纯函数，不涉及网络，不含 msg_type）。

    有异常 → 橙色标题；无异常 → 绿色标题。只列异常部门，正常部门收成一行。
    """
    expected_depts = [x for x in dept_stats if (x.get("expected") or 0) > 0]
    has_alert = bool(exceptions)
    elements = []

    if not expected_depts:
        elements.append(_md(EMPTY_HINT))
    else:
        elements.append(_md(_factory_line(stats)))
        if has_alert:
            elements.append({"tag": "hr"})
            elements.append(_md("⚠ 需处理（%d 个部门）" % len(exceptions)))
            shown = exceptions[:MAX_EXCEPTION_DEPTS]
            for exc in shown:
                elements.append(_md(_dept_block(exc)))
            omitted = len(exceptions) - len(shown)
            if omitted > 0:
                elements.append(_md("另有 %d 个部门存在异常（详见部门看板）" % omitted))
            normal = len(expected_depts) - len(exceptions)
            if normal > 0:
                elements.append({"tag": "hr"})
                elements.append(_md("其余 %d 个部门全部正常" % normal))
        else:
            elements.append(_md("✅ 各部门全部正常，无未打卡、无迟到"))
        if _needs_note(stats):
            elements.append({"tag": "hr"})
            elements.append(_md(NO_CARD_HINT))

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange" if has_alert else "green",
            "title": {"tag": "plain_text",
                      "content": "%s%s %s" % (CARD_TITLE_PREFIX, date_str, hhmm)},
        },
        "elements": elements,
    }


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
    """POST 到飞书群机器人 webhook；永不抛异常，返回 (是否成功, 说明)。

    token 一般用不到（飞书自定义机器人靠 URL 里的 key 鉴权），保留以便接自建网关。
    成功与否交给 feishu_result 判定——飞书失败时也可能返回 HTTP 200。
    """
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer %s" % token
    try:
        import requests  # 放进 try：连 import 失败也吞掉，函数任何情况下都不上抛
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        return feishu_result(r.status_code, r.text)
    except Exception as e:
        return False, str(e)


def _mark_sent_best_effort(date_str):
    """落幂等位；失败只记日志，绝不让调用方判失败。

    消息已经送达（或已按干跑处理），若 mark 失败被外层 except 抓住，会返回
    sent=False 且幂等位没落，同一个 9 点窗口（或第二条 cron）将重复发送——
    已送达却重发比漏记幂等位更糟，故此处必须独立兜住。
    """
    import frappe
    try:
        mark_sent(date_str)
    except Exception as e:
        frappe.log_error(str(e), "HBOS考勤通知幂等位写入失败")


def _build_payload(data, date_str, hhmm, dept_stats, text):
    """构造出站报文；卡片渲染任何异常都降级为纯文本（宁可丑，不能不发）。"""
    import frappe
    try:
        exceptions = collect_exceptions(data.get("rows") or [])
        card = render_card(date_str, hhmm, data.get("stats") or {}, dept_stats, exceptions)
        return build_feishu_payload(card)
    except Exception as e:
        frappe.log_error("%s\n%s" % (e, text), "HBOS考勤通知卡片渲染失败(降级为纯文本)")
        return build_text_payload(text)


def _dry_run_detail(payload, text):
    """干跑留档：卡片 JSON 与纯文本都留，便于先核对版式再配地址。"""
    import json
    return "纯文本:\n%s\n\n报文JSON:\n%s" % (
        text, json.dumps(payload, ensure_ascii=False, indent=2))


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
        hhmm = now.strftime("%H:%M")
        text = render_report(date_str, hhmm, dept_stats)      # 纯文本：降级与留档用
        payload = _build_payload(data, date_str, hhmm, dept_stats, text)

        dry = os.environ.get("HBOS_NOTIFY_DRY_RUN", "") == "1"
        url = os.environ.get("HBOS_NOTIFY_WEBHOOK_URL", "")
        if dry or not url:
            frappe.log_error(_dry_run_detail(payload, text),
                             "HBOS考勤通知(未发送: %s)" % ("dry_run" if dry else "no_webhook"))
            if dry:
                _mark_sent_best_effort(date_str)
            return {"sent": False, "reason": "dry_run" if dry else "no_webhook", "text": text}

        ok, msg = post_to_webhook(url, os.environ.get("HBOS_NOTIFY_TOKEN", ""), payload)
        if ok:
            _mark_sent_best_effort(date_str)
            return {"sent": True, "detail": msg}
        frappe.log_error("%s\n%s" % (msg, text), "HBOS考勤通知发送失败")
        return {"sent": False, "reason": msg}
    except Exception as e:
        frappe.log_error(str(e), "HBOS考勤通知异常")
        return {"sent": False, "reason": str(e)}
