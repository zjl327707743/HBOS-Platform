"""跨进程运行锁 —— 定时与手动任务不能同时写结果表。

两个进程同时跑时，`writer` 的「先读后写」会让双方都认为某条工序不存在，
于是各建一行 —— 重复行就是这么来的。清理只能事后兜底，挡不住并发写入。
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from app import runlock


def test_second_acquire_in_other_process_fails(tmp_path):
    """另一个进程持锁时，本进程拿不到 —— 抛 LockBusy。"""
    lock_path = tmp_path / "ai.lock"
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                f"""
                import sys, time
                sys.path.insert(0, {str(_pkg_root())!r})
                from app import runlock
                with runlock.run_lock({str(lock_path)!r}):
                    print("held", flush=True)
                    time.sleep(3)
                """
            ),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        with pytest.raises(runlock.LockBusy):
            with runlock.run_lock(lock_path):
                pass
    finally:
        holder.kill()
        holder.wait(timeout=5)


def test_lock_released_after_exit(tmp_path):
    lock_path = tmp_path / "ai.lock"
    with runlock.run_lock(lock_path):
        pass
    # 释放后应能再次获得
    with runlock.run_lock(lock_path):
        pass


def test_lock_released_on_exception(tmp_path):
    lock_path = tmp_path / "ai.lock"
    with pytest.raises(RuntimeError):
        with runlock.run_lock(lock_path):
            raise RuntimeError("boom")
    with runlock.run_lock(lock_path):
        pass


def _pkg_root():
    from pathlib import Path

    return Path(__file__).parents[1]


def test_non_contention_oserror_is_not_reported_as_busy(tmp_path, monkeypatch):
    """EIO / ENOLCK 这类真实故障不能被伪装成「有人正在跑，本轮跳过」。

    早先 `except OSError` 一律转 `LockBusy`，调度系统会把系统故障当成功。
    """
    import errno

    from app import runlock

    def boom(fd, op):
        raise OSError(errno.EIO, "I/O error")

    monkeypatch.setattr(runlock.fcntl, "flock", boom)
    with pytest.raises(OSError) as exc:
        with runlock.run_lock(tmp_path / "x.lock"):
            pass
    assert not isinstance(exc.value, runlock.LockBusy)
    assert exc.value.errno == errno.EIO


def test_contention_errno_is_lock_busy(tmp_path, monkeypatch):
    import errno

    from app import runlock

    def busy(fd, op):
        raise OSError(errno.EAGAIN, "locked")

    monkeypatch.setattr(runlock.fcntl, "flock", busy)
    with pytest.raises(runlock.LockBusy):
        with runlock.run_lock(tmp_path / "x.lock"):
            pass
