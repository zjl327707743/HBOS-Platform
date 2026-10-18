"""Audit one pushed PR43 source commit; never compose or change product sources.

Python 3.12 standard library only. Use ``select`` for checkout outputs, then
``verify --source <checkout> --evidence <outside-directory>`` with fetch-depth 2.
The four negative controls change only in-memory source readers/functions.
This is source-only evidence: NOT_PRODUCT_COMPOSITION; native NOT_RUN.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


SOURCE_SHA = "1a8f49251dc818859336ee70fbf81dcef87c0bfd"
SOURCE_TREE = "19487ad99534a9dc1bbc03b1e60dca0e0e361514"
SOURCE_PARENT = "e6d3f6c785850007a6ab68e7092810b0e323f6fa"
LIMS = "apps/hb_lims_app/"
BUSINESS_FILES = (
    LIMS + "hb_lims_app/hbos_lims/doctype/hbos_retention_disposal_apply/hbos_retention_disposal_apply.py",
    LIMS + "hb_lims_app/hbos_lims/doctype/hbos_retention_usage_apply/hbos_retention_usage_apply.py",
    LIMS + "hb_lims_app/hbos_lims/guards.py",
    LIMS + "hb_lims_app/hbos_lims/workflow_contract.py",
)
TEST_FILES = (
    LIMS + "tests/test_lims_guards_contract.py",
    LIMS + "tests/test_lims_retention_guard_contract.py",
)
EXPECTED_TESTS = 39


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def git(source, *args):
    return subprocess.check_output(
        ["git", "-C", str(source), *args], text=True,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"},
    ).strip()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class StripDocstrings(ast.NodeTransformer):
    def strip(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            value = node.body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                node.body.pop(0)
        return node

    visit_Module = strip
    visit_ClassDef = strip
    visit_FunctionDef = strip
    visit_AsyncFunctionDef = strip


def executable_ast(source):
    return ast.dump(StripDocstrings().visit(ast.parse(source)), include_attributes=False)


def authority(source):
    require(Path(git(source, "rev-parse", "--show-toplevel")).resolve() == source,
            "--source must be the root of its own checkout")
    require(not git(source, "status", "--porcelain", "--untracked-files=all"),
            "Source checkout must be clean, including untracked files")
    actual = {
        "sha": git(source, "rev-parse", "HEAD"),
        "tree": git(source, "rev-parse", "HEAD^{tree}"),
        # Reading the object header also works at a shallow boundary; the parent
        # object itself must still be fetched for the content comparison below.
        "parents": [line.split(" ", 1)[1] for line in
                    git(source, "cat-file", "-p", "HEAD").split("\n\n", 1)[0].splitlines()
                    if line.startswith("parent ")],
    }
    require(actual == {"sha": SOURCE_SHA, "tree": SOURCE_TREE, "parents": [SOURCE_PARENT]},
            "Wrong PR43 source commit, tree or parent: " + json.dumps(actual))
    git(source, "cat-file", "-e", SOURCE_PARENT + "^{commit}")
    changes = git(source, "diff", "--name-status", "--no-renames", SOURCE_PARENT, SOURCE_SHA)
    expected = sorted("M\t" + path for path in (*BUSINESS_FILES, *TEST_FILES))
    require(sorted(changes.splitlines()) == expected, "Changes must be exactly the six reviewed files")
    invariants = []
    for relative in BUSINESS_FILES:
        before = git(source, "show", SOURCE_PARENT + ":" + relative)
        after = (source / relative).read_text(encoding="utf-8")
        before_ast, after_ast = executable_ast(before), executable_ast(after)
        require(before_ast == after_ast, relative + ": executable AST changed")
        invariants.append({"path": relative, "status": "EXECUTABLE_AST_IDENTICAL",
                           "ast_sha256": hashlib.sha256(after_ast.encode()).hexdigest()})
    return {**actual, "changes": changes.splitlines(), "executable_ast": invariants}


def load_test(source, relative):
    path = source / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    require(Path(module.wf.__file__).resolve().is_relative_to(source),
            "Contract imported workflow authority from a different checkout")
    return module


def counts(result):
    return {
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }


def run_case(case, log):
    with log.open("w", encoding="utf-8") as stream:
        return unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite([case]))


def negative_controls(tests, retention, evidence, controls):
    source_fn = tests._source

    def detected(label, result, reads=1):
        metrics = counts(result)
        require(reads > 0 and result.testsRun == 1 and result.failures
                and not any(metrics[key] for key in (
                    "errors", "skipped", "expected_failures", "unexpected_successes")),
                label + ": regression was not detected by a real assertion failure")
        controls.append({"control": label, "detected": True, **metrics,
                         "in_memory_only": True, "log": label + ".log"})
        print("[OWNER-R3] lims-negative=" + json.dumps(controls[-1]))

    def reject_source_change(label, case, path, old, new):
        # Validate mutation anchors outside unittest: a missing anchor must not
        # masquerade as the assertion failure expected from a broken guard.
        original = source_fn(path)
        require(original.count(old) == 1, label + ": source anchor is not unique")
        mutated = original.replace(old, new, 1)
        reads = 0

        def source_override(requested):
            nonlocal reads
            if requested == path:
                reads += 1
                return mutated
            return source_fn(requested)

        with patch.object(tests, "_source", side_effect=source_override):
            result = run_case(case, evidence / (label + ".log"))
        detected(label, result, reads)

    reject_source_change(
        "remove_usage_validate_guard",
        tests.TestSystemFieldRegistry("test_registry_matches_controller_guard_calls"),
        tests.DOCTYPES / "hbos_retention_usage_apply/hbos_retention_usage_apply.py",
        "guard_system_fields(self, wf.HBOS_RETENTION_USAGE_SYSTEM_FIELDS)", "pass",
    )
    reject_source_change(
        "silently_add_retention_to_break_glass",
        tests.TestSystemFieldRegistry("test_registry_covers_both_boards"),
        tests.GUARDS, "SYSTEM_FIELD_SETS = {",
        'SYSTEM_FIELD_SETS = {\n\t"HBOS Retention Usage Apply": wf.HBOS_RETENTION_USAGE_SYSTEM_FIELDS,',
    )
    reject_source_change(
        "shared_guard_returns_without_rejecting_field_changes",
        tests.TestSystemFieldRegistry("test_registry_matches_controller_guard_calls"),
        tests.STABILITY_GUARDS,
        '\tbefore = doc.get_doc_before_save()\n\tif doc.flags.get("allow_system_fields"):',
        '\treturn\n\tbefore = doc.get_doc_before_save()\n\tif doc.flags.get("allow_system_fields"):',
    )
    allowed = retention.wf.action_allowed

    def unapproved_business_write(action, role, scope=None):
        if action == "approve_result" and role == "System Manager":
            return True
        return allowed(action, role, scope=scope)

    label = "grant_system_manager_quality_approval"
    with patch.object(retention.wf, "action_allowed", side_effect=unapproved_business_write):
        result = run_case(retention.TestSystemManagerGovernance(
            "test_system_manager_is_denied_business_writes_except_explicit_break_glass"),
            evidence / (label + ".log"))
    detected(label, result)
    require(len(controls) == 4, "All four negative controls are required")
    return controls


def verify(source, evidence):
    require(source.is_dir(), "Missing source checkout")
    require(not evidence.is_relative_to(source), "Audit artifacts must be outside the source checkout")
    evidence.mkdir(parents=True, exist_ok=True)
    audit = {
        "schema": 1, "repository": "zjl327707743/HBOS-Platform", "pr": 43,
        "status": "RUNNING", "scope": "source-only",
        "product_composition": "NOT_PRODUCT_COMPOSITION", "native": "NOT_RUN",
        "source_modifications": "NONE", "remote_writes": "NONE",
        "expected": {"sha": SOURCE_SHA, "tree": SOURCE_TREE, "parent": SOURCE_PARENT},
        "python": sys.version, "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "runner_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    exit_code = 1
    try:
        audit["authority"] = authority(source)
        # No source pyc/cache files, including during test-module imports.
        sys.dont_write_bytecode = True
        modules = [load_test(source, relative) for relative in TEST_FILES]
        loader = unittest.TestLoader()
        suite = unittest.TestSuite(loader.loadTestsFromModule(module) for module in modules)
        audit["discovered_tests"] = suite.countTestCases()
        log = evidence / "contract-39.log"
        with log.open("w", encoding="utf-8") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        audit["contracts"] = counts(result)
        print(log.read_text(encoding="utf-8"), end="")
        require(audit["discovered_tests"] == result.testsRun == EXPECTED_TESTS,
                "Expected exactly 39 discovered and executed contract tests")
        require(result.wasSuccessful() and not result.skipped and not result.expectedFailures,
                "All 39 contracts must pass with zero skips or expected failures")
        audit["negative_controls"] = []
        negative_controls(*modules, evidence, audit["negative_controls"])
        audit["guarded_validate_entries"] = len(modules[0]._controller_guard_calls())
        audit["break_glass_entries"] = len(modules[0]._registry_source_map())
        require(authority(source) == audit["authority"], "Source changed during audit")
        audit["status"] = "PASS"
        exit_code = 0
    except Exception as error:
        audit["status"] = "FAIL"
        audit["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        write_json(evidence / "audit.json", audit)
        print("[OWNER-R3] lims-source-contracts=" + json.dumps(audit, ensure_ascii=False))
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("select", "verify"))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--evidence", type=Path, default=Path("/tmp/owner-r3/lims-contracts"))
    args = parser.parse_args()
    if args.action == "select":
        print("source_sha=" + SOURCE_SHA)
        print("source_tree=" + SOURCE_TREE)
        print("source_parent=" + SOURCE_PARENT)
        return 0
    if args.source is None:
        parser.error("verify requires --source pointing to a separate source checkout")
    return verify(args.source.resolve(), args.evidence.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
