"""R3 native inventory / existing-product LIMS proof on a fresh GitHub CI Site.

Runner-only entry point: copy this file into the disposable application's package
and invoke ``run`` with bench execute. This is not a whitelisted business API.
Stock/GL/Batch-release facts are created only by native document actions and the
existing LIMS services. No SQL fixtures, permission stubs, or release-field writes
are used to make a positive case pass. Failed cases remain visible in the result.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from datetime import date
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

import frappe


LIMS_AUTHORITY = (
    "Product 45658fe4b84d8fb7dd4433c459aa30572e0d13d3 LIMS + "
    "three-line in-memory COA publication metadata reorder; no PR43"
)
LIMS_AUTHORITY_SHA256 = {
    "hb_lims_app/hb_lims_app/hbos_lims/lims_service.py":
        "89ae137faf69d70d83b137e6b980b44c433339b4d31cac227912abe0480a58e2",
    "hb_lims_app/hb_lims_app/hbos_lims/workflow_contract.py":
        "c65dbc7dbd434cf6a9acdecd75934780394ef586bc913d4c6530437e59d8cfbc",
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
         source_product="45658fe4b84d8fb7dd4433c459aa30572e0d13d3",
         authority=LIMS_AUTHORITY, sha256=LIMS_AUTHORITY_SHA256,
         stock_sql_fixtures=False, release_projection_stubs=False)


class Client:
    """Use the same session/CSRF/native endpoints as the shipped Portal clients."""

    def __init__(self):
        origin = str(frappe.conf.hbos_portal_origin)
        self.headers = {"Host": urlsplit(origin).netloc, "Origin": origin,
                        "X-Requested-With": "XMLHttpRequest"}
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(self, method, params=None, *, post=False, csrf=True):
        encoded = urlencode(params or {}).encode()
        url = "http://127.0.0.1:8000/api/method/" + method
        headers = dict(self.headers)
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

    def ok(self, method, params=None, *, post=False):
        status, payload = self.call(method, params, post=post)
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


def deny(client, method, params, *, codes=(403,), contains=None, csrf=True):
    status, payload = client.call(method, params, post=True, csrf=csrf)
    assert status in codes, f"{method}: expected denial {codes}, got HTTP {status}"
    if contains:
        detail = json.dumps(payload, ensure_ascii=False)
        assert contains.lower() in detail.lower(), f"Expected {contains!r} denial, got {payload.get('exc_type')}"
    return {"http": status, "exception": payload.get("exc_type")}


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
    no_role = deny(clients["none"], "frappe.client.insert", {"doc": json.dumps(payload)})
    guest = deny(Client(), "frappe.client.insert", {"doc": json.dumps(payload)})
    cross = dict(payload, items=[dict(payload["items"][0], t_warehouse=wh["b"])])
    cross_scope = deny(clients["restricted"], "frappe.client.insert", {"doc": json.dumps(cross)})
    csrf = deny(clients["stock"], "frappe.client.insert", {"doc": json.dumps(payload)}, csrf=False)
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
        "effective_date": frappe.utils.today(), "items": json.dumps([{"item": "R3-CI-TEST",
            "limits_type": "上限", "upper_limit": 100, "unit": "mg", "significant_digits": 2}])}, post=True)
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
    assert published.get("pdf", "").startswith("/private/files/")
    released = reviewer.ok(LIMS + "release_sample", {"sample_name": sample}, post=True)
    assert released["batch"] == batch and released["coa"] == coa
    fresh_read()
    projection = frappe.db.get_value("Batch", batch, ["hbos_release_status", "hbos_release_source",
        "hbos_release_date", "hbos_lims_reference", "hbos_certificate_no", "hbos_certificate_file"], as_dict=True)
    assert projection.hbos_release_status == "已放行" and projection.hbos_release_source == "LIMS"
    assert projection.hbos_lims_reference == sample and projection.hbos_certificate_no == coa
    published_coa = frappe.db.get_value("HBOS COA", coa,
        ["report_status", "published_by", "published_at"], as_dict=True)
    assert published_coa.report_status == "已发布"
    assert published_coa.published_by == FIXTURE["users"]["qa"] and published_coa.published_at
    file = frappe.get_doc("File", {"file_url": projection.hbos_certificate_file})
    assert file.is_private and file.attached_to_doctype == "HBOS COA" and file.attached_to_name == coa
    assert file.get_content().startswith(b"%PDF-"), "Published COA must contain a real PDF"
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
    client = FIXTURE["clients"]["stock"]
    subcontract = stock_payload(item, batch, "Send to Subcontractor", 1,
        source=wh["a"], target=wh["jobworker"])
    subcontract.update(supplier=supplier, subcontracting_order=sco.name)
    subcontract["items"][0]["main_item_code"] = finished
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
        client.cancel("Stock Entry", target["name"])
        assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
        emit("registered_jobworker_material_transfer", status="FAIL", native_sco=sco.name,
             pending_batch_reached_target=True, http=status, moved=moved, reversed_by_native_cancel=True)
        raise AssertionError("Unreleased Batch reached an ERPNext-registered Job Worker Warehouse using Material Transfer")
    assert status in (403, 417), f"Unexpected external-target failure: HTTP {status}"
    detail = json.dumps(response, ensure_ascii=False)
    assert "LIMS" in detail or "放行" in detail, "External rejection did not prove quality-release enforcement"
    assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
    authority = release_through_existing_lims(item, batch, "JOBWORKER")
    client.submit("Stock Entry", target["name"])
    released_moved = assert_stock(item, {wh["a"]: 99, wh["jobworker"]: 1})
    client.cancel("Stock Entry", target["name"])
    restored = assert_stock(item, {wh["a"]: 100, wh["jobworker"]: 0})
    emit("registered_jobworker_material_transfer", status="PASS", native_sco=sco.name,
         pending_batch_reached_target=False, http=status, **authority,
         released_moved=released_moved, cancelled_restored=restored)


def run():
    guard()
    setup()
    for name, fn in (
        ("receipt_and_permissions", receipt_and_permissions),
        ("native_reconciliation", reconciliation),
        ("internal_and_cross_company_transfer", internal_transfer),
        ("existing_lims_release_chain", lims_release_and_issue),
        ("registered_external_target", registered_jobworker_transfer),
    ):
        fresh_read()
        try:
            fn()
        except Exception as error:
            frappe.db.rollback()
            result = {"name": name, "status": "FAIL", "error": type(error).__name__,
                      "detail": str(error)[:1600]}
        else:
            result = {"name": name, "status": "PASS"}
        RESULTS.append(result)
        emit("case_result", **result)
    emit("summary", results=RESULTS, real_database="NOT_TOUCHED", production="NOT_DEPLOYED",
         dependency=LIMS_AUTHORITY)
    assert all(row["status"] == "PASS" for row in RESULTS), "Native inventory gate has unmet cases"
    return {"ok": True, "results": RESULTS}
