#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/hbzl/Vibe Coding/HBOS-Platform"
APP_DIR="$PROJECT_DIR/apps/hb_lims_app"
WEB_DIR="$PROJECT_DIR/frontend/hbos-lims-web"
DIST_DIR="$WEB_DIR/dist"
REMOTE_DIR="/home/frappe/frappe-bench/sites/frontend/public/hbos-lims"
DOCKER="/Applications/Docker.app/Contents/Resources/bin/docker"

log()  { printf '\n[HBOS-LIMS] %s\n' "$1"; }
fail() { printf '\n[HBOS-LIMS][ERROR] %s\n' "$1" >&2; exit 1; }

cd "$PROJECT_DIR"

log "1/8 Preflight: repository check"
git diff --check

log "2/8 Preflight: backend contract tests"
(
  cd "$APP_DIR"
  python3 -m pytest tests
)

log "3/8 Build production frontend"
(
  cd "$WEB_DIR"
  npm run build:prod
)

log "4/8 Docker service status"
"$DOCKER" compose ps

log "5/8 Apply Frappe migration and clear cache"
"$DOCKER" compose exec -T backend bash -lc \
  'cd /home/frappe/frappe-bench && bench --site frontend migrate'
"$DOCKER" compose exec -T backend bash -lc \
  'cd /home/frappe/frappe-bench && bench --site frontend clear-cache'

log "6/8 Backup and sync frontend production assets"
FRONTEND_ID="$("$DOCKER" compose ps -q frontend)"
[ -n "$FRONTEND_ID" ] || fail "frontend container is not running"
STAMP="$(date +%Y%m%d%H%M%S)"
if "$DOCKER" exec "$FRONTEND_ID" test -d "$REMOTE_DIR"; then
  "$DOCKER" exec "$FRONTEND_ID" cp -a "$REMOTE_DIR" "$REMOTE_DIR.bak-$STAMP"
  printf 'Backup: %s\n' "$REMOTE_DIR.bak-$STAMP"
fi
"$DOCKER" exec "$FRONTEND_ID" mkdir -p "$REMOTE_DIR"
"$DOCKER" cp "$DIST_DIR/." "$FRONTEND_ID:$REMOTE_DIR/"

log "7/8 Restart application services"
"$DOCKER" compose restart backend frontend scheduler queue-short queue-long websocket

log "7b/8 Rebuild frontend container-local assets symlinks (lost on container recreation)"
FRONTEND_ID="$("$DOCKER" compose ps -q frontend)"
[ -n "$FRONTEND_ID" ] || fail "frontend container is not running"
"$DOCKER" exec "$FRONTEND_ID" sh -c \
  'cd /home/frappe/frappe-bench/assets && for a in hb_lims_app hb_attendance_app hrms; do rm -f "$a"; t="/home/frappe/frappe-bench/apps/$a/$a/public"; [ -d "$t" ] && ln -s "$t" "$a" && echo "linked $a"; done'

log "7c/8 Re-inject /hbos-lims nginx SPA fallback (lost on container recreation)"
"$DOCKER" exec -i "$FRONTEND_ID" python3 - <<'PY'
p = "/etc/nginx/conf.d/frappe.conf"
s = open(p).read()
if "^~ /hbos-lims/" not in s:
    block = "\n\tlocation ^~ /hbos-lims/ {\n\t\ttry_files /frontend/public$uri /frontend/public/hbos-lims/index.html =404;\n\t}\n"
    anchor = "\n\tlocation /socket.io {"
    assert anchor in s, "nginx anchor not found"
    open(p, "w").write(s.replace(anchor, block + anchor, 1))
    print("SPA fallback injected")
else:
    print("SPA fallback already present")
PY
"$DOCKER" exec "$FRONTEND_ID" sh -c 'nginx -t && nginx -s reload'

log "7d/8 Container-side runtime smoke (my-todos aggregate over a real Frappe session)"
# 离线契约用 FakeFrappe 桩，抓不到「不存在的 Frappe API」「子表 get_list 权限」这类
# 纯运行期问题；因此这里在容器内真连 Frappe 跑一次待办聚合的只读冒烟。
BACKEND_ID="$("$DOCKER" compose ps -q backend)"
[ -n "$BACKEND_ID" ] || fail "backend container is not running"
if ! "$DOCKER" exec "$BACKEND_ID" test -x /home/frappe/frappe-bench/env/bin/pytest; then
  fail "backend venv 缺少 pytest。请先执行：docker compose exec backend /home/frappe/frappe-bench/env/bin/pip install pytest"
fi
"$DOCKER" exec -e HBOS_FRAPPE_SMOKE=1 -e FRAPPE_SITE=frontend "$BACKEND_ID" bash -c \
  'cd /home/frappe/frappe-bench/sites && /home/frappe/frappe-bench/env/bin/python -m pytest \
     /home/frappe/frappe-bench/apps/hb_lims_app/tests/test_todo_runtime_smoke.py -q'

log "8/8 HTTP smoke checks"
sleep 8
for path in /hbos-lims/ /hbos-lims/dashboard /hbos-lims/samples /hbos-lims/audit /hbos-lims/audit-log \
  /hbos-lims/retention /hbos-lims/retention/samples /hbos-lims/retention/observations \
  /hbos-lims/stability /hbos-lims/stability/study /hbos-lims/stability/samples \
  /hbos-lims/stability/schedule /hbos-lims/stability/results /hbos-lims/stability/reports \
  /hbos-lims/stability/ops \
  /assets/hb_lims_app/hbos-lims-logo.svg /assets/hb_attendance_app/hbos-attendance-logo.svg; do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "http://localhost:8080$path")"
  printf '%-28s %s\n' "$path" "$code"
  [ "$code" = "200" ] || fail "HTTP check failed for $path (status $code)"
done

printf '\n[HBOS-LIMS] Deployment completed successfully.\n'
printf 'URL: http://localhost:8080/hbos-lims/dashboard\n'
