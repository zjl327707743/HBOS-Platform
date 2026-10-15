"""Explicit exact-Preview native-session management query acceptance CLI.

No new Site, schema, service, persisted management configuration or production
activation. Compose the existing real-password WSGI fixture, then remove every
exact synthetic ID and verify native fingerprints. Preflight remains read-only;
the explicit test phase owns exact synthetic IDs.
"""
import argparse
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from hbos_portal.organization.management_http import ManagedHTTPBinding
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, POSITION, POSITION_REVISION, RECEIPT,
)

if __package__:
    from .integration_management_http import NativeManagementHTTPCases, ORIGIN, find_field
    from .integration_management_relations import POLICY_KINDS, OPERATIONS
    from .integration_management_storage import policy_presence, policy_schema_check
    from .integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )
else:
    from integration_management_http import NativeManagementHTTPCases, ORIGIN, find_field
    from integration_management_relations import POLICY_KINDS, OPERATIONS
    from integration_management_storage import policy_presence, policy_schema_check
    from integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )


QUERY_SPEC_READY = True
QUERY_PREFIX = "/api/method/hbos_portal.api.organization_relations."
QUERIES = ("get_management_context", "list_positions", "get_person_assignments", "lookup_people")
READ_OPERATIONS = {
    "hbos.organization.position.read", "hbos.organization.assignment.read", "hbos.organization.person.lookup",
}
POSITION_FIELDS = {"record_id", "title", "company_id", "department_id", "designation_id", "status", "revision"}
ASSIGNMENT_FIELDS = {"record_id", "position_id", "person_source_id", "status", "is_primary", "valid_from_utc", "valid_until_utc", "revision"}
PERSON_FIELDS = {"source_id", "display_name", "company_id", "department_id", "designation_id", "link_status", "employee_status"}


class NativeManagementQueryCases(unittest.TestCase):
    """Composition does not inherit or silently rerun write acceptance cases."""
    native = None

    def setUp(self):
        self.http = NativeManagementHTTPCases()
        self.http.native = self.native
        self.addCleanup(self.cleanup)
        self.http.setUp()
        self.http._cleanups.clear()
        self.fixture = self.http.fixture
        self.extra_users, self.extra_employees = [], []
        self.extra_company = self.fixture.prefix + "-QUERY-CO"
        self.extra_department = self.fixture.prefix + "-QUERY-DEPT"
        self.positions, self.assignments = {}, {}
        self.seed_dataset()
        self.assertEqual(self.counts(), (5, 5, 5, 5, 10))
        self.configure_client()

    def cleanup(self):
        if hasattr(self, "fixture"):
            f = self.http.reconnect()
            for key in self.assignments.values():
                f.db.sql("DELETE FROM `tabHBOS Personnel Assignment Revision` WHERE assignment=%s", (key,))
                f.db.sql("DELETE FROM `tabHBOS Personnel Assignment` WHERE name=%s", (key,))
            for key in self.positions.values():
                f.db.sql("DELETE FROM `tabHBOS Position Revision` WHERE position=%s", (key,))
                f.db.sql("DELETE FROM `tabHBOS Position` WHERE name=%s", (key,))
            for employee in self.extra_employees:
                f.db.sql("DELETE FROM `tabEmployee` WHERE name=%s", (employee,))
            for user in self.extra_users:
                f.db.sql("DELETE FROM `tabUser` WHERE name=%s", (user,))
                f.clear_cache(user=user)
            f.db.sql("DELETE FROM `tabDepartment` WHERE name=%s", (self.extra_department,))
            f.db.sql("DELETE FROM `tabCompany` WHERE name=%s", (self.extra_company,))
            f.db.commit()
        self.http.cleanup()

    def seed_dataset(self):
        f = self.http.reconnect()
        base = self.fixture
        f.db.sql("INSERT INTO `tabCompany` (name,modified) VALUES (%s,NOW(6))", (self.extra_company,))
        f.db.sql("INSERT INTO `tabDepartment` (name,company,is_group,disabled,modified) VALUES (%s,%s,0,0,NOW(6))",
                 (self.extra_department, self.extra_company))
        for suffix, company, department, label in (
                ("-QUERY-D2", base.company, base.other_department, "隐藏部门人员"),
                ("-QUERY-C2", self.extra_company, self.extra_department, "隐藏公司人员")):
            user = base.prefix.lower() + suffix.lower() + "@example.invalid"
            employee = base.prefix + suffix + "-EMP"
            self.extra_users.append(user)
            self.extra_employees.append(employee)
            f.db.sql("INSERT INTO `tabUser` (name,email,enabled,user_type,phone,mobile_no,modified) "
                     "VALUES (%s,%s,1,'System User',%s,%s,NOW(6))",
                     (user, user, "SYNTH-PRIVATE-PHONE-" + user, "SYNTH-PRIVATE-MOBILE-" + user))
            f.db.sql("INSERT INTO `tabEmployee` (name,employee_name,user_id,company,department,designation,status,date_of_joining,cell_number,modified) "
                     "VALUES (%s,%s,%s,%s,%s,%s,'Active','2026-01-01',%s,NOW(6))",
                     (employee, label, user, company, department, base.designation, "SYNTH-PRIVATE-CELL-" + employee))
        for employee, label in ((base.employee, "公开人员甲"), (base.manager_employee, "公开人员乙")):
            f.db.sql("UPDATE `tabEmployee` SET employee_name=%s,cell_number=%s WHERE name=%s",
                     (label, "SYNTH-PRIVATE-CELL-" + employee, employee))
        for user in (base.manager, base.beneficiary):
            f.db.sql("UPDATE `tabUser` SET phone=%s,mobile_no=%s WHERE name=%s",
                     ("SYNTH-PRIVATE-PHONE-" + user, "SYNTH-PRIVATE-MOBILE-" + user, user))
        f.db.commit()
        rules = []
        for index, company, departments in ((1, base.company, [base.department, base.other_department]),
                                             (2, self.extra_company, [self.extra_department])):
            rules.append(dict(rule_id="synthetic-query-owner-" + str(index), operation_schema_version=1,
                operation_ids=list(OPERATIONS), company_id=company, target_department_ids=departments,
                include_children=False, assignment_until_limit_utc="2026-10-25T00:00:00Z",
                person_scope=dict(source_type="Employee", company_id=company, department_ids=departments)))
        owner = base.make_policy(subject=base.approver, policy_id=str(uuid4()), rules=rules)
        base.install(owner)
        f.db.commit()
        f.set_user(base.approver)
        base.service = base.make_service(f)
        for key, lead, company, department, title in (
                ("allowed_a", "f", base.company, base.department, "公开岗位甲"),
                ("allowed_b", "f", base.company, base.department, "公开岗位乙"),
                ("allowed_c", "f", base.company, base.department, "公开岗位丙"),
                ("hidden_department", "0", base.company, base.other_department, "隐藏部门岗位"),
                ("hidden_company", "1", self.extra_company, self.extra_department, "隐藏公司岗位")):
            record_id = lead + str(uuid4())[1:]
            base.service.id_factory = lambda record_id=record_id: record_id
            result = base.command("create_position", dict(title=title, company=company, department=department,
                                                          designation=base.designation, status="active"))
            self.positions[key] = result.record_id
        base.service.id_factory = uuid4
        for key, employee, position in (
                ("allowed_a", base.employee, self.positions["allowed_a"]),
                ("allowed_b", base.employee, self.positions["allowed_b"]),
                ("hidden_position", base.employee, self.positions["hidden_department"]),
                ("hidden_person", self.extra_employees[0], self.positions["allowed_a"]),
                ("hidden_company", self.extra_employees[1], self.positions["hidden_company"])):
            result = base.command("create_assignment", base.assignment_payload(position, employee=employee))
            self.assignments[key] = result.record_id
        f.db.commit()
        f.set_user("Administrator")

    def configure_client(self, *, binding=True):
        from hbos_portal.organization.management_query_http import ManagedQueryHTTPApplication
        server = None
        if binding:
            server = ManagedHTTPBinding(site_id=SITE, database_sha256=DB_HASH, origin=ORIGIN,
                approval_verifier=self.fixture.approvals(), clock=lambda: self.http.now, enabled=True)
        self.application = ManagedQueryHTTPApplication(self.http.native_application, binding=server)
        self.client = self.query_client(self.application)

    def query_client(self, application):
        """Reuse a genuinely authenticated native SID, without making a session."""
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        client = Client(application, Response, use_cookies=True)
        sid = self.http.client.get_cookie("sid", domain=SITE)
        self.assertIsNotNone(sid)
        client.set_cookie("sid", sid.value, domain=SITE)
        self.http.clients.append(client)
        return client

    def request(self, query, params=None, *, client=None, method="GET", origin=ORIGIN, token=None,
                body=None, fetch_site=None, base_url=ORIGIN):
        headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
        if origin is not None:
            headers["Origin"] = origin
        if token is not False:
            headers["X-Frappe-CSRF-Token"] = self.http.token if token is None else token
        if fetch_site is not None:
            headers["Sec-Fetch-Site"] = fetch_site
        response = (client or self.client).open(QUERY_PREFIX + query, method=method, base_url=base_url,
            query_string=params or {}, data=body, headers=headers, buffered=True)
        try:
            return response.status_code, response.get_json(), response.get_data(as_text=True)
        finally:
            response.close()

    def data(self, response):
        self.assertEqual(response[0], 200)
        message = response[1].get("message")
        self.assertIsInstance(message, dict)
        self.assertIs(message.get("ok"), True)
        data = message.get("data")
        self.assertIsInstance(data, dict)
        self.assertIs(data.get("read_only"), True)
        self.assertIs(data.get("runtime_verified"), False)
        self.assertEqual(data.get("authorization_effect"), "none")
        self.assertIs(data.get("position_authorization_connected"), False)
        return data

    def counts(self):
        return self.http.counts()

    def denied(self, response, before):
        self.assertGreaterEqual(response[0], 400)
        self.assertIsInstance(response[1], dict)
        message = response[1].get("message")
        self.assertIsInstance(message, dict)
        self.assertIs(message.get("ok"), False)
        self.assertIsNone(find_field(response[1], "items"))
        self.assertIsNone(find_field(response[1], "total"))
        self.assertNotIn("SAVE_RESULT_UNKNOWN", response[2])
        for key in ("exc", "exception", "traceback", "_server_messages"):
            self.assertIsNone(find_field(response[1], key))
        self.assertEqual(self.counts(), before)

    def outside_scope(self, response):
        if response[0] == 200:
            data = self.data(response)
            self.assertEqual((data["items"], data["total"]), ([], 0))
        else:
            self.assertGreaterEqual(response[0], 400)
            self.assertIsNone(find_field(response[1], "items"))
            self.assertIsNone(find_field(response[1], "total"))

    def rewrite_policy(self, operation):
        base = self.fixture
        rule = dict(rule_id="synthetic-independent-read", operation_schema_version=1,
            operation_ids=[operation], company_id=base.company, target_department_ids=[base.department],
            include_children=False, assignment_until_limit_utc=None,
            person_scope=None if operation.endswith("position.read") else
                dict(source_type="Employee", company_id=base.company, department_ids=[base.department]))
        f = self.http.reconnect()
        base.policy = base.make_policy(revision=2, generation=2, rules=[rule])
        base.install(base.policy, expected=1)
        f.db.commit()
        self.configure_client()

    def after_query(self, action, *, before_recheck=False):
        from hbos_portal.organization.management_queries import ManagementQueryService
        method = "recheck_pending" if before_recheck else "execute"
        original = getattr(ManagementQueryService, method)

        def wrapped(service, *args, **kwargs):
            if before_recheck:
                action(service)
                return original(service, *args, **kwargs)
            result = original(service, *args, **kwargs)
            action(service)
            return result

        return patch.object(ManagementQueryService, method, wrapped)

    def test_position_filtering_happens_before_total_and_pagination(self):
        before = self.counts()
        first = self.data(self.request("list_positions", {"page": "1", "page_size": "2"}))
        second = self.data(self.request("list_positions", {"page": "2", "page_size": "2"}))
        self.assertEqual((first["total"], second["total"], len(first["items"]), len(second["items"])), (3, 3, 2, 1))
        expected = {self.positions[key] for key in ("allowed_a", "allowed_b", "allowed_c")}
        actual = {row["record_id"] for row in first["items"] + second["items"]}
        self.assertEqual(actual, expected)
        self.assertTrue(all(set(row) == POSITION_FIELDS for row in first["items"] + second["items"]))
        self.assertEqual(self.counts(), before)

    def test_company_department_and_search_filters_cannot_widen_scope(self):
        before = self.counts()
        for params in ({"company_id": self.extra_company}, {"department_id": self.fixture.other_department}, {"q": "隐藏"}):
            self.outside_scope(self.request("list_positions", params))
        self.assertEqual(self.data(self.request("list_positions", {"q": "公开"}))["total"], 3)
        self.assertEqual(self.counts(), before)

    def test_position_read_does_not_supply_assignment_or_person_lookup(self):
        self.rewrite_policy("hbos.organization.position.read")
        before = self.counts()
        self.assertEqual(self.data(self.request("list_positions"))["total"], 3)
        self.denied(self.request("get_person_assignments", {"employee_id": self.fixture.employee}), before)
        self.denied(self.request("lookup_people"), before)

    def test_assignment_read_is_independent_and_matches_person_and_position_scope(self):
        self.rewrite_policy("hbos.organization.assignment.read")
        before = self.counts()
        data = self.data(self.request("get_person_assignments", {"employee_id": self.fixture.employee, "page_size": "1"}))
        second = self.data(self.request("get_person_assignments", {"employee_id": self.fixture.employee, "page": "2", "page_size": "1"}))
        self.assertEqual((data["total"], second["total"]), (2, 2))
        actual = {row["record_id"] for row in data["items"] + second["items"]}
        self.assertEqual(actual, {self.assignments["allowed_a"], self.assignments["allowed_b"]})
        self.assertTrue(all(set(row) == ASSIGNMENT_FIELDS for row in data["items"] + second["items"]))
        self.outside_scope(self.request("get_person_assignments", {"employee_id": self.extra_employees[0]}))
        self.denied(self.request("list_positions"), before)
        self.denied(self.request("lookup_people"), before)

    def test_person_lookup_is_independent_and_projects_only_safe_fields(self):
        self.rewrite_policy("hbos.organization.person.lookup")
        before = self.counts()
        response = self.request("lookup_people")
        data = self.data(response)
        self.assertEqual(data["total"], 2)
        self.assertEqual({row["source_id"] for row in data["items"]}, {self.fixture.employee, self.fixture.manager_employee})
        self.assertEqual({row["display_name"] for row in data["items"]}, {"公开人员甲", "公开人员乙"})
        self.assertTrue(all(set(row) == PERSON_FIELDS for row in data["items"]))
        named = self.data(self.request("lookup_people", {"q": "公开人员甲", "page_size": "1"}))
        self.assertEqual(named["total"], 1)
        self.assertEqual([row["source_id"] for row in named["items"]], [self.fixture.employee])
        for params in ({"company_id": self.extra_company}, {"department_id": self.fixture.other_department}):
            self.outside_scope(self.request("lookup_people", params))
        for secret in ("SYNTH-PRIVATE", self.fixture.manager, self.fixture.beneficiary, "System Manager"):
            self.assertNotIn(secret, response[2])
        self.denied(self.request("list_positions"), before)
        self.denied(self.request("get_person_assignments", {"employee_id": self.fixture.employee}), before)

    def test_context_has_only_independent_read_operations_and_scoped_metadata(self):
        before = self.counts()
        response = self.request("get_management_context")
        data = self.data(response)
        self.assertEqual(set(data["operation_ids"]), READ_OPERATIONS)
        self.assertEqual({scope["operation_id"] for scope in data["scopes"]}, READ_OPERATIONS)
        for scope in data["scopes"]:
            self.assertEqual(set(scope), {"operation_id", "operation_schema_version", "company_id",
                "target_department_ids", "include_children", "person_scope"})
            self.assertEqual(scope["company_id"], self.fixture.company)
            self.assertEqual(scope["target_department_ids"], [self.fixture.department])
            self.assertEqual(scope["operation_schema_version"], 1)
            self.assertIs(scope["include_children"], False)
            self.assertEqual(scope["person_scope"], {"source_type": "Employee",
                "company_id": self.fixture.company, "department_ids": [self.fixture.department]})
        for secret in (self.extra_company, self.fixture.other_department, self.fixture.approver,
                       self.fixture.manager, "SYNTH-PRIVATE", "System Manager"):
            self.assertNotIn(secret, response[2])
        self.assertEqual(self.counts(), before)

    def test_native_system_manager_without_policy_cannot_query(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        client = Client(self.application, Response, use_cookies=True)
        self.http.clients.append(client)
        token = self.http.login(client, self.fixture.beneficiary, self.http.ordinary_password)
        before = self.counts()
        for query in QUERIES:
            params = {"employee_id": self.fixture.employee} if query == "get_person_assignments" else None
            self.denied(self.request(query, params, client=client, token=token), before)

    def test_protocol_cookie_csrf_origin_method_fields_and_duplicates_are_strict(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        before = self.counts()
        guest = Client(self.application, Response, use_cookies=True)
        self.http.clients.append(guest)
        for options in ({"client": guest}, {"token": False}, {"token": "synthetic-wrong-token"},
                        {"origin": "https://other.invalid"}, {"fetch_site": "cross-site"},
                        {"method": "POST"}, {"body": "{}"}):
            self.denied(self.request("list_positions", **options), before)
        self.assertEqual(self.data(self.request("list_positions", origin=None, fetch_site="same-origin"))["total"], 3)
        self.assertEqual(self.counts(), before)
        for params in ([('page', '1'), ('page', '2')], {"phone": "SYNTH-PRIVATE"}, {"user": self.fixture.manager},
                       {"fields": "*"}, {"order": "name desc"}, {"page": "0"}, {"page_size": "99999"}):
            self.denied(self.request("list_positions", params), before)
        self.denied(self.request("get_management_context", {"company_id": self.fixture.company}), before)
        self.denied(self.request("get_person_assignments"), before)

    def test_native_application_and_unbound_query_wrapper_remain_closed(self):
        from hbos_portal.organization.management_query_http import ManagedQueryHTTPApplication
        before = self.counts()
        bound = self.application.binding
        invalid = (replace(bound, enabled=False), replace(bound, site_id="other-preview.invalid"),
                   replace(bound, database_sha256="0" * 64), replace(bound, origin="https://other.invalid"))
        applications = [self.http.native_application, ManagedQueryHTTPApplication(self.http.native_application)]
        applications.extend(ManagedQueryHTTPApplication(self.http.native_application, binding=item) for item in invalid)
        for application in applications:
            client = self.query_client(application)
            self.denied(self.request("list_positions", client=client), before)

    def test_expired_policy_refuses_query_and_returns_no_count(self):
        before = self.counts()
        self.http.now = self.fixture.policy.valid_until_utc
        self.denied(self.request("list_positions"), before)

    def test_revoked_policy_refuses_query_and_returns_no_count(self):
        before = self.counts()
        f = self.http.reconnect()
        self.fixture.install(replace(self.fixture.policy, status="revoked", revision=2, authority_generation=2),
                             expected=1, approved=False)
        f.db.commit()
        self.denied(self.request("list_positions"), before)

    def test_policy_expiring_after_selection_is_refused_before_release(self):
        before = self.counts()
        with self.after_query(lambda service: setattr(self.http, "now", self.fixture.policy.valid_until_utc)):
            self.denied(self.request("list_positions"), before)

    def test_return_guard_rejects_policy_changed_by_independent_committed_connection(self):
        before = self.counts()
        revoked = replace(self.fixture.policy, status="revoked", revision=2, authority_generation=2)
        with self.after_query(lambda service: self.fixture.external(
                lambda f: self.fixture.install(revoked, native=f, expected=1, approved=False)), before_recheck=True):
            self.denied(self.request("list_positions"), before)
        self.assertEqual(self.native.db.get_value("HBOS Organization Management Policy", self.fixture.policy_id, "revision"), 2)

    def test_return_guard_rejects_native_source_changed_by_independent_connection(self):
        before = self.counts()
        with self.after_query(lambda service: self.fixture.external(lambda f: f.db.sql(
                "UPDATE `tabDepartment` SET disabled=1,modified=NOW(6) WHERE name=%s", (self.fixture.department,))), before_recheck=True):
            self.denied(self.request("list_positions"), before)
        self.assertEqual(self.native.db.get_value("Department", self.fixture.department, "disabled"), 1)

    def test_return_guard_rejects_fact_changed_by_independent_controlled_writer(self):
        before = self.counts()
        position = self.positions["allowed_a"]
        payload = {**self.fixture.position_payload(), "title": "公开岗位并发更新"}
        options = self.fixture.options("update_position", actor=self.fixture.manager, record_id=position, expected_revision=1)

        def update(f):
            f.set_user(self.fixture.manager)
            return self.fixture.make_service(f).execute("update_position", payload, **options)

        with self.after_query(lambda service: self.fixture.external(update), before_recheck=True):
            response = self.request("list_positions")
        expected = tuple(value + delta for value, delta in zip(before, (0, 1, 0, 0, 1)))
        self.denied(response, expected)
        self.assertEqual(self.native.db.get_value(POSITION, position, "revision"), 2)

    def test_native_session_refresh_commits_metadata_without_managed_fact_write(self):
        before = self.counts()
        sid = self.client.get_cookie("sid", domain=SITE).value
        f = self.http.reconnect()
        old = f.utils.now_datetime() - timedelta(seconds=601)
        f.db.sql("UPDATE `tabSessions` SET lastupdate=%s WHERE sid=%s AND user=%s", (old, sid, self.fixture.manager))
        f.db.commit()
        commits = []
        original = self.http.database_class.commit

        def commit(db, *args, **kwargs):
            request = getattr(self.native.local, "request", None)
            if request and request.path == QUERY_PREFIX + "list_positions":
                commits.append(db.transaction_writes)
            return original(db, *args, **kwargs)

        def age(service):
            session = self.native.local.session_obj
            self.assertEqual(session.sid, sid)
            session.data.data.last_updated = old

        with patch.object(self.http.database_class, "commit", commit), self.after_query(age):
            self.assertEqual(self.data(self.request("list_positions"))["total"], 3)
        self.assertEqual(self.counts(), before)
        self.assertEqual(len(commits), 1)
        self.assertGreaterEqual(commits[0], 1)
        row = self.native.db.sql("SELECT lastupdate,sessiondata FROM `tabSessions` WHERE sid=%s AND user=%s", (sid, self.fixture.manager))
        self.assertEqual(len(row), 1)
        self.assertGreater(row[0][0], old)
        self.assertGreater(self.native.utils.get_datetime(json.loads(row[0][1])["last_updated"]), old)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("preflight", "test"), default="preflight")
    parser.add_argument("--expected-database-sha256", required=True)
    args = parser.parse_args()
    if args.phase == "test" and not QUERY_SPEC_READY:
        raise RuntimeError("QUERY_ACCEPTANCE_SPEC_REQUIRED")
    import frappe
    frappe.init(site=SITE, sites_path=".")
    frappe.connect()
    try:
        frappe.db.sql("START TRANSACTION READ ONLY")
        report = check_target(frappe, args.expected_database_sha256)
        report["preflight"] = preflight(frappe)
        report["policy_tables_present"] = policy_presence(frappe)
        if not all(report["preflight"]["tables_present"].values()) or not all(report["policy_tables_present"].values()):
            raise RuntimeError("MANAGED_SCHEMA_REQUIRED")
        if any(frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)):
            raise RuntimeError("MANAGED_TABLES_NOT_EMPTY")
        report["relation_schema"] = schema_check(frappe)
        report["policy_schema"] = policy_schema_check(frappe)
        frappe.db.rollback()
        if args.phase == "test":
            before = native_fingerprints(frappe)
            NativeManagementQueryCases.native = frappe
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeManagementQueryCases)
            names = [test.id().rsplit(".", 1)[1] for test in suite]
            if len(names) < 10:
                raise RuntimeError("QUERY_ACCEPTANCE_CASES_INCOMPLETE")
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            frappe.init(site=SITE, sites_path=".", force=True)
            frappe.connect()
            frappe.set_user("Administrator")
            report["tests_run"] = result.testsRun
            report["test_names"] = names
            report["test_status"] = "PASS" if result.wasSuccessful() else "FAIL"
            report["native_preservation"] = "PASS" if native_fingerprints(frappe) == before else "FAIL"
            report["final_native_counts"] = preflight(frappe)["native_counts"]
            report["final_managed_counts"] = {kind: frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)}
            report["tables_empty"] = not any(report["final_managed_counts"].values())
            report["real_native_password_session"] = True
            report["limits"] = "No Administrator password/session fabrication, real management activation, schema action, business grant or full restore."
            print(json.dumps(report, ensure_ascii=False, default=str))
            if not result.wasSuccessful() or not report["tables_empty"] or report["native_preservation"] != "PASS":
                raise SystemExit(1)
        else:
            print(json.dumps(report, ensure_ascii=False, default=str))
    finally:
        if getattr(frappe.local, "db", None):
            frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
