#!/bin/sh
# Return bff/service to the image ids recorded by the last apply.sh.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
RB="$HERE/rollback.json"
[ -f "$RB" ] || { echo "no rollback.json; nothing to return to"; exit 1; }
python3 - "$RB" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
for name,image in d.items():
    if not image: continue
    print(f'{name}={image}')
PY
echo "Restore manually with: docker run --name <container> <image> ... (mounts from the override)"
echo "Rollback is deliberately manual: an automated re-create from a stale image id is what caused the outage."
