"""launchd / 启动脚本的静态契约 —— 防止「服务起不来」再来一次。

2026-10-27 实测：宿主机 8100 无人监听，页面报「识别服务不可达」，排查很久
才发现**这个服务从来没有自启配置**。本文件把那次修复的关键点钉住：

  1. plist 必须存在、能过 plutil 语法、且是常驻（KeepAlive）而不是定时；
  2. plist 指向的脚本必须存在且可执行；
  3. 脚本必须**只挑 HBOS_OCR_***，不能 source 整个 .env（含 DB / 飞书密钥）；
  4. 令牌缺失时必须以非零码退出，不能起一个半残服务。
"""

from __future__ import annotations

import os
import plistlib
import stat
import subprocess
import sys
from pathlib import Path

SERVICE = Path(__file__).parents[1]
PLIST = SERVICE / "launchd" / "com.haibin.hbos.ocr.plist"
SCRIPT = SERVICE / "scripts" / "start.sh"


def test_plist_exists_and_parses():
    assert PLIST.is_file(), "缺少 launchd plist"
    with PLIST.open("rb") as f:
        data = plistlib.load(f)
    assert data["Label"] == "com.haibin.hbos.ocr"


def test_plist_is_a_daemon_not_a_timer():
    with PLIST.open("rb") as f:
        data = plistlib.load(f)
    assert data.get("KeepAlive") is True, "必须 KeepAlive —— 崩溃要自动拉起"
    assert data.get("RunAtLoad") is True, "必须 RunAtLoad —— 登录即起"
    assert "StartCalendarInterval" not in data, "这是常驻服务，不是定时任务"


def test_plist_program_points_to_existing_executable_script():
    with PLIST.open("rb") as f:
        data = plistlib.load(f)
    args = data["ProgramArguments"]
    assert args[0].endswith("bash")
    script = Path(args[1])
    assert script.is_file(), f"plist 指向的脚本不存在：{script}"
    assert os.stat(script).st_mode & stat.S_IXUSR, f"脚本没有可执行位：{script}"


def test_start_script_only_reads_hbos_ocr_keys():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "HBOS_OCR_*=" in src, "应当只挑 HBOS_OCR_ 前缀的行"
    assert "source " not in src and ". \"$ENV_FILE\"" not in src, (
        "不能 source 整个 .env —— 里面有 DB 密码与飞书密钥"
    )


def test_start_script_fails_fast_without_token(tmp_path):
    """令牌缺失 → exit 2，且 stderr 说明原因。"""
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [str(SCRIPT)],
        env={**os.environ, "HBOS_OCR_ENV_FILE": str(empty_env), "HBOS_OCR_PORT": "8199"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2, proc.stderr
    assert "HBOS_OCR_SHARED_TOKEN" in proc.stderr


def test_start_script_binds_all_interfaces_by_default():
    """默认必须绑 0.0.0.0 —— 绑 127.0.0.1 时容器连不上。"""
    src = SCRIPT.read_text(encoding="utf-8")
    assert 'HBOS_OCR_HOST:-0.0.0.0' in src
