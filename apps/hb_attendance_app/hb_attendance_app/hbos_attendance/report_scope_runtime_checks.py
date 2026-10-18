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
from urllib.parse import quote, urlencode
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
        url = "http://127.0.0.1:8000/api/method/" + quote(method, safe=".")
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
    company = prefix + "-COMPANY"
    company_abbr = "RS" + test_id.split("-", 1)[0][-3:]
    users = [f"hbos-rs-{test_id}-{kind}@example.invalid" for kind in ("all", "a")]
    passwords = {user: secrets.token_urlsafe(32) for user in users}
    employees = [prefix + "-EMP-A", prefix + "-EMP-B"]
    row_ids = [prefix + "-ATT-A", prefix + "-ATT-B"]
    checkin_ids = [prefix + "-LOG-A", prefix + "-LOG-B"]
    staging_ids = [prefix + "-STAGING-A", prefix + "-STAGING-B"]
    departments, created_users, grants = [], [], []
    tables = ("Company", "User", "Employee", "Department", "User Permission",
              "Attendance", "Employee Checkin", "HBOS Attendance Import Log")
    before = {kind: frappe.db.count(kind) for kind in tables}
    # Refusal happens before entering cleanup: never delete a pre-existing ID.
    for kind, names in (("Company", (company,)), ("User", users), ("Employee", employees),
                        ("Attendance", row_ids), ("Employee Checkin", checkin_ids),
                        ("HBOS Attendance Import Log", staging_ids)):
        if any(frappe.db.exists(kind, name) for name in names):
            raise RuntimeError("Refusing to reuse existing synthetic fixture IDs")
    if frappe.db.exists("Company", {"abbr": company_abbr}):
        raise RuntimeError("Refusing to reuse a pre-existing synthetic company abbreviation")
    for suffix in ("A", "B"):
        if frappe.db.exists("Department", {"department_name": prefix + "-" + suffix}):
            raise RuntimeError("Refusing to reuse a pre-existing synthetic department")
    if before["Employee"]:
        raise RuntimeError("Report scope CI must start on an empty employee dataset")
    checks = []
    from hb_attendance_app.hbos_attendance import report_data
    from hb_attendance_app.hbos_attendance.report_scope import require_unrestricted_employee_read

    def grant(user, value, *, allow="Department", applicable_for=None):
        frappe.set_user("Administrator")
        permission = frappe.get_doc({"doctype": "User Permission", "user": user,
                                   "allow": allow, "for_value": value,
                                   "apply_to_all_doctypes": 0 if applicable_for else 1,
                                   "applicable_for": applicable_for, "hide_descendants": 1}).insert()
        grants.append(permission.name)
        frappe.db.commit()
        frappe.clear_cache(user=user)
        return permission.name

    def remove_grant(user, permission):
        frappe.set_user("Administrator")
        frappe.delete_doc("User Permission", permission)
        grants.remove(permission)
        frappe.db.commit()
        frappe.clear_cache(user=user)

    def visible(user):
        frappe.set_user(user)
        return set(frappe.get_list("Employee", pluck="name", limit_page_length=0))

    def exercise(client, filters, denied, *, only=None):
        selected = [row for row in REPORTS if only is None or row[0] in only]
        for _, report_name, endpoint in selected:
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
        checks.append({"case": "http_deny" if denied else "http_allow", "routes": 2 * len(selected),
                       "filter_keys": sorted(filters)})

    def ai_preview(client, denied):
        response = client.call(report_data._REPORTS["monthly"] + ".ai_review_preview",
                               {"year": 2026, "month": 1})
        if denied:
            _require_denied(response, employees[1], "ai-review-preview")
        else:
            result = _require_ok(response, "ai-review-preview")
            if not isinstance(result.get("employee_count"), int):
                raise AssertionError("Native AI preview did not return its normal count contract")
        checks.append({"case": "ai_preview_deny" if denied else "ai_preview_allow", "result": "PASS"})

    def require_staging_marker(client):
        result = _require_ok(client.call(
            "hb_attendance_app.hbos_attendance.report_data.get_monthly_staging",
            {"filters": json.dumps({"import_log": staging_ids[1]})}), "positive-unknown-staging")
        if employees[1] not in json.dumps(result, default=str):
            raise AssertionError("Unrestricted HR must still read the synthetic unmatched staging row")

    try:
        # Minimal synthetic master, as with Employee/Attendance below: this suite
        # tests report permissions, not Company accounting setup or lifecycle.
        # Do not create a chart of accounts, relax mandatory fields, or borrow
        # an existing Company. Departments still use their native controller.
        _sql_fixture("Company", {"name": company, "company_name": company,
            "abbr": company_abbr, "default_currency": "CNY", "country": "China"})
        for suffix in ("A", "B"):
            dep = frappe.get_doc({"doctype": "Department", "department_name": prefix + "-" + suffix,
                                 "company": company, "is_group": 0}).insert()
            departments.append(dep.name)
        for user in users:
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "Synthetic Scope HR",
                            "enabled": 1, "user_type": "System User", "send_welcome_email": 0,
                            "new_password": passwords[user], "roles": [{"role": "HR User"}]}).insert()
            created_users.append(user)
        for index, employee in enumerate(employees):
            _sql_fixture("Employee", {"name": employee, "employee_name": employee,
                "employee_number": prefix + "-" + str(index), "status": "Active",
                "department": departments[index], "company": company})
            _sql_fixture("Attendance", {"name": row_ids[index], "employee": employee,
                "attendance_date": "2026-01-05", "status": "Present", "docstatus": 1,
                "company": company})
            _sql_fixture("Employee Checkin", {"name": checkin_ids[index], "employee": employee,
                "time": "2026-01-05 08:00:00", "log_type": "IN"})
            # The imported JSON does not depend on an Employee foreign key.
            # B deliberately carries an unmatched employee_number.
            _sql_fixture("HBOS Attendance Import Log", {"name": staging_ids[index],
                "import_type": "考勤机月度导出表", "import_status": "Success",
                "period_start": "2026-01-01", "period_end": "2026-01-31",
                "monthly_summary_staging": json.dumps({"records": [{
                    "employee_name": employee,
                    "employee_number": prefix + ("-0" if index == 0 else "-UNMATCHED-B"),
                    "department": departments[index], "expected_days": 20,
                    "actual_days": 20, "absent_days": 0}]})})
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
        ai_preview(scoped, denied=True)
        ai_preview(full, denied=False)
        require_staging_marker(full)
        # Add B without changing the HTTP session. A+B matches every current
        # Employee but remains an explicit scope: it cannot prove permission
        # over unknown historical/staging rows. Keep this as a negative case.
        extra = grant(users[1], departments[1])
        if visible(users[1]) != set(employees):
            raise AssertionError("Grant of department B did not change native visible scope")
        exercise(scoped, {}, denied=True)
        checks.append({"case": "all_current_departments_granted_remains_scoped", "result": "PASS"})
        remove_grant(users[1], extra)
        exercise(scoped, {}, denied=True)
        # Grant genuinely unrestricted read by removing the only remaining
        # scope, then restore department A, all on the very same HTTP session.
        remove_grant(users[1], grants[0])
        if frappe.permissions.get_user_permissions(users[1]):
            raise AssertionError("Positive HR fixture must have no native User Permission scope")
        exercise(scoped, {}, denied=False)
        grant(users[1], departments[0])
        exercise(scoped, {}, denied=True)
        checks.append({"case": "same_session_grant_then_revocation", "result": "PASS"})

        # Scopes applicable only to a source DocType leave Employee fully
        # visible. Each actual source must still close the corresponding raw
        # report before it reads data; no role or permission algorithm changes.
        source_cases = (
            ("Employee", employees[0], "Attendance", "results"),
            ("Employee", employees[0], "Employee Checkin", "checkins"),
            ("Employee", employees[0], "HBOS Leave Record", "monthly"),
            ("HBOS Attendance Import Log", staging_ids[0], "HBOS Attendance Import Log", "staging"),
            ("Department", departments[0], "HBOS Shift Rule", "checkins"),
        )
        for allow, value, doctype, report_key in source_cases:
            source_permission = grant(users[0], value, allow=allow, applicable_for=doctype)
            if visible(users[0]) != set(employees):
                raise AssertionError("Source-only fixture unexpectedly restricted Employee: " + doctype)
            exercise(full, {}, denied=True, only={report_key})
            if report_key == "monthly":
                ai_preview(full, denied=True)
            remove_grant(users[0], source_permission)
            exercise(full, {}, denied=False, only={report_key})
            checks.append({"case": "source_only_scope", "doctype": doctype, "result": "PASS"})

        # A departed Employee still counts in native visibility. Then remove
        # only these newly inserted synthetic Employee masters to model legacy
        # orphan Attendance/Checkin rows. Never delete an existing employee.
        frappe.set_user("Administrator")
        frappe.db.set_value("Employee", employees[1], "status", "Left")
        frappe.db.commit()
        if employees[1] not in visible(users[0]) or employees[1] in visible(users[1]):
            raise AssertionError("Departed employee visibility fixture is not meaningful")
        exercise(full, {}, denied=False)
        exercise(scoped, {}, denied=True)
        checks.append({"case": "departed_employee", "result": "PASS"})
        for remaining, removed in ((1, employees[1]), (0, employees[0])):
            frappe.set_user("Administrator")
            frappe.db.delete("Employee", {"name": removed})
            frappe.db.commit()
            frappe.clear_cache(user=users[1])
            if len(visible(users[1])) != remaining or frappe.db.count("Employee") != remaining:
                raise AssertionError("Historical fixture must reproduce equal visible/total Employee counts")
            exercise(scoped, {}, denied=True)
            ai_preview(scoped, denied=True)
            exercise(full, {}, denied=False)
            require_staging_marker(full)
            checks.append({"case": "orphan_and_unmatched_staging" if remaining else "zero_employee_history",
                           "remaining_employees": remaining, "result": "PASS"})
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
        for kind, names in (("Attendance", row_ids), ("Employee Checkin", checkin_ids),
                            ("HBOS Attendance Import Log", staging_ids), ("Employee", employees)):
            for name in names:
                frappe.db.delete(kind, {"name": name})
        for user in created_users:
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, force=1)
        for department in reversed(departments):
            if frappe.db.exists("Department", department):
                frappe.delete_doc("Department", department, force=1)
        frappe.db.delete("Company", {"name": company})
        frappe.db.commit()
        after = {kind: frappe.db.count(kind) for kind in tables}
        frappe.set_user(original_user)
        if before != after:
            raise AssertionError("Disposable fixture counts were not restored")
    return {"status": "PASS", "checks": checks, "fixture_counts_restored": True,
            "runtime": "real_frappe_mariadb_http", "scope": "temporary_whole_report_gate_only",
            "owner_site": "NOT_ACCESSED", "iam_v1": "NOT_IMPLEMENTED"}
