"""飞书「换班」表 → HBOS Shift Swap Record（只读登记，不改考勤判定）。

注意：换班表链接是 /wiki/ 形式，其节点 ID 不是 bitable app_token，
必须先用 wiki API 解析真实 obj_token，否则读取会失败（且不能静默跳过）。
"""
import requests

try:
    import frappe
except ImportError:
    # 离线单测环境未安装 frappe（本机无 bench）：注册最小桩，使本模块及其
    # api 依赖可被导入，纯函数 resolve_wiki_obj_token 得以离线测试。
    # 桩仅覆盖导入期用到的 whitelist；真实 frappe 调用仍由 bench 运行时提供。
    import sys
    import types

    frappe = types.SimpleNamespace(whitelist=lambda *a, **k: (lambda fn: fn))
    sys.modules.setdefault("frappe", frappe)

from hb_attendance_app.hbos_attendance.api import _get_token, _fetch_all_records_custom
from hb_attendance_app.hbos_attendance.swap_mapping import (
    swap_fields, SWAP_WIKI_NODE, SWAP_TABLE_ID,
)

DOCTYPE = "HBOS Shift Swap Record"
ID_PREFIX = "feishu-bitable-swap-"
WIKI_NODE_API = "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node"


def resolve_wiki_obj_token(token, node_token, get=requests.get):
    """wiki 节点 → 真实 bitable app_token；任何异常都抛出（不静默）。"""
    resp = get(WIKI_NODE_API, params={"token": node_token},
               headers={"Authorization": "Bearer " + token}, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception("解析 wiki 节点失败: code=%s msg=%s"
                        % (data.get("code"), data.get("msg")))
    node = (data.get("data") or {}).get("node") or {}
    obj_token = node.get("obj_token")
    if not obj_token:
        raise Exception("wiki 节点未返回 obj_token: %s" % node_token)
    return obj_token


def _match_employee(num, name):
    if num:
        emp = frappe.db.get_value("Employee", {"employee_number": num}, "name")
        if emp:
            return emp
    if name:
        return frappe.db.get_value("Employee", {"employee_name": name}, "name")
    return None


@frappe.whitelist()
def sync_shift_swap_from_bitable():
    try:
        token = _get_token()
        app_token = resolve_wiki_obj_token(token, SWAP_WIKI_NODE)
        records = _fetch_all_records_custom(token, app_token, SWAP_TABLE_ID)
    except Exception as e:
        frappe.log_error(str(e), "飞书换班同步")
        frappe.throw(f"读取飞书换班表格失败: {e}")

    created = updated = skipped = 0
    for record in records:
        fields = record.get("fields", {}) or {}
        if fields.get("申请状态") != "已通过":
            skipped += 1
            continue
        rid = record.get("id", "")
        if not rid:
            skipped += 1
            continue
        mapped = swap_fields(fields)
        if not mapped:
            skipped += 1
            continue
        applicant = _match_employee(mapped["applicant_number"], mapped["applicant_name"])
        substitute = _match_employee(mapped["substitute_number"], mapped["substitute_name"])
        if not applicant or not substitute:
            skipped += 1
            continue

        aid = ID_PREFIX + rid
        exists = frappe.db.exists(DOCTYPE, {"feishu_approval_id": aid})
        doc = (frappe.get_doc(DOCTYPE, {"feishu_approval_id": aid}) if exists
               else frappe.get_doc({"doctype": DOCTYPE, "feishu_approval_id": aid}))
        doc.update({
            "applicant": applicant,
            "substitute": substitute,
            "swap_date": mapped["swap_date"],
            "repay_date": mapped["repay_date"],
            "remarks": mapped["remarks"],
            "approval_status": "已通过",
            "feishu_sync_time": frappe.utils.now_datetime(),
        })
        try:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            if exists:
                updated += 1
            else:
                created += 1
        except Exception as e:
            frappe.log_error(str(e), "飞书换班写入失败")
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped}
