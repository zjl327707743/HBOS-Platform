#!/bin/sh
# Restores verified images and static mounts through all seven Compose files.
# It never restores business data, publication state, account state or tokens.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$HERE/../release_candidate.py" --task-root "${HBOS_KNOWLEDGE_TASK_ROOT:?set isolated task root}" --evidence-root "${HBOS_RC1_EVIDENCE_ROOT:?set private RC1 evidence root}" rollback "$@"
