"""Native database + HTTP checks for PR49; disposable GitHub CI only.

No Frappe mocks, no modified permission algorithms, no real employee import.
This proves the temporary all-employee-report gate, not IAM V1 row filtering.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

import frappe

REPORTS = (
    ("monthly", "月度考勤汇总", "get_monthly_summary"),
    ("checkins", "打卡流水", "get_checkin_flow"),
    ("results", "考勤结果", "get_attendance_results"),
    ("staging", "HBOS 月度汇总暂存（对账）", "get_monthly_staging"),
)


class Client:
    """Real loopback HTTP; never print cookies, passwords or response bodies."""
    def __init__(self, origin):
        self.headers = {"Host": origin.split("//", 1)[1], "Origin": origin,
                        "X-Requested-With": "XMLHttpRequest"}
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(self, method, params=None, *, post=False):
        url = "http://127.0.0.1:8000/api/method/" + method
        encoded = urlencode(params or {}).encode()
        request = Request(url if post or not encoded else url + "?" + encoded.decode(),
                          data=encoded if post else None, headers=self.headers)
        try:
            response = self.opener.open(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            text = response.read().decode("utf-8")
            try:
                payload = json.loads(text)
            except ValueError:
                payload = {}
            return response.code, payload, text

    def login(self, user, password):
        status, _, _ = self.call("login", {"usr": user, "pwd": password}, post=True)
        if status != 200:
            raise AssertionError(f"Synthetic standard login failed: HTTP {status}")
        status, payload, _ = self.call("hbos_portal.auth.accounts.get_request_security")
        token = payload.get("message", {}).get("csrf_token")
        if status != 200 or not token:
            raise AssertionError("Synthetic session security token was not issued")
        self.headers["X-Frappe-CSRF-Token"] = token
        return self


def _guard():
    test_id = os.environ.get("HBOS_REPORT_SCOPE_TEST_ID", "")
    site = "report-scope-" + test_id + ".localhost"
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or not re.fullmatch(r"[0-9]+-[0-9]+", test_id)
            or frappe.local.site != site
            or str(frappe.conf.get("hbos_report_scope_ci")) != test_id):
        raise RuntimeError("Report scope runtime checks require the exact disposable CI Site")
    for key in ("HBOS_FEISHU_SYNC_ENABLED", "HBOS_DELICLOUD_SYNC_ENABLED", "HBOS_AI_ENABLED",
                "HBOS_AI_ALLOW_PII"):
        if os.environ.get(key) != "0":
            raise RuntimeError("Report scope runtime requires all outbound integrations disabled")
    return test_id


def _sql_fixture(doctype, values):
    # This helper is used ONLY with constant schema fields and synthetic records.
    now = frappe.utils.now_datetime()
    values = {**values, "creation": now, "modified": now, "owner": "Administrator",
              "modified_by": "Administrator", "docstatus": values.get("docstatus", 0)}
    columns = ",".join("`" + key + "`" for key in values)
    frappe.db.sql(f"INSERT INTO `tab{doctype}` ({columns}) VALUES ({','.join(['%s'] * len(values))})",
                  tuple(values.values()))


def _require_ok(response, label):
    status, payload, _ = response
    if status != 200 or "exc_type" in payload:
        raise AssertionError(f"{label}: HTTP {status}, {payload.get('exc_type', 'unknown')}")
    return payload.get("message")


def _require_denied(response, secret_marker, label):
    status, payload, text = response
    if status != 403 or payload.get("exc_type") != "PermissionError":
        raise AssertionError(f"{label}: expected native PermissionError/403; got HTTP {status}")
    if secret_marker in text:
        raise AssertionError(f"{label}: denied response contains another department's marker")
    # Distinguish a data-scope refusal from an unrelated missing-role failure.
    details = str(payload.get("exception", ""))
    try:
        for message in json.loads(payload.get("_server_messages", "[]")):
            details += str(json.loads(message).get("message", ""))
    except (ValueError, TypeError, AttributeError):
        pass
    if "部分员工" not in details:
        raise AssertionError(f"{label}: refusal did not originate at the report scope gate")


def run():
    """Called by bench execute, never whitelisted; all fixtures are destroyed."""
    test_id = _guard()
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    prefix = "HBOS-RS-" + test_id
    users = [f"hbos-rs-{test_id}-{kind}@example.invalid" for kind in ("all", "a")]
    passwords = {user: secrets.token_urlsafe(32) for user in users}
    employees = [prefix + "-EMP-A", prefix + "-EMP-B"]
    row_ids = [prefix + "-ATT-A", prefix + "-ATT-B"]
    checkin_ids = [prefix + "-LOG-A", prefix + "-LOG-B"]
    departments, created_users, grants = [], [], []
    tables = ("User", "Employee", "Department", "User Permission", "Attendance", "Employee Checkin")
    before = {kind: frappe.db.count(kind) for kind in tables}
    # Refusal happens before entering cleanup: never delete a pre-existing ID.
    for kind, names in (("User", users), ("Employee", employees),
                        ("Attendance", row_ids), ("Employee Checkin", checkin_ids)):
        if any(frappe.db.exists(kind, name) for name in names):
            raise RuntimeError("Refusing to reuse existing synthetic fixture IDs")
    for suffix in ("A", "B"):
        if frappe.db.exists("Department", {"department_name": prefix + "-" + suffix}):
            raise RuntimeError("Refusing to reuse a pre-existing synthetic department")
    if before["Employee"]:
        raise RuntimeError("Report scope CI must start on an empty employee dataset")
    checks = []
    from hb_attendance_app.hbos_attendance import report_data
    from hb_attendance_app.hbos_attendance.report_scope import require_unrestricted_employee_read

    def grant(user, department):
        frappe.set_user("Administrator")
        permission = frappe.get_doc({"doctype": "User Permission", "user": user,
                                   "allow": "Department", "for_value": department,
                                   "apply_to_all_doctypes": 1, "hide_descendants": 1}).insert()
        grants.append(permission.name)
        frappe.db.commit()
        frappe.clear_cache(user=user)
        return permission.name

    def visible(user):
        frappe.set_user(user)
        return set(frappe.get_list("Employee", pluck="name", limit_page_length=0))

    def exercise(client, filters, denied):
        for _, report_name, endpoint in REPORTS:
            encoded = json.dumps(filters)
            responses = (
                ("portal", client.call("hb_attendance_app.hbos_attendance.report_data." + endpoint,
                                       {"filters": encoded})),
                ("native-query-report", client.call("frappe.desk.query_report.run",
                    {"report_name": report_name, "filters": encoded, "ignore_prepared_report": 1})),
            )
            for route, response in responses:
                label = route + ":" + report_name
                if denied:
                    _require_denied(response, employees[1], label)
                else:
                    _require_ok(response, label)
        checks.append({"case": "http_deny" if denied else "http_allow", "routes": 8,
                       "filter_keys": sorted(filters)})

    try:
        for suffix in ("A", "B"):
            dep = frappe.get_doc({"doctype": "Department", "department_name": prefix + "-" + suffix,
                                 "is_group": 0}).insert()
            departments.append(dep.name)
        for user in users:
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "Synthetic Scope HR",
                            "enabled": 1, "user_type": "System User", "send_welcome_email": 0,
                            "new_password": passwords[user], "roles": [{"role": "HR User"}]}).insert()
            created_users.append(user)
        for index, employee in enumerate(employees):
            _sql_fixture("Employee", {"name": employee, "employee_name": employee,
                "employee_number": prefix + "-" + str(index), "status": "Active",
                "department": departments[index]})
            _sql_fixture("Attendance", {"name": row_ids[index], "employee": employee,
                "attendance_date": "2026-01-05", "status": "Present", "docstatus": 1})
            _sql_fixture("Employee Checkin", {"name": checkin_ids[index], "employee": employee,
                "time": "2026-01-05 08:00:00", "log_type": "IN"})
        frappe.db.commit()
        grant(users[1], departments[0])
        if not set(employees).issubset(visible(users[0])):
            raise AssertionError("Unrestricted HR does not see both synthetic Employees")
        if visible(users[1]) != {employees[0]}:
            raise AssertionError("Native Frappe Department permission is not actually restricting Employee")
        checks.append({"case": "native_employee_user_permission", "result": "PASS"})
        for key, _, _ in REPORTS:
            frappe.set_user(users[1])
            try:
                report_data._run(key, {})
            except frappe.PermissionError:
                pass
            else:
                raise AssertionError("Native scoped report function did not refuse: " + key)
        frappe.set_user(users[0])
        require_unrestricted_employee_read()
        result = report_data.get_attendance_results({"employee": employees[1]})
        if employees[1] not in json.dumps(result, default=str):
            raise AssertionError("Positive report fixture did not contain department B's real row")
        checks.append({"case": "native_report_functions_and_positive_row", "result": "PASS"})
        origin = str(frappe.conf.hbos_portal_origin)
        full = Client(origin).login(users[0], passwords[users[0]])
        scoped = Client(origin).login(users[1], passwords[users[1]])
        exercise(full, {"year": 2026, "month": 1}, denied=False)
        for filters in ({}, {"department": departments[1]}, {"employee": employees[1]},
                        {"department": departments[0]}):
            exercise(scoped, filters, denied=True)
        # Add the other department without changing the HTTP session.
        extra = grant(users[1], departments[1])
        if visible(users[1]) != set(employees):
            raise AssertionError("Grant of department B did not change native visible scope")
        exercise(scoped, {}, denied=False)
        frappe.set_user("Administrator")
        frappe.delete_doc("User Permission", extra)
        grants.remove(extra)
        frappe.db.commit()
        frappe.clear_cache(user=users[1])
        exercise(scoped, {}, denied=True)
        checks.append({"case": "same_session_grant_then_revocation", "result": "PASS"})
        frappe.set_user("Guest")
        try:
            require_unrestricted_employee_read()
        except frappe.PermissionError:
            checks.append({"case": "guest_denied", "result": "PASS"})
        else:
            raise AssertionError("Guest did not fail closed")
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for permission in grants:
            if frappe.db.exists("User Permission", permission):
                frappe.delete_doc("User Permission", permission)
        for kind, names in (("Attendance", row_ids), ("Employee Checkin", checkin_ids), ("Employee", employees)):
            for name in names:
                frappe.db.delete(kind, {"name": name})
        for user in created_users:
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, force=1)
        for department in reversed(departments):
            if frappe.db.exists("Department", department):
                frappe.delete_doc("Department", department, force=1)
        frappe.db.commit()
        after = {kind: frappe.db.count(kind) for kind in tables}
        frappe.set_user(original_user)
        if before != after:
            raise AssertionError("Disposable fixture counts were not restored")
    return {"status": "PASS", "checks": checks, "fixture_counts_restored": True,
            "runtime": "real_frappe_mariadb_http", "scope": "temporary_whole_report_gate_only",
            "owner_site": "NOT_ACCESSED", "iam_v1": "NOT_IMPLEMENTED"}
