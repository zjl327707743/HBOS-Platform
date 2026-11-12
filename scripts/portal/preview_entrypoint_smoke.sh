#!/usr/bin/env bash
# CI-only probe; never starts a Site, connects to a business database, or uses secrets.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${CI:-}" == true ]] || {
  echo 'This disposable entrypoint probe is restricted to GitHub Actions.' >&2
  exit 2
}
[[ "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ && "${GITHUB_RUN_ATTEMPT:-}" =~ ^[0-9]+$ ]] || exit 2
IMAGE='frappe/erpnext:v16.26.2'
PREFIX="hbos-ci-entrypoint-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
LABEL='hbos.preview.entrypoint.probe'
BENCH='/home/frappe/frappe-bench'
TMP="$(mktemp -d)"
CREATED=()

cleanup() {
  local vol owned
  for vol in "${CREATED[@]}"; do
    owned="$(docker volume inspect -f "{{ index .Labels \"$LABEL\" }}" "$vol" 2>/dev/null || true)"
    if [[ "$owned" == "$PREFIX" ]]; then
      docker volume rm "$vol" >/dev/null || true
    fi
  done
  rm -rf -- "$TMP"
}
trap cleanup EXIT

command -v docker >/dev/null
docker pull "$IMAGE"
docker image inspect "$IMAGE" --format 'Image ID={{.Id}}; Digests={{json .RepoDigests}}; Entrypoint={{json .Config.Entrypoint}}'

for suffix in sites logs assets nested; do
  vol="${PREFIX}-${suffix}"
  if docker volume inspect "$vol" >/dev/null 2>&1; then
    echo "Refusing to reuse existing volume: $vol" >&2
    exit 1
  fi
  docker volume create --label "$LABEL=$PREFIX" "$vol" >/dev/null
  CREATED+=("$vol")
done

# Regression control: preserve the image's real entrypoint. A nested mount must
# reproduce the documented EBUSY failure, not a fabricated shell implementation.
set +e
timeout 120 docker run --rm --network none \
  --label "$LABEL=$PREFIX" \
  --mount "type=volume,source=${PREFIX}-sites,target=${BENCH}/sites" \
  --mount "type=volume,source=${PREFIX}-logs,target=${BENCH}/logs" \
  --mount "type=volume,source=${PREFIX}-assets,target=${BENCH}/assets" \
  --mount "type=volume,source=${PREFIX}-nested,target=${BENCH}/sites/assets" \
  "$IMAGE" bash -ec 'echo UNEXPECTED_NESTED_MOUNT_SUCCESS' >"$TMP/negative.log" 2>&1
NEGATIVE_RC=$?
set -e
cat "$TMP/negative.log"
if [[ "$NEGATIVE_RC" == 0 || "$NEGATIVE_RC" == 124 ]]; then
  echo 'The negative control did not reproduce the expected entrypoint failure.' >&2
  exit 1
fi
grep -q 'Device or resource busy' "$TMP/negative.log"

# Positive control: only the normal named sites/logs/bench-assets volumes exist.
# No entrypoint override is allowed: the real image must create a valid symlink.
timeout 120 docker run --rm --network none \
  --label "$LABEL=$PREFIX" \
  --mount "type=volume,source=${PREFIX}-sites,target=${BENCH}/sites" \
  --mount "type=volume,source=${PREFIX}-logs,target=${BENCH}/logs" \
  --mount "type=volume,source=${PREFIX}-assets,target=${BENCH}/assets" \
  "$IMAGE" bash -ec '
    test -L /home/frappe/frappe-bench/sites/assets
    test -d /home/frappe/frappe-bench/sites/assets
    actual="$(readlink -f /home/frappe/frappe-bench/sites/assets)"
    test "$actual" = /home/frappe/frappe-bench/assets
    printf "Real entrypoint PASS: sites/assets -> %s\n" "$actual"
  '
printf 'Preview entrypoint probe PASS; no Site, database or user records were created.\n'
