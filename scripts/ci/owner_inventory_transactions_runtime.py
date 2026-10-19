"""R3 native inventory / declared LIMS source proof on a fresh GitHub CI Site.

Runner-only entry point: copy this file into the disposable application's package
and invoke ``run`` with bench execute. This is not a whitelisted business API.
Stock/GL/Batch-release facts are created only by native document actions and the
existing LIMS services. No SQL fixtures, permission stubs, or release-field writes
are used to make a positive case pass. Failed cases remain visible in the result.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import time
import traceback
from datetime import date
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

import frappe


LIMS_AUTHORITY = (
    "PR43 formal LIMS integration on product 366b3ad5ceba7fbc417bb3cd8ba93b12e57a7857; "
    "reviewed Administrator action boundary, canonical COA snapshot binding and unchanged inventory quality projection"
)
LIMS_AUTHORITY_SHA256 = {
    "hb_lims_app/hb_lims_app/hbos_lims/lims_service.py":
        "2f7f137f1159286bfe897e7278b554fb131e8d6bfe49d58cb62429942f767db0",
    "hb_lims_app/hb_lims_app/hbos_lims/workflow_contract.py":
        "7dfa43cd30f67eda1b9ccf636615d01ef36f1838bb9ce72c258c082545b65fca",
    "hb_inventory_app/hb_inventory_app/hbos_inventory/quality_projection.py":
        "b1f0112d2d202fa3d612315a86e534d89456716a5d4f645cf515e661b99c5cb0",
}
RESULTS: list[dict] = []
FIXTURE: dict = {}
LIMS = "hb_lims_app.hbos_lims.lims_service."


def emit(case, **data):
    print("[INVENTORY-R3] " + json.dumps({"case": case, **data}, ensure_ascii=False, default=str))


def guard():
    marker = os.environ.get("HBOS_REPORT_SCOPE_TEST_ID", "")
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    assert os.environ.get("HBOS_FRAPPE_SMOKE") == "1"
    assert os.environ.get("OWNER_AUDIT_DOMAIN") == "inventory-transactions"
    assert re.fullmatch(r"[0-9]+-[0-9]+", marker)
    assert frappe.local.site == "report-scope-" + marker + ".localhost"
    assert str(frappe.conf.hbos_report_scope_ci) == marker
    assert all(os.environ.get(key) == "0" for key in (
        "HBOS_AI_ENABLED", "HBOS_AI_ALLOW_PII", "HBOS_FEISHU_SYNC_ENABLED",
        "HBOS_DELICLOUD_SYNC_ENABLED",
    ))
    origin = str(frappe.conf.hbos_portal_origin)
    assert urlsplit(origin).hostname == frappe.local.site
    assert not frappe.conf.ignore_csrf, "Do not turn off native CSRF for the proof"
    assert not frappe.db.count("Stock Entry"), "Refuse pre-existing stock documents"
    assert not frappe.db.count("Stock Reconciliation"), "Refuse pre-existing reconciliations"
    assert not frappe.db.count("Company"), "Proof requires a newly installed Site"
    for rel, expected in LIMS_AUTHORITY_SHA256.items():
        actual = hashlib.sha256((Path("/home/frappe/frappe-bench/apps") / rel).read_bytes()).hexdigest()
        assert actual == expected, "Declared LIMS authority changed: " + rel
    emit("isolation_and_existing_lims_authority", status="PASS", site=frappe.local.site,
         lims_origin_product="366b3ad5ceba7fbc417bb3cd8ba93b12e57a7857", integration_pr=43,
         authority=LIMS_AUTHORITY, sha256=LIMS_AUTHORITY_SHA256,
         stock_sql_fixtures=False, release_projection_stubs=False)


class Client:
    """Use the same session/CSRF/native endpoints as the shipped Portal clients."""

    def __init__(self):
        origin = str(frappe.conf.hbos_portal_origin)
        self.headers = {"Host": urlsplit(origin).netloc, "Origin": origin,
                        "X-Requested-With": "XMLHttpRequest"}
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(self, method, params=None, *, post=False, csrf=True, json_body=False):
        assert not json_body or post, "JSON request bodies are only used for explicit POST calls"
        encoded = (json.dumps(params or {}) if json_body else urlencode(params or {})).encode()
        url = "http://127.0.0.1:8000/api/method/" + method
        headers = dict(self.headers)
        if json_body:
            headers["Content-Type"] = "application/json"
        if not csrf:
            headers.pop("X-Frappe-CSRF-Token", None)
        request = Request(url if post or not encoded else url + "?" + encoded.decode(),
                          data=encoded if post else None, headers=headers)
        try:
            response = self.opener.open(request, timeout=60)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read().decode("utf-8")
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {}
            return response.code, payload

    def ok(self, method, params=None, *, post=False, json_body=False):
        status, payload = self.call(method, params, post=post, json_body=json_body)
        if status != 200:
            # Synthetic business diagnostics only; credentials/cookies never enter this path.
            detail = str(payload.get("_server_messages") or payload.get("exc_type") or "")[:1000]
            raise AssertionError(f"{method}: HTTP {status}, {detail}")
        return payload.get("message")

    def login(self, user, password):
        status, _ = self.call("login", {"usr": user, "pwd": password}, post=True)
        assert status == 200, f"Synthetic login failed ({status})"
        security = self.ok("hbos_portal.auth.accounts.get_request_security")
        assert security and security.get("csrf_token"), "No native request-security token"
        self.headers["X-Frappe-CSRF-Token"] = security["csrf_token"]
        assert self.ok("frappe.auth.get_logged_user") == user
        return self

    def get_doc(self, doctype, name):
        doc = self.ok("frappe.client.get", {"doctype": doctype, "name": name})
        assert doc and doc.get("name") == name
        doc["doctype"] = doctype
        return doc

    def insert(self, doc):
        return self.ok("frappe.client.insert", {"doc": json.dumps(doc)}, post=True)

    def submit(self, doctype, name):
        # The Portal sends the complete document, not merely {doctype, name}.
        return self.ok("frappe.client.submit", {
            "doc": json.dumps(self.get_doc(doctype, name))}, post=True)

    def cancel(self, doctype, name):
        return self.ok("frappe.client.cancel", {"doctype": doctype, "name": name}, post=True)


def deny(client, method, params, *, codes=(403,), contains=None, csrf=True,
         exception=None, label=None, audit_stock=False):
    before = stock_write_counts() if audit_stock else None
    status, payload = client.call(method, params, post=True, csrf=csrf)
    actual_exception = payload.get("exc_type")
    observation = {"label": label or method, "http": status, "exception": actual_exception}
    if audit_stock:
        after = stock_write_counts()
        observation.update(stock_facts_before=before, stock_facts_after=after)
    # Log only the guard label, native exception class and synthetic fact counts.
    # Never emit request parameters, credentials, cookies or CSRF token values.
    emit("native_negative_observation", **observation)
    assert status in codes, (
        f"{label or method}: expected denial {codes}, got HTTP {status} ({actual_exception})")
    if exception:
        assert actual_exception == exception, f"{label or method}: unexpected denial class {actual_exception}"
    if audit_stock:
        assert before == after, f"{label or method}: denied action changed stock document or ledger counts"
    if contains:
        detail = json.dumps(payload, ensure_ascii=False)
        assert contains.lower() in detail.lower(), f"Expected {contains!r} denial, got {payload.get('exc_type')}"
    return observation


def native_insert(data):
    """Setup only: native Administrator insertion, with all document validation."""
    frappe.set_user("Administrator")
    return frappe.get_doc(data).insert()


def setup():
    frappe.set_user("Administrator")
    # install-app does not run the ERPNext setup wizard. These are native master
    # records required by the transaction forms, not synthetic ledger facts.
    if not frappe.db.exists("Item Group", "All Item Groups"):
        native_insert({"doctype": "Item Group", "item_group_name": "All Item Groups",
            "is_group": 1, "parent_item_group": ""})
    for purpose in ("Material Receipt", "Material Issue", "Material Transfer", "Send to Subcontractor"):
        if not frappe.db.exists("Stock Entry Type", purpose):
            native_insert({"doctype": "Stock Entry Type", "name": purpose,
                "purpose": purpose, "is_standard": 1})
        assert frappe.db.get_value("Stock Entry Type", purpose, "purpose") == purpose
    # ERPNext v16.26.2 Company creates "Goods In Transit" with this linked type.
    # The setup wizard normally inserts it; install-app alone does not.
    if not frappe.db.exists("Warehouse Type", "Transit"):
        native_insert({"doctype": "Warehouse Type", "name": "Transit"})
    # v16 defaults batch tracking to disabled. Enable the native feature before
    # exercising real batch documents; retain negative-stock and valuation rules.
    stock_settings = frappe.get_doc("Stock Settings")
    stock_settings.enable_serial_and_batch_no_for_item = 1
    stock_settings.save()
    frappe.db.commit()
    stock_settings.reload()
    assert stock_settings.enable_serial_and_batch_no_for_item == 1
    assert not stock_settings.allow_negative_stock and not stock_settings.allow_negative_stock_for_batch
    assert not stock_settings.do_not_use_batchwise_valuation
    emit("native_stock_settings", status="PASS", saved_and_reloaded=True,
         enable_serial_and_batch_no_for_item=stock_settings.enable_serial_and_batch_no_for_item,
         use_serial_batch_fields=stock_settings.use_serial_batch_fields,
         allow_negative_stock=stock_settings.allow_negative_stock,
         allow_negative_stock_for_batch=stock_settings.allow_negative_stock_for_batch,
         do_not_use_batchwise_valuation=stock_settings.do_not_use_batchwise_valuation)
    # Native Company creation builds the chart, default accounts and cost centres.
    companies = []
    for label, abbr in (("HBOS R3 Inventory CI", "HCI"), ("HBOS R3 Outside CI", "HCO")):
        company = native_insert({"doctype": "Company", "company_name": label,
            "abbr": abbr, "default_currency": "USD", "country": "United States",
            "chart_of_accounts": "Standard", "enable_perpetual_inventory": 1})
        company.reload()
        assert company.default_inventory_account and company.stock_adjustment_account and company.cost_center
        companies.append(company)
    company, outside = companies
    today = date.fromisoformat(frappe.utils.today())
    native_insert({"doctype": "Fiscal Year", "year": f"HBOS R3 CI {today.year}",
        "year_start_date": date(today.year, 1, 1).isoformat(),
        "year_end_date": date(today.year, 12, 31).isoformat()})
    frappe.defaults.set_global_default("company", company.name)
    frappe.defaults.set_global_default("currency", "USD")
    frappe.db.set_single_value("Global Defaults", "default_company", company.name)
    uom = native_insert({"doctype": "UOM", "uom_name": "HBOS R3 CI Unit", "enabled": 1}).name
    group_root = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ""}, "name")
    assert group_root, "ERPNext Item Group root is missing"
    group = native_insert({"doctype": "Item Group", "item_group_name": "HBOS R3 CI Items",
        "parent_item_group": group_root, "is_group": 0}).name
    warehouses = {}
    for key, name, co, rejected in (
        ("a", "HBOS R3 A", company, 0), ("b", "HBOS R3 B", company, 0),
        ("quarantine", "HBOS R3 Quarantine", company, 1),
        ("jobworker", "HBOS R3 Job Worker", company, 0),
        ("outside", "HBOS R3 Outside", outside, 0),
    ):
        root = frappe.db.get_value("Warehouse", {"company": co.name, "is_group": 1}, "name")
        warehouses[key] = native_insert({"doctype": "Warehouse", "warehouse_name": name,
            "company": co.name, "parent_warehouse": root, "is_group": 0,
            "is_rejected_warehouse": rejected}).name
    native_insert({"doctype": "HBOS Test Item", "item_code": "R3-CI-TEST",
        "item_name": "Synthetic identity test", "item_category": "理化检验",
        "test_unit": "mg", "significant_digits": 2})
    sample_type = native_insert({"doctype": "HBOS Sample Type", "sample_type_code": "R3-CI-TYPE",
        "sample_type_name": "Synthetic inventory release"}).name
    lab = native_insert({"doctype": "HBOS Lab Department", "department_code": "R3-CI-LAB",
        "department_name": "Synthetic laboratory"}).name
    frappe.db.commit()
    users = {
        "stock": ["Stock User", "Item Manager"],
        "restricted": ["Stock User", "Item Manager"],
        "stock_manager": ["Stock Manager", "Stock User", "Item Manager"],
        "none": ["Employee"],
        "lims_manager": ["LIMS Manager"],
        "analyst": ["LIMS Analyst"],
        "reviewer": ["LIMS Reviewer"],
        "qa": ["LIMS QA"],
    }
    clients, identities = {}, {}
    for key, roles in users.items():
        user = f"r3-inventory-{key.replace('_', '-')}@example.invalid"
        password = secrets.token_urlsafe(32)
        native_insert({"doctype": "User", "email": user, "first_name": "Synthetic R3",
            "enabled": 1, "send_welcome_email": 0, "user_type": "System User", "language": "en",
            "new_password": password, "roles": [{"role": role} for role in roles]})
        if key == "restricted":
            native_insert({"doctype": "User Permission", "user": user, "allow": "Warehouse",
                "for_value": warehouses["a"], "apply_to_all_doctypes": 1, "hide_descendants": 1})
        frappe.defaults.set_user_default("Company", company.name, user)
        frappe.db.commit()
        frappe.clear_cache(user=user)
        clients[key] = Client().login(user, password)
        identities[key] = user
        # Retain production User creation throttling; no fixture-only bypass.
        time.sleep(8)
    FIXTURE.update(company=company.name, outside=outside.name, warehouses=warehouses,
                   uom=uom, group=group, clients=clients, users=identities,
                   expense=company.stock_adjustment_account, cost_center=company.cost_center,
                   sample_type=sample_type, lab=lab)
    emit("native_fixture", status="PASS", companies=2, users=len(users),
         accounting="native Standard chart / perpetual inventory enabled",
         roles_modified=False, permission_overrides=False)


def new_stock(label):
    name = "HBOS-R3-" + label
    item = native_insert({"doctype": "Item", "item_code": name, "item_name": "Synthetic " + label,
        "item_group": FIXTURE["group"], "stock_uom": FIXTURE["uom"], "is_stock_item": 1,
        "has_batch_no": 1, "create_new_batch": 0,
        "item_defaults": [{"company": FIXTURE["company"],
            "default_warehouse": FIXTURE["warehouses"]["a"],
            "expense_account": FIXTURE["expense"], "buying_cost_center": FIXTURE["cost_center"]}]}).name
    batch = native_insert({"doctype": "Batch", "batch_id": name + "-BATCH", "item": item}).name
    frappe.db.commit()
    assert frappe.db.get_value("Batch", batch, "hbos_release_status") == "待检"
    return item, batch


def stock_payload(item, batch, purpose, qty, *, source=None, target=None):
    row = {"item_code": item, "qty": qty, "uom": FIXTURE["uom"], "stock_uom": FIXTURE["uom"],
        "conversion_factor": 1, "basic_rate": 10, "batch_no": batch, "use_serial_batch_fields": 1,
        "expense_account": FIXTURE["expense"], "cost_center": FIXTURE["cost_center"]}
    if source:
        row["s_warehouse"] = source
    if target:
        row["t_warehouse"] = target
    return {"doctype": "Stock Entry", "company": FIXTURE["company"],
        "stock_entry_type": purpose, "purpose": purpose, "posting_date": frappe.utils.today(),
        "items": [row], "remarks": "Synthetic R3 native transaction proof"}


def fresh_read():
    # HTTP actions commit in another connection. End any local repeatable-read snapshot.
    frappe.db.rollback()
    frappe.set_user("Administrator")


def stock_write_counts():
    fresh_read()
    return {doctype: frappe.db.count(doctype) for doctype in (
        "Stock Entry", "Serial and Batch Bundle", "Stock Ledger Entry", "GL Entry",
    )}


def assert_stock(item, expected):
    fresh_read()
    actual = {}
    for warehouse, qty in expected.items():
        value = float(frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse}, "actual_qty") or 0)
        assert abs(value - qty) < 0.00001, f"Bin mismatch {warehouse}: {value} != {qty}"
        ledger = float(frappe.db.sql("""select coalesce(sum(actual_qty),0) from `tabStock Ledger Entry`
            where item_code=%s and warehouse=%s""", (item, warehouse))[0][0])
        assert abs(ledger - qty) < 0.00001, f"Native SLE net mismatch: {ledger} != {qty}"
        actual[warehouse] = {"bin": value, "native_sle_net": ledger}
    return actual


def assert_gl(doctype, name, *, cancelled=False):
    fresh_read()
    entries = frappe.get_all("GL Entry", filters={"voucher_type": doctype, "voucher_no": name},
        fields=["account", "debit", "credit", "is_cancelled"])
    assert entries, f"Native accounting entry absent for {doctype} {name}"
    assert abs(sum(float(r.debit) - float(r.credit) for r in entries)) < 0.00001
    assert sum(float(r.debit) for r in entries) > 0
    if cancelled:
        by_account = {}
        for row in entries:
            by_account[row.account] = by_account.get(row.account, 0) + float(row.debit) - float(row.credit)
        assert all(abs(value) < 0.00001 for value in by_account.values()), "Cancel did not reverse GL accounts"
    return {"entries": len(entries), "balanced": True, "cancel_reversed": cancelled}


def receive(item, batch, qty=100):
    client = FIXTURE["clients"]["stock"]
    name = client.insert(stock_payload(item, batch, "Material Receipt", qty,
        target=FIXTURE["warehouses"]["a"]))["name"]
    client.submit("Stock Entry", name)
    assert_stock(item, {FIXTURE["warehouses"]["a"]: qty})
    assert_gl("Stock Entry", name)
    return name


def receipt_and_permissions():
    item, batch = new_stock("RECEIPT")
    wh = FIXTURE["warehouses"]
    clients = FIXTURE["clients"]
    payload = stock_payload(item, batch, "Material Receipt", 100, target=wh["a"])
    no_role = deny(clients["none"], "frappe.client.insert", {"doc": json.dumps(payload)},
        label="no_stock_role_insert", exception="PermissionError", audit_stock=True)
    guest = deny(Client(), "frappe.client.insert", {"doc": json.dumps(payload)},
        label="guest_insert", exception="PermissionError", audit_stock=True)
    cross = dict(payload, items=[dict(payload["items"][0], t_warehouse=wh["b"])])
    cross_scope = deny(clients["restricted"], "frappe.client.insert", {"doc": json.dumps(cross)},
        label="warehouse_scope_insert", exception="PermissionError", audit_stock=True)
    # Frappe v16.26.3 declares CSRFTokenError as HTTP 400, independently of the
    # 403 permission denials above. An unrelated 400 must still fail this proof.
    csrf = deny(clients["stock"], "frappe.client.insert", {"doc": json.dumps(payload)},
        csrf=False, codes=(400,), exception="CSRFTokenError", label="missing_csrf_insert", audit_stock=True)
    name = receive(item, batch)
    # Wrong identity cannot cancel the real posted voucher.
    no_role_cancel = deny(clients["none"], "frappe.client.cancel", {"doctype": "Stock Entry", "name": name})
    clients["stock"].cancel("Stock Entry", name)
    balances = assert_stock(item, {wh["a"]: 0})
    accounting = assert_gl("Stock Entry", name, cancelled=True)
    assert frappe.db.get_value("Stock Entry", name, "docstatus") == 2
    emit("receipt_permissions_submit_cancel", status="PASS", voucher=name, balances=balances,
         accounting=accounting, guest=guest, no_role=no_role, no_role_cancel=no_role_cancel,
         cross_warehouse=cross_scope, csrf=csrf)


def reconciliation():
    item, batch = new_stock("RECONCILE")
    wh = FIXTURE["warehouses"]["a"]
    clients = FIXTURE["clients"]
    receive(item, batch)
    payload = {"doctype": "Stock Reconciliation", "company": FIXTURE["company"],
        "purpose": "Stock Reconciliation", "posting_date": frappe.utils.today(),
        "posting_time": frappe.utils.nowtime(), "expense_account": FIXTURE["expense"],
        "cost_center": FIXTURE["cost_center"], "items": [{"item_code": item, "warehouse": wh,
            "qty": 123, "valuation_rate": 10, "batch_no": batch, "use_serial_batch_fields": 1}]}
    create_denial = deny(clients["stock"], "frappe.client.insert", {"doc": json.dumps(payload)})
    draft = clients["stock_manager"].insert(payload)
    doc = clients["stock_manager"].get_doc("Stock Reconciliation", draft["name"])
    submit_denial = deny(clients["stock"], "frappe.client.submit", {"doc": json.dumps(doc)})
    assert_stock(item, {wh: 100})
    clients["stock_manager"].submit("Stock Reconciliation", draft["name"])
    posted = assert_stock(item, {wh: 123})
    gl = assert_gl("Stock Reconciliation", draft["name"])
    cancel_denial = deny(clients["stock"], "frappe.client.cancel", {
        "doctype": "Stock Reconciliation", "name": draft["name"]})
    assert_stock(item, {wh: 123})
    clients["stock_manager"].cancel("Stock Reconciliation", draft["name"])
    reversed_stock = assert_stock(item, {wh: 100})
    reversed_gl = assert_gl("Stock Reconciliation", draft["name"], cancelled=True)
    emit("native_reconciliation_role_and_ledger", status="PASS", voucher=draft["name"],
         create_denial=create_denial, submit_denial=submit_denial, cancel_denial=cancel_denial,
         posted=posted, gl=gl, reversed_stock=reversed_stock, reversed_gl=reversed_gl)


def internal_transfer():
    item, batch = new_stock("INTERNAL")
    wh = FIXTURE["warehouses"]
    client = FIXTURE["clients"]["stock"]
    receive(item, batch)
    draft = client.insert(stock_payload(item, batch, "Material Transfer", 20,
        source=wh["a"], target=wh["quarantine"]))
    client.submit("Stock Entry", draft["name"])
    moved = assert_stock(item, {wh["a"]: 80, wh["quarantine"]: 20})
    assert frappe.db.get_value("Batch", batch, "hbos_release_status") == "待检"
    client.cancel("Stock Entry", draft["name"])
    restored = assert_stock(item, {wh["a"]: 100, wh["quarantine"]: 0})
    foreign = stock_payload(item, batch, "Material Transfer", 1, source=wh["a"], target=wh["outside"])
    # Native validation may reject a cross-company document at save or submit.
    status, response = client.call("frappe.client.insert", {"doc": json.dumps(foreign)}, post=True)
    phase = "insert"
    if status == 200:
        foreign_name = response["message"]["name"]
        document = client.get_doc("Stock Entry", foreign_name)
        status, response = client.call("frappe.client.submit", {"doc": json.dumps(document)}, post=True)
        phase = "submit"
        if status == 200:
            client.cancel("Stock Entry", foreign_name)
            assert_stock(item, {wh["a"]: 100, wh["outside"]: 0})
            raise AssertionError("Cross-company Material Transfer posted; reversed by native cancel")
    assert status in (403, 417), f"Cross-company validation returned HTTP {status}"
    assert "company" in json.dumps(response).lower(), "Cross-company denial did not identify the company boundary"
    cross_company = {"http": status, "phase": phase, "exception": response.get("exc_type")}
    assert_stock(item, {wh["a"]: 100, wh["outside"]: 0})
    emit("pending_internal_quarantine_transfer", status="PASS", voucher=draft["name"],
         moved=moved, restored=restored, cross_company=cross_company)


def assert_coa_publication_rollback(coa, sample, batch):
    """Real renderer, injected PDF failure in bench, then unchanged native DB.

    This fault case uses the same QA identity in the bench process; it does not
    claim HTTP fault injection. The subsequent HTTP publication uses real PDF
    generation with every temporary wrapper restored.
    """
    from unittest.mock import patch

    import frappe.utils.pdf
    from hb_lims_app.hbos_lims import lims_service as service

    fresh_read()
    coa_fields = ["report_status", "published_by", "published_at", "pdf_attachment", "modified"]
    batch_fields = ["hbos_release_status", "hbos_release_source", "hbos_release_date",
        "hbos_lims_reference", "hbos_certificate_no", "hbos_certificate_file"]
    before_coa = frappe.db.get_value("HBOS COA", coa, coa_fields, as_dict=True)
    before_batch = frappe.db.get_value("Batch", batch, batch_fields, as_dict=True)
    before_sample = frappe.db.get_value("HBOS Sample", sample, "status")
    file_filter = {"attached_to_doctype": "HBOS COA", "attached_to_name": coa}
    before_files = sorted(frappe.get_all("File", filters=file_filter, pluck="name"))
    assert before_coa.report_status == "已审核" and before_sample == "检验完成"
    assert before_batch.hbos_release_status == "待检"
    observed = []
    original_renderer = service._coa_print_html

    def record_real_render(document):
        assert document.report_status == "已发布"
        assert document.published_by == FIXTURE["users"]["qa"] and document.published_at
        html = original_renderer(document)
        assert "已发布" in html and str(document.published_at) in html
        observed.append({"report_status": document.report_status,
            "published_by": document.published_by, "published_at": document.published_at,
            "real_renderer_called": True, "html_contains_publication_metadata": True})
        return html

    injected = "HBOS R3 synthetic PDF generation failure"
    try:
        frappe.set_user(FIXTURE["users"]["qa"])
        with patch.object(service, "_coa_print_html", side_effect=record_real_render):
            with patch.object(frappe.utils.pdf, "get_pdf", side_effect=RuntimeError(injected)) as failure:
                try:
                    service.publish_coa(coa)
                except RuntimeError as error:
                    assert str(error) == injected, "Unexpected failure before the PDF injection"
                else:
                    raise AssertionError("Injected PDF failure did not fail publication")
                failure.assert_called_once()
    finally:
        fresh_read()
    assert len(observed) == 1
    assert frappe.db.get_value("HBOS COA", coa, coa_fields, as_dict=True) == before_coa
    assert sorted(frappe.get_all("File", filters=file_filter, pluck="name")) == before_files
    assert frappe.db.get_value("Batch", batch, batch_fields, as_dict=True) == before_batch
    assert frappe.db.get_value("HBOS Sample", sample, "status") == before_sample
    try:
        frappe.set_user(FIXTURE["users"]["reviewer"])
        try:
            service.release_sample(sample)
        except frappe.ValidationError as error:
            assert "COA" in str(error), "Release failed for an unrelated reason"
        else:
            raise AssertionError("Sample released after failed COA publication")
    finally:
        fresh_read()
    assert frappe.db.get_value("Batch", batch, batch_fields, as_dict=True) == before_batch
    assert frappe.db.get_value("HBOS Sample", sample, "status") == before_sample
    emit("coa_publication_render_and_rollback", status="PASS", sample=sample, coa=coa,
         render_input=observed[0], fault_level="native service / same QA identity in bench",
         pdf_failure_injected=True, coa_and_files_unchanged=True, release_denied=True,
         batch_unchanged=True, temporary_wrappers_restored=True)


def release_through_existing_lims(item, batch, label):
    """Create the authority by real LIMS actions, never by assigning Batch fields."""
    clients = FIXTURE["clients"]
    manager, analyst = clients["lims_manager"], clients["analyst"]
    reviewer, qa = clients["reviewer"], clients["qa"]
    spec = manager.ok(LIMS + "create_specification", {"spec_code": "R3-" + label + "-SPEC",
        "spec_name": "Synthetic R3 release specification", "material_code": item,
        "material_name": "Synthetic release material", "standard_source": "企业内控", "version": "1.0",
        "effective_date": frappe.utils.today(), "items": [{"item": "R3-CI-TEST",
            "limits_type": "上限", "upper_limit": 100, "unit": "mg", "significant_digits": 2}]},
        post=True, json_body=True)
    manager.ok(LIMS + "activate_specification", {"spec_name": spec}, post=True)
    sample = manager.ok(LIMS + "register_sample", {"sample_type": FIXTURE["sample_type"],
        "material_code": item, "batch_no": batch, "item_ref": item, "batch_ref": batch,
        "sample_source": "生产取样", "specification": spec}, post=True)
    tasks = manager.ok(LIMS + "generate_tasks", {"sample_name": sample,
        "lab_department": FIXTURE["lab"]}, post=True)
    assert tasks, "LIMS generated no test tasks"
    for task in tasks:
        manager.ok(LIMS + "assign_task", {"task_name": task, "assignee": FIXTURE["users"]["analyst"]}, post=True)
        result = analyst.ok(LIMS + "start_task", {"task_name": task}, post=True)["result"]
        analyst.ok(LIMS + "submit_result", {"result_name": result, "raw_value": 50, "result_value": 50}, post=True)
        reviewer.ok(LIMS + "review_result", {"result_name": result}, post=True)
        manager.ok(LIMS + "approve_result", {"result_name": result}, post=True)
    coa = reviewer.ok(LIMS + "create_coa", {"sample_name": sample}, post=True)
    reviewer.ok(LIMS + "review_coa", {"coa_name": coa}, post=True)
    if label == "RELEASE":
        assert_coa_publication_rollback(coa, sample, batch)
    published = qa.ok(LIMS + "publish_coa", {"coa_name": coa}, post=True)
    assert isinstance(published, dict), f"publish_coa must return a mapping; received {type(published).__name__}"
    emit("lims_publication_http_response", sample=sample, coa=coa,
         returned_coa=published.get("coa"), pdf_url=published.get("pdf"))
    assert isinstance(published.get("pdf"), str) and published["pdf"].startswith("/private/files/"), (
        f"publish_coa did not return a private PDF URL: {published.get('pdf')!r}")
    released = reviewer.ok(LIMS + "release_sample", {"sample_name": sample}, post=True)
    assert isinstance(released, dict), f"release_sample must return a mapping; received {type(released).__name__}"
    emit("lims_release_http_response", expected_sample=sample, expected_coa=coa, expected_batch=batch,
         sample=released.get("sample"), coa=released.get("coa"), batch=released.get("batch"))
    assert released.get("batch") == batch, f"release_sample Batch mismatch: {released.get('batch')!r} != {batch!r}"
    assert released.get("coa") == coa, f"release_sample COA mismatch: {released.get('coa')!r} != {coa!r}"
    fresh_read()
    projection_fields = ["hbos_release_status", "hbos_release_source", "hbos_release_date",
        "hbos_lims_reference", "hbos_certificate_no", "hbos_certificate_file"]
    projection = frappe.db.get_value("Batch", batch, projection_fields, as_dict=True)
    emit("lims_batch_projection", batch=batch, projection=projection,
         field_types={field: frappe.get_meta("Batch").get_field(field).fieldtype for field in projection_fields})
    assert projection, f"Published LIMS release has no native Batch row: {batch}"
    assert projection.hbos_release_status == "已放行", f"Batch release status mismatch: {projection.hbos_release_status!r}"
    assert projection.hbos_release_source == "LIMS", f"Batch release source mismatch: {projection.hbos_release_source!r}"
    assert projection.hbos_lims_reference == sample, f"Batch LIMS reference mismatch: {projection.hbos_lims_reference!r} != {sample!r}"
    assert projection.hbos_certificate_no == coa, f"Batch COA certificate mismatch: {projection.hbos_certificate_no!r} != {coa!r}"
    published_coa = frappe.db.get_value("HBOS COA", coa,
        ["report_status", "published_by", "published_at", "pdf_attachment"], as_dict=True)
    emit("lims_published_coa_record", coa=coa, published_coa=published_coa,
         expected_publisher=FIXTURE["users"]["qa"])
    assert published_coa, f"Published COA record is missing: {coa}"
    assert published_coa.report_status == "已发布", f"COA report status mismatch: {published_coa.report_status!r}"
    assert published_coa.published_by == FIXTURE["users"]["qa"], f"COA publishing identity mismatch: {published_coa.published_by!r}"
    assert published_coa.published_at, "Published COA has no publication timestamp"
    linked_files = frappe.get_all("File", filters={"file_url": projection.hbos_certificate_file},
        fields=["name", "file_name", "file_url", "is_private", "attached_to_doctype", "attached_to_name"],
        order_by="name", limit_page_length=20)
    # Native Attach fields also create File records for the Batch projection.
    # Audit the COA attachment itself, not an arbitrary record sharing its URL.
    file = frappe.get_doc("File", {"file_url": projection.hbos_certificate_file,
        "attached_to_doctype": "HBOS COA", "attached_to_name": coa})
    emit("lims_coa_file_lookup", certificate_url=projection.hbos_certificate_file,
         selected_file=file.name, same_url_records=linked_files)
    assert file.is_private, f"Published COA File is not private: {file.name}"
    assert file.attached_to_doctype == "HBOS COA", f"Published COA File has wrong parent type: {file.attached_to_doctype!r}"
    assert file.attached_to_name == coa, f"Published COA File has wrong parent: {file.attached_to_name!r} != {coa!r}"
    content = file.get_content()
    emit("lims_coa_pdf_bytes", file=file.name, content_type=type(content).__name__,
         bytes=len(content), sha256=hashlib.sha256(content).hexdigest() if isinstance(content, bytes) else None)
    assert content.startswith(b"%PDF-"), "Published COA must contain a real PDF"
    return {"sample": sample, "coa": coa, "real_pdf": True,
            "publication_positive_level": "real HTTP / unpatched PDF generator"}


def lims_release_and_issue():
    item, batch = new_stock("RELEASE")
    clients = FIXTURE["clients"]
    wh = FIXTURE["warehouses"]["a"]
    receive(item, batch)
    outward = clients["stock"].insert(stock_payload(item, batch, "Material Issue", 7, source=wh))
    outward_doc = clients["stock"].get_doc("Stock Entry", outward["name"])
    before = deny(clients["stock"], "frappe.client.submit", {"doc": json.dumps(outward_doc)},
        codes=(417,), contains="LIMS")
    assert_stock(item, {wh: 100})
    projection_denial = deny(clients["stock"], "frappe.client.set_value", {
        "doctype": "Batch", "name": batch, "fieldname": "hbos_release_status", "value": "已放行"},
        contains="LIMS")
    authority = release_through_existing_lims(item, batch, "RELEASE")
    clients["stock"].submit("Stock Entry", outward["name"])
    issued = assert_stock(item, {wh: 93})
    issue_gl = assert_gl("Stock Entry", outward["name"])
    clients["stock"].cancel("Stock Entry", outward["name"])
    restored = assert_stock(item, {wh: 100})
    reverse_gl = assert_gl("Stock Entry", outward["name"], cancelled=True)
    emit("existing_lims_native_release_to_inventory", status="PASS", **authority,
         batch=batch, before_release_denied=before, projection_direct_write_denied=projection_denial,
         issued=issued, issue_gl=issue_gl, restored=restored, reverse_gl=reverse_gl)


def registered_jobworker_transfer():
    """Native SCO establishes that the same-company target is a job worker warehouse."""
    item, batch = new_stock("JOBWORKER")
    wh = FIXTURE["warehouses"]
    receive(item, batch)
    frappe.set_user("Administrator")
    supplier = native_insert({"doctype": "Supplier", "supplier_name": "HBOS R3 CI Job Worker",
        "supplier_type": "Company"}).name
    finished = native_insert({"doctype": "Item", "item_code": "HBOS-R3-FINISHED",
        "item_group": FIXTURE["group"], "stock_uom": FIXTURE["uom"],
        "is_stock_item": 1, "is_sub_contracted_item": 1}).name
    service = native_insert({"doctype": "Item", "item_code": "HBOS-R3-SERVICE",
        "item_group": FIXTURE["group"], "stock_uom": FIXTURE["uom"], "is_stock_item": 0}).name
    bom = native_insert({"doctype": "BOM", "item": finished, "company": FIXTURE["company"],
        "quantity": 1, "is_active": 1, "is_default": 1,
        "items": [{"item_code": item, "qty": 1, "uom": FIXTURE["uom"], "rate": 10}]})
    bom.submit()
    po = native_insert({"doctype": "Purchase Order", "company": FIXTURE["company"],
        "supplier": supplier, "is_subcontracted": 1, "is_old_subcontracting_flow": 0,
        "transaction_date": frappe.utils.today(), "schedule_date": frappe.utils.today(),
        "currency": "USD", "conversion_rate": 1, "set_warehouse": wh["a"],
        "supplier_warehouse": wh["jobworker"],
        "items": [{"item_code": service, "qty": 1, "rate": 5, "uom": FIXTURE["uom"],
            "conversion_factor": 1, "warehouse": wh["a"], "fg_item": finished, "fg_item_qty": 1,
            "schedule_date": frappe.utils.today()}]})
    po.submit()
    from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_subcontracting_order
    sco = get_mapped_subcontracting_order(po.name)
    sco.supplier_warehouse = wh["jobworker"]
    sco.set_warehouse = wh["a"]
    sco.set_reserve_warehouse = wh["a"]
    sco.reserve_stock = 0
    sco.insert()
    sco.submit()
    frappe.db.commit()
    assert sco.docstatus == 1 and sco.supplier_warehouse == wh["jobworker"]
    assert any(row.rm_item_code == item and row.main_item_code == finished
               for row in sco.supplied_items), "Native SCO/BOM did not establish the supplied raw-material relationship"
    client = FIXTURE["clients"]["stock"]
    subcontract = stock_payload(item, batch, "Send to Subcontractor", 1,
        source=wh["a"], target=wh["jobworker"])
    subcontract.update(supplier=supplier, subcontracting_order=sco.name)
    subcontract["items"][0]["subcontracted_item"] = finished
    native_send = client.insert(subcontract)
    send_denial = deny(client, "frappe.client.submit", {
        "doc": json.dumps(client.get_doc("Stock Entry", native_send["name"]))},
        codes=(417,), contains="LIMS")
    assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
    emit("native_send_to_subcontractor_pending_denied", status="PASS", native_sco=sco.name,
         voucher=native_send["name"], denial=send_denial)
    target = client.insert(stock_payload(item, batch, "Material Transfer", 1,
        source=wh["a"], target=wh["jobworker"]))
    document = client.get_doc("Stock Entry", target["name"])
    status, response = client.call("frappe.client.submit", {"doc": json.dumps(document)}, post=True)
    fresh_read()
    reached = status == 200 and frappe.db.get_value("Stock Entry", target["name"], "docstatus") == 1
    if reached:
        moved = assert_stock(item, {wh["a"]: 99, wh["jobworker"]: 1})
        posted_gl = observe_transfer_gl(target["name"])
        client.cancel("Stock Entry", target["name"])
        restored = assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
        reversed_gl = observe_transfer_gl(target["name"])
        emit("registered_jobworker_material_transfer", status="FAIL", native_sco=sco.name,
             voucher=target["name"], batch=batch, pending_batch_reached_target=True,
             http=status, moved=moved, posted_gl=posted_gl, restored=restored,
             reversed_gl=reversed_gl, reversed_by_native_cancel=True)
        raise AssertionError("Unreleased Batch reached an ERPNext-registered Job Worker Warehouse using Material Transfer")
    assert status in (403, 417), f"Unexpected external-target failure: HTTP {status}"
    detail = json.dumps(response, ensure_ascii=False)
    assert "LIMS" in detail or "放行" in detail, "External rejection did not prove quality-release enforcement"
    assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
    authority = release_through_existing_lims(item, batch, "JOBWORKER")
    client.submit("Stock Entry", native_send["name"])
    send_moved = assert_stock(item, {wh["a"]: 99, wh["jobworker"]: 1})
    send_submitted = frappe.db.get_value("Stock Entry", native_send["name"], "docstatus")
    assert send_submitted == 1, "Released Send to Subcontractor did not submit natively"
    send_gl = observe_transfer_gl(native_send["name"])
    client.cancel("Stock Entry", native_send["name"])
    send_restored = assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
    send_cancelled = frappe.db.get_value("Stock Entry", native_send["name"], "docstatus")
    assert send_cancelled == 2, "Released Send to Subcontractor did not cancel natively"
    send_reversed_gl = observe_transfer_gl(native_send["name"])
    emit("native_send_to_subcontractor_released_submit_cancel", status="PASS", native_sco=sco.name,
         voucher=native_send["name"], batch=batch, actor=FIXTURE["users"]["stock"], **authority,
         submitted_docstatus=send_submitted, moved=send_moved, posted_gl=send_gl,
         cancelled_docstatus=send_cancelled, restored=send_restored, reversed_gl=send_reversed_gl,
         execution_level="same Stock User HTTP submit/cancel; native controller and ledgers")
    client.submit("Stock Entry", target["name"])
    released_moved = assert_stock(item, {wh["a"]: 99, wh["jobworker"]: 1})
    posted_gl = observe_transfer_gl(target["name"])
    client.cancel("Stock Entry", target["name"])
    restored = assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
    reversed_gl = observe_transfer_gl(target["name"])
    emit("registered_jobworker_material_transfer", status="PASS", native_sco=sco.name,
         voucher=target["name"], batch=batch, pending_batch_reached_target=False,
         http=status, **authority, released_moved=released_moved,
         posted_gl=posted_gl, cancelled_restored=restored, reversed_gl=reversed_gl)


def observe_transfer_gl(voucher):
    """Record native GL facts; same-account internal transfers may have no rows."""
    fresh_read()
    rows = frappe.get_all("GL Entry", filters={"voucher_type": "Stock Entry", "voucher_no": voucher},
        fields=["name", "account", "debit", "credit", "is_cancelled"], order_by="name")
    return {"entries": len(rows), "rows": rows,
            "debit": sum(float(row.debit) for row in rows),
            "credit": sum(float(row.credit) for row in rows),
            "zero_rows_permitted_for_same_inventory_account": True}


def _automatic_http(client, path, params=None, *, post=False, timeout=180):
    """Binary-safe HTTP using the Client's existing cookie jar and actual CSRF."""
    encoded = urlencode(params or {}).encode()
    url = "http://127.0.0.1:8000" + path
    if encoded and not post:
        url += ("&" if "?" in url else "?") + encoded.decode()
    request = Request(url, data=encoded if post else None, headers=dict(client.headers))
    try:
        response = client.opener.open(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            payload = {}
        return response.code, payload, body


def _automatic_user(scoped):
    key = "automatic_scoped" if scoped else "automatic_pure"
    if key not in FIXTURE["clients"]:
        fresh_read()
        time.sleep(8)
        user = "r3-inventory-" + key.replace("_", "-") + "@example.invalid"
        password = secrets.token_urlsafe(32)
        native_insert({"doctype": "User", "email": user, "first_name": "Synthetic Receipt PDF",
            "enabled": 1, "send_welcome_email": 0, "user_type": "System User", "language": "en",
            "new_password": password, "roles": [{"role": "Stock User"}]})
        if scoped:
            native_insert({"doctype": "User Permission", "user": user, "allow": "Warehouse",
                "for_value": FIXTURE["warehouses"]["a"], "apply_to_all_doctypes": 1, "hide_descendants": 1})
        frappe.defaults.set_user_default("Company", FIXTURE["company"], user)
        frappe.db.commit()
        frappe.clear_cache(user=user)
        FIXTURE["clients"][key] = Client().login(user, password)
        FIXTURE["users"][key] = user
    return FIXTURE["users"][key], FIXTURE["clients"][key]


def _automatic_permissions(user, batch):
    """Native role/range/DocShare/Batch permissions, not UI capability flags."""
    fresh_read()
    doc = frappe.get_doc("Batch", batch)
    return {
        "roles": sorted(frappe.get_roles(user)),
        "batch_read": bool(doc.has_permission("read", user=user)),
        "batch_write": bool(doc.has_permission("write", user=user)),
        "warehouse_read": sorted(frappe.get_list("Warehouse", pluck="name", limit_page_length=0, user=user)),
        "user_permissions": frappe.get_all("User Permission", filters={"user": user},
            fields=["name", "allow", "for_value", "apply_to_all_doctypes", "hide_descendants"], order_by="name"),
        "shares": frappe.get_all("DocShare", filters={"user": user},
            fields=["share_doctype", "share_name", "read", "write", "share"], order_by="name"),
    }


def _automatic_card_ids(batch):
    fresh_read()
    return sorted(frappe.get_all("File", filters={"attached_to_doctype": "Batch", "attached_to_name": batch}, pluck="name"))


def _automatic_card_error_logs(batch, voucher):
    """Only the current synthetic receipt's card errors, without request metadata."""
    try:
        rows = frappe.get_all("Error Log", filters={"method": ["in", [
            "生成货位卡/待检证失败", "自动生成货位卡/待检证失败（整体）"]],
            "error": ["like", "%" + voucher + "%"]},
            fields=["method", "error"], order_by="creation desc", limit_page_length=5)
        errors = []
        for row in rows:
            safe_lines = []
            for line in str(row.error or "").splitlines():
                if line.lstrip().startswith("Traceback"):
                    break
                if re.search(r"cookie|csrf|password|authorization|session|\bsid\b", line, re.I):
                    safe_lines.append("[authentication or session detail omitted]")
                elif not line.lstrip().startswith(('File "', "locals:")):
                    safe_lines.append(line[:800])
                if len(safe_lines) == 4:
                    break
            errors.append({"title": row.method, "message": "\n".join(safe_lines)[:1500]})
        emit("automatic_receipt_missing_pdf_errors", batch=batch, voucher=voucher, errors=errors)
    except Exception as error:
        # Diagnostics cannot replace the original missing-PDF gate below.
        emit("automatic_receipt_error_diagnostic_unavailable", batch=batch, voucher=voucher,
             error=type(error).__name__)


def _automatic_card(batch, actor, *, warehouses, voucher):
    """Require actual on_submit output; no standalone/fallback PDF is acceptable."""
    from pypdf import PdfReader

    names = _automatic_card_ids(batch)
    if not names:
        _automatic_card_error_logs(batch, voucher)
    assert len(names) == 1, f"Automatic receipt must create exactly one private Batch PDF: {names}"
    doc = frappe.get_doc("File", names[0])
    assert doc.owner == actor, "Automatic card must preserve the actual receiving actor"
    assert doc.is_private and doc.file_url.startswith("/private/files/")
    assert doc.attached_to_doctype == "Batch" and doc.attached_to_name == batch
    assert doc.file_name.startswith("HBOS-") and "-待检证+货位卡" in doc.file_name and doc.file_name.endswith(".pdf")
    content = Path(doc.get_full_path()).read_bytes()
    assert content.startswith(b"%PDF-"), "Automatic receipt attachment is not a PDF"
    assert re.fullmatch(r"HBOS-R3-AUTO-[A-Z0-9-]+", batch), "Only synthetic receipt PDFs may be retained as CI evidence"
    evidence_dir = Path("/tmp/owner-r3-pdf-evidence")
    evidence_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    evidence_name = "synthetic-transaction-" + batch
    (evidence_dir / (evidence_name + ".pdf")).write_bytes(content)
    reader = PdfReader(io.BytesIO(content))
    page_texts = [page.extract_text() or "" for page in reader.pages]
    diagnostic = {"batch": batch, "voucher": voucher, "file": doc.name,
                  "owner": doc.owner, "is_private": bool(doc.is_private), "file_url": doc.file_url,
                  "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
                  "pages": len(reader.pages), "page_details": [
                      {"page": index + 1, "width_pt": float(page.mediabox.width),
                       "height_pt": float(page.mediabox.height), "text_characters": len(page_texts[index]),
                       "text": page_texts[index][:1500]} for index, page in enumerate(reader.pages)]}
    (evidence_dir / (evidence_name + ".json")).write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
    emit("automatic_receipt_pdf_diagnostic", **diagnostic)
    compact = re.sub(r"\s+", "", " ".join(page_texts))
    for warehouse in warehouses:
        short = re.sub(r"\s+", "", warehouse.split(" - ")[0])
        assert short in compact, "Real automatic PDF is missing synthetic warehouse " + short
    return {"name": doc.name, "file_name": doc.file_name, "file_url": doc.file_url,
            "owner": doc.owner, "batch": batch, "is_private": bool(doc.is_private),
            "bytes": len(content), "pages": len(reader.pages),
            "sha256": hashlib.sha256(content).hexdigest(), "checked_warehouses": list(warehouses)}


def _automatic_source(voucher, batch, actor, warehouse, qty):
    """Read the submitted native documents and their SLE linkage, never fabricate it."""
    fresh_read()
    entry = frappe.get_doc("Stock Entry", voucher)
    assert entry.docstatus == 1 and entry.purpose == "Material Receipt"
    assert entry.owner == actor and entry.modified_by == actor
    bundles = []
    for detail in entry.items:
        assert detail.t_warehouse == warehouse and not detail.s_warehouse
        assert detail.serial_and_batch_bundle, "Native receipt did not create its Batch Bundle"
        bundle = frappe.get_doc("Serial and Batch Bundle", detail.serial_and_batch_bundle)
        assert bundle.docstatus == 1 and not bundle.is_cancelled
        assert bundle.voucher_type == "Stock Entry" and bundle.voucher_no == voucher
        rows = [row for row in bundle.entries if row.batch_no == batch and not row.is_cancelled]
        assert rows and all(float(row.qty) > 0 for row in rows)
        assert abs(sum(float(row.qty) for row in rows) - qty) < 0.00001
        ledger = frappe.get_all("Stock Ledger Entry", filters={"voucher_type": "Stock Entry",
            "voucher_no": voucher, "serial_and_batch_bundle": bundle.name, "is_cancelled": 0},
            fields=["name", "warehouse", "actual_qty"])
        assert ledger and all(row.warehouse == warehouse and float(row.actual_qty) > 0 for row in ledger)
        assert abs(sum(float(row.actual_qty) for row in ledger) - qty) < 0.00001
        bundles.append({"name": bundle.name, "batch_entries": len(rows), "sle": ledger})
    result = {"voucher": voucher, "owner": entry.owner, "docstatus": entry.docstatus,
              "purpose": entry.purpose, "native_bundles": bundles, "gl": assert_gl("Stock Entry", voucher)}
    emit("automatic_receipt_native_source", batch=batch, **result)
    return result


def _automatic_denials(user, client, batch, voucher, card, *, scoped):
    """No internal receipt authority is inherited by the next ordinary request."""
    before_counts = stock_write_counts()
    before_card_ids = _automatic_card_ids(batch)
    regenerate = "hb_inventory_app.hbos_inventory.doc_gen.regenerate_for_batch"
    fake_context = {"actor": user, "entry": voucher, "batch": batch}
    fake_flags = {"ignore_permissions": True, "ignore_print_permissions": True,
                  "hbos_automatic_receipt_card": fake_context, "_AUTOMATIC_CARD": [user, voucher, batch]}
    deny(client, regenerate, {"batch_name": batch}, exception="PermissionError",
         label="automatic_receipt_does_not_grant_manual_regeneration", audit_stock=True)
    deny(client, regenerate, {"batch_name": batch, "flags": json.dumps(fake_flags),
         "_automatic_card": json.dumps(fake_context)}, exception="PermissionError",
         label="client_parameters_do_not_establish_receipt_context", audit_stock=True)
    for flag_payload in ({}, fake_flags):
        payload = {"doctype": "File", "file_name": card["file_name"], "file_url": card["file_url"],
            "is_private": 1, "attached_to_doctype": "Batch", "attached_to_name": batch,
            "flags": flag_payload}
        deny(client, "frappe.client.insert", {"doc": json.dumps(payload)},
             exception="PermissionError", label="native_file_creation_without_receipt_context"
             + ("_forged_flags" if flag_payload else ""), audit_stock=True)
    methods = (
        "hb_inventory_app.hbos_inventory.doc_gen.generate_for_batch",
        "hb_inventory_app.hbos_inventory.doc_gen.generate_for_stock_entry",
        "hb_inventory_app.hbos_inventory.card_permissions._automatic_receipt_card",
        "hb_inventory_app.hbos_inventory.card_permissions._automatic_print_permission",
    )
    for method in methods:
        for post in (False, True):
            status, payload = client.call(method, {"batch_name": batch, "doc": voucher,
                "doctype": "Batch", "name": batch, "print_format": "HBOS 自产货位卡"}, post=post)
            emit("automatic_receipt_internal_endpoint_denial", method=method,
                 http_method="POST" if post else "GET", http=status, exception=payload.get("exc_type"))
            assert status == 403 and payload.get("exc_type") == "PermissionError", "Internal helper became an RPC"
    deny(client, "run_doc_method", {"dt": "Stock Entry", "dn": voucher, "method": "on_submit"},
         exception="PermissionError", label="cannot_replay_on_submit_via_rpc", audit_stock=True)
    assert client.ok("frappe.auth.get_logged_user") == user
    assert stock_write_counts() == before_counts and _automatic_card_ids(batch) == before_card_ids
    fresh_read()
    assert hashlib.sha256(Path(frappe.get_doc("File", card["name"]).get_full_path()).read_bytes()).hexdigest() == card["sha256"]
    for label, path, params in (
        ("private_url", quote(card["file_url"], safe="/"), None),
        ("download_file", "/api/method/download_file", {"file_url": card["file_url"]}),
    ):
        status, payload, body = _automatic_http(client, path, params)
        if scoped:
            assert status == 403 and not body.startswith(b"%PDF-"), "Restricted receiving owner downloaded full card"
            assert FIXTURE["warehouses"]["b"].split(" - ")[0].encode() not in body
        else:
            assert status == 200 and hashlib.sha256(body).hexdigest() == card["sha256"], "Full-scope owner cannot read actual generated PDF"
        emit("automatic_receipt_pdf_access", path=label, scoped=scoped, http=status,
             receiving_owner=user, pdf_returned=body.startswith(b"%PDF-"))
    if scoped:
        status, payload, body = _automatic_http(client, "/api/method/frappe.core.api.file.zip_files",
            {"files": json.dumps([card["name"]])})
        assert status == 403 and payload.get("exc_type") == "PermissionError"
        emit("automatic_receipt_scoped_owner_zip_denied", http=status, exception=payload.get("exc_type"))


def automatic_receipt_private_pdf(*, scoped=False):
    user, client = _automatic_user(scoped)
    label = "AUTO-SCOPED" if scoped else "AUTO-PURE"
    item, batch = new_stock(label)
    wh = FIXTURE["warehouses"]
    if scoped:
        # Establish B stock with a genuine authorized receipt. The A-only user's
        # later derived PDF includes that same batch's A+B inventory, but its
        # receiving owner still must not be able to download the full snapshot.
        seed = FIXTURE["clients"]["stock"].insert(stock_payload(item, batch, "Material Receipt", 7, target=wh["b"]))
        FIXTURE["clients"]["stock"].submit("Stock Entry", seed["name"])
        assert_stock(item, {wh["a"]: 0, wh["b"]: 7})
        assert_gl("Stock Entry", seed["name"])
    before_permissions = _automatic_permissions(user, batch)
    assert not before_permissions["batch_read"] and not before_permissions["batch_write"]
    assert "Stock User" in before_permissions["roles"]
    assert not {"Item Manager", "Stock Manager", "System Manager"}.intersection(before_permissions["roles"])
    assert wh["a"] in before_permissions["warehouse_read"]
    assert (wh["b"] not in before_permissions["warehouse_read"]) == scoped
    qty = 3 if scoped else 11
    old_cards = _automatic_card_ids(batch)
    draft = client.insert(stock_payload(item, batch, "Material Receipt", qty, target=wh["a"]))
    assert draft["docstatus"] == 0 and _automatic_card_ids(batch) == old_cards, "Draft save generated a card"
    status, payload, _ = _automatic_http(client, "/api/method/frappe.client.submit",
        {"doc": json.dumps(client.get_doc("Stock Entry", draft["name"]))}, post=True)
    assert status == 200, "Pure Stock User receipt submit failed: " + str(payload.get("exc_type"))
    expected = {wh["a"]: qty, **({wh["b"]: 7} if scoped else {})}
    balances = assert_stock(item, expected)
    source = _automatic_source(draft["name"], batch, user, wh["a"], qty)
    card = _automatic_card(batch, user, warehouses=list(expected), voucher=draft["name"])
    assert card["name"] not in old_cards, "on_submit reused an old card instead of generating the new batch snapshot"
    _automatic_denials(user, client, batch, draft["name"], card, scoped=scoped)
    after_permissions = _automatic_permissions(user, batch)
    assert after_permissions == before_permissions, "Automatic receipt altered native business permissions"
    emit("automatic_receipt_private_pdf", status="PASS", scoped=scoped,
         source=source, balances=balances, card=card, batch_read=False, batch_write=False,
         roles_and_ranges_unchanged=True, privileges_added=False,
         positive_level="real HTTP native insert/submit/on_submit + real PDF; no mocks or SQL fixtures")


def automatic_receipt_context_restoration():
    """Same-process native submit proves context/print flags are reset on return."""
    from hb_inventory_app.hbos_inventory import card_permissions, doc_gen

    user, _ = _automatic_user(True)
    item, batch = new_stock("AUTO-CONTEXT")
    warehouse = FIXTURE["warehouses"]["a"]
    before_permissions = _automatic_permissions(user, batch)
    assert not before_permissions["batch_read"] and not before_permissions["batch_write"]
    before_context = card_permissions._AUTOMATIC_CARD.get()
    assert before_context is None, "Native runner already has a receipt capability"
    before_flag = ("ignore_print_permissions" in frappe.flags, frappe.flags.get("ignore_print_permissions"))
    assert not before_flag[1], "Do not start the lifecycle proof with elevated print flags"
    try:
        frappe.set_user(user)
        doc = frappe.get_doc(stock_payload(item, batch, "Material Receipt", 2, target=warehouse)).insert()
        assert doc.docstatus == 0
        doc.submit()  # Actual StockEntry controller + installed on_submit hooks.
        assert frappe.session.user == user, "Automatic generation changed the receiving identity"
        assert card_permissions._AUTOMATIC_CARD.get() is None
        assert not card_permissions._is_automatic_batch(batch)
        assert ("ignore_print_permissions" in frappe.flags, frappe.flags.get("ignore_print_permissions")) == before_flag
        frappe.db.commit()
        # In the SAME Python context, not a fresh HTTP request, the user no
        # longer has the internal ability even when calling the service directly.
        try:
            doc_gen.generate_for_batch(batch)
        except frappe.PermissionError:
            pass
        else:
            raise AssertionError("Receipt capability survived and allowed a later direct regeneration")
        assert card_permissions._AUTOMATIC_CARD.get() is None
        assert ("ignore_print_permissions" in frappe.flags, frappe.flags.get("ignore_print_permissions")) == before_flag
    finally:
        fresh_read()
    balances = assert_stock(item, {warehouse: 2})
    source = _automatic_source(doc.name, batch, user, warehouse, 2)
    card = _automatic_card(batch, user, warehouses=[warehouse], voucher=doc.name)
    assert _automatic_permissions(user, batch) == before_permissions
    emit("automatic_receipt_context_restoration", status="PASS", source=source,
         balances=balances, card=card, same_process=True, context_restored=True,
         print_flag_restored=True, direct_regeneration_after_context_denied=True,
         native_permissions_unchanged=True, execution_level="native bench insert/submit; no permission stubs")


def run():
    guard()
    setup()
    for name, fn in (
        ("receipt_and_permissions", receipt_and_permissions),
        ("native_reconciliation", reconciliation),
        ("internal_and_cross_company_transfer", internal_transfer),
        ("existing_lims_release_chain", lims_release_and_issue),
        ("registered_external_target", registered_jobworker_transfer),
        ("automatic_receipt_pure_stock_user", automatic_receipt_private_pdf),
        ("automatic_receipt_scoped_stock_user", lambda: automatic_receipt_private_pdf(scoped=True)),
        ("automatic_receipt_context_restoration", automatic_receipt_context_restoration),
    ):
        fresh_read()
        try:
            fn()
        except Exception as error:
            frappe.db.rollback()
            result = {"name": name, "status": "FAIL", "error": type(error).__name__,
                      "detail": str(error)[:1600],
                      "frames": [{"file": frame.filename, "line": frame.lineno, "function": frame.name}
                                 for frame in traceback.extract_tb(error.__traceback__)[-12:]]}
        else:
            result = {"name": name, "status": "PASS"}
        RESULTS.append(result)
        emit("case_result", **result)
    emit("summary", results=RESULTS, real_database="NOT_TOUCHED", production="NOT_DEPLOYED",
         dependency=LIMS_AUTHORITY)
    assert all(row["status"] == "PASS" for row in RESULTS), "Native inventory gate has unmet cases"
    return {"ok": True, "results": RESULTS}
