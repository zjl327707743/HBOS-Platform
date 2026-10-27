# RC13 maintenance controller templates (host-only, private)

Versioned, secret-free templates for the host-side maintenance controller that
drains the batch import queue. This directory intentionally contains **no real
credentials, host paths, tenant ids or dataset ids**: the private config is
materialized at deploy time (outside the repository) from these templates plus
environment variables.

## Files

| File | Meaning |
| --- | --- |
| `controller.json` | Template for the private controller config consumed by `python -m knowledge_service.maintenance_controller <private-config.json>`. Every `${VAR}` is expanded by `load_controller_config()`; a missing variable fails startup and names only the variable. |
| `worker.json` | Documentation-only contract of the native worker scope file the controller writes (`<private_work>/worker-scope-<job_id>.json`) and the environment passed to the native parser. It is not read as a controller config. |
| `README.md` | This deployment note. |

## Materializing the private config (Main/deploy step)

1. Copy `controller.json` to a private path outside the repository (mode `0600`),
   e.g. `<private-root>/controller.json`.
2. Fill every `${...}` reference at runtime: either export the referenced
   variables in the controller's service environment (the controller performs
   the expansion itself) or materialize a resolved JSON in the private path and
   pass that file to the controller. Scalar values and `python_paths` list
   entries support `${ENV_VAR}`.
3. Run the controller as a host process (not in the candidate web container):

   ```
   PYTHONPATH=<app + service checkout paths> \
   python -m knowledge_service.maintenance_controller <private-root>/controller.json
   ```

   `--once` processes at most one job (operational smoke use); the default mode
   is continuous consumption with bounded idle backoff.
4. Verify the liveness file: `<private_work>/controller-heartbeat.json` exists,
   is mode `0600`, and carries `schema = rc13-controller-heartbeat-v1`.

## Required configuration keys

`authority_url`, `gateway_config`, `native_budget_config`, `model_egress_config`
(recommended), `ragflow_auth`, `embedding_model`, `private_work`,
`registered_worker_record`, `native_worker_log`, `native_source`,
`native_python`, `native_env_file`, `python_paths`. Optional:
`native_project_base`, `native_deploy_base`, `nltk_data`, `native_library_path`,
`heartbeat_path`, `heartbeat_interval` (5..300 s), `idle_backoff_start`,
`idle_backoff_max`, `idle_backoff_factor`, `max_job_seconds` (default 1500, bounded
300..14400; raise only for the reviewed >64MiB controlled local derivative path).

`private_work` must be a directory the controller host owns (mode `0700`). It is
**also the shared derivative root** (`maintenance_derivative_root` on the BFF
side): batch submit writes `<private_work>/<batch_id>/derivatives/<version>.txt`
before registering the batch, and the host controller reads that same path next
to its own `state.json`. Mount that directory read-write into the BFF container
and keep the host controller's `private_work` pointed at it; do not mount it into
any employee-facing service.

## Continuous consumption

`main()` claims one queued batch at a time (lock file prevents two controllers
on the same host), drains all groups, and immediately claims the next batch.
When no batch is queued it backs off exponentially from `idle_backoff_start` up
to `idle_backoff_max`; the counter resets after a processed job. `SIGTERM`/
`SIGINT` stops claiming, lets the in-flight native task settle (no `SIGKILL`),
reports the terminal outcome and exits. A maintainer pause is delivered through
the `progress` response (`pause_requested: true`); the controller stops the
worker at the next safe point and reports `Blocked / PAUSED_BY_MAINTAINER`, so
`resume_import` can requeue the same job without a restart.

## Lease / fence semantics

* `claim` increments `job_json.lease_generation`, sets a fresh nonce and a
  1800 s lease.
* `progress` must present the current `lease_generation` + nonce and an
  unexpired lease. Running progress renews the lease; a terminal report clears
  the nonce and only the current fence can terminate the batch.
* `claim` performs a **bounded** expired-lease sweep (at most 20 rows) before
  selecting work; `reclaim_import` does the same on demand. Only a `Running`
  batch whose own lease has expired is requeued, and only its `job_json`
  changes: item states are never bulk-reset. Each reclaim appends an audit entry
  (`actor_hash`, previous/new generation, previous lease, previous nonce hash).
* Migration note: jobs claimed before this release have no
  `lease_generation`; their `progress` keeps the legacy nonce+lease check until
  the next claim. A controller binary that still omits `lease_generation` is
  rejected with `IMPORT_BUSY` as soon as the first fenced claim happens, so the
  controller and the BFF must be deployed together.

## Heartbeat

The controller writes `<heartbeat_path>` atomically (tmp + `os.replace`, mode
`0600`) on every state change and every `heartbeat_interval` seconds from a
daemon thread (so a long native parse never looks dead). Schema:

```json
{"schema":"rc13-controller-heartbeat-v1","version":1,"pid":123,
 "started_at_utc":"...","at_utc":"...","state":"idle|working|stopping|stopped",
 "current":{"batch_id":"IMP_...","job_id":"JOB_...","lease_generation":3},
 "idle_seconds":2.0,"interval_seconds":15}
```

Only the host reads this file; it is never served to the browser. A stale
heartbeat is an operator signal, not an authorization: takeover requires the
BFF-side expired-lease reclaim, which is the only operation that moves the
fence.

## Safety constraints

* Host-only: no image layers, compose files or public endpoints in this
  directory. Real values are injected at deploy time and stay in private paths.
* The controller is not a scheduler: it never starts a parse from a clock or
  retry; only a maintainer-registered, queued batch with `document_ids` is
  executed (at most four documents per job).
* `HBOS_MODEL_EGRESS_REQUIRED=1` stays enforced by the service image; the
  controller imports `model_egress` before starting a worker and refuses to run
  without the startup guard.
* The native worker environment is still `MAX_CONCURRENT_TASKS=1` and
  `MAX_CONCURRENT_CHUNK_BUILDERS=1`; a second registered worker pid blocks a new
  spawn.
