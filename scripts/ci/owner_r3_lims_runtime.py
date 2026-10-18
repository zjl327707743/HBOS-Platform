"""R3 LIMS proof on a new, disposable GitHub Actions Site.

The unchanged R2 runner executes seven original native Frappe suites (32 tests).
The additional checks below use genuine HTTP sessions and CSRF tokens. Bench
setup creates only labelled master data and an empty stability sample; schedule
dates use the explicit System Manager break-glass API, and all delay signatures
come from apply/approve/reject services. No business method or projection is
mocked, and no client flag is used to grant an authoritative write.

Copy into the disposable hbos_portal package and invoke run from the R3
dispatcher. This runner is not a whitelisted endpoint or a product service.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import re
import time
import traceback
from datetime import date, timedelta
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

import frappe


LIMS = "hb_lims_app.hbos_lims.lims_service."
STABILITY = "hb_lims_app.hbos_lims.stability_service."
ANCHOR = "hb_lims_app.hbos_lims.audit_anchor_service."
TIMEPOINT = "HBOS Stability Timepoint"
DELAY = "HBOS Stability Timepoint Delay"
STAMP = "R3-LIMS-NATIVE"
LEGACY_SHA256 = "67d75217ed3b6756fe39acf345ab8476b3072685dc65c70293820260721054ef"
LEGACY_COUNTS = {
    "test_lims_guards_runtime": 9,
    "test_lims_result_sod_runtime": 4,
    "test_lims_coa_snapshot_runtime": 3,
    "test_lims_break_glass_runtime": 3,
    "test_lims_spec_version_runtime": 3,
    "test_audit_transaction_runtime": 5,
    "test_lims_audit_integrity_runtime": 5,
}
USERS = {
    "manager": ("r3-lims-manager@test.local", "LIMS Manager"),
    "analyst": ("r3-lims-analyst@test.local", "LIMS Analyst"),
    "reviewer": ("r3-lims-reviewer@test.local", "LIMS Reviewer"),
    "qa": ("r3-lims-qa@test.local", "LIMS QA"),
    "system": ("r3-lims-system@test.local", "System Manager"),
}
RESULTS = []
FIXTURE = {}


def emit(case, **data):
    print("[LIMS-R3] " + json.dumps(
        {"case": case, **data}, ensure_ascii=False, default=str, sort_keys=True))


def serial(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def digest(value):
    return hashlib.sha256(json.dumps(
        serial(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


def fresh():
    # HTTP workers commit on different connections. End the bench connection's
    # previous read transaction before inspecting the persisted business facts.
    frappe.db.rollback()
    frappe.set_user("Administrator")


def error_message(payload):
    """Extract native throw messages; never print response tracebacks or headers."""
    result = []
    messages = payload.get("_server_messages") or []
    try:
        messages = json.loads(messages) if isinstance(messages, str) else messages
    except (TypeError, ValueError):
        messages = []
    for message in messages if isinstance(messages, list) else []:
        try:
            message = json.loads(message) if isinstance(message, str) else message
        except (TypeError, ValueError):
            continue
        if isinstance(message, dict) and message.get("message"):
            result.append(str(message["message"]))
    return " | ".join(result)


class Client:
    """Native form RPC plus JSON REST, with a real per-user session cookie jar."""

    def __init__(self):
        origin = str(frappe.conf.hbos_portal_origin)
        self.headers = {
            "Host": urlsplit(origin).netloc, "Origin": origin,
            "X-Requested-With": "XMLHttpRequest",
        }
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.user = "Guest"

    def request(self, path, *, verb="GET", data=None, json_body=False):
        assert path.startswith(("/api/method/", "/api/resource/", "/private/files/"))
        assert not urlsplit(path).netloc, "Only this disposable Site may be requested"
        headers = dict(self.headers)
        encoded = None
        if data is not None:
            if json_body:
                headers["Content-Type"] = "application/json"
                encoded = json.dumps(data, default=str).encode()
            else:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                encoded = urlencode(data).encode()
        request = Request("http://127.0.0.1:8000" + path,
                          data=encoded, headers=headers, method=verb)
        try:
            response = self.opener.open(request, timeout=90)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            try:
                payload = json.loads(raw)
            except (UnicodeDecodeError, ValueError):
                payload = {}
            return response.code, payload, raw

    def rpc(self, method, params=None, *, post=False, json_body=False):
        assert re.fullmatch(r"[A-Za-z0-9_.]+", method)
        path = "/api/method/" + method
        if not post:
            assert not json_body
            if params:
                path += "?" + urlencode(params)
            return self.request(path)
        return self.request(path, verb="POST", data=params or {}, json_body=json_body)

    def ok(self, method, params=None, *, post=False, json_body=False):
        code, payload, _ = self.rpc(method, params, post=post, json_body=json_body)
        assert code == 200 and not payload.get("exc_type"), (
            f"{method}: HTTP {code}, {payload.get('exc_type')}, "
            f"{error_message(payload)[:800]}")
        return payload.get("message")

    def login(self, user, password):
        # Login errors do not include submitted credentials in diagnostics.
        code, _, _ = self.rpc("login", {"usr": user, "pwd": password}, post=True)
        assert code == 200, f"Native synthetic login failed: HTTP {code}"
        security = self.ok("hbos_portal.auth.accounts.get_request_security")
        assert isinstance(security, dict) and security.get("csrf_token"), (
            "Native request-security endpoint did not issue a token")
        self.headers["X-Frappe-CSRF-Token"] = security["csrf_token"]
        self.user = self.ok("frappe.auth.get_logged_user")
        assert self.user == user, "HTTP session identity differs from the requested synthetic user"
        return self

    def get_doc(self, doctype, name):
        doc = self.ok("frappe.client.get", {"doctype": doctype, "name": name})
        assert isinstance(doc, dict) and doc.get("name") == name
        doc["doctype"] = doctype
        return doc

    def insert(self, doc):
        return self.ok("frappe.client.insert", {"doc": json.dumps(doc, default=str)}, post=True)

    def save(self, doc):
        return self.ok("frappe.client.save", {"doc": json.dumps(doc, default=str)}, post=True)

    def rest(self, doctype, name=None, *, verb="GET", data=None):
        path = "/api/resource/" + quote(doctype, safe="")
        if name is not None:
            path += "/" + quote(name, safe="")
        return self.request(path, verb=verb, data=data, json_body=data is not None)


def case(label, action):
    try:
        evidence = action()
        row = {"case": label, "status": "PASS", "evidence": evidence or {}}
    except Exception as error:
        row = {
            "case": label, "status": "FAIL", "error": type(error).__name__,
            "detail": str(error)[:1600],
            "trace": [{"file": frame.filename, "line": frame.lineno, "function": frame.name}
                      for frame in traceback.extract_tb(error.__traceback__)],
        }
    finally:
        fresh()
    RESULTS.append(row)
    emit(label, **{key: value for key, value in row.items() if key != "case"})
    return row["status"] == "PASS"


def not_run(label, reason):
    row = {"case": label, "status": "NOT_RUN", "reason": reason}
    RESULTS.append(row)
    emit(label, status="NOT_RUN", reason=reason)


def denied(label, request, snapshot, *, codes=(417,), exceptions=("ValidationError",),
           contains=()):
    before = snapshot()
    code, payload, _ = request()
    after = snapshot()
    evidence = {
        "label": label, "http": code, "exception": payload.get("exc_type"),
        "before_sha256": digest(before), "after_sha256": digest(after),
        "persisted_business_unchanged": before == after,
    }
    emit("negative_observation", **evidence)
    assert code in codes, f"{label}: expected native denial {codes}, got HTTP {code}"
    assert payload.get("exc_type") in exceptions, (
        f"{label}: unexpected denial class {payload.get('exc_type')}")
    if contains:
        message = error_message(payload)
        assert any(part in message for part in contains), (
            f"{label}: intended guard was not reached; native message={message[:700]}")
    assert before == after, f"{label}: denied request changed persisted business data"
    return evidence


def guard():
    marker = os.environ.get("HBOS_REPORT_SCOPE_TEST_ID", "")
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    assert os.environ.get("HBOS_FRAPPE_SMOKE") == "1"
    assert os.environ.get("OWNER_AUDIT_DOMAIN") == "lims"
    assert re.fullmatch(r"[0-9]+-[0-9]+", marker)
    assert frappe.local.site == "report-scope-" + marker + ".localhost"
    assert str(frappe.conf.hbos_report_scope_ci) == marker
    assert all(os.environ.get(key) == "0" for key in (
        "HBOS_AI_ENABLED", "HBOS_AI_ALLOW_PII", "HBOS_FEISHU_SYNC_ENABLED",
        "HBOS_DELICLOUD_SYNC_ENABLED",
    ))
    assert not frappe.conf.ignore_csrf, "Native CSRF must remain enabled"
    assert urlsplit(str(frappe.conf.hbos_portal_origin)).hostname == frappe.local.site
    assert os.environ.get("OWNER_AUDIT_ADMIN_PASSWORD"), "Fresh Site administrator password is missing"
    legacy = importlib.import_module("hbos_portal._owner_r3_legacy_runtime")
    actual = hashlib.sha256(Path(legacy.__file__).read_bytes()).hexdigest()
    assert actual == LEGACY_SHA256, "The original 32-test runner changed"
    assert not frappe.db.count("Stock Ledger Entry"), "LIMS proof requires an isolated empty ledger"
    emit("isolation", status="PASS", site=frappe.local.site,
         legacy_sha256=actual, original_suites=LEGACY_COUNTS,
         owner_environment="NOT_TOUCHED", genuine_http_csrf=True,
         new_checks_sql_business_fixtures=False,
         legacy_synthetic_audit_preconditions="unchanged original runner")


def original_suites():
    root = Path("/home/frappe/frappe-bench/apps/hb_lims_app/tests")
    hashes = {name: hashlib.sha256((root / (name + ".py")).read_bytes()).hexdigest()
              for name in LEGACY_COUNTS}
    emit("original_suite_sources", sha256=hashes)
    legacy = importlib.import_module("hbos_portal._owner_r3_legacy_runtime")
    result = legacy.run()
    assert isinstance(result, dict) and result.get("ok") is True
    suites = result.get("suites") or []
    assert {row["name"]: row["run"] for row in suites} == LEGACY_COUNTS, (
        "The original seven suites did not execute the expected 32 native tests")
    assert sum(row["run"] for row in suites) == 32
    assert all(not (row["failures"] or row["errors"] or row["skips"]) for row in suites)
    FIXTURE["legacy"] = result
    return {"native_frappe_tests": 32, "http_only": False, "suites": suites, "sha256": hashes}


def native_insert(data):
    """Declared setup only: native validation, no SQL and no service bypass flags."""
    frappe.set_user("Administrator")
    return frappe.get_doc(data).insert()


def setup():
    legacy = importlib.import_module("hbos_portal._owner_r3_legacy_runtime")
    clients = {}
    roles = {}
    sensitive_roles = {value[1] for value in USERS.values()} | {"LIMS QA Manager", "LIMS QP"}
    for key, (user, role) in USERS.items():
        fresh()
        time.sleep(8)  # Keep the native User creation throttle; no config override.
        password = legacy.make_user(user, role)
        clients[key] = Client().login(user, password)
        actual = set(frappe.get_roles(user))
        assert actual & sensitive_roles == {role}, f"Unexpected authority for synthetic {key}"
        roles[key] = sorted(actual)
    clients["admin"] = Client().login("Administrator", os.environ["OWNER_AUDIT_ADMIN_PASSWORD"])
    FIXTURE["clients"] = clients
    FIXTURE["roles"] = roles
    fresh()
    if not frappe.db.exists("Item Group", "All Item Groups"):
        native_insert({"doctype": "Item Group", "item_group_name": "All Item Groups",
                       "is_group": 1, "parent_item_group": ""})
    group = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ""}, "name")
    assert group, "Native ERPNext root Item Group is missing"
    if not frappe.db.exists("UOM", "g"):
        native_insert({"doctype": "UOM", "uom_name": "g", "enabled": 1})
    item = native_insert({
        "doctype": "Item", "item_code": STAMP + "-ITEM", "item_name": STAMP + " material",
        "item_group": group, "stock_uom": "g", "is_stock_item": 0,
        "is_purchase_item": 0, "is_sales_item": 0,
    })
    test_item = native_insert({
        "doctype": "HBOS Test Item", "item_code": STAMP + "-TEST",
        "item_name": STAMP + " assay", "item_category": "理化检验", "significant_digits": 2,
    })
    sample_type = native_insert({
        "doctype": "HBOS Sample Type", "sample_type_code": STAMP + "-TYPE",
        "sample_type_name": STAMP + " synthetic sample",
    })
    lab = native_insert({
        "doctype": "HBOS Lab Department", "department_code": STAMP + "-LAB",
        "department_name": STAMP + " laboratory",
    })
    product = native_insert({
        "doctype": "HBOS Stability Product", "item_ref": item.name,
        "product_code": item.name, "product_name": item.item_name,
        "category": "年度持续稳定性考察类", "default_uom": "g", "vd_months": 12,
        "qty_factor": 1, "is_outsource": 0, "is_active": 1,
    })
    sample = native_insert({
        "doctype": "HBOS Stability Sample", "stability_product": product.name,
        "sample_name": STAMP + " delay fixture", "batch_no": STAMP + "-DELAY-BATCH",
        "in_date": frappe.utils.today(), "init_qty": 0,
    })
    frappe.db.commit()
    FIXTURE.update(item=item.name, item_name=item.item_name, test_item=test_item.name,
                   sample_type=sample_type.name, lab=lab.name,
                   stability_sample=sample.name, stability_product=product.name)
    system = USERS["system"][0]
    permissions = {action: bool(frappe.has_permission(TIMEPOINT, ptype=action, user=system))
                   for action in ("read", "create", "write", "delete")}
    assert all(permissions.values()), "System Manager must have real native parent CRUD permission"
    assert "System Manager" not in frappe.get_roles(USERS["manager"][0])
    return {
        "users": {key: user for key, (user, _) in USERS.items()}, "roles": roles,
        "pure_system_manager_timepoint_permissions": permissions,
        "master_item": item.name, "stability_sample": sample.name,
        "fixture_scope": "empty synthetic sample for delay guard; not a full stability registration acceptance",
    }


def portal_access():
    admin = FIXTURE["clients"]["admin"]
    bootstrap = admin.ok("hbos_portal.api.bootstrap.get_bootstrap")
    assert bootstrap.get("ok") is True and isinstance(bootstrap.get("data"), dict), (
        "Administrator bootstrap did not return a successful Portal envelope")
    boot = bootstrap["data"]
    assert boot["user"]["id"] == "Administrator"
    assert any(entry["manifest"]["id"] == "lims" and entry["access"]["can_enter"]
               for entry in boot["apps"]), "Administrator lost the LIMS read entry"
    required_read = {"lims.read", "lims.results.read", "lims.ledger.read",
                     "lims.retention.read", "lims.audit.read"}
    write_caps = {"lims.results.submit", "lims.results.review", "lims.results.approve"}
    observed = {}
    for key in ("admin", "system", "manager"):
        envelope = FIXTURE["clients"][key].ok("hbos_portal.api.apps.get_app", {"app_id": "lims"})
        assert envelope.get("ok") is True and isinstance(envelope.get("data"), dict), (
            f"{key}: LIMS app access did not return a successful Portal envelope")
        data = envelope["data"]
        assert data["manifest"]["id"] == "lims" and data["access"]["can_enter"] is True
        # Manifest capabilities describe the provider, not this user's authority.
        # Only access.capabilities is the actual result of the provider guard.
        capabilities = set(data["access"].get("capabilities") or [])
        assert required_read <= capabilities, f"{key}: expected LIMS read authority disappeared"
        if key == "manager":
            assert write_caps <= capabilities, "Named LIMS Manager lost its legitimate write capabilities"
        else:
            assert not (capabilities & write_caps), f"{key}: Portal still exposes ordinary quality write authority"
        observed[key] = sorted(capabilities)
    return {"native_http": 200, "administrator_bootstrap_lims_entry": True,
            "user_access_capabilities": observed, "manifest_capabilities_used_as_authority": False}


def fields():
    return [field.fieldname for field in frappe.get_meta(DELAY).fields
            if field.fieldname and field.fieldtype not in ("Section Break", "Column Break", "Tab Break")]


def history(doc):
    columns = ["name", "idx", "parent", "parenttype", "parentfield", *fields()]
    return [serial({field: row.get(field) for field in columns}) for row in doc.get("delays", [])]


def delay_snapshot():
    fresh()
    names = frappe.get_all(TIMEPOINT, filters={"stability_sample": FIXTURE["stability_sample"]},
                           pluck="name", order_by="name")
    docs = [serial(frappe.get_doc(TIMEPOINT, name).as_dict()) for name in names]
    children = frappe.get_all(
        DELAY, filters={"parent": ["in", names], "parenttype": TIMEPOINT,
                        "parentfield": "delays"}, fields=["*"], order_by="parent, idx, name") if names else []
    return {"parents": docs, "children": serial(children)}


def fresh_timepoint():
    fresh()
    return serial(frappe.get_doc(TIMEPOINT, FIXTURE["timepoint"]).as_dict())


def audit_rows(reason=None):
    fresh()
    filters = {"doctype_target": TIMEPOINT, "doc_name": FIXTURE["timepoint"]}
    if reason:
        filters["reason"] = reason
    return serial(frappe.get_all(
        "HBOS Audit Log", filters=filters,
        fields=["name", "log_type", "user", "field_changed", "old_value", "new_value", "reason"],
        order_by="creation, name"))


def delay_service_history():
    clients = FIXTURE["clients"]
    system, manager, analyst, reviewer = [clients[key] for key in ("system", "manager", "analyst", "reviewer")]
    doc = system.insert({
        "doctype": TIMEPOINT, "stability_sample": FIXTURE["stability_sample"],
        "condition_type": "长期", "time_point_value": 1, "time_point_unit": "月",
        "extra_reason": STAMP + " initial fixture",
    })
    assert doc.get("name") and not doc.get("delays"), "Native empty-history parent insert failed"
    FIXTURE["timepoint"] = doc["name"]
    today = date.fromisoformat(frappe.utils.today())
    FIXTURE["planned"] = today.isoformat()
    FIXTURE["test_planned"] = (today + timedelta(days=7)).isoformat()
    requested = (today + timedelta(days=1)).isoformat()
    approved = (today + timedelta(days=2)).isoformat()
    reason = STAMP + " explicit technical setup of initial schedule; no approval history"
    dates = {"plan_sample_date": FIXTURE["planned"], "plan_test_date": FIXTURE["test_planned"]}
    changed = system.ok(LIMS + "break_glass_update", {
        "doctype": TIMEPOINT, "doc_name": doc["name"], "values": json.dumps(dates),
        "reason": reason,
    }, post=True)
    assert changed == {"name": doc["name"], "changed": sorted(dates)}, (
        "Explicit System Manager break-glass did not report exactly the planned fields")
    stored = fresh_timepoint()
    assert all(stored.get(key) == value for key, value in dates.items())
    rows = audit_rows(reason)
    assert len(rows) == 2 and {row["field_changed"] for row in rows} == set(dates)
    assert all(row["user"] == USERS["system"][0] and row["log_type"] == "应急处置" for row in rows)
    FIXTURE["technical_audit"] = rows[0]["name"]
    emit("system_manager_explicit_break_glass", status="PASS", timepoint=doc["name"],
         changed=dates, audits=rows, delay_fields_added_to_allowlist=False)

    denied("delay_apply_outside_policy", lambda: manager.rpc(STABILITY + "apply_delay", {
        "timepoint_name": doc["name"], "delay_type": "取样延期",
        "requested_due_date": (today + timedelta(days=20)).isoformat(),
        "reason": STAMP + " must reject beyond policy",
    }, post=True), delay_snapshot, contains=("政策上限",))
    response = manager.ok(STABILITY + "apply_delay", {
        "timepoint_name": doc["name"], "delay_type": "取样延期",
        "requested_due_date": requested, "reason": STAMP + " sampling application",
    }, post=True)
    assert response == {"name": doc["name"], "delay_type": "取样延期"}
    first = history(fresh_timepoint())
    assert len(first) == 1 and first[0]["status"] == "待批准"
    assert first[0]["apply_by"] == USERS["manager"][0] and first[0]["requested_due_date"] == requested
    for value in (0, False):
        def pending_empty_field_write(value=value):
            pending = system.get_doc(TIMEPOINT, doc["name"])
            assert pending["delays"][0]["status"] == "待批准"
            assert pending["delays"][0].get("reject_reason") in (None, "")
            pending["delays"][0]["reject_reason"] = value
            return system.rpc("frappe.client.save", {"doc": json.dumps(pending)}, post=True)

        denied("parent_pending_reject_reason_" + ("false" if value is False else "numeric_zero"),
               pending_empty_field_write, delay_snapshot,
               contains=("禁止替换、重排或修改历史行",))
    sod_before = [row for row in audit_rows() if row["log_type"] == "SoD 拦截"]
    denied("delay_applicant_cannot_approve_own_request", lambda: manager.rpc(STABILITY + "approve_delay", {
        "timepoint_name": doc["name"], "delay_type": "取样延期", "approved_due_date": approved,
    }, post=True), delay_snapshot, contains=("延期批准人不得为申请人",))
    sod_after = [row for row in audit_rows() if row["log_type"] == "SoD 拦截"]
    assert len(sod_after) == len(sod_before) + 1 and sod_after[-1]["user"] == USERS["manager"][0], (
        "Native delay SoD denial did not retain the actual actor's audit")
    denied("delay_approval_cannot_precede_request", lambda: reviewer.rpc(STABILITY + "approve_delay", {
        "timepoint_name": doc["name"], "delay_type": "取样延期",
        "approved_due_date": today.isoformat(),
    }, post=True), delay_snapshot, contains=("不得早于申请",))
    reviewer.ok(STABILITY + "approve_delay", {
        "timepoint_name": doc["name"], "delay_type": "取样延期", "approved_due_date": approved,
    }, post=True)
    after_approve = history(fresh_timepoint())
    assert len(after_approve) == 1 and after_approve[0]["name"] == first[0]["name"]
    assert after_approve[0]["status"] == "已批准" and after_approve[0]["approved_due_date"] == approved
    assert after_approve[0]["apply_by"] == USERS["manager"][0]
    assert after_approve[0]["approver_by"] == USERS["reviewer"][0] and after_approve[0]["approve_at"]

    analyst.ok(STABILITY + "apply_delay", {
        "timepoint_name": doc["name"], "delay_type": "检测延期",
        "requested_due_date": (today + timedelta(days=8)).isoformat(),
        "reason": STAMP + " testing application",
    }, post=True)
    reject_reason = STAMP + " independent reviewer rejection"
    reviewer.ok(STABILITY + "reject_delay", {
        "timepoint_name": doc["name"], "delay_type": "检测延期", "reason": reject_reason,
    }, post=True)
    final = history(fresh_timepoint())
    assert len(final) == 2 and final[0] == after_approve[0], "Second service cycle changed signed first history"
    assert final[1]["status"] == "已驳回" and final[1]["reject_reason"] == reject_reason
    assert final[1]["apply_by"] == USERS["analyst"][0]
    assert final[1]["approver_by"] == USERS["reviewer"][0] and final[1]["approve_at"]
    assert [row["idx"] for row in final] == [1, 2] and final[0]["name"] != final[1]["name"]
    FIXTURE["delay_baseline"] = delay_snapshot()
    return {"timepoint": doc["name"], "history": final,
            "native_parent_child_db_insert_and_update": "successful service saves",
            "applicant_and_approver_different": True, "normal_roles_unchanged": True}


def parent_unrelated_edit(label):
    system = FIXTURE["clients"]["system"]
    before = history(fresh_timepoint())
    doc = system.get_doc(TIMEPOINT, FIXTURE["timepoint"])
    doc["extra_reason"] = STAMP + " ordinary native parent edit " + label
    result = system.save(doc)
    stored = fresh_timepoint()
    assert result.get("name") == stored["name"] and stored["extra_reason"] == doc["extra_reason"]
    assert history(stored) == before, "Ordinary parent edit changed approval history"
    FIXTURE["delay_baseline"] = delay_snapshot()
    return {"timepoint": stored["name"], "native_http": 200,
            "history": before, "unrelated_field": "extra_reason"}


def forged_delay():
    return {
        "doctype": DELAY, "delay_type": "取样延期",
        "planned_due_date": FIXTURE["planned"], "policy_latest_due_date": FIXTURE["planned"],
        "requested_due_date": FIXTURE["planned"], "reason": STAMP + " forged history",
        "apply_by": USERS["analyst"][0], "apply_date": FIXTURE["planned"],
        "status": "已批准", "approver_by": USERS["qa"][0],
        "approve_at": FIXTURE["planned"] + " 12:00:00",
        "approved_due_date": FIXTURE["planned"],
    }


def parent_request(kind, client):
    doc = client.get_doc(TIMEPOINT, FIXTURE["timepoint"])
    rows = doc["delays"]
    assert len(rows) == 2, "Native negative checks require two different authoritative history rows"
    if kind == "content":
        rows[0]["reason"] = STAMP + " edited signed reason"
    elif kind == "append":
        rows.append(forged_delay())
    elif kind == "delete":
        rows.pop()
    elif kind == "order":
        rows.reverse()
    elif kind == "idx_only":
        rows[0]["idx"], rows[1]["idx"] = rows[1]["idx"], rows[0]["idx"]
    elif kind == "identity":
        rows[0]["name"] = "r3-lims-forged-delay-identity"
    elif kind == "swap_contents":
        first, second = copy.deepcopy(rows[0]), copy.deepcopy(rows[1])
        for field in fields():
            rows[0][field], rows[1][field] = second.get(field), first.get(field)
    elif kind == "fake_flags":
        doc["flags"] = {"allow_system_fields": True, "ignore_permissions": True}
        rows[0]["reason"] = STAMP + " forged parent flags"
    else:
        raise AssertionError("Unknown parent mutation " + kind)
    return client.rpc("frappe.client.save", {"doc": json.dumps(doc)}, post=True)


def new_parent():
    return {
        "doctype": TIMEPOINT, "stability_sample": FIXTURE["stability_sample"],
        "condition_type": "长期", "time_point_value": 2, "time_point_unit": "月",
        "extra_reason": STAMP + " first-insert forgery", "delays": [forged_delay()],
    }


def new_child():
    return {**forged_delay(), "parent": FIXTURE["timepoint"],
            "parenttype": TIMEPOINT, "parentfield": "delays"}


def independent_save(fake_flags=False):
    doc = copy.deepcopy(fresh_timepoint()["delays"][0])
    doc["doctype"] = DELAY
    doc["reason"] = STAMP + " independent child write"
    if fake_flags:
        doc["flags"] = {"allow_system_fields": True, "ignore_permissions": True}
    return FIXTURE["clients"]["system"].rpc(
        "frappe.client.save", {"doc": json.dumps(doc)}, post=True)


def run_delay_native_negatives():
    system = FIXTURE["clients"]["system"]
    admin = FIXTURE["clients"]["admin"]
    row_name = history(fresh_timepoint())[0]["name"]
    cases = []
    for kind in ("content", "append", "delete", "order", "idx_only", "identity", "swap_contents", "fake_flags"):
        cases.append(("parent_save_" + kind, lambda kind=kind: parent_request(kind, system),
                      (417,), ("ValidationError",), ("delays", "延期记录")))
    cases.extend([
        ("administrator_parent_history_edit", lambda: parent_request("content", admin),
         (417,), ("ValidationError",), ("delays", "延期记录")),
        ("parent_first_insert_rpc", lambda: system.rpc("frappe.client.insert", {
            "doc": json.dumps(new_parent())}, post=True),
         (417,), ("ValidationError",), ("禁止新建时直接填写",)),
        ("parent_first_insert_rest", lambda: system.rest(TIMEPOINT, verb="POST", data=new_parent()),
         (417,), ("ValidationError",), ("禁止新建时直接填写",)),
        ("child_client_set_value_via_parent", lambda: system.rpc("frappe.client.set_value", {
            "doctype": DELAY, "name": row_name, "fieldname": "reason",
            "value": STAMP + " direct set_value"}, post=True),
         (417,), ("ValidationError",), ("delays", "延期记录")),
        ("child_client_insert_via_parent", lambda: system.rpc("frappe.client.insert", {
            "doc": json.dumps(new_child())}, post=True),
         (417,), ("ValidationError",), ("delays", "延期记录")),
        ("child_client_delete_via_parent", lambda: system.rpc("frappe.client.delete", {
            "doctype": DELAY, "name": row_name}, post=True),
         (417,), ("ValidationError",), ("delays", "延期记录")),
        ("child_independent_client_save", lambda: independent_save(),
         (403,), ("PermissionError",), ("禁止独立新增或修改",)),
        ("child_independent_client_save_fake_flags", lambda: independent_save(True),
         (403,), ("PermissionError",), ("禁止独立新增或修改",)),
        ("child_independent_rest_post", lambda: system.rest(DELAY, verb="POST", data=new_child()),
         (403,), ("PermissionError",), ("禁止独立新增或修改",)),
        ("child_independent_rest_put", lambda: system.rest(DELAY, row_name, verb="PUT",
                                                        data={"reason": STAMP + " REST child update"}),
         (403,), ("PermissionError",), ("禁止独立新增或修改",)),
        ("child_independent_rest_delete", lambda: system.rest(DELAY, row_name, verb="DELETE"),
         (403,), ("PermissionError",), ("延期审批历史禁止直接删除",)),
        ("break_glass_cannot_include_delay_history", lambda: system.rpc(LIMS + "break_glass_update", {
            "doctype": TIMEPOINT, "doc_name": FIXTURE["timepoint"],
            "values": json.dumps({"delays": []}), "reason": STAMP + " forbidden history rewrite",
        }, post=True), (417,), ("ValidationError",), ("未登记为系统字段",)),
        ("administrator_ordinary_delay_apply", lambda: admin.rpc(STABILITY + "apply_delay", {
            "timepoint_name": FIXTURE["timepoint"], "delay_type": "取样延期",
            "requested_due_date": FIXTURE["planned"], "reason": STAMP + " forbidden Admin application",
        }, post=True), (417,), ("ValidationError",), ("权限",)),
    ])
    for label, request, codes, exceptions, contains in cases:
        if delay_snapshot() != FIXTURE["delay_baseline"]:
            not_run(label, "A prior failing request changed this fixture; no repair or reseeding was performed")
            continue
        case(label, lambda label=label, request=request, codes=codes,
             exceptions=exceptions, contains=contains: denied(
                 label, request, delay_snapshot, codes=codes,
                 exceptions=exceptions, contains=contains))


def quality_snapshot():
    fresh()
    state = {}
    for key, doctype in (("quality_sample", "HBOS Sample"), ("task", "HBOS Sample Task"),
                         ("result", "HBOS Test Result"), ("coa", "HBOS COA")):
        if FIXTURE.get(key):
            state[key] = serial(frappe.get_doc(doctype, FIXTURE[key]).as_dict())
    if FIXTURE.get("coa"):
        state["files"] = serial(frappe.get_all(
            "File", filters={"attached_to_doctype": "HBOS COA", "attached_to_name": FIXTURE["coa"]},
            fields=["*"], order_by="name"))
    return state


def quality_chain():
    clients = FIXTURE["clients"]
    manager, analyst, reviewer, qa, admin = [clients[key]
        for key in ("manager", "analyst", "reviewer", "qa", "admin")]
    spec = manager.ok(LIMS + "create_specification", {
        "spec_code": STAMP + "-SPEC", "spec_name": STAMP + " native standard",
        "material_code": FIXTURE["item"], "material_name": FIXTURE["item_name"],
        "standard_source": "企业内控", "version": "1.0", "effective_date": frappe.utils.today(),
        "items": [{"item": FIXTURE["test_item"], "item_name": STAMP + " assay",
                   "limits_type": "上限", "upper_limit": 100, "unit": "g",
                   "significant_digits": 2}],
    }, post=True, json_body=True)
    assert isinstance(spec, str) and spec, "Specification creation did not return its native name"
    manager.ok(LIMS + "activate_specification", {"spec_name": spec}, post=True)
    sample = manager.ok(LIMS + "register_sample", {
        "sample_type": FIXTURE["sample_type"], "item_ref": FIXTURE["item"],
        "material_code": FIXTURE["item"], "material_name": FIXTURE["item_name"],
        "batch_no": STAMP + "-QUALITY-BATCH", "sample_source": "生产取样",
        "specification": spec, "priority": "常规",
    }, post=True)
    FIXTURE["quality_sample"] = sample
    tasks = manager.ok(LIMS + "generate_tasks", {"sample_name": sample, "lab_department": FIXTURE["lab"]},
                       post=True)
    assert isinstance(tasks, list) and len(tasks) == 1, "Expected one real quality task"
    task = FIXTURE["task"] = tasks[0]
    manager.ok(LIMS + "assign_task", {"task_name": task, "assignee": USERS["analyst"][0]}, post=True)
    started = analyst.ok(LIMS + "start_task", {"task_name": task}, post=True)
    assert started.get("task") == task and started.get("result"), "Native task did not create a result"
    result = FIXTURE["result"] = started["result"]
    analyst.ok(LIMS + "submit_result", {"result_name": result, "raw_value": 50, "result_value": 50},
               post=True)
    reviewer.ok(LIMS + "review_result", {"result_name": result}, post=True)
    before = quality_snapshot()
    reviewed = before["result"]
    assert reviewed["result_status"] == "已复核" and not reviewed["is_oos_candidate"]
    assert reviewed["analyst"] == USERS["analyst"][0] and reviewed["reviewer"] == USERS["reviewer"][0]
    assert "Administrator" not in {reviewed["analyst"], reviewed["reviewer"]}, (
        "Administrator denial must test the principal boundary, not a same-person SoD denial")
    denied("administrator_third_person_approve_result", lambda: admin.rpc(
        LIMS + "approve_result", {"result_name": result}, post=True),
        quality_snapshot, contains=("权限",))
    # A pure System Manager has the same technical boundary, independently of the
    # special literal Administrator identity and with no business role added.
    denied("pure_system_manager_approve_result", lambda: clients["system"].rpc(
        LIMS + "approve_result", {"result_name": result}, post=True),
        quality_snapshot, contains=("权限",))
    manager.ok(LIMS + "approve_result", {"result_name": result}, post=True)
    after = quality_snapshot()
    approved = after["result"]
    assert approved["result_status"] == "已批准" and approved["approver"] == USERS["manager"][0]
    assert approved["approved_signature"] and approved["approved_at"], "Named approver signature is missing"
    assert len({approved["analyst"], approved["reviewer"], approved["approver"]}) == 3
    assert after["task"]["status"] == "已批准" and after["quality_sample"]["status"] == "检验完成"
    emit("named_result_chain", status="PASS", result=result, sample=sample, task=task,
         analyst=approved["analyst"], reviewer=approved["reviewer"], approver=approved["approver"],
         verdict=approved["verdict"], approved_at=approved["approved_at"])

    coa = FIXTURE["coa"] = manager.ok(LIMS + "create_coa", {"sample_name": sample}, post=True)
    reviewer.ok(LIMS + "review_coa", {"coa_name": coa}, post=True)
    before_publish = quality_snapshot()
    reviewed_coa = before_publish["coa"]
    assert reviewed_coa["report_status"] == "已审核" and not reviewed_coa.get("pdf_attachment")
    assert reviewed_coa["qa_reviewer"] == USERS["reviewer"][0] != "Administrator"
    assert not before_publish["files"], "Fresh reviewed COA unexpectedly already has archived files"
    denied("administrator_third_person_publish_coa", lambda: admin.rpc(
        LIMS + "publish_coa", {"coa_name": coa}, post=True),
        quality_snapshot, contains=("权限",))
    denied("pure_system_manager_publish_coa", lambda: clients["system"].rpc(
        LIMS + "publish_coa", {"coa_name": coa}, post=True),
        quality_snapshot, contains=("权限",))
    published = qa.ok(LIMS + "publish_coa", {"coa_name": coa}, post=True)
    assert isinstance(published, dict) and published.get("coa") == coa
    url = published.get("pdf")
    assert isinstance(url, str) and url.startswith("/private/files/"), "Published COA must return a private PDF URL"
    state = quality_snapshot()
    saved = state["coa"]
    assert saved["report_status"] == "已发布" and saved["published_by"] == USERS["qa"][0]
    assert saved["qa_reviewer"] == USERS["reviewer"][0] and saved["published_at"]
    assert saved["pdf_attachment"] == url and saved["content_fingerprint"]
    fresh()
    # Native Attach handling may create additional File rows for the same URL.
    # Identify this COA's archive by all three properties, never by URL alone.
    files = frappe.get_all("File", filters={"file_url": url,
        "attached_to_doctype": "HBOS COA", "attached_to_name": coa},
        fields=["name", "file_url", "is_private", "attached_to_doctype", "attached_to_name"], order_by="name")
    assert files and all(row.is_private and row.attached_to_name == coa for row in files)
    file_doc = frappe.get_doc("File", files[0].name)
    blob = file_doc.get_content()
    assert isinstance(blob, bytes) and blob.startswith(b"%PDF-") and len(blob) > 1000, (
        "COA archive is not a real generated PDF")
    from pypdf import PdfReader
    pages = PdfReader(io.BytesIO(blob)).pages
    text = "\n".join(page.extract_text() or "" for page in pages)
    assert len(pages) >= 1 and coa in text and sample in text, (
        "Native PDF did not contain the current synthetic COA and sample identifiers")
    # The product's formal publication-order repair must still be effective.
    assert str(saved["published_at"])[:10] in text, "Published date is missing from the archived PDF"
    native_path = quote(url, safe="/%")
    status, _, downloaded = qa.request(native_path)
    assert status == 200 and downloaded == blob, "QA's native private download differs from the archived PDF"
    guest_status, _, guest_body = Client().request(native_path)
    assert guest_status in (403, 404) and not guest_body.startswith(b"%PDF-"), (
        "Guest downloaded the private COA PDF")
    verified = admin.ok(LIMS + "verify_coa_content", {"coa_name": coa})
    assert verified.get("ok") is True and verified.get("stored") == saved["content_fingerprint"]
    release = reviewer.ok(LIMS + "release_sample", {"sample_name": sample}, post=True)
    released = quality_snapshot()
    assert release.get("sample") == sample and release.get("coa") == coa
    assert released["quality_sample"]["status"] == "已放行"
    emit("named_coa_publish_and_release", status="PASS", sample=sample, coa=coa,
         reviewer=saved["qa_reviewer"], publisher=saved["published_by"],
         private_files=serial(files), bytes=len(blob), pages=len(pages),
         pdf_sha256=hashlib.sha256(blob).hexdigest(), native_qa_download=200,
         guest_download=guest_status, published_at=saved["published_at"],
         source_batch_projection="not exercised by this unbatched fixture; retained in inventory transaction domain")
    return {"specification": spec, "sample": sample, "result": result, "coa": coa,
            "named_roles": [USERS[key][1] for key in ("manager", "analyst", "reviewer", "qa")],
            "third_person_administrator_approve_and_publish_denied": True,
            "pdf_sha256": hashlib.sha256(blob).hexdigest(), "pdf_bytes": len(blob)}


def administrator_read_and_integrity():
    admin = FIXTURE["clients"]["admin"]
    assert admin.ok("frappe.auth.get_logged_user") == "Administrator"
    before = quality_snapshot()
    sample = admin.get_doc("HBOS Sample", FIXTURE["quality_sample"])
    coa = admin.get_doc("HBOS COA", FIXTURE["coa"])
    assert sample["status"] == "已放行" and coa["report_status"] == "已发布"
    ledger = admin.ok(LIMS + "get_result_ledger", {"material": FIXTURE["item_name"]})
    assert any(row.get("name") == FIXTURE["result"] for row in ledger.get("results", [])), (
        "Administrator's allowed read did not include the synthetic result")
    assert admin.ok(LIMS + "verify_coa_content", {"coa_name": FIXTURE["coa"]}).get("ok") is True
    integrity = admin.ok(LIMS + "verify_audit_integrity", {"name": FIXTURE["technical_audit"]})
    assert integrity.get("checked") == 1 and not integrity.get("mismatched"), (
        "Explicit break-glass audit did not verify as an intact new audit row")
    anchor = admin.ok(ANCHOR + "verify_audit_anchor")
    assert isinstance(anchor, dict) and isinstance(anchor.get("ok"), bool)
    # The legacy suite intentionally tests missing/tampered synthetic anchors.
    # HTTP access is the assertion here; an unanchored Site is not misreported as
    # having a valid external integrity anchor.
    detail = admin.ok(STABILITY + "get_stability_timepoint_detail",
                      {"timepoint_name": FIXTURE["timepoint"]})
    assert detail.get("name") == FIXTURE["timepoint"]
    assert before == quality_snapshot(), "Administrator read/verify endpoints changed quality business data"
    return {"native_login_and_reads": 200, "coa_content_ok": True,
            "technical_audit": integrity, "anchor_authorization_http": 200,
            "anchor_integrity_result": anchor,
            "stability_timepoint_read": detail["name"]}


def sessions_and_roles_unchanged():
    for key, (user, _) in USERS.items():
        assert FIXTURE["clients"][key].ok("frappe.auth.get_logged_user") == user
        fresh()
        assert sorted(frappe.get_roles(user)) == FIXTURE["roles"][key], (
            "Native proof changed a synthetic user's authority")
    assert not frappe.db.count("Stock Ledger Entry"), "LIMS proof unexpectedly posted stock"
    return {"native_sessions": len(USERS), "roles_unchanged": True, "stock_ledger_rows": 0}


def run():
    RESULTS.clear()
    FIXTURE.clear()
    guard()
    case("original_native_lims_32", original_suites)
    ready = case("synthetic_users_and_master_data", setup)
    if ready:
        case("portal_administrator_and_named_role_access", portal_access)
        delay_ready = case("delay_real_service_history_and_sod", delay_service_history)
        if delay_ready:
            case("parent_unrelated_edit_with_signed_history", lambda: parent_unrelated_edit("before negatives"))
            run_delay_native_negatives()
            if delay_snapshot() == FIXTURE["delay_baseline"]:
                case("parent_unrelated_edit_after_denials", lambda: parent_unrelated_edit("after negatives"))
            else:
                not_run("parent_unrelated_edit_after_denials", "A failing negative changed persisted history")
        else:
            not_run("delay_parent_and_child_native_matrix", "Authoritative two-row service history was not established")
        quality_ready = case("quality_named_roles_and_administrator_boundary", quality_chain)
        if quality_ready and delay_ready:
            case("administrator_read_and_integrity", administrator_read_and_integrity)
        else:
            not_run("administrator_read_and_integrity", "Its quality or technical-audit fixture is incomplete")
        case("native_sessions_and_roles_unchanged", sessions_and_roles_unchanged)
    else:
        not_run("new_http_business_checks", "Native synthetic users or master data setup failed")
    result = {
        "ok": bool(RESULTS) and all(row["status"] == "PASS" for row in RESULTS),
        "legacy": FIXTURE.get("legacy"), "checks": RESULTS,
        "pass": sum(row["status"] == "PASS" for row in RESULTS),
        "fail": sum(row["status"] == "FAIL" for row in RESULTS),
        "not_run": sum(row["status"] == "NOT_RUN" for row in RESULTS),
        "native_http_not_mocked": True, "owner_environment": "NOT_TOUCHED",
    }
    emit("summary", **result)
    return result
