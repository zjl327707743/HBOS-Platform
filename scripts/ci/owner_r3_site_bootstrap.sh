#!/usr/bin/env bash
# R3 disposable native Site; copied from the pinned R2 isolation bootstrap.
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
case "${OWNER_AUDIT_DOMAIN:-}" in
  attendance|production|inventory-reports|inventory-transactions|lims) ;;
  *) echo 'Unsupported R3 native domain' >&2; exit 2 ;;
esac
python3 - "$OWNER_AUDIT_DOMAIN" <<'PY_MANIFEST'
import json, subprocess, sys
from pathlib import Path
manifest = json.loads(Path('apps/hbos_portal/hbos_portal/_owner_r3_manifest.json').read_text())
domain = sys.argv[1]
assert domain in manifest['candidates'], 'Domain has no frozen source authority'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip() == manifest['candidates'][domain]['expected_tree'], 'Candidate tree changed'
assert subprocess.check_output(['git', '-C', 'runtime/apps/hrms', 'rev-parse', 'HEAD'], text=True).strip() == manifest['upstream']['hrms_sha'], 'HRMS source is not pinned'
PY_MANIFEST
# Record exact files actually checked out on this attempt. No credentials or
# config contents are printed; compare these IDs with the PR merge checkout.
printf '[REPORT-SCOPE] checkout=%s\n' "$(git rev-parse HEAD)"
TEST_ID="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
PROJECT="hbos-platform-r3-${OWNER_AUDIT_DOMAIN}-${TEST_ID}"
export COMPOSE_PROJECT_NAME="$PROJECT"
export SITE_NAME="report-scope-${TEST_ID}.localhost"
export FRAPPE_SITE_NAME_HEADER="$SITE_NAME"
export HTTP_PORT=18090
export ERPNEXT_VERSION='v16.26.2@sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583'
export MARIADB_HOST=db DB_PORT=3306
export DB_ROOT_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export MYSQL_ROOT_PASSWORD="$DB_ROOT_PASSWORD"
export ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export OWNER_AUDIT_ADMIN_PASSWORD="$ADMIN_PASSWORD"
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
  local status=$?
  trap - EXIT
  if [[ "$OWNER_AUDIT_DOMAIN" == inventory-* ]] && \
      dc exec -T backend test -d /tmp/owner-r3-pdf-evidence >/dev/null 2>&1; then
    # Only the audit's explicit synthetic PDFs/text; never copy the Site,
    # database, private-file directory, sessions or configuration.
    mkdir -p "/tmp/owner-r3/$OWNER_AUDIT_DOMAIN/pdf"
    if ! dc cp backend:/tmp/owner-r3-pdf-evidence/. "/tmp/owner-r3/$OWNER_AUDIT_DOMAIN/pdf"; then
      echo '[OWNER-R3] synthetic_pdf_evidence_copy=FAIL' >&2
      status=1
    fi
  fi
  if ! dc down -v --remove-orphans >/dev/null 2>&1; then
    echo '[OWNER-R3] cleanup=FAIL' >&2
    status=1
  fi
  for kind in container volume network; do
    flags=(-q)
    [[ "$kind" != container ]] || flags+=(-a)
    if [[ -n "$(docker "$kind" ls "${flags[@]}" --filter "label=com.docker.compose.project=$PROJECT")" ]]; then
      echo "[OWNER-R3] cleanup_remaining=$kind" >&2
      status=1
    fi
  done
  rm -f -- "$CONFIG"
  printf '[OWNER-R3] cleanup_exit=%s\n' "$status"
  exit "$status"
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
  printf '[OWNER-R3] migrate_attempt=%s\n' "$attempt"
  dc exec -T backend bench --site "$SITE_NAME" migrate
done
dc exec -T backend bench --site "$SITE_NAME" set-config hbos_portal_origin "http://$SITE_NAME:$HTTP_PORT"
dc exec -T backend bench --site "$SITE_NAME" set-config hbos_report_scope_ci "$TEST_ID"
if [[ "$OWNER_AUDIT_DOMAIN" == inventory-* || "$OWNER_AUDIT_DOMAIN" == lims ]]; then
  # Real inventory PDFs use Frappe's print CSS/assets. Serve them through this
  # disposable project's native frontend instead of an unreachable Site URL.
  dc up -d frontend
  dc exec -T backend bench --site "$SITE_NAME" set-config host_name http://frontend:8080
fi
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

if [[ "$OWNER_AUDIT_DOMAIN" == inventory-* || "$OWNER_AUDIT_DOMAIN" == lims ]]; then
  dc exec -T backend /home/frappe/frappe-bench/env/bin/python - <<'PY_PDF_ASSETS'
import json
from pathlib import Path
from urllib.request import urlopen

assets = json.loads(Path('sites/assets/assets.json').read_text())
print_css = assets['print.bundle.css']
assert print_css.startswith('/assets/')
for path in ('/api/method/ping', print_css):
    with urlopen('http://frontend:8080' + path, timeout=20) as response:
        content = response.read()
        assert response.status == 200 and content, 'Native PDF asset endpoint unavailable'
print('[OWNER-R3] native_pdf_asset_preflight=PASS')
PY_PDF_ASSETS
fi

dc exec -T backend /home/frappe/frappe-bench/env/bin/python -c 'import frappe,erpnext,hrms,json; print(json.dumps({"frappe":frappe.__version__,"erpnext":erpnext.__version__,"hrms":hrms.__version__}))' 
# Production services use an isolated Python environment in this disposable
# backend container. Do not install FastAPI dependencies into the Frappe env.
export OWNER_PRODUCTION_PYTHON=/tmp/owner-production-venv/bin/python
export OWNER_PRODUCTION_SERVICES=/tmp/owner-production-services
if [[ "$OWNER_AUDIT_DOMAIN" == production ]]; then
  test -f services/hbos_production/requirements.txt
  test -f services/hbos_production_ai/requirements.txt
  dc exec -T backend mkdir -p "$OWNER_PRODUCTION_SERVICES"
  dc cp services/hbos_production "backend:$OWNER_PRODUCTION_SERVICES/hbos_production"
  dc cp services/hbos_production_ai "backend:$OWNER_PRODUCTION_SERVICES/hbos_production_ai"
  dc exec -T backend /home/frappe/frappe-bench/env/bin/python -m venv /tmp/owner-production-venv
  dc exec -T backend "$OWNER_PRODUCTION_PYTHON" -m pip install \
    -r "$OWNER_PRODUCTION_SERVICES/hbos_production/requirements.txt" \
    -r "$OWNER_PRODUCTION_SERVICES/hbos_production_ai/requirements.txt"
fi

dc exec -T -e GITHUB_ACTIONS=true -e HBOS_REPORT_SCOPE_TEST_ID="$TEST_ID" \
  -e HBOS_FRAPPE_SMOKE=1 -e OWNER_AUDIT_DOMAIN="$OWNER_AUDIT_DOMAIN" \
  -e FRAPPE_SITE="$SITE_NAME" -e OWNER_AUDIT_ADMIN_PASSWORD \
  -e OWNER_PRODUCTION_PYTHON -e OWNER_PRODUCTION_SERVICES \
  backend bench --site "$SITE_NAME" execute hbos_portal._owner_r3_runtime.run

# Preserve the main probe's set -e failure and cleanup behavior. The old Todo
# test clears hb_lims_app imports, so run it only in a new bench process after
# the LIMS main probe succeeds, while this same disposable Site still exists.
if [[ "$OWNER_AUDIT_DOMAIN" == lims ]]; then
  printf '[OWNER-R3] phase=todo-native-independent-process\n'
  dc exec -T -e GITHUB_ACTIONS=true -e HBOS_REPORT_SCOPE_TEST_ID="$TEST_ID" \
    -e HBOS_FRAPPE_SMOKE=1 -e OWNER_AUDIT_DOMAIN=lims \
    -e FRAPPE_SITE="$SITE_NAME" -e OWNER_AUDIT_ADMIN_PASSWORD \
    backend bench --site "$SITE_NAME" execute hbos_portal._owner_r3_lims_runtime.todo_native_smoke
fi
