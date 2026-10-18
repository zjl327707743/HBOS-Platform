"""Native inventory QR/card/private-file audit on the R3 report-only Site.

This runner is never whitelisted. It uses synthetic report fixtures, native
Users/User Permissions/DocShare, real login/CSRF and loopback HTTP. It does not
post stock or run on the separate inventory transaction Site. Permission code,
File methods and HTTP authentication are never replaced or monkeypatched.

Pinned upstream paths exercised: Frappe v16.26.3 printview, private URLs,
handler.download_file, core.api.file.zip_files, client get/save/set_value/insert,
and run_doc_method. File.get_content itself is NOT a whitelisted RPC; content
checks use the actual download/zip callers and a separately labelled native
Python invocation. This suite makes no claim about every possible file API.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import re
import time
import zipfile
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

import frappe


GROUP = "R3QR-GROUP - CST"
WAREHOUSE_A = "R3QR-A - CST"
WAREHOUSE_B = "R3QR-B-HIDDEN - CST"
BATCH = "R3QR-BATCH-SYNTHETIC"
BATCH_B = "CLOUD-BATCH-B"
HIDDEN_MARKERS = (BATCH_B, "CLOUD-SUPPLIER-B")
CARD_FORMAT = "HBOS 自产货位卡"
REGENERATE = "hb_inventory_app.hbos_inventory.doc_gen.regenerate_for_batch"
IDENTITY_FIELDS = ("file_name", "file_url", "attached_to_doctype", "attached_to_name", "is_private")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


class NativeClient:
    """Keep the actual cookie jar; do not log credentials, tokens or raw bodies."""

    def __init__(self, origin):
        self.headers = {
            "Host": urlsplit(origin).netloc,
            "Origin": origin,
            "X-Requested-With": "XMLHttpRequest",
        }
        self.jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.jar), _NoRedirect())

    def request(self, path, params=None, *, post=False, timeout=120):
        encoded = urlencode(params or {}).encode()
        url = "http://127.0.0.1:8000" + path
        if encoded and not post:
            url += ("&" if "?" in url else "?") + encoded.decode()
        request = Request(url, data=encoded if post else None, headers=self.headers)
        try:
            response = self.opener.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            try:
                payload = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                payload = {}
            return {"http": response.code, "body": body, "json": payload,
                    "location": response.headers.get("Location", "")}

    def rpc(self, method, params=None, *, post=False, timeout=120):
        return self.request("/api/method/" + method, params, post=post, timeout=timeout)

    def login(self, user, password):
        response = self.rpc("login", {"usr": user, "pwd": password}, post=True)
        assert response["http"] == 200, "Native fixture login failed"
        response = self.rpc("hbos_portal.auth.accounts.get_request_security")
        token = response["json"].get("message", {}).get("csrf_token")
        assert response["http"] == 200 and token, "Native CSRF token was not issued"
        self.headers["X-Frappe-CSRF-Token"] = token
        response = self.rpc("frappe.auth.get_logged_user")
        assert response["http"] == 200 and response["json"].get("message") == user
        return self


class Audit:
    def __init__(self):
        self.checks = []

    def check(self, case, ok, **evidence):
        row = {"case": case, "ok": bool(ok), **evidence}
        self.checks.append(row)
        print("[OWNER-R3] inventory-permission=" + json.dumps(row, ensure_ascii=False))
        return bool(ok)

    def denied(self, case, response, *, rpc=False):
        body = response["body"]
        leaked = body.startswith(b"%PDF-") or any(marker.encode() in body for marker in HIDDEN_MARKERS)
        exception = response["json"].get("exc_type")
        return self.check(case, response["http"] == 403 and not leaked
                          and (not rpc or exception == "PermissionError"),
                          http=response["http"], exc_type=exception, leaked=leaked)


def _fresh_admin():
    # HTTP writes commit in another DB connection. End this runner's old read
    # snapshot before observing their effects; every fixture write commits first.
    frappe.db.rollback()
    frappe.set_user("Administrator")


def _scope(user, warehouse):
    doc = frappe.get_doc({
        "doctype": "User Permission", "user": user, "allow": "Warehouse",
        "for_value": warehouse, "apply_to_all_doctypes": 1, "hide_descendants": 1,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache(user=user)
    return doc.name


def _fixtures(legacy):
    """Only report inputs: no Stock Entry, reconciliation or Stock Ledger Entry."""
    assert frappe.db.exists("Company", "CLOUD-STOCK-COMPANY")
    assert frappe.db.exists("Batch", BATCH_B)
    assert all(not frappe.db.exists("Warehouse", name) for name in (GROUP, WAREHOUSE_A, WAREHOUSE_B))
    for name, group, left, right, parent in (
        (GROUP, 1, 100, 105, None),
        (WAREHOUSE_A, 0, 101, 102, GROUP),
        (WAREHOUSE_B, 0, 103, 104, GROUP),
    ):
        legacy.sql_fixture("Warehouse", {
            "name": name, "warehouse_name": name.split(" - ")[0],
            "company": "CLOUD-STOCK-COMPANY", "is_group": group, "disabled": 0,
            "lft": left, "rgt": right, "parent_warehouse": parent,
        })
    assert not frappe.db.exists("Batch", BATCH)
    legacy.sql_fixture("Batch", {
        "name": BATCH, "batch_id": BATCH, "item": "CLOUD-ITEM-A",
        "item_name": "SYNTHETIC CI INVENTORY CARD", "hbos_source_type": "自产",
        "expiry_date": frappe.utils.add_days(frappe.utils.today(), 10),
    })
    for suffix, warehouse, batch, item, qty in (
        ("A", WAREHOUSE_A, BATCH, "CLOUD-ITEM-A", 3),
        ("B", WAREHOUSE_B, BATCH, "CLOUD-ITEM-A", 7),
        ("B-ONLY", WAREHOUSE_B, BATCH_B, "CLOUD-ITEM-B", 2),
    ):
        bundle = "R3QR-BUNDLE-" + suffix
        legacy.sql_fixture("Serial and Batch Bundle", {
            "name": bundle, "docstatus": 1, "is_cancelled": 0, "is_rejected": 0,
            "item_code": item, "warehouse": warehouse,
        })
        legacy.sql_fixture("Serial and Batch Entry", {
            "name": "R3QR-ENTRY-" + suffix, "parent": bundle,
            "parenttype": "Serial and Batch Bundle", "parentfield": "entries", "idx": 1,
            "docstatus": 1, "item_code": item, "batch_no": batch,
            "warehouse": warehouse, "qty": qty, "is_cancelled": 0,
        })
    frappe.db.commit()


def _file_state(name):
    _fresh_admin()
    doc = frappe.get_doc("File", name)
    content = Path(doc.get_full_path()).read_bytes()
    return {**{field: doc.get(field) for field in IDENTITY_FIELDS},
            "content_sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def _download_checks(audit, client, file_doc, label, *, allowed=False, expected_hash=None):
    requests = (
        ("private_url", lambda: client.request(quote(file_doc.file_url, safe="/"))),
        ("private_url_fid", lambda: client.request(quote(file_doc.file_url, safe="/"), {"fid": file_doc.name})),
        ("download_file", lambda: client.rpc("download_file", {"file_url": file_doc.file_url})),
    )
    for name, call in requests:
        response = call()
        if allowed:
            digest = hashlib.sha256(response["body"]).hexdigest()
            audit.check(label + ":" + name,
                        response["http"] == 200 and response["body"].startswith(b"%PDF-")
                        and digest == expected_hash, http=response["http"], same_pdf=digest == expected_hash)
        else:
            audit.denied(label + ":" + name, response, rpc=name == "download_file")


def _pdf_fixture(audit, full_client):
    """Try the real regeneration path; any failure remains FAIL even with fallback."""
    response = full_client.rpc(REGENERATE, {"batch_name": BATCH}, post=True, timeout=180)
    output = response["json"].get("message")
    generated = response["http"] == 200 and isinstance(output, dict) and output.get("file")
    audit.check("regenerate_full_batch_native_post", generated,
                http=response["http"], exc_type=response["json"].get("exc_type"))
    _fresh_admin()
    if generated:
        file_doc = frappe.get_doc("File", output["file"])
        content = Path(file_doc.get_full_path()).read_bytes()
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        page_texts = [page.extract_text() or "" for page in reader.pages]
        extracted = " ".join(page_texts)
        # These documents contain only this disposable Site's synthetic fixtures.
        # Retain the actual PDF and bounded text evidence before any assertion;
        # a broken CMap must not turn into an unexplained missing-marker failure.
        evidence_dir = Path("/tmp/owner-r3-pdf-evidence")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "synthetic-report-card.pdf").write_bytes(content)
        pdf_evidence = {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                        "pages": [{"width": float(page.mediabox.width),
                                   "height": float(page.mediabox.height),
                                   "text_excerpt": text[:1500], "text_chars": len(text)}
                                  for page, text in zip(reader.pages, page_texts)]}
        (evidence_dir / "synthetic-report-card.json").write_text(
            json.dumps(pdf_evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[OWNER-R3] inventory-pdf-evidence=" + json.dumps(pdf_evidence, ensure_ascii=False))
        # ASCII synthetic warehouse markers survive font substitutions. They
        # prove this is a full-batch A+B snapshot, not an empty placeholder PDF.
        compact = re.sub(r"\s+", "", extracted)
        audit.check("generated_pdf_contains_a_and_b", content.startswith(b"%PDF-")
                    and "R3QR-A" in compact and "R3QR-B-HIDDEN" in compact,
                    pages=len(reader.pages), bytes=len(content),
                    a_present="R3QR-A" in compact, b_present="R3QR-B-HIDDEN" in compact)
    else:
        # Continue the access audit if business rendering fails. This is a real
        # synthetic PDF, explicitly labelled fallback; the failed positive
        # above keeps the whole suite FAIL. No successful regeneration is claimed.
        from frappe.utils.pdf import get_pdf
        from frappe.utils.file_manager import save_file

        content = get_pdf("<html><body><h1>SYNTHETIC CI INVENTORY CARD</h1>"
                          "<p>R3QR-A: 3</p><p>R3QR-B-HIDDEN: 7</p></body></html>")
        file_doc = save_file("HBOS-" + BATCH + "-待检证+货位卡.pdf", content,
                             "Batch", BATCH, is_private=1)
        frappe.db.commit()
        print("[OWNER-R3] inventory-pdf-fixture=standalone_wkhtmltopdf_fallback_after_failed_regeneration")
    audit.check("inventory_card_is_private_batch_attachment",
                bool(file_doc.is_private) and file_doc.file_url.startswith("/private/files/")
                and file_doc.attached_to_doctype == "Batch" and file_doc.attached_to_name == BATCH)
    return file_doc


def run():
    marker = os.environ.get("HBOS_REPORT_SCOPE_TEST_ID", "")
    assert os.environ.get("GITHUB_ACTIONS") == "true" and re.fullmatch(r"[0-9]+-[0-9]+", marker)
    assert os.environ.get("OWNER_AUDIT_DOMAIN") == "inventory-reports", "Never run on transaction Site"
    assert frappe.local.site == "report-scope-" + marker + ".localhost"
    assert str(frappe.conf.hbos_report_scope_ci) == marker
    assert os.environ.get("HBOS_FRAPPE_SMOKE") == "1"
    assert frappe.__version__ == "16.26.3"
    assert all(os.environ.get(key) == "0" for key in (
        "HBOS_AI_ENABLED", "HBOS_AI_ALLOW_PII", "HBOS_FEISHU_SYNC_ENABLED", "HBOS_DELICLOUD_SYNC_ENABLED"
    ))
    _fresh_admin()
    assert frappe.db.count("Stock Ledger Entry") == 0, "Report-only audit requires empty ledger"
    legacy = importlib.import_module("hbos_portal._owner_r3_legacy_runtime")
    _fixtures(legacy)
    audit = Audit()
    origin = str(frappe.conf.hbos_portal_origin)
    accounts = {
        "scoped": ("r3-qr-stock-a@example.invalid", ["Stock User", "Item Manager"]),
        "full": ("r3-card-full@example.invalid", ["Stock User", "Item Manager"]),
        "employee": ("r3-qr-employee@example.invalid", ["Employee"]),
        "reader": ("r3-card-readshare@example.invalid", ["Stock User"]),
    }
    clients = {}
    for key, (user, roles) in accounts.items():
        _fresh_admin()
        time.sleep(8)  # Native User creation throttling, including prior export user.
        password = legacy.make_user(user, roles)
        clients[key] = NativeClient(origin).login(user, password)
    scoped_user = accounts["scoped"][0]
    full_user = accounts["full"][0]
    reader_user = accounts["reader"][0]
    _fresh_admin()
    scope_name = _scope(scoped_user, WAREHOUSE_A)
    _scope(scoped_user, GROUP)  # hide_descendants=1: group itself, not implicit B grant.

    # Positive preconditions: scope denial must not be a missing Batch role or
    # broken session. Read-only DocShare must not grant Batch.write.
    for key in ("scoped", "full"):
        response = clients[key].rpc("frappe.client.get", {"doctype": "Batch", "name": BATCH})
        assert response["http"] == 200, key + " requires native Batch.read"
    response = clients["reader"].rpc("frappe.client.get", {"doctype": "Batch", "name": BATCH})
    audit.denied("pure_stock_user_native_batch_denied", response, rpc=True)
    _fresh_admin()
    frappe.share.add("Batch", BATCH, reader_user, read=1, write=0, share=0, notify=0)
    frappe.db.commit()
    frappe.clear_cache(user=reader_user)
    response = clients["reader"].rpc("frappe.client.get", {"doctype": "Batch", "name": BATCH})
    assert response["http"] == 200, "Actual read-only Batch DocShare must permit read"
    _fresh_admin()
    batch_doc = frappe.get_doc("Batch", BATCH)
    assert batch_doc.has_permission("write", user=full_user)
    assert batch_doc.has_permission("read", user=reader_user)
    assert not batch_doc.has_permission("write", user=reader_user)
    response = clients["scoped"].rpc("frappe.client.get_list", {
        "doctype": "Warehouse", "fields": json.dumps(["name"]), "limit_page_length": 200,
    })
    names = {row["name"] for row in response["json"].get("message", [])}
    assert response["http"] == 200 and WAREHOUSE_A in names and GROUP in names and WAREHOUSE_B not in names

    guest = NativeClient(origin)
    response = guest.request("/hbos_bin", {"bin": WAREHOUSE_A})
    audit.check("qr_guest_login_redirect", response["http"] in (301, 302, 303, 307, 308)
                and urlsplit(response["location"]).path == "/login"
                and "/hbos_bin" in unquote(response["location"])
                and BATCH.encode() not in response["body"], http=response["http"])
    audit.denied("qr_employee_denied", clients["employee"].request("/hbos_bin", {"bin": WAREHOUSE_A}))
    for label, code in (("a_full", WAREHOUSE_A), ("a_short", "R3QR-A"), ("group_intersection", GROUP)):
        response = clients["scoped"].request("/hbos_bin", {"bin": code})
        text = response["body"].decode("utf-8", errors="replace")
        audit.check("qr_" + label, response["http"] == 200 and BATCH in text and "R3QR-A" in text
                    and "R3QR-B-HIDDEN" not in text and not any(s in text for s in HIDDEN_MARKERS),
                    http=response["http"], a_present=BATCH in text,
                    hidden_b=any(s in text for s in (*HIDDEN_MARKERS, "R3QR-B-HIDDEN")))
    for label, code in (("b_full", WAREHOUSE_B), ("b_short", "R3QR-B-HIDDEN"), ("b_prefix", "R3QR-B")):
        audit.denied("qr_" + label, clients["scoped"].request("/hbos_bin", {"bin": code}))

    print_params = {"doctype": "Batch", "name": BATCH, "format": CARD_FORMAT, "no_letterhead": 1}
    audit.denied("native_printview_scoped_batch_reader_denied", clients["scoped"].request("/printview", print_params))
    for key in ("full", "reader"):
        response = clients[key].request("/printview", print_params)
        text = response["body"].decode("utf-8", errors="replace")
        audit.check("native_printview_" + key, response["http"] == 200
                    and "R3QR-A" in text and "R3QR-B-HIDDEN" in text, http=response["http"])
    _fresh_admin()
    initial_files = frappe.get_all("File", filters={"attached_to_doctype": "Batch", "attached_to_name": BATCH}, pluck="name")
    for key in ("scoped", "reader"):
        response = clients[key].rpc(REGENERATE, {"batch_name": BATCH}, post=True)
        audit.denied("regenerate_" + key + "_denied", response, rpc=True)
    audit.denied("regenerate_get_forbidden", clients["full"].rpc(REGENERATE, {"batch_name": BATCH}), rpc=True)
    _fresh_admin()
    audit.check("denied_regeneration_has_no_file_effect", initial_files == frappe.get_all(
        "File", filters={"attached_to_doctype": "Batch", "attached_to_name": BATCH}, pluck="name"))

    file_doc = _pdf_fixture(audit, clients["full"])
    original = _file_state(file_doc.name)
    response = clients["reader"].rpc("frappe.client.insert", {"doc": json.dumps({
        "doctype": "File", "file_name": file_doc.file_name, "file_url": file_doc.file_url,
        "is_private": 1, "attached_to_doctype": "Batch", "attached_to_name": BATCH,
    })}, post=True)
    audit.denied("native_card_file_insert_requires_batch_write", response, rpc=True)
    _fresh_admin()
    audit.check("readonly_share_inserted_no_card_alias", frappe.db.count(
        "File", {"file_url": file_doc.file_url}) == 1)
    _download_checks(audit, clients["full"], file_doc, "full", allowed=True, expected_hash=original["content_sha256"])
    _download_checks(audit, clients["scoped"], file_doc, "scoped")
    audit.denied("private_pdf_guest_denied", guest.request(quote(file_doc.file_url, safe="/")))

    # File ownership and explicit sharing are real fixtures that activate the
    # upstream shortcuts. They must not remove the warehouse boundary.
    _fresh_admin()
    frappe.db.set_value("File", file_doc.name, "owner", scoped_user, update_modified=False)
    frappe.db.commit()
    _download_checks(audit, clients["scoped"], file_doc, "scoped_file_owner")
    _fresh_admin()
    frappe.share.add("File", file_doc.name, scoped_user, read=1, write=1, share=1, notify=0)
    frappe.db.commit()
    frappe.clear_cache(user=scoped_user)
    _download_checks(audit, clients["scoped"], file_doc, "scoped_file_owner_and_share")
    audit.denied("native_file_get_owner_share_denied", clients["scoped"].rpc(
        "frappe.client.get", {"doctype": "File", "name": file_doc.name}), rpc=True)

    response = clients["scoped"].rpc("frappe.core.api.file.zip_files", {"files": json.dumps([file_doc.name])})
    audit.denied("native_zip_owner_share_denied", response, rpc=True)
    response = clients["full"].rpc("frappe.core.api.file.zip_files", {"files": json.dumps([file_doc.name])})
    zip_ok = False
    if response["http"] == 200 and zipfile.is_zipfile(io.BytesIO(response["body"])):
        with zipfile.ZipFile(io.BytesIO(response["body"])) as archive:
            zip_ok = len(archive.namelist()) == 1 and hashlib.sha256(
                archive.read(archive.namelist()[0])).hexdigest() == original["content_sha256"]
    audit.check("native_zip_full_same_pdf", zip_ok, http=response["http"])
    _fresh_admin()
    frappe.set_user(scoped_user)
    content_denied = False
    try:
        frappe.get_doc("File", file_doc.name).get_content()
    except frappe.PermissionError:
        content_denied = True
    finally:
        _fresh_admin()
    audit.check("native_python_file_get_content_owner_share_denied", content_denied, transport="native_python")
    # Probe the actual dispatcher without claiming get_content is a public API.
    for key in ("scoped", "full"):
        response = clients[key].rpc("run_doc_method", {"dt": "File", "dn": file_doc.name, "method": "get_content"}, post=True)
        audit.denied("unwhitelisted_get_content_rpc_" + key, response, rpc=True)

    mutations = {
        "rename_filename": {"file_name": "r3-innocent.pdf"},
        "change_url": {"file_url": "/private/files/r3-innocent.pdf"},
        "relink_to_item": {"attached_to_doctype": "Item", "attached_to_name": "CLOUD-ITEM-A"},
        "make_public": {"is_private": 0},
    }
    for key in ("scoped", "full"):
        for label, values in mutations.items():
            response = clients[key].rpc("frappe.client.set_value", {
                "doctype": "File", "name": file_doc.name, "fieldname": json.dumps(values),
            }, post=True)
            audit.denied("file_" + key + "_" + label, response, rpc=True)
            audit.check("file_unchanged_" + key + "_" + label, _file_state(file_doc.name) == original)
    _fresh_admin()
    payload = frappe.get_doc("File", file_doc.name).as_dict()
    payload.update({"file_name": "r3-disguised.pdf", "file_url": "/files/r3-disguised.pdf",
                    "attached_to_doctype": "Item", "attached_to_name": "CLOUD-ITEM-A", "is_private": 0})
    response = clients["scoped"].rpc("frappe.client.save", {"doc": frappe.as_json(payload)}, post=True)
    audit.denied("file_save_disguise_all_identity_fields", response, rpc=True)
    audit.check("file_unchanged_after_disguise_save", _file_state(file_doc.name) == original)
    for key in ("scoped", "full"):
        response = clients[key].rpc("frappe.client.insert", {"doc": json.dumps({
            "doctype": "File", "file_name": "r3-alias-" + key + ".pdf", "file_url": file_doc.file_url,
            "is_private": 1, "attached_to_doctype": "Item", "attached_to_name": "CLOUD-ITEM-A",
        })}, post=True)
        audit.denied("file_relink_existing_blob_" + key, response, rpc=True)
        _fresh_admin()
        audit.check("no_alias_file_" + key, not frappe.db.exists("File", {"file_name": "r3-alias-" + key + ".pdf"}))
    _download_checks(audit, clients["scoped"], file_doc, "after_identity_mutations")

    # A normal private Batch attachment retains ordinary native permissions.
    # This is not a claim about every LIMS COA or arbitrary historical filename.
    _fresh_admin()
    from frappe.utils.file_manager import save_file

    ordinary = save_file("R3-ordinary-private.txt", b"R3-ORDINARY-NATIVE-POSITIVE", "Batch", BATCH, is_private=1)
    frappe.db.commit()
    response = clients["scoped"].request(quote(ordinary.file_url, safe="/"))
    audit.check("ordinary_private_batch_attachment_still_readable", response["http"] == 200
                and response["body"] == b"R3-ORDINARY-NATIVE-POSITIVE", http=response["http"])
    audit.denied("ordinary_private_attachment_employee_denied", clients["employee"].request(quote(ordinary.file_url, safe="/")))

    # Change the native scope without removing all constraints (which would
    # mean unrestricted access). The same authenticated cookie must re-evaluate.
    _fresh_admin()
    permission = frappe.get_doc("User Permission", scope_name)
    permission.for_value = "CLOUD-WH-A"
    permission.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache(user=scoped_user)
    response = clients["scoped"].rpc("frappe.auth.get_logged_user")
    audit.check("scope_revocation_keeps_same_authenticated_cookie", response["http"] == 200
                and response["json"].get("message") == scoped_user, http=response["http"])
    audit.denied("qr_same_cookie_after_scope_revocation", clients["scoped"].request("/hbos_bin", {"bin": WAREHOUSE_A}))
    _fresh_admin()
    _scope(full_user, WAREHOUSE_A)
    response = clients["full"].rpc("frappe.auth.get_logged_user")
    audit.check("pdf_reader_revocation_keeps_same_authenticated_cookie", response["http"] == 200
                and response["json"].get("message") == full_user, http=response["http"])
    _download_checks(audit, clients["full"], file_doc, "full_reader_after_scope_restriction")
    _fresh_admin()
    audit.check("report_permission_audit_posted_no_stock", frappe.db.count("Stock Ledger Entry") == 0)
    failures = [row for row in audit.checks if not row["ok"]]
    result = {"ok": not failures, "checks": audit.checks, "failures": failures,
              "site_purpose": "report_fixtures_only", "stock_posting": "NOT_RUN",
              "coverage": "named QR/print/regenerate/private URL/download_file/zip/client/RPC paths only",
              "unclaimed": ["all possible file APIs", "historical files with both filename and URL already rewritten",
                            "complete LIMS COA permission matrix"]}
    print("[OWNER-R3] inventory-permission-summary=" + json.dumps({
        "checks": len(audit.checks), "failures": len(failures), "ok": result["ok"]}))
    assert not failures, "Native inventory permission failures: " + json.dumps(failures, ensure_ascii=False)
    return result
