"""Swap the running candidate's static bundle in one rename, after the swap.

`sites/.../public/portal` is a bind mount into both nginx and bff. Writing a
fresh build straight into it left the candidate serving a new frontend against
the old BFF for however long the recreate took - the "new front-end + old BFF"
window from the 2026-10-20 incident. The build now stages its output elsewhere
and this script performs the switch only once the containers are recreated.

The previous bundle is kept beside the mount as ``portal.previous`` so a failed
readiness check can put it back without a rebuild.

  install_static.py --staged work/build/frontend-staged --target <portal dir>
  install_static.py --rollback --target <portal dir>
"""
from __future__ import annotations
import argparse, os, pathlib, shutil, sys, tempfile


def refuse(msg):
    print(f'REFUSE: {msg}')
    sys.exit(2)


def staged_ok(staged):
    """A staged bundle is only usable if it looks like one this project built."""
    index = staged / 'index.html'
    if not index.is_file():
        return f'staged bundle has no index.html: {staged}'
    html = index.read_text(errors='replace')
    if '/assets/hbos_portal/portal/assets/' not in html:
        return 'staged index.html does not reference /assets/hbos_portal/portal/assets/'
    if not (staged / 'assets').is_dir():
        return 'staged bundle has no assets directory'
    return None


def atomic_swap(staged, target):
    """Replace `target` with `staged`, keeping the old one as `target.previous`.

    rename(2) within one filesystem is atomic, so no request can observe a
    half-copied bundle. The target's parent must be the staging filesystem;
    both live under the task root.
    """
    previous = target.with_name(target.name + '.previous')
    if previous.exists():
        shutil.rmtree(previous)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.rename(previous)
    staged.rename(target)


def restore(target):
    previous = target.with_name(target.name + '.previous')
    if not previous.exists():
        refuse(f'no previous bundle to restore beside {target}')
    if target.exists():
        shutil.rmtree(target)
    previous.rename(target)
    print(f'restored previous bundle at {target}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--staged', help='bundle produced by the build, e.g. work/build/frontend-staged')
    ap.add_argument('--target', required=True, help='live mount, e.g. work/hbos/apps/hbos_portal/hbos_portal/public/portal')
    ap.add_argument('--rollback', action='store_true', help='put the previous bundle back')
    args = ap.parse_args()

    target = pathlib.Path(args.target).resolve()
    if args.rollback:
        restore(target)
        return
    if not args.staged:
        refuse('--staged is required unless --rollback is given')

    staged = pathlib.Path(args.staged).resolve()
    if not staged.is_dir():
        refuse(f'staged bundle directory missing: {staged}')
    problem = staged_ok(staged)
    if problem:
        refuse(problem)
    if staged.stat().st_dev != target.parent.resolve().stat().st_dev:
        # rename across filesystems fails, and a copy is not atomic.
        refuse(f'staged bundle and live mount are on different filesystems: {staged} -> {target.parent}')

    atomic_swap(staged, target)
    print(f'switched static bundle: {target} (previous kept as {target.name}.previous)')


if __name__ == '__main__':
    main()
