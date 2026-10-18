#!/usr/bin/env bash
# Fresh report-only native Site: no state inherited from account lifecycle tests.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${CI:-}" == true ]] || {
  echo 'This native report probe is restricted to disposable GitHub Actions runners.' >&2
  exit 2
}
[[ "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ && "${GITHUB_RUN_ATTEMPT:-}" =~ ^[0-9]+$ ]] || exit 2
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
[[ ! -e .env ]] || { echo 'Refusing a worktree with an existing .env' >&2; exit 2; }
test -d runtime/apps/hrms
# Record exact files actually checked out on this attempt. No credentials or
# config contents are printed; compare these IDs with the PR merge checkout.
printf '[REPORT-SCOPE] checkout=%s\n' "$(git rev-parse HEAD)"
for source in scripts/ci/attendance_report_scope_smoke.sh \
  apps/hb_attendance_app/hb_attendance_app/hbos_attendance/report_scope_runtime_checks.py \
  apps/hb_attendance_app/hb_attendance_app/hbos_attendance/report_scope.py; do
  printf '[REPORT-SCOPE] blob=%s path=%s\n' "$(git hash-object "$source")" "$source"
done
TEST_ID="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
PROJECT="hbos-platform-report-${TEST_ID}"
export COMPOSE_PROJECT_NAME="$PROJECT"
export SITE_NAME="report-scope-${TEST_ID}.localhost"
export FRAPPE_SITE_NAME_HEADER="$SITE_NAME"
export HTTP_PORT=18090
export ERPNEXT_VERSION='v16.26.2@sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583'
export MARIADB_HOST=db DB_PORT=3306
export DB_ROOT_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export MYSQL_ROOT_PASSWORD="$DB_ROOT_PASSWORD"
export ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export REDIS_CACHE=redis-cache:6379 REDIS_QUEUE=redis-queue:6379 SOCKETIO_PORT=9000
export UPSTREAM_REAL_IP_ADDRESS=127.0.0.1 UPSTREAM_REAL_IP_HEADER=X-Forwarded-For
export UPSTREAM_REAL_IP_RECURSIVE=off PROXY_READ_TIMEOUT=120 CLIENT_MAX_BODY_SIZE=50m
export HBOS_FEISHU_SYNC_ENABLED=0 HBOS_DELICLOUD_SYNC_ENABLED=0 HBOS_AI_ENABLED=0 HBOS_AI_ALLOW_PII=0
export HBOS_NOTIFY_DRY_RUN=1 HBOS_AI_TIMEOUT=60
for name in FEISHU_APP_ID FEISHU_APP_SECRET HBOS_FEISHU_LEAVE_APP_TOKEN HBOS_FEISHU_LEAVE_TABLE_ID \
  HBOS_FEISHU_OVERTIME_APP_TOKEN HBOS_FEISHU_OVERTIME_TABLE_ID HBOS_FEISHU_REST_LEAVE_APP_TOKEN \
  HBOS_FEISHU_REST_LEAVE_TABLE_ID HBOS_FEISHU_EXCEPTION_APP_TOKEN HBOS_FEISHU_EXCEPTION_TABLE_ID \
  DELICLOUD_APP_KEY DELICLOUD_APP_SECRET HBOS_NOTIFY_WEBHOOK_URL HBOS_AI_BASE_URL \
  HBOS_AI_API_KEY HBOS_AI_MODEL HBOS_OCR_SHARED_TOKEN; do
  export "$name="
done
export HBOS_OCR_URL=http://127.0.0.1:9
command -v docker >/dev/null

dc() { docker compose --env-file .env.example -p "$PROJECT" "$@"; }
# Refuse existing resources BEFORE installing a destructive cleanup trap.
for kind in container volume network; do
  flags=(-q)
  [[ "$kind" != container ]] || flags+=(-a)
  if [[ -n "$(docker "$kind" ls "${flags[@]}" --filter "label=com.docker.compose.project=$PROJECT")" ]]; then
    echo "Refusing to reuse existing CI $kind resources" >&2
    exit 2
  fi
done
CONFIG="$(mktemp)"
chmod 600 "$CONFIG"
trap 'rm -f -- "$CONFIG"' EXIT
dc config --format json > "$CONFIG"
python3 - "$CONFIG" "$PROJECT" <<'PY'
import json
import sys
config = json.load(open(sys.argv[1], encoding="utf-8"))
project = sys.argv[2]
assert config["name"] == project, "Wrong project"
volumes = config.get("volumes", {})
for key, volume in volumes.items():
    assert volume.get("name") == f"{project}_{key}", "Foreign named volume"
    assert not volume.get("external") and not volume.get("driver_opts"), "External storage refused"
for service in config["services"].values():
    for volume in service.get("volumes", []):
        if volume["type"] == "volume":
            assert volume.get("source") in volumes, "Anonymous or undeclared volume"
        assert volume.get("target") != "/home/frappe/frappe-bench/sites/assets", "Nested assets mount"
for volume in config["services"]["db"]["volumes"]:
    if volume.get("target") == "/var/lib/mysql":
        assert volume["type"] == "volume" and volume["source"] == "db-data", "Unsafe database mount"
PY
# Also refuse name collisions whose labels were removed or never set.
while IFS= read -r volume; do
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    echo 'Refusing a pre-existing resolved volume name' >&2
    exit 2
  fi
done < <(python3 -c 'import json,sys; print("\n".join(v["name"] for v in json.load(open(sys.argv[1]))["volumes"].values()))' "$CONFIG")
cleanup() {
  dc down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f -- "$CONFIG"
}
trap cleanup EXIT

# Use the same pinned sources, installation and migration as the platform gate,
# but not its synthetic account suites. Native User creation throttling remains
# completely unchanged; report fixtures start on their own empty Site.
dc up -d db redis-cache redis-queue
dc run --rm configurator
# Keep initialization failures separate from permission-test failures.
printf '[REPORT-SCOPE] phase=create-site\n'
if ! dc run --rm create-site; then
  printf '[REPORT-SCOPE] create-site failed; permission assertions NOT_RUN\n' >&2
  exit 1
fi
dc up -d backend
dc exec -T backend /home/frappe/frappe-bench/env/bin/pip install --only-binary=:all: --require-hashes \
  -r /home/frappe/frappe-bench/apps/hbos_portal/requirements.txt
for attempt in 1 2; do
  dc exec -T backend bench --site "$SITE_NAME" migrate
done
dc exec -T backend bench --site "$SITE_NAME" set-config hbos_portal_origin "http://$SITE_NAME:$HTTP_PORT"
dc exec -T backend bench --site "$SITE_NAME" set-config hbos_report_scope_ci "$TEST_ID"
dc restart backend
dc exec -T -e HBOS_EXPECTED_SITE="$SITE_NAME" backend /home/frappe/frappe-bench/env/bin/python - <<'PY'
import os
import time
from urllib.request import Request, urlopen
for attempt in range(60):
    try:
        request = Request("http://127.0.0.1:8000/api/method/ping", headers={"Host": os.environ["HBOS_EXPECTED_SITE"]})
        with urlopen(request, timeout=2) as response:
            if response.status == 200:
                break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("Native Frappe HTTP did not become ready")
PY
# Prove the container sees the same test source and approved non-secret marker
# before invoking bench. Never dump the environment, site_config or passwords.
EXPECTED_RUNTIME_BLOB="$(git hash-object apps/hb_attendance_app/hb_attendance_app/hbos_attendance/report_scope_runtime_checks.py)"
dc exec -T \
  -e GITHUB_ACTIONS=true -e HBOS_REPORT_SCOPE_TEST_ID="$TEST_ID" \
  -e HBOS_SCOPE_EXPECTED_BLOB="$EXPECTED_RUNTIME_BLOB" \
  backend /home/frappe/frappe-bench/env/bin/python - <<'PY_DIAGNOSTIC'
import hashlib
import json
import os
from pathlib import Path
path = Path("/home/frappe/frappe-bench/apps/hb_attendance_app/hb_attendance_app/hbos_attendance/report_scope_runtime_checks.py")
source = path.read_bytes()
actual = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
expected = os.environ["HBOS_SCOPE_EXPECTED_BLOB"]
print("[REPORT-SCOPE] " + json.dumps({"phase": "pre-execute", "runtime_blob": actual,
      "matches_checkout": actual == expected,
      "github_actions_flag": os.environ.get("GITHUB_ACTIONS") == "true",
      "test_id_present": bool(os.environ.get("HBOS_REPORT_SCOPE_TEST_ID"))}))
if actual != expected:
    raise SystemExit("Refusing to test a container source different from the reviewed checkout")
PY_DIAGNOSTIC
printf '[REPORT-SCOPE] phase=permission-assertions\n'
dc exec -T \
  -e GITHUB_ACTIONS=true -e HBOS_REPORT_SCOPE_TEST_ID="$TEST_ID" \
  -e HBOS_FEISHU_SYNC_ENABLED=0 -e HBOS_DELICLOUD_SYNC_ENABLED=0 \
  -e HBOS_AI_ENABLED=0 -e HBOS_AI_ALLOW_PII=0 \
  backend bench --site "$SITE_NAME" execute \
  hb_attendance_app.hbos_attendance.report_scope_runtime_checks.run
printf 'HBOS native report scope runtime PASS; fresh ephemeral CI Site only.\n'
