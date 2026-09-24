#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Rebuild the HBOS LIMS production bundle and refresh the shared custom-app
# asset links. Force recreation is intentional: bind-mounted source changes
# do not alter Compose service configuration, so an already-completed one-shot
# container would otherwise keep an older bundle after git pull.
docker compose up --force-recreate --no-deps hbos-web-prepare
