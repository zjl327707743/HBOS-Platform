#!/bin/sh
# Controlled source. The task's generated launcher supplies its private paths.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$HERE/../release_candidate.py" --task-root "${HBOS_KNOWLEDGE_TASK_ROOT:?set isolated task root}" --evidence-root "${HBOS_RC1_EVIDENCE_ROOT:?set private RC1 evidence root}" apply --cycle "${HBOS_RELEASE_CYCLE:-RC1}" "$@"
