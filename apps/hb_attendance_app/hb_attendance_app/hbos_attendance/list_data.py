"""把考勤的 4 个 DocType 列表以 JSON 形式提供给门户。

## 为什么单独一份白名单

门户不再 iframe 内嵌 Desk 列表页，而是原生渲染。列表能显示哪些列、哪些能筛选，
是**门户的呈现选择**，写在 `LIST_SPECS` 里；数据一律经 `frappe.get_list()` 取，
它自带用户权限过滤（比 `frappe.db.get_all` 安全——后者跳过权限）。

## 边界

只读。白名单之外一律拒绝——不提供通用的「任意 DocType 随便查」接口。
"""
from __future__ import annotations

import frappe

READ_ROLES = ("System Manager", "HR Manager", "HR User")


def _require_read():
    frappe.only_for(list(READ_ROLES))


# 每个列表：标题、说明、显示列（字段名 + 中文表头 + 宽度 + 类型）、
# 可作为筛选的字段、默认排序。
#
# 列的取舍依据 DocType 自己的 in_list_view，再补上门户里更需要一眼看到的字段
# （如调休记录的核实结论）。
LIST_SPECS = {
    "import-log": {
        "doctype": "HBOS Attendance Import Log",
        "title": "考勤导入日志",
        "hint": "每次导入的批次记录：类型、状态、期间、统计与是否重复导入。",
        "order_by": "creation desc",
        "columns": [
            {"fieldname": "name", "label": "批次号", "width": 170},
            {"fieldname": "import_type", "label": "导入类型", "width": 150},
            {"fieldname": "import_status", "label": "状态", "width": 100, "kind": "status"},
            {"fieldname": "source_file_name", "label": "源文件", "width": 200},
            {"fieldname": "period_start", "label": "开始", "width": 110},
            {"fieldname": "period_end", "label": "结束", "width": 110},
            {"fieldname": "is_repeat_import", "label": "重复导入", "width": 100, "kind": "bool"},
            {"fieldname": "matched_rows", "label": "匹配", "width": 80, "kind": "int"},
            {"fieldname": "success_rows", "label": "成功", "width": 80, "kind": "int"},
            {"fieldname": "failed_rows", "label": "失败", "width": 80, "kind": "int"},
            {"fieldname": "created_checkins", "label": "写入打卡", "width": 100, "kind": "int"},
            {"fieldname": "creation", "label": "导入时间", "width": 160},
        ],
        "filters": ["import_type", "import_status"],
    },
    "feishu-leave": {
        "doctype": "HBOS Leave Record",
        "title": "飞书请假记录",
        "hint": "自飞书审批同步的请假单。请假审批通过即豁免考勤判定。",
        "order_by": "start_date desc",
        "columns": [
            {"fieldname": "employee_name", "label": "姓名", "width": 110},
            {"fieldname": "employee", "label": "员工", "width": 150},
            {"fieldname": "department", "label": "部门", "width": 140},
            {"fieldname": "leave_type", "label": "请假类型", "width": 120},
            {"fieldname": "start_date", "label": "开始", "width": 110},
            {"fieldname": "end_date", "label": "结束", "width": 110},
            {"fieldname": "leave_days", "label": "天数", "width": 80, "kind": "num"},
            {"fieldname": "approval_status", "label": "审批状态", "width": 110, "kind": "status"},
            {"fieldname": "feishu_sync_time", "label": "同步时间", "width": 160},
        ],
        "filters": ["approval_status", "leave_type"],
    },
    "feishu-overtime": {
        "doctype": "HBOS Overtime Record",
        "title": "飞书加班记录",
        "hint": "自飞书审批同步的加班单，用于与调休的加班日核实对账。",
        "order_by": "start_time desc",
        "columns": [
            {"fieldname": "employee_name", "label": "姓名", "width": 110},
            {"fieldname": "employee", "label": "员工", "width": 150},
            {"fieldname": "department", "label": "部门", "width": 140},
            {"fieldname": "overtime_type", "label": "加班类型", "width": 120},
            {"fieldname": "start_time", "label": "开始", "width": 160},
            {"fieldname": "end_time", "label": "结束", "width": 160},
            {"fieldname": "duration_hours", "label": "时长(时)", "width": 100, "kind": "num"},
            {"fieldname": "approval_status", "label": "审批状态", "width": 110, "kind": "status"},
            {"fieldname": "feishu_sync_time", "label": "同步时间", "width": 160},
        ],
        "filters": ["approval_status", "overtime_type"],
    },
    "feishu-rest-leave": {
        "doctype": "HBOS Rest Leave Record",
        "title": "飞书调休记录",
        "hint": "调休单。与请假不同：调休须先核实加班日，核实通过的才豁免考勤。",
        "order_by": "start_date desc",
        "columns": [
            {"fieldname": "employee_name", "label": "姓名", "width": 110},
            {"fieldname": "employee_number", "label": "工号", "width": 110},
            {"fieldname": "department", "label": "部门", "width": 140},
            {"fieldname": "start_date", "label": "开始", "width": 110},
            {"fieldname": "end_date", "label": "结束", "width": 110},
            {"fieldname": "rest_days", "label": "天数", "width": 80, "kind": "num"},
            {"fieldname": "approval_status", "label": "审批状态", "width": 110, "kind": "status"},
            {"fieldname": "overtime_dates", "label": "加班日", "width": 200},
            {"fieldname": "verify_status", "label": "核实结论", "width": 130, "kind": "status"},
        ],
        "filters": ["approval_status", "verify_status"],
    },
}


def _clean(raw) -> dict:
    """接受 dict 或 JSON 字符串。字符串必须处理——经 HTTP 传来的是 JSON 文本。"""
    if isinstance(raw, str):
        try:
            raw = frappe.parse_json(raw)
        except Exception:
            return {}
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if isinstance(k, str) and k and v not in (None, "")}


def _spec(key: str) -> dict:
    spec = LIST_SPECS.get(key)
    if not spec:
        frappe.throw(f"未注册的列表：{key}", frappe.ValidationError)
    return spec


@frappe.whitelist()
def get_list(key: str, filters=None, limit: int = 200, start: int = 0):
    """按白名单取一个 DocType 列表。

    limit 封顶 500：这些表都可能上千行，不封顶会让浏览器直接卡住。
    超出部分由前端分页承担（一次只取一页）。
    """
    _require_read()
    spec = _spec(key)

    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 200
    try:
        start = max(0, int(start))
    except (TypeError, ValueError):
        start = 0

    fields = [c["fieldname"] for c in spec["columns"]]
    allowed_filters = set(spec.get("filters", []))
    clean = {k: v for k, v in _clean(filters).items() if k in allowed_filters}

    # frappe.get_list 会带上当前用户的权限过滤；db.get_all 不会。
    rows = frappe.get_list(
        spec["doctype"],
        filters=clean,
        fields=fields,
        order_by=spec["order_by"],
        limit_page_length=limit,
        limit_start=start,
    )
    total = frappe.db.count(spec["doctype"], filters=clean or None)

    return {
        "key": key,
        "doctype": spec["doctype"],
        "title": spec["title"],
        "hint": spec["hint"],
        "columns": spec["columns"],
        # 可筛选字段由后端给出白名单，前端照它渲染筛选条——
        # 否则前端要么写死（与后端漂移），要么放任意字段（可被用来探测不存在的列）。
        "filter_fields": spec.get("filters", []),
        "rows": rows,
        "total": total,
        "limit": limit,
        "start": start,
    }


@frappe.whitelist()
def get_filter_options(key: str, fieldname: str):
    """某筛选字段的可选值（去重后的现有取值）。

    不新造字典表：选项从真实数据里归纳，避免「选项里有、数据里没有」的假选择。
    """
    _require_read()
    spec = _spec(key)
    if fieldname not in set(spec.get("filters", [])):
        frappe.throw(f"字段不可筛选：{fieldname}", frappe.ValidationError)

    values = frappe.db.get_all(
        spec["doctype"], fields=[fieldname], distinct=True, limit_page_length=200
    )
    out = sorted({str(v.get(fieldname)) for v in values if v.get(fieldname)})
    return [{"value": v, "label": v} for v in out]
