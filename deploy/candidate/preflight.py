"""Refuse a candidate swap that would drop something the running stack needs.

The 2026-10-20 outage happened because bff and service were recreated from a
trimmed file: the reference mount, the two budget mounts and the reference
config environment disappeared, both containers exited 78 and nginx lost its
upstream. This preflight resolves the seven-file composition, compares it with
what is actually running, and checks the things that fail late and loudly.

Every check is a refusal. There is no WARN path for anything that decides
whether the swap is safe: a changed compose file, or a rollback image that is
no longer on this machine, stops the swap instead of printing a note.

The authority is DEPLOY_LOCK_CURRENT.json (what the running candidate actually
is). DEPLOY_LOCK.json is an older snapshot kept for history; reading it was why
every deploy reported the override as "changed since the lock was taken" while
the override matched the current lock byte for byte.

  python3 work/deploy/candidate/preflight.py            # check only
  python3 work/deploy/candidate/preflight.py --lock path/to/lock.json
  python3 work/deploy/candidate/preflight.py --fault config-missing
  python3 work/deploy/candidate/preflight.py --fault mount-missing
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, subprocess, sys

HERE = pathlib.Path(os.environ.get('HBOS_DEPLOY_STATE_DIR') or pathlib.Path(__file__).resolve().parent)
DEFAULT_LOCK = HERE / 'DEPLOY_LOCK_CURRENT.json'
# The task root: <root>/work/deploy/candidate
ROOT = pathlib.Path(os.environ.get('HBOS_KNOWLEDGE_TASK_ROOT') or HERE.parents[2])
REQUIRED_ENV = {
    'bff': ('HBOS_KNOWLEDGE_REFERENCE_CONFIG', 'HBOS_MODEL_EGRESS_CONFIG', 'HBOS_MODEL_EGRESS_REQUIRED'),
    'service': ('HBOS_KNOWLEDGE_SERVICE_CONFIG', 'HBOS_MODEL_EGRESS_CONFIG', 'HBOS_MODEL_REGISTRY',
                'HBOS_KNOWLEDGE_NATIVE_BUDGET_CONFIG', 'HBOS_RECOVERY_PROVIDER_BUDGET'),
}
REQUIRED_TARGETS = {
    'bff': ('/run/hbos-reference', '/run/hbos-uat4-config', '/run/hbos-uat4-audit', '/run/hbos-budget',
            '/run/hbos-native-budget'),
    'service': ('/run/hbos-reference', '/run/hbos-uat4-config', '/run/hbos-uat4-audit', '/run/hbos-budget',
                '/run/hbos-native-budget'),
}


def fail(msg):
    print(f'REFUSE: {msg}')
    sys.exit(2)


def load_lock(path=None):
    path = pathlib.Path(path) if path else DEFAULT_LOCK
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        fail(f'deploy lock missing: {path}')
    except json.JSONDecodeError as error:
        fail(f'deploy lock is not valid JSON: {path} ({error.msg})')


def locked_files(lock):
    """The compose files the lock pins, as (resolved path, expected sha256)."""
    entries = (lock.get('composition') or {}).get('files') or []
    if not entries:
        fail('deploy lock lists no compose files')
    out = []
    for entry in entries:
        raw = pathlib.Path(entry.get('path') or '')
        resolved = raw if raw.is_absolute() else (ROOT / raw)
        expected = entry.get('sha256') or ''
        if not expected:
            fail(f'deploy lock has no sha256 for {resolved.name}')
        out.append((resolved, expected))
    return out


def compose_hash_problems(lock):
    """Every pinned compose file that is missing or no longer matches."""
    problems = []
    for path, expected in locked_files(lock):
        if not path.exists():
            problems.append(f'compose file missing: {path}')
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            problems.append(f'compose file changed since the deploy lock: {path.name} '
                            f'(locked {expected[:12]}, now {actual[:12]})')
    return problems


def rollback_image_problems(rollback_path, inspect=None):
    """Rollback image ids the lock promises but this machine no longer has.

    A recorded id that cannot be inspected is not a usable way back, so the
    swap is refused before anything is recreated rather than after a failed
    readiness check.
    """
    inspect = inspect or docker_image_id
    path = pathlib.Path(rollback_path)
    if not path.exists():
        return []
    try:
        recorded = json.loads(path.read_text())
    except json.JSONDecodeError:
        return [f'rollback record is not valid JSON: {path}']
    problems = []
    for name, image in sorted(recorded.items()):
        if not image:
            problems.append(f'rollback record has no image for {name}')
            continue
        if not inspect(image):
            problems.append(f'rollback image for {name} is not on this machine: {image[:19]} '
                            f'(tag the running image before deploying, or rebuild it)')
    return problems


def docker_image_id(reference):
    got = subprocess.run(['docker', 'image', 'inspect', reference, '--format', '{{.Id}}'],
                         capture_output=True, text=True)
    return got.returncode == 0 and bool(got.stdout.strip())


def compose(manifest, *args):
    cmd = ['docker', 'compose', '--project-directory', manifest['working_dir'], '-p', manifest['project']]
    for f in manifest['compose_files']:
        cmd += ['-f', f]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=manifest['working_dir'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fault', choices=('config-missing', 'mount-missing', 'env-missing'))
    ap.add_argument('--lock', help='deploy lock to verify against (default: DEPLOY_LOCK_CURRENT.json)')
    ap.add_argument('--rollback', help='rollback record to verify (default: rollback.json beside this script)')
    args = ap.parse_args()

    manifest = json.loads((HERE / 'manifest.json').read_text())
    lock = load_lock(args.lock)

    # 1. The seven pinned compose files are present and unchanged.
    problems = compose_hash_problems(lock)
    if problems:
        fail('; '.join(problems))

    # 2. Every rollback image the last apply recorded is still here.
    rollback = args.rollback or (HERE / 'rollback.json')
    problems = rollback_image_problems(rollback)
    if problems:
        fail('; '.join(problems))

    # 3. The composition resolves.
    r = compose(manifest, 'config')
    if r.returncode != 0:
        fail('compose config rejected: ' + (r.stderr.strip()[:200] or 'unknown error'))
    try:
        resolved = json.loads(subprocess.run(
            ['python3', '-c', 'import sys,yaml,json;print(json.dumps(yaml.safe_load(sys.stdin)))'],
            input=r.stdout, capture_output=True, text=True).stdout)
    except Exception:
        fail('could not parse resolved compose config')

    services = resolved.get('services') or {}
    fault = args.fault

    # 4. Required environment variables are declared for each service.
    for name, keys in REQUIRED_ENV.items():
        env = (services.get(name) or {}).get('environment') or {}
        missing = [k for k in keys if k not in env]
        if fault == 'env-missing' and name == 'bff':
            missing.append('HBOS_KNOWLEDGE_REFERENCE_CONFIG (fault injected)')
        if missing:
            fail(f'{name} is missing environment: {", ".join(missing)}')

    # 5. Required mount targets are present.
    for name, targets in REQUIRED_TARGETS.items():
        vols = (services.get(name) or {}).get('volumes') or []
        have = {v.get('target') for v in vols if isinstance(v, dict)}
        missing = [t for t in targets if t not in have]
        if fault == 'mount-missing' and name == 'service':
            missing.append('/run/hbos-reference (fault injected)')
        if missing:
            fail(f'{name} is missing mounts: {", ".join(missing)}')

    # 6. The mounted configuration files exist inside the image and parse as JSON.
    probe = compose(manifest, 'run', '--rm', '--no-deps', '-T', 'service', 'python', '-c',
                    'import json,os,sys;'
                    'pairs=[("HBOS_KNOWLEDGE_SERVICE_CONFIG",os.environ.get("HBOS_KNOWLEDGE_SERVICE_CONFIG")),'
                    '("HBOS_MODEL_REGISTRY",os.environ.get("HBOS_MODEL_REGISTRY")),'
                    '("HBOS_MODEL_EGRESS_CONFIG",os.environ.get("HBOS_MODEL_EGRESS_CONFIG"))];'
                    'bad=[n for n,p in pairs if not p or not os.path.isfile(p) or not json.load(open(p))];'
                    'print("MISSING:"+",".join(bad));sys.exit(2 if bad else 0)')
    if fault == 'config-missing':
        print('FAULT: config-missing injected -> refusing as if a mounted config were unreadable')
        fail('mounted config unreadable (fault injected)')
    if probe.returncode != 0:
        tail = (probe.stdout or '') + (probe.stderr or '')
        fail('mounted configuration unreadable: ' + tail.strip()[-200:])

    # 7. The audit volume is writable by the user that will run the service.
    audit = compose(manifest, 'run', '--rm', '--no-deps', '-T', 'service', 'python', '-c',
                    'import pathlib,sys;p=pathlib.Path("/run/hbos-uat4-audit");p.mkdir(parents=True,exist_ok=True);'
                    'f=p/".preflight";f.write_text("ok");f.unlink();print("writable")')
    if audit.returncode != 0 or 'writable' not in (audit.stdout or ''):
        fail('audit volume is not writable: ' + ((audit.stderr or '').strip()[-160:]))

    # 8. Report how the running containers compare with the lock (informational:
    #    the point of apply.sh is to move them, so a difference is expected).
    for name, entry in (lock.get('containers') or {}).items():
        got = subprocess.run(['docker', 'inspect', f'{manifest["project"]}-{name}-1', '--format', '{{.Image}}'],
                             capture_output=True, text=True)
        if got.returncode == 0 and entry.get('image_id') and got.stdout.strip() != entry['image_id']:
            print(f'NOTE: running {name} differs from the lock; recording the new id after switching')

    print('PREFLIGHT OK: seven-file composition pinned and unchanged, rollback images present, '
          'env and mounts complete, configs readable, audit writable')


if __name__ == '__main__':
    main()
