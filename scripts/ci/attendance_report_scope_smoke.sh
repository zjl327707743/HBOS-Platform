#!/usr/bin/env bash
# Extends the existing ephemeral platform smoke; never targets a local Site.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${CI:-}" == true ]] || {
  echo 'This native report probe is restricted to disposable GitHub Actions runners.' >&2
  exit 2
}
[[ "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ && "${GITHUB_RUN_ATTEMPT:-}" =~ ^[0-9]+$ ]] || exit 2
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
[[ ! -e .env ]] || { echo 'Refusing a worktree with an existing .env' >&2; exit 2; }
TEST_ID="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
export HBOS_SMOKE_PROJECT="hbos-platform-report-${TEST_ID}"
export SITE_NAME="report-scope-${TEST_ID}.localhost"
export HTTP_PORT=18090
export ERPNEXT_VERSION='v16.26.2@sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583'
command -v docker >/dev/null
# Refuse reused resources before the existing harness installs its cleanup trap.
for kind in container volume network; do
  flags=(-q)
  [[ "$kind" != container ]] || flags+=(-a)
  if [[ -n "$(docker "$kind" ls "${flags[@]}" --filter "label=com.docker.compose.project=$HBOS_SMOKE_PROJECT")" ]]; then
    echo "Refusing to reuse existing CI $kind resources" >&2
    exit 2
  fi
done

# Sourcing intentionally keeps the harness's EXIT cleanup trap and containers
# alive until THIS script exits. No change to its defaults or other workflows.
source scripts/ci/platform_clean_site_smoke.sh

[[ "$PROJECT" == "$HBOS_SMOKE_PROJECT" && "$SITE_NAME" == "report-scope-${TEST_ID}.localhost" ]] || exit 2
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" \
  set-config hbos_report_scope_ci "$TEST_ID"
docker compose -p "$PROJECT" exec -T \
  -e GITHUB_ACTIONS=true -e HBOS_REPORT_SCOPE_TEST_ID="$TEST_ID" \
  -e HBOS_FEISHU_SYNC_ENABLED=0 -e HBOS_DELICLOUD_SYNC_ENABLED=0 \
  -e HBOS_AI_ENABLED=0 -e HBOS_AI_ALLOW_PII=0 \
  backend bench --site "$SITE_NAME" execute \
  hb_attendance_app.hbos_attendance.report_scope_runtime_checks.run
printf 'HBOS native report scope runtime PASS; ephemeral CI only.\n'
