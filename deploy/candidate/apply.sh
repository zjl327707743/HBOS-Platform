#!/bin/sh
# Bring bff and service under the pinned composition, with preflight and rollback.
#
# The composition is the six-file stack plus the explicit override, so a swap
# cannot silently drop a mount or an environment variable again. The previous
# image ids are written to rollback.json before anything is recreated.
#
# The front-end bundle is switched only after the containers are recreated:
# public/portal is a bind mount into both nginx and bff, and writing a fresh
# build into it earlier served a new front-end against the old BFF.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
PY="$ROOT/work/knowledge_service/.venv-dsh/bin/python"
STAGED="$ROOT/work/build/frontend-staged"
PUBLIC="$ROOT/work/hbos/apps/hbos_portal/hbos_portal/public/portal"
PROJECT=$(python3 -c "import json;print(json.load(open('$HERE/manifest.json'))['project'])")

"$PY" "$HERE/preflight.py"

"$PY" - "$HERE" <<'PY'
import json, pathlib, subprocess, sys
here = pathlib.Path(sys.argv[1])
lock = json.loads((here/'DEPLOY_LOCK_CURRENT.json').read_text())
state = {}
for name in ('bff','service','frontend'):
    cid = f"{lock['project']}-{name}-1"
    got = subprocess.run(['docker','inspect',cid,'--format','{{.Image}}'],capture_output=True,text=True)
    state[name] = got.stdout.strip() if got.returncode == 0 else None
(here/'rollback.json').write_text(json.dumps(state, indent=1)+'\n')
print('rollback images recorded:', {k:(v or '')[:19] for k,v in state.items()})
PY

cd "$(python3 -c "import json,sys;print(json.load(open('$HERE/manifest.json'))['working_dir'])")"
set -- -p "$PROJECT"
for f in $(python3 -c "import json;[print(p) for p in json.load(open('$HERE/manifest.json'))['compose_files']]"); do
  set -- "$@" -f "$f"
done
docker compose "$@" up -d bff service
# nginx resolves its upstream once at startup. Recreating bff changes that
# address, so the proxy has to be restarted after the swap; leaving it alone is
# what produced a 502 while the BFF itself was already serving on 8000.
docker restart "$PROJECT-frontend-1" >/dev/null 2>&1 || true

# One rename, after the containers are the new ones. Skipped when the build
# produced no staged bundle (a bff/service-only change).
if [ -d "$STAGED" ]; then
  "$PY" "$HERE/install_static.py" --staged "$STAGED" --target "$PUBLIC"
else
  echo "no staged front-end bundle; keeping the running static files"
fi

echo "waiting for readiness (180s window after proxy restart)"
i=0
while [ $i -lt 36 ]; do
  if curl -s -o /dev/null -w '%{http_code}' http://knowledge-r2.localhost:18350/hbos/login 2>/dev/null | grep -q 200; then
    echo "READY: login 200 after $((i*5))s"
    exit 0
  fi
  i=$((i+1)); sleep 5
done
echo "NOT READY after 180s; restoring the previous static bundle and stopping for rollback.sh"
"$PY" "$HERE/install_static.py" --rollback --target "$PUBLIC" >/dev/null 2>&1 || true
exit 3
