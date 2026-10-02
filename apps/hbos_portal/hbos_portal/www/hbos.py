from pathlib import Path
import frappe

no_cache = 1


def get_context(context):
    frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"
    frappe.local.response_headers["Referrer-Policy"] = "no-referrer"
    index = Path(frappe.get_app_path("hbos_portal", "public", "portal", "index.html"))
    if not index.is_file():
        frappe.throw("Portal 正式构建尚未部署，请联系管理员。")
    context.portal_html = index.read_text(encoding="utf-8")
    context.no_cache = 1
    context.no_header = 1
    context.no_breadcrumbs = 1
