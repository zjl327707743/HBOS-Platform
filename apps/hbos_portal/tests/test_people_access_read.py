from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch


class NativePermissionError(Exception):
    pass


class PeopleAccessReadTest(unittest.TestCase):
    def setUp(self):
        self.native = types.SimpleNamespace(
            whitelist=lambda **kw: lambda fn: fn,
            PermissionError=NativePermissionError,
            get_list=Mock(), session=types.SimpleNamespace(user="synthetic-reader"),
        )
        self.modules = patch.dict(sys.modules, {"frappe": self.native})
        self.modules.start()
        self.api = importlib.import_module("hbos_portal.api.people_access")
        self.binding = patch.object(self.api, "frappe", self.native)
        self.binding.start()
        self.auth = patch.object(self.api, "require_authenticated_user", return_value="synthetic-reader")
        self.actor = self.auth.start()

    def tearDown(self):
        self.auth.stop()
        self.binding.stop()
        self.modules.stop()

    def test_page_and_total_use_native_permissions_and_phone_is_masked(self):
        self.native.get_list.side_effect = [[{"total": 21}], [
            {"name": "synthetic-user", "full_name": "合成人员", "mobile_no": "13812345678", "enabled": 1},
        ]]
        result = self.api.get_people(page=2, page_size=10, name="合成", phone="")
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["items"][0]["phone"], "138****5678")
        self.assertEqual(data["total"], 21)
        self.assertFalse(data["position_authorization_connected"])
        self.assertEqual(data["authorization_domain"], "native_personnel")
        self.assertFalse(data["management_policy_applied"])
        count, rows = self.native.get_list.call_args_list
        self.assertEqual(count.kwargs["filters"], rows.kwargs["filters"])
        self.assertEqual(count.kwargs["fields"], [{"COUNT": "name", "as": "total"}])
        self.assertEqual(rows.kwargs["limit_start"], 10)
        self.assertNotIn("ignore_permissions", rows.kwargs)
        self.assertNotIn("13812345678", str(result))

    def test_employee_keeps_native_department_and_does_not_invent_user_or_grant(self):
        self.native.get_list.side_effect = [[{"total": 1}], [{
            "name": "EMP-DEMO", "employee_name": "合成员工", "employee_number": "E-1",
            "department": "DEPT-A", "designation": "检验员", "user_id": "", "status": "Active",
        }]]
        result = self.api.get_people(source="Employee", department="DEPT-A", position="检验")
        person = result["data"]["items"][0]
        self.assertEqual(person["department"], "DEPT-A")
        self.assertFalse(person["account_linked"])
        self.assertEqual(person["role_profile"], "")
        self.assertNotIn("user_id", person)
        self.assertEqual(self.native.get_list.call_args.args[0], "Employee")

    def test_native_denial_does_not_fall_back_to_other_data(self):
        self.native.get_list.side_effect = NativePermissionError()
        result = self.api.get_people()
        self.assertEqual(result["error"]["code"], "FORBIDDEN")
        self.assertNotIn("data", result)
        self.assertEqual(self.native.get_list.call_count, 1)

    def test_anonymous_is_rejected_before_query(self):
        from hbos_portal.contracts.errors import PortalException
        self.actor.side_effect = PortalException("UNAUTHENTICATED", "请登录。")
        self.assertEqual(self.api.get_roles()["error"]["code"], "UNAUTHENTICATED")
        self.native.get_list.assert_not_called()

    def test_invalid_source_page_and_filter_are_rejected_without_query(self):
        for kwargs in [{"source": "Secret"}, {"page": 0}, {"page": "1.5"}, {"page_size": 51},
                       {"department": "DEPT-A"}, {"name": "x" * 101}]:
            with self.subTest(kwargs=kwargs):
                self.assertFalse(self.api.get_people(**kwargs)["ok"])
        self.native.get_list.assert_not_called()

    def test_native_roles_are_read_only_and_do_not_claim_position_mapping(self):
        self.native.get_list.side_effect = [[{"total": 1}], [{"name": "Native Role", "creation": "2026-10-01", "desk_access": 1}]]
        result = self.api.get_roles(name="Native")
        self.assertEqual(result["data"]["items"][0]["name"], "Native Role")
        self.assertTrue(result["data"]["read_only"])
        self.assertFalse(result["data"]["position_authorization_connected"])
        self.assertEqual(result["data"]["authorization_domain"], "native_personnel")
        self.assertFalse(result["data"]["management_policy_applied"])

    def test_organization_cap_is_explicit_and_no_hidden_counts_are_queried(self):
        self.native.get_list.return_value = [{"name": f"D-{i}", "parent_department": None} for i in range(201)]
        result = self.api.get_organizations()["data"]
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["items"]), 200)
        self.assertEqual(self.native.get_list.call_count, 1)
        self.assertEqual(result["authorization_domain"], "native_personnel")
        self.assertFalse(result["management_policy_applied"])

    def test_phone_probes_are_rejected_before_count_or_rows(self):
        for source in ("User", "Employee"):
            for phone in ("5678", "%", "_", "13812345678", " 5678 "):
                with self.subTest(source=source, phone=phone):
                    result = self.api.get_people(source=source, phone=phone)
                    self.assertEqual(result["error"]["code"], "INVALID_REQUEST")
        self.native.get_list.assert_not_called()

    def test_empty_phone_keeps_native_read_compatibility(self):
        for phone in ("", None, "   "):
            with self.subTest(phone=phone):
                self.native.get_list.reset_mock()
                self.native.get_list.side_effect = [[{"total": 0}], []]
                result = self.api.get_people(phone=phone)
                self.assertTrue(result["ok"])
                self.assertEqual(self.native.get_list.call_count, 2)
                self.assertFalse(any(item[0] == "mobile_no" for item in self.native.get_list.call_args.kwargs["filters"]))

    def test_non_string_filters_are_rejected_without_query(self):
        for value in ({"name": "synthetic"}, ["synthetic"], 1, True, 1.5):
            for field in ("name", "phone", "department", "position"):
                with self.subTest(field=field, value=value):
                    result = self.api.get_people(source="Employee", **{field: value})
                    self.assertEqual(result["error"]["code"], "INVALID_REQUEST")
            with self.subTest(role_name=value):
                self.assertEqual(self.api.get_roles(name=value)["error"]["code"], "INVALID_REQUEST")
        self.native.get_list.assert_not_called()

    def test_like_search_uses_literals_and_count_uses_identical_filters(self):
        keyword = "合成%_\\人员"
        pattern = "%合成\\%\\_\\\\人员%"
        cases = (
            (self.api.get_people, {"source": "User", "name": keyword}, [["full_name", "like", pattern], ["name", "not in", ["Guest", "Administrator"]]]),
            (self.api.get_people, {"source": "Employee", "name": keyword, "position": keyword}, [["employee_name", "like", pattern], ["designation", "like", pattern]]),
            (self.api.get_roles, {"name": keyword}, [["name", "like", pattern]]),
        )
        for method, params, expected in cases:
            with self.subTest(method=method.__name__, params=params):
                self.native.get_list.reset_mock()
                self.native.get_list.side_effect = [[{"total": 0}], []]
                self.assertTrue(method(**params)["ok"])
                count, rows = self.native.get_list.call_args_list
                self.assertEqual(count.kwargs["filters"], expected)
                self.assertEqual(rows.kwargs["filters"], expected)

    def test_page_and_size_reject_non_ascii_decimal_or_non_integer_values(self):
        invalid = (None, "", True, False, 1.0, 1.5, "1.0", "1e0", "+1", "-1", " 1", "1 ", "１", "١", {}, [], "9" * 5000)
        for method in (self.api.get_people, self.api.get_roles):
            for field in ("page", "page_size"):
                for value in invalid:
                    with self.subTest(method=method.__name__, field=field, value_type=type(value).__name__):
                        result = method(**{field: value})
                        self.assertEqual(result["error"]["code"], "INVALID_REQUEST")
        self.native.get_list.assert_not_called()

    def test_ascii_decimal_pagination_and_bounds_keep_native_permissions(self):
        for method in (self.api.get_people, self.api.get_roles):
            for page, size in ((1, 1), (10000, 50), ("0002", "10")):
                with self.subTest(method=method.__name__, page=page, size=size):
                    self.native.get_list.reset_mock()
                    self.native.get_list.side_effect = [[{"total": 0}], []]
                    self.assertTrue(method(page=page, page_size=size)["ok"])
                    count, rows = self.native.get_list.call_args_list
                    self.assertEqual(rows.kwargs["limit_start"], (int(page) - 1) * int(size))
                    self.assertEqual(rows.kwargs["limit_page_length"], int(size))
                    self.assertEqual(count.kwargs["filters"], rows.kwargs["filters"])
                    self.assertNotIn("ignore_permissions", count.kwargs)
                    self.assertNotIn("ignore_permissions", rows.kwargs)
            self.native.get_list.reset_mock()
            for params in ({"page": 0}, {"page": 10001}, {"page_size": 0}, {"page_size": 51}):
                self.assertEqual(method(**params)["error"]["code"], "INVALID_REQUEST")
            self.native.get_list.assert_not_called()
