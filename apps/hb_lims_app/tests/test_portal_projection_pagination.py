from __future__ import annotations

import datetime
import re
import sys
import types
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from hb_lims_app.hbos_lims.portal.coa import get_coa_projection
from hb_lims_app.hbos_lims.portal.retention import get_retention_projection
from hb_lims_app.hbos_lims.portal.specifications import get_specification_projection
from hb_lims_app.hbos_lims.portal.summary import get_summary_projection
from hb_lims_app.hbos_lims.portal.tasks import get_task_projection


class PermissionList:
    """Model the get_list contract: ACL and filters precede database pagination.

    This fake deliberately offers no get_all, SQL or db.count escape hatch.
    Hidden records exist in the backing data but never leave get_list.
    """

    def __init__(self, tables):
        self.tables = tables
        self.calls = []
        self.utils = types.SimpleNamespace(
            today=lambda: "2026-10-18",
            getdate=lambda value: datetime.date.fromisoformat(str(value)),
        )

    @staticmethod
    def _condition(row, condition):
        field, operator, expected = condition[-3:]
        actual = row.get(field)
        if operator == "=":
            return actual == expected
        if operator == "in":
            return actual in expected
        if operator == "like":
            expression = "".join(
                ".*" if char == "%" else "." if char == "_" else re.escape(char)
                for char in str(expected)
            )
            return bool(re.fullmatch(expression, str(actual or ""), re.IGNORECASE))
        raise AssertionError(f"Unexpected filter operator {operator!r}")

    @classmethod
    def _conditions(cls, filters):
        if isinstance(filters, dict):
            return [
                [field, *value] if isinstance(value, (list, tuple)) else [field, "=", value]
                for field, value in filters.items()
            ]
        return list(filters or [])

    def get_list(self, doctype, **query):
        self.calls.append((doctype, dict(query)))
        assert not query.get("ignore_permissions"), "Projection must retain native ACL"
        rows = [row for row in self.tables.get(doctype, []) if not row.get("hidden")]
        filters = self._conditions(query.get("filters"))
        alternatives = self._conditions(query.get("or_filters"))
        rows = [
            row for row in rows
            if all(self._condition(row, condition) for condition in filters)
            and (not alternatives or any(self._condition(row, condition) for condition in alternatives))
        ]
        for term in reversed(str(query.get("order_by") or "").split(",")):
            parts = term.strip().split()
            if parts:
                field = parts[0].strip("`").split(".")[-1]
                rows.sort(key=lambda row: str(row.get(field) or ""), reverse=parts[-1].lower() == "desc")
        offset = int(query.get("limit_start", 0))
        limit = int(query.get("limit_page_length", 20))
        assert 0 < limit <= 51, "Do not hide truncation by raising the native batch limit"
        rows = rows[offset:offset + limit]
        fields = query.get("fields") or ["name"]
        return [{field: row.get(field) for field in fields} for row in rows]

    def get_doc(self, doctype, name):
        raise AssertionError("An unauthorized detail must not reach get_doc")


def _document(index, **extra):
    return {
        "name": f"DOC-{index:04d}",
        "creation": "2026-10-18 08:00:00",
        "modified": "2026-10-18 08:00:00",
        "material_name": "Visible material",
        "report_status": "已审核",
        "status": "已生效",
        **extra,
    }


def _sample(index, **extra):
    return _document(
        index, retention_product=f"PRODUCT-{index:04d}",
        sample_name="Authorized sample", retention_date="2026-10-18",
        status="在库", current_qty=10, reserved_qty=2,
        observed_flag=0, retention_due_date="2027-10-18", **extra,
    )


def _product(index, **extra):
    return _document(
        index, name=f"PRODUCT-{index:04d}", product_name="Authorized product",
        product_code=f"ITEM-{index:04d}", is_active=1, **extra,
    )


@contextmanager
def _retention_context(database):
    service = types.ModuleType("hb_lims_app.hbos_lims.retention_service")
    service.get_observation_plan = lambda: {"rows": [], "completeness": []}
    service.list_usage_applies = lambda status=None: {"rows": [], "total": 0}
    service.list_disposal_applies = lambda status=None: {"rows": [], "total": 0}
    with patch.dict(sys.modules, {
        "frappe": database,
        "hb_lims_app.hbos_lims.retention_service": service,
    }):
        yield


def _todo(index, **extra):
    return {
        "todo_key": f"TASK-{index:04d}", "route": "/tasks", "route_params": {},
        "title": "Visible task", "description": "Authorized work", "source_name": f"TASK-{index:04d}",
        "action": "start_task", "status": "待检", "priority": "常规", **extra,
    }


class DomainTodos:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get_my_todos(self, *, limit=50, offset=0, status=None, priority=None, keyword=None):
        self.calls.append({"limit": limit, "offset": offset, "status": status, "priority": priority, "keyword": keyword})
        assert 0 < limit <= 200, "Domain response limit must not be increased"
        needle = str(keyword or "").strip().lower()
        rows = [
            row for row in self.rows if not row.get("hidden")
            and (not status or row.get("status") == status)
            and (not priority or row.get("priority") == priority)
            and (not needle or needle in " ".join(str(row.get(field) or "") for field in
                ("title", "description", "source_name", "action_label")).lower())
        ]
        return {"items": rows[offset:offset + limit], "total": len(rows)}


@contextmanager
def _todo_context(domain, coa=None):
    service = types.ModuleType("hb_lims_app.hbos_lims.todo_service")
    service.get_my_todos = domain.get_my_todos
    service.get_my_todo_summary = lambda: {"summary": {"overdue": 0}, "generated_at": "2026-10-18"}
    with patch.dict(sys.modules, {"hb_lims_app.hbos_lims.todo_service": service}), patch(
        "hb_lims_app.hbos_lims.portal.tasks.get_pending_coa_todos", return_value=coa or [],
    ), patch("hb_lims_app.hbos_lims.portal.summary._scope_label", return_value="检验范围"):
        yield


class PortalProjectionPaginationTest(unittest.TestCase):
    LISTS = (
        ("HBOS COA", get_coa_projection, "coas", "coa_id"),
        ("HBOS Specification", get_specification_projection, "specifications", "specification_id"),
    )

    def test_coa_and_specification_totals_at_50_51_52_ignore_hidden_rows(self):
        for doctype, projection, key, identifier in self.LISTS:
            for size in (50, 51, 52):
                with self.subTest(doctype=doctype, size=size):
                    database = PermissionList({doctype: [
                        *[_document(index) for index in range(size)],
                        _document(9999, hidden=True),
                    ]})
                    with patch.dict(sys.modules, {"frappe": database}):
                        payload = projection(limit=50)
                    self.assertEqual(size, payload["total"])
                    self.assertEqual(50, len(payload[key]))
                    self.assertNotIn("DOC-9999", [row[identifier] for row in payload[key]])
                    self.assertEqual("50" if size > 50 else None, payload["next_cursor"])

    def test_coa_and_specification_database_offset_reaches_last_two_with_stable_ties(self):
        for doctype, projection, key, identifier in self.LISTS:
            with self.subTest(doctype=doctype):
                database = PermissionList({doctype: [_document(index) for index in range(52)]})
                with patch.dict(sys.modules, {"frappe": database}):
                    first = projection(limit=50)
                    last = projection(limit=50, cursor="50")
                self.assertEqual(2, len(last[key]))
                self.assertEqual(52, last["total"])
                self.assertIsNone(last["next_cursor"])
                names = [row[identifier] for row in first[key] + last[key]]
                self.assertEqual(52, len(set(names)))
                page_queries = [query for _, query in database.calls if "material_name" in query["fields"]]
                self.assertTrue(any(query.get("limit_start") == 50 for query in page_queries))
                self.assertTrue(all("name" in query.get("order_by", "").split(",")[-1] for query in page_queries))

    def test_filtered_coa_and_specification_keywords_are_complete_and_normalized(self):
        for doctype, projection, key, _ in self.LISTS:
            with self.subTest(doctype=doctype):
                rows = [_document(index) for index in range(120)]
                rows += [_document(200 + index, material_name="Needle material") for index in range(52)]
                rows += [_document(9999, material_name="Needle material", hidden=True)]
                status = "已审核" if key == "coas" else "已生效"
                database = PermissionList({doctype: rows})
                with patch.dict(sys.modules, {"frappe": database}):
                    result = projection(keyword="  Needle  ", status=status, cursor="50")
                self.assertEqual(52, result["total"])
                self.assertEqual(2, len(result[key]))

    def test_hidden_coa_and_specification_details_do_not_reach_get_doc(self):
        for doctype, projection, key, identifier in self.LISTS:
            with self.subTest(doctype=doctype):
                database = PermissionList({doctype: [_document(1, hidden=True)]})
                with patch.dict(sys.modules, {"frappe": database}):
                    result = projection(**{identifier: "DOC-0001"})
                self.assertEqual([], result[key])
                self.assertIsNone(result["detail"])

    def test_coa_and_specification_keyword_wildcards_remain_literal(self):
        for doctype, projection, key, _ in self.LISTS:
            with self.subTest(doctype=doctype):
                database = PermissionList({doctype: [
                    _document(1, material_name="Batch_50%"),
                    _document(2, material_name="BatchX500"),
                ]})
                with patch.dict(sys.modules, {"frappe": database}):
                    payload = projection(keyword="_50%")
                self.assertEqual(1, payload["total"])
                self.assertEqual("Batch_50%", payload[key][0]["material_name"])

    def test_retention_sample_and_product_second_pages_and_totals(self):
        database = PermissionList({
            "HBOS Retention Sample": [_sample(index) for index in range(52)] + [_sample(9999, hidden=True)],
            "HBOS Retention Product": [_product(index) for index in range(52)] + [_product(9999, hidden=True)],
        })
        with _retention_context(database):
            payload = get_retention_projection(cursor="50")
        self.assertEqual(52, payload["samples_total"])
        self.assertEqual(52, payload["products_total"])
        self.assertEqual(2, len(payload["samples"]))
        self.assertEqual(2, len(payload["products"]))
        self.assertIsNone(payload["samples_next_cursor"])
        self.assertIsNone(payload["products_next_cursor"])
        for doctype in ("HBOS Retention Sample", "HBOS Retention Product"):
            self.assertTrue(any(name == doctype and query.get("limit_start") == 50 for name, query in database.calls))

    def test_retention_kpis_cover_all_authorized_filtered_samples(self):
        rows = [_sample(index) for index in range(103)]
        for row in rows[:52]:
            row.update(observed_flag=1, retention_due_date="2026-11-01")
        rows[0]["status"] = "已耗尽"
        hidden = _sample(9999, hidden=True)
        hidden.update(observed_flag=1, retention_due_date="2026-11-01")
        database = PermissionList({"HBOS Retention Sample": [*rows, hidden]})
        with _retention_context(database):
            payload = get_retention_projection(limit=1, status="在库")
        self.assertEqual(1, len(payload["samples"]))
        self.assertEqual(102, payload["samples_total"])
        self.assertEqual({"sample_total": 102, "in_stock": 102, "observed": 51, "near_due_30": 51}, {
            key: payload["summary"][key] for key in ("sample_total", "in_stock", "observed", "near_due_30")
        })

    def test_retention_product_name_search_handles_multiple_products_and_or_deduplication(self):
        first = _product(1)
        second = _product(2)
        concealed = _product(3, hidden=True)
        for row in (first, second, concealed):
            row["product_name"] = "Needle product"
        rows = [_sample(index) for index in range(52)]
        for index, row in enumerate(rows):
            row["retention_product"] = "PRODUCT-0001" if index % 2 else "PRODUCT-0002"
        rows[0]["sample_name"] = "Needle also matches sample"
        direct = _sample(100)
        direct.update(sample_name="Needle direct sample", retention_product="PRODUCT-0003")
        only_hidden_product = _sample(101)
        only_hidden_product["retention_product"] = "PRODUCT-0003"
        hidden_sample = _sample(9999, hidden=True)
        hidden_sample["retention_product"] = "PRODUCT-0001"
        database = PermissionList({
            "HBOS Retention Sample": [*rows, direct, only_hidden_product, hidden_sample],
            "HBOS Retention Product": [first, second, concealed],
        })
        with _retention_context(database):
            first_page = get_retention_projection(keyword="  Needle  ")
            last_page = get_retention_projection(keyword="  Needle  ", cursor="50")
        self.assertEqual(53, first_page["samples_total"])
        self.assertEqual(3, len(last_page["samples"]))
        combined = first_page["samples"] + last_page["samples"]
        self.assertEqual(53, len({row["name"] for row in combined}))
        self.assertNotIn("DOC-0101", {row["name"] for row in combined})
        self.assertEqual("", next(row["product_name"] for row in combined if row["name"] == "DOC-0100"))

    def test_retention_product_keyword_lookup_itself_reads_beyond_50(self):
        products = [_product(index) for index in range(52)]
        for row in products:
            row["product_name"] = "Needle product"
        database = PermissionList({
            "HBOS Retention Sample": [_sample(index) for index in range(52)],
            "HBOS Retention Product": products,
        })
        with _retention_context(database):
            payload = get_retention_projection(keyword="Needle", active="启用", cursor="50")
        self.assertEqual(52, payload["samples_total"])
        self.assertEqual(52, payload["products_total"])
        self.assertEqual(2, len(payload["products"]))
        self.assertEqual(2, len(payload["samples"]))

    def test_retention_literal_wildcards_do_not_expand_product_or_sample_matches(self):
        products = [_product(1), _product(2)]
        products[0]["product_name"] = "Batch_50%"
        products[1]["product_name"] = "BatchX500"
        rows = [_sample(1), _sample(2), _sample(3), _sample(4)]
        rows[2]["sample_name"] = "Batch_50%"
        rows[3]["sample_name"] = "BatchX500"
        database = PermissionList({"HBOS Retention Sample": rows, "HBOS Retention Product": products})
        with _retention_context(database):
            payload = get_retention_projection(keyword="_50%")
        self.assertEqual(2, payload["samples_total"])
        self.assertEqual({"DOC-0001", "DOC-0003"}, {row["name"] for row in payload["samples"]})
        self.assertEqual(1, payload["products_total"])

    def test_tasks_total_and_tail_at_200_201_use_domain_offsets(self):
        for count in (200, 201):
            with self.subTest(count=count):
                domain = DomainTodos([*[_todo(index) for index in range(count)], _todo(9999, hidden=True)])
                with _todo_context(domain):
                    payload = get_task_projection(limit=50, cursor="200")
                self.assertEqual(count, payload["total"])
                self.assertEqual(count - 200, len(payload["tasks"]))
                self.assertIsNone(payload["next_cursor"])
                if count == 201:
                    self.assertIn(200, [call["offset"] for call in domain.calls])
                    self.assertEqual("lims:TASK-0200", payload["tasks"][0]["task_id"])

    def test_tasks_sparse_view_in_second_domain_page_is_reachable(self):
        domain = DomainTodos([
            *[_todo(index) for index in range(200)],
            _todo(200, action="review_result", status="已提交"),
            _todo(9999, action="review_result", hidden=True),
        ])
        with _todo_context(domain):
            payload = get_task_projection(view="my-review")
        self.assertEqual(1, payload["total"])
        self.assertEqual("lims:TASK-0200", payload["tasks"][0]["task_id"])

    def test_tasks_filtered_total_includes_second_page_and_appended_coa_once(self):
        matches = [_todo(index, title="Needle", priority="高", status="已审核") for index in range(201)]
        matches += [_todo(9999, title="Needle", priority="高", status="已审核", hidden=True)]
        domain = DomainTodos(matches + [_todo(3000)])
        coa = _todo(5000, action="publish_coa", title="Needle COA", priority="高", status="已审核")
        with _todo_context(domain, [coa]):
            payload = get_task_projection(limit=50, cursor="200", keyword="Needle", priority="high", status="已审核")
        self.assertEqual(202, payload["total"])
        self.assertEqual({"lims:TASK-0200", "lims:TASK-5000"}, {row["task_id"] for row in payload["tasks"]})
        self.assertTrue(all(call["priority"] == "高" and call["keyword"] == "Needle" for call in domain.calls))

    def test_task_response_limit_stays_50_even_when_provider_called_directly(self):
        domain = DomainTodos([_todo(index) for index in range(201)])
        with _todo_context(domain):
            payload = get_task_projection(limit=999)
        self.assertEqual(50, len(payload["tasks"]))
        self.assertEqual("50", payload["next_cursor"])

    def test_summary_semantic_counts_include_second_domain_page_but_not_hidden_rows(self):
        domain = DomainTodos([
            *[_todo(index) for index in range(200)],
            _todo(200, action="review_result"),
            _todo(9999, action="review_result", hidden=True),
        ])
        with _todo_context(domain, [_todo(5000, action="publish_coa")]):
            payload = get_summary_projection()
        values = {metric["id"]: metric["value"] for metric in payload["metrics"]}
        self.assertEqual({"my_testing": 200, "in_testing": 0, "my_review": 1, "coa_publish": 1}, values)
        self.assertIn(200, [call["offset"] for call in domain.calls])

    def test_summary_review_kpi_is_201_when_all_visible_tasks_require_review(self):
        domain = DomainTodos([_todo(index, action="review_result") for index in range(201)])
        with _todo_context(domain):
            payload = get_summary_projection()
        self.assertEqual(201, next(metric["value"] for metric in payload["metrics"] if metric["id"] == "my_review"))


if __name__ == "__main__":
    unittest.main()
