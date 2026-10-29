# demo/knowledge-20261030 — UNMERGED_KNOWLEDGE_DEMO

Status: **UNMERGED_KNOWLEDGE_DEMO**. This branch does **not** inherit the product
branch, and the 2026-10-30 demonstration does not run it. It is cut from the
frozen stable knowledge source so the round has one named, source-pinned
reference; the running candidate was built before it existed.

| Fact | Value |
| --- | --- |
| Branch base | `a5ef507c9c151086cb4a9ece580c913138c6eeac` (`codex/knowledge-uat5`, PR #30 head before integration) |
| Running candidate | `rc1-bf21f3f81a8e99058a2c8abc` (cycle RC154), unchanged since 2026-10-28 20:58 +08:00 |
| Built from | `8a36b514d3f9d4f3186dd1b04bec8e111be7af5a` + runtime preview assets (see DEMO_BASELINE.lock.json) |
| Entry | http://knowledge-r2.localhost:18350/hbos/knowledge |
| Product branch | `feature/hbos-portal-product` @ `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b` — **not** an ancestor of this branch |
| PR #30 | still **open, Draft and unmerged**; the integrated candidate is `09debef7884a633e71d6e54558bef5484446ca32` |

## Why this branch is not "the demo build"

The images that will be shown run the code in the table above, which was built on
2026-10-28 and has been running since. Cutting a branch now cannot change what is
running, and pretending otherwise would misstate what the audience is seeing.

## What may be changed here before the demo

Only small, already-diagnosed fixes that block the demonstration: error wording,
waiting/failure states, a proven path error, a demo account's necessary
permission, restoring navigation state. The model, embedding, rerank and the
existing fact checks stay as they are. The 97 parsed-but-unpublished items stay
unpublished.

## What must not happen here

- No knowledge algorithm rewrite, no deployment rework, no model change.
- No new publishing batch, no re-parse, no index rebuild.
- No 96007f2 / `codex/knowledge-rc14-answer` content: it never deployed and H05
  regressed against it.

## Rollback

`work/deploy/candidate/release_candidate_rc154.py ... rollback` with the
`private/release154` evidence root restores the previous release
(`rc1-4fa950c59bf4b94f7eea0cb6b`) images. The frozen baseline for this round
(images, static build-id, asset manifest, preview hashes, database dump) is
`outputs/OWNER_LOCAL_ONLY/KNOWLEDGE_INTEGRATION_DEMO_20261029/DEMO_BASELINE.lock.json`.
