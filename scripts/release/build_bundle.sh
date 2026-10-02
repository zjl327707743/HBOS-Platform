#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT="${1:-$ROOT/.release}"
mkdir -p "$OUTPUT"
OUTPUT="$(cd "$OUTPUT" && pwd)"
STAGE="$(mktemp -d "$OUTPUT/hbos-stage.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
cd "$ROOT/frontend/hbos-portal-web"
npm ci --no-audit --no-fund
VITE_PORTAL_DATA_MODE=frappe VITE_BASE=/assets/hbos_portal/portal/ VITE_FRAPPE_BASE_URL='' VITE_FRAPPE_APP_ORIGIN='' npm run build
cd "$ROOT/frontend/hbos-lims-web"
npm ci --no-audit --no-fund
npm run build:prod
cd "$ROOT"
python3 scripts/release/package_bundle.py "$STAGE" "$OUTPUT/hbos-portal-release.tar.gz"
python3 scripts/release/validate_bundle.py "$OUTPUT/hbos-portal-release.tar.gz" --source-commit "$(git rev-parse HEAD)"
python3 - "$OUTPUT/hbos-portal-release.tar.gz" <<'PY'
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]); print('bundle',p); print('sha256',hashlib.sha256(p.read_bytes()).hexdigest())
PY
