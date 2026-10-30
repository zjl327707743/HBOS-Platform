"""跨进程运行锁 —— 定时任务与手动任务不能同时写同一张结果表。

## 为什么需要

`writer.write_results()` 是「先读全表 → 再决定 create/update」。两个进程
同时跑时，双方都可能读到「这条工序还不存在」，于是各自 create 一条 ——
**重复行就此产生**。清理重复行只能事后兜底，挡不住正在发生的并发写入。

## 为什么用 flock

launchd 与本机手动运行通常同用户、同机执行，`fcntl.flock` 跨进程有效，
进程退出时自动释放（不会像自己实现的锁文件那样留下死锁）。

拿不到锁时**直接退出**而不是等待 —— 定时任务和手动任务撞车时，
让后来者跳过这一轮比排队跑两遍更安全（跑两遍会重复调模型，很贵）。
"""

from __future__ import annotations

import errno
import fcntl
import logging
import os
from contextlib import contextmanager
from pathlib import Path

log = logging.getLogger("hbos_production_ai.runlock")

DEFAULT_LOCK_PATH = Path(os.environ.get("HBOS_AI_LOCK_PATH", "/tmp/hbos_production_ai.lock"))


class LockBusy(RuntimeError):
    """另一个进程正在跑 —— 调用方应当跳过本轮。"""


#: 只有这两个 errno 表示「锁被别的进程占着」。其余（EIO / ENOLCK / ENOSPC…）
#: 是**真实故障**，不能伪装成「本轮有人在跑所以跳过」—— 那会让调度系统
#: 永远显示成功，而分析其实一次都没跑。
_LOCK_BUSY_ERRNOS = frozenset({errno.EACCES, errno.EAGAIN})


@contextmanager
def run_lock(path: Path | str | None = None):
    """拿不到排他锁就抛 `LockBusy`；真正的系统故障原样抛出。"""
    target = Path(path) if path is not None else DEFAULT_LOCK_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(target), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in _LOCK_BUSY_ERRNOS:
                raise LockBusy(f"另一个 AI 分析进程正在运行（{target}）") from exc
            raise
        os.truncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        yield target
    finally:
        # 解锁失败不该掩盖调用方真正的异常（比如上面刚抛的 LockBusy / OSError），
        # 而且 fd 关掉时内核也会释放锁 —— 记一条日志足够。
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError as exc:
            log.warning("释放运行锁失败（%s）：%s", target, exc)
        finally:
            os.close(fd)
