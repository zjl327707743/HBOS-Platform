"""运行态：跨进程锁（真起两个进程抢同一把锁）。

单测里 `runlock` 只是被调用；这里真的起一个子进程持锁，
验证「定时任务与手动任务撞车时，后来者立刻跳过而不是各建一行」。
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest


def _pkg_root() -> Path:
    return Path(__file__).parents[1]


def _spawn_holder(lock_path: Path) -> subprocess.Popen:
    script = textwrap.dedent(
        f"""
        import sys, time
        sys.path.insert(0, {str(_pkg_root())!r})
        from app import runlock
        with runlock.run_lock({str(lock_path)!r}):
            print("held", flush=True)
            time.sleep(10)
        """
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    line = proc.stdout.readline().strip()
    assert line == "held", line
    return proc


def test_second_process_skips_when_lock_held(tmp_path):
    """另一个进程持锁期间，本进程的 `run_lock` 必须立刻失败（不是等 10 秒）。"""
    from app import runlock

    lock_path = tmp_path / "ai.lock"
    holder = _spawn_holder(lock_path)
    try:
        started = time.time()
        with pytest.raises(runlock.LockBusy):
            with runlock.run_lock(lock_path):
                pass
        elapsed = time.time() - started
        assert elapsed < 2, f"抢锁等了 {elapsed:.1f}s，应当立刻返回"
    finally:
        holder.kill()
        holder.wait(timeout=5)


def test_lock_is_reacquirable_after_holder_exits(tmp_path):
    """持锁进程退出后，锁必须释放（flock 随进程消失）。"""
    from app import runlock

    lock_path = tmp_path / "ai.lock"
    holder = _spawn_holder(lock_path)
    holder.kill()
    holder.wait(timeout=5)

    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            with runlock.run_lock(lock_path):
                return
        except runlock.LockBusy:
            time.sleep(0.1)
    pytest.fail("持锁进程退出后锁仍未释放")
