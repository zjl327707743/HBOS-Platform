"""launchd / 启动脚本的静态契约 —— 生产取数服务的自启。

2026-10-29：这个服务**从来没有自启配置**。排查 OCR 时一条
`pkill -f "port 8101"` 把它一起杀了（命令行里就含那个端口参数），
页面立刻报「无法连接生产数据服务」。

本文件把这次修复的关键点钉住：

  1. plist 存在、能解析、是常驻（KeepAlive）而不是定时；
  2. plist 指向的脚本存在且可执行；
  3. 脚本只挑需要的变量，不 source 整个 .env；
  4. 缺飞书凭据时以非零码退出，不起一个「所有接口都 503」的服务；
  5. **外部显式设置的变量优先** —— 临时换端口不能被 .env 覆盖
     （早先无条件 export，`PORT=8121 ./start.sh` 仍然起在 8101）。
"""

from __future__ import annotations

import os
import plistlib
import stat
import subprocess
from pathlib import Path

SERVICE = Path(__file__).parents[1]
PLIST = SERVICE / "launchd" / "com.haibin.hbos.production.plist"
SCRIPT = SERVICE / "scripts" / "start.sh"


def test_plist_exists_and_is_a_daemon():
    assert PLIST.is_file(), "缺少 launchd plist"
    with PLIST.open("rb") as f:
        data = plistlib.load(f)
    assert data["Label"] == "com.haibin.hbos.production"
    assert data.get("KeepAlive") is True, "必须 KeepAlive —— 被误杀/崩溃要自动拉起"
    assert data.get("RunAtLoad") is True
    assert "StartCalendarInterval" not in data, "这是常驻服务，不是定时任务"


def test_plist_points_to_executable_script():
    with PLIST.open("rb") as f:
        data = plistlib.load(f)
    args = data["ProgramArguments"]
    assert args[0].endswith("bash")
    script = Path(args[1])
    assert script.is_file(), f"脚本不存在：{script}"
    assert os.stat(script).st_mode & stat.S_IXUSR, "脚本没有可执行位"


def test_script_reads_only_its_own_keys():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "HBOS_PRODUCTION" in src
    assert "source " not in src, "不能 source 整个 .env（里面有 DB 密码等无关密钥）"


def test_script_fails_fast_without_feishu_credentials(tmp_path):
    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [str(SCRIPT)],
        env={
            **os.environ,
            "HBOS_PRODUCTION_ENV_FILE": str(empty),
            "HBOS_PRODUCTION_PORT": "8199",
            # 清掉从外部继承的凭据，确保走「缺失」分支
            "HBOS_FEISHU_APP_ID": "",
            "HBOS_FEISHU_APP_SECRET": "",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2, proc.stderr
    assert "HBOS_FEISHU_APP_ID" in proc.stderr


def test_external_env_wins_over_dotenv(tmp_path):
    """外部显式设的端口不能被 .env 覆盖。

    早先 `PORT=8121 ./start.sh` 仍然起在 8101 —— 因为脚本无条件 export .env
    里的值，结果两个实例抢同一端口，后来的 bind 失败。
    """
    env_file = tmp_path / "svc.env"
    env_file.write_text(
        "HBOS_PRODUCTION_PORT=8101\n"
        "HBOS_FEISHU_APP_ID=cli_fake\n"
        "HBOS_FEISHU_APP_SECRET=fake\n",
        encoding="utf-8",
    )
    # 探针必须放在服务目录的 scripts/ 下 —— 脚本靠 `HERE/..` 找服务目录，
    # 放到 tmp_path 会让它找不到 .venv。
    src = SCRIPT.read_text(encoding="utf-8")
    probe = SCRIPT.parent / "_probe_start_test.sh"
    probe.write_text(
        src.replace(
            'exec "$PYTHON" -m uvicorn',
            'echo "RESOLVED_PORT=$HBOS_PRODUCTION_PORT"\nexit 0\nexec "$PYTHON" -m uvicorn',
        ),
        encoding="utf-8",
    )
    probe.chmod(0o755)
    try:
        proc = subprocess.run(
            [str(probe)],
            env={
                **os.environ,
                "HBOS_PRODUCTION_ENV_FILE": str(env_file),
                "HBOS_PRODUCTION_PORT": "8121",     # 外部指定，应胜出
            },
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        probe.unlink(missing_ok=True)
    assert "RESOLVED_PORT=8121" in proc.stdout, proc.stdout + proc.stderr


def test_script_binds_loopback_by_default():
    """默认只绑 127.0.0.1 —— 服务目前零鉴权，不能暴露到局域网。"""
    src = SCRIPT.read_text(encoding="utf-8")
    assert 'HBOS_PRODUCTION_HOST:-127.0.0.1' in src
