# SDD ledger — plan: docs/superpowers/plans/2026-09-22-我的待办身份绑定实施计划.md

Setup: branch `m2-r8`, clean baseline at `f757dd5`; backend `342 passed`, frontend sidebar test passed, production build passed with only the pre-existing Vite chunk-size warning.

Setup Ruling: execute in the current clean feature checkout instead of creating a linked worktree — Docker Compose bind-mounts this checkout, so a separate worktree would not exercise the implementation during Frappe runtime verification — cost if wrong: less filesystem isolation from unrelated user work, mitigated by a clean dedicated feature branch and per-task commits.

Pre-flight Task 1 → Task 2: `TodoRule`, identity, ownership, dedupe and ordering helpers are consumed by the service; names and approved API fields align.

Pre-flight Task 2 → Task 3: the service collector registry is extended by stability providers; response shape and permission policy remain shared and align.

Pre-flight Tasks 2/3 → Task 4: retention, summary cache and report scope consume the same identity and candidate schema; the interfaces align.

Pre-flight Tasks 2/4 → Task 5: backend API uses `source_doctype`, `assigned_to_me`, `overdue`, `filtered_summary` and `generated_at`; frontend types consume the same names.

Pre-flight Task 5 → Task 6: the page and sidebar consume the todo store summary/list lifecycle; interfaces align.

Pre-flight Tasks 5/6 → Task 7: route parameters and direct actions consume `TodoItem.route_params`, `module`, `action` and `execute_mode`; interfaces align.

Pre-flight Tasks 1–7 → Task 8: final performance, runtime and UI verification cover the same approved contracts; interfaces align.

Pre-flight Ruling: replace planned AST/source-text assertions with executable behavior tests wherever possible — `writing-good-tests.md` forbids source-grep tests because they do not prove behavior; Frappe boundaries will use a faithful test double plus pure-policy tests, while true Frappe behavior remains in Task 8 runtime verification — cost if wrong: the test double could diverge from Frappe, mitigated by real-site verification.

Pre-flight Ruling: `removeResolved` is never called before the source API succeeds; after success the canonical list is refreshed — this reconciles Task 5 wording with Task 7's no-optimistic-removal safety rule — cost if wrong: a brief extra stale row while refresh is in flight, never a false success.

Task 1 Ruling: rule identity is `(module, status, condition)` rather than only `(module, status)` — stability `检测中/已完成` and disposal `待执行` select mutually exclusive actions from record context; the spec requires one action per record, not one action per status string — cost if wrong: providers could select an incorrect branch, covered by explicit condition tests.
Task 1: complete (commits f757dd5..73b3631, tests: bash -lc 'cd apps/hb_lims_app && python3 -m pytest tests -q' → 357 passed in 0.26s)
Task 2: complete (commits 963bb35 + follow-up, tests: `python3 -m pytest tests/test_todo_service_contract.py -q` → 6 passed; `python3 -m pytest -q` → 363 passed in 0.24s)
Task 3: complete (commit pending, tests: `python3 -m pytest tests/test_todo_contract.py tests/test_todo_service_contract.py tests/test_stability_r8b_contract.py tests/test_stability_r8c_contract.py tests/test_stability_r8j_contract.py -q` → 134 passed; `python3 -m pytest -q` → 368 passed in 0.27s)
Task 4: complete (commit pending, tests: `python3 -m pytest tests/test_todo_service_contract.py tests/test_todo_report_scope_contract.py -q` → 22 passed; `python3 -m pytest -q` → 379 passed in 0.35s)
Task 5: complete (commit pending, tests: `npm run test:unit` → 6 passed; `npm run build` → passed with existing large-chunk warning)
