"""考勤规则引擎 v3 — 完整重写
按优先级 P1→P2→P3 处理，核心修复：
- 中班跨天配对：前一天16:00+ + 次日00:00-10:00 → 中班IN/OUT
- 下班反推优先：15:30-16:30 → 早班，17:00-18:00 → 行政班
- 时间窗严格按文档定义
"""
import frappe
import json
from datetime import datetime, timedelta, date
from collections import defaultdict

SHIFT_DEFS = {
    "早班":   {"in_min": 480,  "out_min": 960,  "late_grace": 5},
    "行政班": {"in_min": 510,  "out_min": 1050, "late_grace": 5},
    "中班":   {"in_min": 960,  "out_min": 1440, "late_grace": 5},
    "晚班":   {"in_min": 0,    "out_min": 480,  "late_grace": 10},
}

def _m(t): return t.hour * 60 + t.minute


def load_checkins(from_date, to_date):
    next_day = (datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")
    rows = frappe.db.sql("""
        SELECT employee, time FROM `tabEmployee Checkin`
        WHERE name LIKE 'DELICLOUD-%%' AND employee IS NOT NULL
          AND time >= %s AND time < %s ORDER BY employee, time
    """, (from_date, next_day), as_dict=True)
    groups = defaultdict(list)
    for r in rows:
        groups[r["employee"]].append(r["time"])
    return dict(groups)


def match_shifts_v2(from_date="2026-07-28", to_date="2026-07-30"):
    fd = datetime.strptime(from_date, "%Y-%m-%d").date()
    td = datetime.strptime(to_date, "%Y-%m-%d").date()

    all_checkins = load_checkins(from_date, to_date)
    EI = {e["name"]: e for e in frappe.db.sql(
        "SELECT name, employee_name, department FROM tabEmployee WHERE status='Active'", as_dict=1)}

    print(f"[shift_matcher] Employees: {len(all_checkins)}")

    output = {}

    for emp, times in all_checkins.items():
        if not times:
            continue
        times.sort()

        # 按日期分组
        by_date = defaultdict(list)
        for t in times:
            by_date[t.date()].append(t)
        for d in by_date:
            by_date[d].sort()

        # ====== P1: 跨天连续性 ======
        consumed = set()

        # 遍历所有日期，查找中班跨天配对
        all_dates = sorted(by_date.keys())
        for idx, d in enumerate(all_dates):
            if d < fd or d > td:
                continue

            day_times = by_date[d]
            am = [t for t in day_times if _m(t) < 12 * 60]
            pm = [t for t in day_times if _m(t) >= 15 * 60]

            # P1.3: 中班跨天 — 前日 16:00-19:00 单打卡 + 次日 00:00-10:00 打卡
            # 注意：19:00 后的打卡大概率不是中班，不配对
            if len(pm) == 1 and len(am) == 0:
                t = pm[0]
                pm_m = _m(t)
                if pm_m >= 16 * 60 and pm_m <= 19 * 60:  # 16:00-19:00 中班标准到岗窗口
                    next_day = d + timedelta(days=1)
                    if next_day in by_date:
                        next_times = by_date[next_day]
                        next_early = [x for x in next_times if _m(x) <= 10 * 60]
                        if next_early:
                            in_t = t
                            out_t = next_early[0]
                            ds = d.strftime("%Y-%m-%d")
                            output[(emp, ds)] = {
                                "employee": emp, "date": ds, "shift": "中班",
                                "in_punch": in_t, "out_punch": out_t,
                                "confidence": "high", "match_source": "cross_day_mid_shift"
                            }
                            consumed.add((d, t))
                            consumed.add((next_day, next_early[0]))
                            continue

            # P1.1: 午夜窗 — 最后的 23:30+ 或 00:00-00:30
            for t in day_times:
                if (d, t) in consumed:
                    continue
                m = _m(t)
                if m >= 23 * 60 + 30:
                    # 23:30+ → 晚班上班
                    next_day = d + timedelta(days=1)
                    next_out = None
                    if next_day in by_date:
                        candidates = [x for x in by_date[next_day] if _m(x) <= 8 * 60 + 30]
                        if candidates:
                            next_out = candidates[0]
                            consumed.add((next_day, next_out))
                    ds = d.strftime("%Y-%m-%d")
                    output[(emp, ds)] = {
                        "employee": emp, "date": ds, "shift": "晚班",
                        "in_punch": t, "out_punch": next_out,
                        "confidence": "high", "match_source": "cross_dawn_night_23"
                    }
                    consumed.add((d, t))
                elif m <= 0 * 60 + 30:
                    # 00:00-00:30 → 晚班上班 or 中班下班
                    prev_day = d - timedelta(days=1)
                    if prev_day in by_date:
                        prev_pm = [x for x in by_date[prev_day] if _m(x) >= 15 * 60]
                        if prev_pm and (prev_day, prev_pm[0]) not in consumed:
                            # 中班 IN=prev_pm, OUT=t
                            ds = prev_day.strftime("%Y-%m-%d")
                            output[(emp, ds)] = {
                                "employee": emp, "date": ds, "shift": "中班",
                                "in_punch": prev_pm[0], "out_punch": t,
                                "confidence": "high", "match_source": "cross_midnight_out"
                            }
                            consumed.add((prev_day, prev_pm[0]))
                            consumed.add((d, t))
                            continue
                    # 否则 → 晚班上班
                    next_out = None
                    if d + timedelta(days=1) in by_date:
                        candidates = [x for x in by_date[d + timedelta(days=1)] if _m(x) <= 8 * 60 + 30]
                        if candidates:
                            next_out = candidates[0]
                            consumed.add((d + timedelta(days=1), next_out))
                    ds = d.strftime("%Y-%m-%d")
                    output[(emp, ds)] = {
                        "employee": emp, "date": ds, "shift": "晚班",
                        "in_punch": t, "out_punch": next_out,
                        "confidence": "high", "match_source": "cross_dawn_night_in"
                    }
                    consumed.add((d, t))

        # ====== P2: 配对反推 (剩余未消费) ======
        for d in all_dates:
            if d < fd or d > td:
                continue
            ds = d.strftime("%Y-%m-%d")
            if (emp, ds) in output:
                continue

            remaining = [t for t in by_date[d] if (d, t) not in consumed]
            if not remaining:
                continue
            remaining.sort()

            am = [t for t in remaining if _m(t) < 12 * 60]
            pm = [t for t in remaining if _m(t) >= 12 * 60]

            shift = None; in_t = None; out_t = None; src = ""

            # Rule 2.1: 下班反推
            out_early = [t for t in pm if 15 * 60 + 30 <= _m(t) <= 16 * 60 + 30]
            out_admin = [t for t in pm if 17 * 60 <= _m(t) <= 18 * 60]

            if out_early and am:
                shift = "早班"; out_t = out_early[-1]
                in_t = min(am, key=lambda t: abs(_m(t) - 480))
                src = "reverse_out_early"
            elif out_admin and am:
                shift = "行政班"; out_t = out_admin[-1]
                in_t = min(am, key=lambda t: abs(_m(t) - 510))
                src = "reverse_out_admin"
            elif out_early and not am:
                # 16:00± 无AM → 中班上班
                shift = "中班"; in_t = out_early[-1]; src = "pm_mid_without_am"
            elif out_admin and not am:
                shift = "行政班"; out_t = out_admin[-1]; src = "admin_out_only"
            elif am and pm:
                # 有AM有PM但非标准 — AM邻近度判定
                t = am[0]; m = _m(t)
                if 7 * 60 + 30 <= m <= 8 * 60 + 5:
                    shift = "早班"; src = "am_proximity_early"
                elif 8 * 60 + 25 <= m <= 9 * 60:
                    shift = "行政班"; src = "am_proximity_admin"
                elif 8 * 60 + 5 < m < 8 * 60 + 25:
                    ei = EI.get(emp)
                    dept = (ei.get("department") or "") if ei else ""
                    admin_kw = ["行政","办公室","财务","采购","市场","技术","设备","QC","QA","安全","人事","注册","质量","总经办","生产部","AI","司机","环保","绿化","电工","精馏"]
                    shift = "行政班" if any(k in dept for k in admin_kw) else "早班"
                    src = "am_fuzzy_dept"
                else:
                    shift = "早班"; src = "am_fallback"
                in_t = t; out_t = pm[-1]
            elif am and not pm:
                t = am[0]; m = _m(t)
                ei = EI.get(emp)
                dept = (ei.get("department") or "") if ei else ""
                admin_kw = ["行政","办公室","财务","采购","市场","技术","设备","QC","QA","安全","人事","注册","质量","总经办","生产部","AI","司机","环保","绿化","电工","精馏"]
                if m <= 8 * 60 + 5:
                    shift = "早班"; src = "am_only_early"
                elif m >= 8 * 60 + 25:
                    shift = "行政班"; src = "am_only_admin"
                else:
                    shift = "行政班" if any(k in dept for k in admin_kw) else "早班"
                    src = "am_only_fuzzy"
                in_t = t
            elif pm and not am:
                t = pm[-1]; m = _m(t)
                if 17 * 60 <= m <= 18 * 60:
                    shift = "行政班"; out_t = t; src = "pm_only_admin"
                elif m >= 16 * 60:
                    shift = "中班"; in_t = t; src = "pm_only_mid"
                else:
                    shift = "中班"; in_t = t; src = "pm_only_fallback"
            elif remaining:
                t = remaining[0]; m = _m(t)
                if m < 8 * 60: shift = "晚班"; in_t = t; src = "fallback_night"
                elif m < 16 * 60: shift = "行政班"; in_t = t; src = "fallback_day"
                else: shift = "中班"; in_t = t; src = "fallback_evening"

            if shift:
                output[(emp, ds)] = {
                    "employee": emp, "date": ds, "shift": shift,
                    "in_punch": in_t, "out_punch": out_t,
                    "confidence": "high" if "reverse" in src else ("medium" if "proximity" in src or "fuzzy" in src else "low"),
                    "match_source": src,
                }

    # 人工修正：质量控制部、行政类部门明确为行政班
    dept_to_shift = {
        "质量控制部": "行政班", "质量保证部": "行政班", "财务部": "行政班",
        "人事行政办公室": "行政班", "采购部": "行政班", "市场部": "行政班",
        "技术部": "行政班", "注册部": "行政班", "安全部办公室": "行政班",
        "AI创新部": "行政班", "生产部办公室": "行政班", "设备动力部办公室": "行政班",
        "生产部自控室": "行政班", "环保办公室1": "行政班", "环保办公室2": "行政班",
        "精馏塔办公室": "行政班", "厂外QC办公室": "行政班", "厂外QA": "行政班",
        "非规线办公室": "行政班", "仓库行政班": "行政班",
    }

    for key, r in output.items():
        if r["match_source"].startswith("cross_"):
            continue  # 跨天已确定，不修改
        emp = r["employee"]
        ei = EI.get(emp)
        if ei:
            dept = ei.get("department", "")
            if dept in dept_to_shift and r["shift"] in ("早班", "中班", "晚班") and r["match_source"] not in ("reverse_out_early", "reverse_out_admin"):
                if dept_to_shift[dept] == "行政班":
                    # 检查是否合理：如果上班时间在 8:00-9:00 之间
                    if r["in_punch"] and 7 * 60 + 30 <= _m(r["in_punch"]) <= 9 * 60:
                        r["shift"] = "行政班"
                        r["match_source"] = "dept_override_admin"
                        r["confidence"] = "high"

    # ============ 迟到/早退判定 ============
    late_list = []
    early_list = []

    for key, r in output.items():
        sd = SHIFT_DEFS.get(r["shift"])
        if not sd:
            continue

        if r["in_punch"]:
            if _m(r["in_punch"]) > sd["in_min"] + sd["late_grace"]:
                late_list.append(r)

        if r["out_punch"]:
            out_m = _m(r["out_punch"])
            if r["shift"] in ("早班", "行政班"):
                if out_m < sd["out_min"] - 5:
                    early_list.append(r)
            elif r["shift"] == "晚班":
                if out_m < sd["out_min"] - 5:
                    early_list.append(r)
            # 中班跨天不算早退

    # ============ 统计 ============
    shifts = {}
    sources = {}
    for r in output.values():
        s = r["shift"]
        shifts[s] = shifts.get(s, 0) + 1
        src = r["match_source"]
        sources[src] = sources.get(src, 0) + 1

    print(f"[shift_matcher] Matched: {len(output)} employee-days")
    print(f"[shift_matcher] Shifts: {shifts}")
    print(f"[shift_matcher] Late: {len(late_list)}, Early: {len(early_list)}")

    return {
        "matched": list(output.values()),
        "late": late_list,
        "early": early_list,
        "stats": {
            "total_employee_days": len(output),
            "shift_distribution": shifts,
            "late_count": len(late_list),
            "early_count": len(early_list),
            "sources": sources,
        },
    }