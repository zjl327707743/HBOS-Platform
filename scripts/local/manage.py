"""Persistent loopback entry for a preserved Compose project and existing Site.

Never creates a Site, resets credentials, removes volumes, or runs migration on
ordinary startup. Configuration, secrets and backups live outside the checkout.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

SERVICES = ["db", "redis-cache", "redis-queue", "backend", "websocket", "queue-long", "queue-short", "scheduler", "frontend", "local-gateway", "local-entry"]
APPS = ["hb_attendance_app", "hb_inventory_app", "hb_lims_app", "hbos_portal", "hb_knowledge_app", "hb_twin_app"]
BENCH = "/home/frappe/frappe-bench"


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def capture(args):
    return run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def config(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ValueError(f"LOCAL_CONFIG_MISSING: 请按 scripts/local/config.example.json 配置 {p}")
    if p.stat().st_mode & 0o077:
        raise ValueError("LOCAL_CONFIG_PERMISSIONS: 配置须为 0600")
    c = json.loads(p.read_text())
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]+", c["project"]):
        raise ValueError("COMPOSE_PROJECT_INVALID")
    if not re.fullmatch(r"[a-zA-Z0-9.-]+", c["site"]):
        raise ValueError("SITE_INVALID")
    origin = urlsplit(c["origin"])
    if origin.scheme != "http" or not (origin.hostname == "localhost" or str(origin.hostname).endswith(".localhost")) or not origin.port or origin.path or origin.query or origin.fragment or origin.username:
        raise ValueError("LOCAL_ORIGIN_INVALID: 仅支持固定 .localhost 的 loopback HTTP；服务器继续使用 HTTPS 发布流程")
    addresses = socket.getaddrinfo(origin.hostname, origin.port)
    if any(a[4][0] not in {"127.0.0.1", "::1"} for a in addresses):
        raise ValueError("LOCAL_HOST_NOT_LOOPBACK")
    c["port"] = origin.port
    c["hostname"] = origin.hostname
    for key in ["base_compose", "env_file", "runtime_root", "release_root"]:
        c[key] = str(Path(c[key]).expanduser().resolve())
    c["config_path"] = str(p)
    return c


def require_docker(start=False):
    try:
        capture(["docker", "info", "--format", "{{.ServerVersion}}"])
    except (FileNotFoundError, subprocess.CalledProcessError):
        if start and sys.platform == "darwin" and Path("/Applications/Docker.app").is_dir():
            run(["open", "-a", "Docker"])
            for _ in range(45):
                time.sleep(1)
                try:
                    capture(["docker", "info", "--format", "{{.ServerVersion}}"])
                    return
                except (FileNotFoundError, subprocess.CalledProcessError):
                    pass
        raise ValueError("DOCKER_NOT_RUNNING: 请启动已安装的 Docker Desktop，再执行同一启动命令") from None


def containers(c, service=None, all_states=True):
    args = ["docker", "ps", "-aq" if all_states else "-q", "--filter", f"label=com.docker.compose.project={c['project']}"]
    if service:
        args += ["--filter", f"label=com.docker.compose.service={service}"]
    return capture(args).split()


def backend(c):
    ids = containers(c, "backend", False)
    if len(ids) != 1:
        raise ValueError("BACKEND_NOT_RUNNING: 目标 project 必须有唯一 backend")
    return ids[0]


def require_site(c):
    try:
        run(["docker", "exec", backend(c), "test", "-f", f"{BENCH}/sites/{c['site']}/site_config.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise ValueError("SITE_NOT_FOUND: 目标 backend 没有当前 Site；不会创建替代库") from None
    raw = json.loads(capture(["docker", "exec", backend(c), "cat", f"{BENCH}/sites/{c['site']}/site_config.json"]))
    if not c.get("expected_database") or hashlib.sha256(str(raw["db_name"]).encode()).hexdigest() != c["expected_database"]:
        raise ValueError("DATABASE_TARGET_MISMATCH: 与已备份的目标数据库不一致")


def release(c):
    root = Path(c["release_root"])
    info = json.loads((root / "release.json").read_text())
    if info.get("source_dirty") or info.get("portal_data_mode") != "frappe":
        raise ValueError("RELEASE_INVALID: 必须使用 clean 提交的真实 Frappe 制品")
    for name, digest in info["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("RELEASE_CHECKSUM_FAILED: " + name)
    for name in ["apps/hbos_portal/hbos_portal/public/portal/index.html", "apps/hb_lims_app/hb_lims_app/public/hbos-lims/index.html"]:
        if not (root / name).is_file():
            raise ValueError("ASSETS_NOT_DEPLOYED: Portal 或 LIMS 编译资产缺失")
    actual = json.loads((root / "apps/hbos_portal/hbos_portal/public/portal/build-info.json").read_text())
    if actual["source_commit"] != info["source_commit"] or actual["build_id"] != info["build_id"]:
        raise ValueError("BUILD_ID_MISMATCH")
    return info


def install_launcher(c):
    """Stable thin launcher follows the protected config's verified version."""
    release(c)
    root = Path(c["runtime_root"])
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    target = root / "hbos"
    code = "import json,os,sys;from pathlib import Path;cfg=Path(sys.argv[1]);root=Path(json.loads(cfg.read_text())['release_root']);os.execv(sys.executable,[sys.executable,str(root/'scripts/local/manage.py'),*sys.argv[2:],'--config',str(cfg)])"
    target.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexec python3 -c " + shlex.quote(code) + " " + shlex.quote(c["config_path"]) + ' "$@"\n')
    target.chmod(0o700)
    print("常用启动器已安装：" + str(target))


def write_runtime(c):
    """Compose override uses the original project/volumes and reviewed release."""
    state = Path(c["runtime_root"])
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    state.chmod(0o700)
    empty = state / "unconfigured"
    empty.mkdir(mode=0o700, exist_ok=True)
    index = empty / "index.jsonl"
    if not index.exists():
        index.touch(mode=0o600)
    def mount(source, target):
        return {"type": "bind", "source": str(source), "target": target, "read_only": True}
    root = Path(c["release_root"])
    code = [mount(root / "apps" / app, f"{BENCH}/apps/{app}") for app in APPS]
    model = c.get("model_root") or str(empty)
    py = ":".join([f"{BENCH}/apps/hrms"] + [f"{BENCH}/apps/{app}" for app in APPS])
    services = {}
    for name in ["backend", "queue-long", "queue-short", "scheduler", "websocket", "frontend"]:
        volumes = list(code)
        if name != "websocket":
            # Override the old nested LIMS dist volume; the original volume is retained.
            volumes.append(mount(root / "apps/hb_lims_app/hb_lims_app/public/hbos-lims", f"{BENCH}/apps/hb_lims_app/hb_lims_app/public/hbos-lims"))
        if name == "backend":
            volumes.append(mount(model, "/opt/hbos-p1/private-assets/twin"))
            volumes.append(mount(root, "/opt/hbos-release"))
        services[name] = {"volumes": volumes, "restart": "unless-stopped", "environment": {"PYTHONPATH": py}}
    services["frontend"]["environment"]["FRAPPE_SITE_NAME_HEADER"] = c["site"]
    services["frontend"]["volumes"].append(mount(root / "scripts/local/nginx-frontend.conf", "/etc/nginx/nginx.conf"))
    for name in ["db", "redis-cache", "redis-queue"]:
        services[name] = {"restart": "unless-stopped"}
    services["local-gateway"] = {
        "image": "hbos-local-gateway:" + release(c)["source_commit"][:12],
        "build": {"context": str(root), "dockerfile": "services/hbos_gateway/Dockerfile"},
        "restart": "unless-stopped", "read_only": True, "tmpfs": ["/tmp"],
        "environment": {"HBOS_GATEWAY_TOKEN_FILE": "/run/hbos-private/gateway_token", "HBOS_GATEWAY_POLICY_PATH": "/run/hbos-private/gateway_policy.json", "HBOS_GATEWAY_LOCAL_INDEX_PATH": "/run/hbos-index/index.jsonl", "HBOS_GATEWAY_CLIENT_ID": c.get("gateway_client_id", "hbos-frappe")},
        "volumes": [mount(c.get("gateway_config_root") or empty, "/run/hbos-private"), mount(c.get("knowledge_index") or index, "/run/hbos-index/index.jsonl")],
        "networks": ["frappe_network"]}
    nginx = f'''pid /tmp/hbos-nginx.pid;
error_log /dev/stderr warn;
events {{ worker_connections 1024; }}
http {{
  include /etc/nginx/mime.types;
  access_log off;
  client_body_temp_path /tmp/hbos-client;
  proxy_temp_path /tmp/hbos-proxy;
  map $http_upgrade $connection_upgrade {{ default upgrade; '' close; }}
  map $http_origin $hbos_socket_origin {{ '' "{c['origin']}"; default $http_origin; }}
  server {{ listen 8080 default_server; listen {c['port']} default_server; server_name _; return 421; }}
  server {{
    listen 8080; listen {c['port']}; server_name {c['hostname']};
    client_max_body_size 50m;
    add_header Referrer-Policy no-referrer always;
    add_header X-Content-Type-Options nosniff always;
    location = / {{ return 302 /hbos; }}
    location /socket.io {{
      if ($hbos_socket_origin != "{c['origin']}") {{ return 403; }}
      proxy_pass http://websocket:9000;
      proxy_http_version 1.1;
      proxy_set_header Host $http_host;
      proxy_set_header Origin $hbos_socket_origin;
      proxy_set_header X-Frappe-Site-Name {c['site']};
      proxy_set_header X-Forwarded-Proto http;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection $connection_upgrade;
      proxy_read_timeout 120s;
    }}
    location / {{
      proxy_pass http://frontend:8080;
      proxy_set_header Host $http_host;
      proxy_set_header X-Forwarded-Host $http_host;
      proxy_set_header X-Forwarded-Proto http;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection $connection_upgrade;
      proxy_read_timeout 120s;
    }}
  }}
}}
'''
    (state / "nginx.conf").write_text(nginx)
    # Reuse the already installed Frappe image's nginx; no second web runtime.
    services["local-entry"] = {"image": "frappe/erpnext:" + c.get("erpnext_version", "v16.26.2"), "entrypoint": ["nginx"], "command": ["-c", "/opt/hbos-local/nginx.conf", "-g", "daemon off;"], "restart": "unless-stopped", "ports": [f"127.0.0.1:{c['port']}:8080"], "volumes": [mount(state / "nginx.conf", "/opt/hbos-local/nginx.conf")], "networks": {"frappe_network": {"aliases": [c['hostname']]}}}
    (state / "compose.local.json").write_text(json.dumps({"services": services}, indent=2))
    return state


def compose(c, *args, **kwargs):
    return run(["docker", "compose", "--project-directory", str(Path(c["base_compose"]).parent), "--env-file", c["env_file"], "-p", c["project"], "-f", c["base_compose"], "-f", str(Path(c["runtime_root"]) / "compose.local.json"), *args], **kwargs)


def get_json(url):
    # Local health/auth configuration checks must stay on loopback even when
    # the user's shell has a system or environment HTTP proxy configured.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=5) as r:
        return json.load(r)


def status(c):
    info = release(c)
    require_site(c)
    print(f"Site: {c['site']}\nCompose: {c['project']}\nSHA: {info['source_commit']}\nBuild ID: {info['build_id']}")
    unavailable = [s for s in SERVICES if len(containers(c, s, False)) != 1]
    if unavailable:
        raise ValueError("SERVICES_NOT_RUNNING: " + ", ".join(unavailable))
    origin = c["origin"].rstrip("/")
    if get_json(origin + "/api/method/ping").get("message") != "pong":
        raise ValueError("FRAPPE_UNHEALTHY")
    actual = get_json(origin + "/assets/hbos_portal/portal/build-info.json")
    if actual["source_commit"] != info["source_commit"] or actual["build_id"] != info["build_id"]:
        raise ValueError("RUNNING_BUILD_MISMATCH")
    installed = capture(["docker", "exec", backend(c), "bench", "--site", c["site"], "list-apps"])
    missing = [app for app in APPS if app not in installed]
    if missing:
        raise ValueError("APP_NOT_INSTALLED: " + ", ".join(missing))
    print("Apps: all installed")
    gateway = containers(c, "local-gateway", False)[0]
    health = json.loads(capture(["docker", "exec", gateway, "python", "-c", "import json,urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/health').read().decode())"]))
    print("Gateway:", "configured / health PASS (检索需登录验证)" if health.get("configured") else "GATEWAY_NOT_CONFIGURED: 知识私有配置/索引未接入；未加载 mock")
    try:
        feishu = get_json(origin + "/api/method/hbos_portal.auth.feishu.get_status")["message"]
        print("Feishu:", "configured / 本人 OAuth 尚需单独验收" if feishu.get("configured") else "FEISHU_NOT_CONFIGURED: " + ", ".join(feishu.get("missing", [])))
        print("Feishu Administrator link:", "enabled / 仍须本人密码与原 MFA" if feishu.get("administrator_link", {}).get("enabled") else "disabled")
        print("Feishu self inbox:", "enabled / 须本人主动请求并核验接收" if feishu.get("inbox_stepup", {}).get("enabled") else "not configured / 无密码设密与恢复需先完成发送能力")
    except urllib.error.HTTPError as e:
        print("Feishu: CONFIG_CHECK_FAILED HTTP", e.code)
    print("Model:", "private root connected / 交互需登录验证" if c.get("model_root") else "MODEL_NOT_CONFIGURED: 未接入私有模型")
    print("Login: " + origin + "/hbos/login （密码错误请核对当前 Site；启动不会重置密码）")
    print("Local runtime: PASS / loopback only; Mac、Docker 停止或关机后不可访问")


def start(c, open_page=True):
    info = release(c)
    # Refuse to create a replacement database/project. Existing containers can restart.
    for service in SERVICES[:9]:
        ids = containers(c, service)
        if len(ids) != 1:
            raise ValueError("EXISTING_SERVICE_REQUIRED: " + service)
        if not containers(c, service, False):
            run(["docker", "start", ids[0]], stdout=subprocess.DEVNULL)
    require_site(c)
    entry = containers(c, "local-entry", False)
    if not entry:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", c["port"])) == 0:
                raise ValueError(f"PORT_CONFLICT: {c['port']} 被现有进程占用；核对归属后再迁移，不自动终止进程")
    write_runtime(c)
    compose(c, "config", "--quiet")
    image_name = "hbos-local-gateway:" + info["source_commit"][:12]
    present = subprocess.run(["docker", "image", "inspect", image_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if present.returncode:
        compose(c, "build", "local-gateway")
    compose(c, "up", "-d", "--no-deps", "--no-build", *SERVICES)
    # A bind-mounted config's content is not part of Compose's container hash.
    # Validate/reload only our entry so repeated starts apply reviewed updates.
    compose(c, "exec", "-T", "local-entry", "nginx", "-t", "-c", "/opt/hbos-local/nginx.conf")
    compose(c, "exec", "-T", "local-entry", "nginx", "-s", "reload", "-c", "/opt/hbos-local/nginx.conf")
    for _ in range(45):
        try:
            if get_json(c["origin"] + "/api/method/ping").get("message") == "pong":
                break
        except (OSError, ValueError):
            time.sleep(1)
    status(c)
    if open_page:
        webbrowser.open(c["origin"] + "/hbos/login")


def administrator_password(c):
    require_site(c)
    if not sys.stdin.isatty():
        raise ValueError("INTERACTIVE_TERMINAL_REQUIRED: 由本人在本机终端隐藏输入")
    print(f"仅为 Compose {c['project']} / Site {c['site']} / Administrator 设密。已有可用密码请取消。")
    password = getpass.getpass("新密码（至少 16 位；隐藏输入）: ")
    if len(password) < 16 or password != getpass.getpass("再次输入: "):
        raise ValueError("两次密码不一致或长度不足；没有修改")
    if input(f"输入 {c['site']} 确认执行: ").strip() != c["site"]:
        raise ValueError("确认不匹配；没有修改")
    # Password stays on stdin. No argv, environment, shell interpolation or logging.
    code = '''import os,sys,frappe
os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site=sys.argv[1]);frappe.connect()
from frappe.utils.password import update_password
from hbos_portal.auth.accounts import revoke_sessions
password=sys.stdin.read()
update_password("Administrator",password,logout_all_sessions=True)
revoke_sessions("Administrator")
frappe.db.commit();frappe.destroy()
print("当前 Site 的 Administrator 密码已更新；旧会话已撤销，密码未输出。")
'''
    result = subprocess.run(["docker", "exec", "-i", backend(c), f"{BENCH}/env/bin/python", "-c", code, c["site"]], input=password, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    del password
    if result.returncode:
        raise ValueError("PASSWORD_UPDATE_FAILED: 未输出敏感诊断，请在本机检查保护日志")
    print(result.stdout.strip())


def feishu_config(c, enable_inbox=False):
    require_site(c)
    if not sys.stdin.isatty():
        raise ValueError("INTERACTIVE_TERMINAL_REQUIRED")
    raw = json.loads(capture(["docker", "exec", backend(c), "cat", f"{BENCH}/sites/{c['site']}/site_config.json"]))
    app_id = str(raw.get("hbos_feishu_app_id") or "")
    if not re.fullmatch(r"cli_[A-Za-z0-9]+", app_id):
        raise ValueError("FEISHU_APP_ID_MISSING: 请先登记已有飞书应用的公开 App ID")
    # The bench helper reuses an existing Secret; otherwise getpass is on the
    # user's local TTY. Enterprise identity is discovered by the official API.
    args = ["docker", "exec", "-it", backend(c), f"{BENCH}/env/bin/python", "/opt/hbos-release/scripts/release/configure_feishu.py", "--site", c["site"], "--bench", BENCH, "--app-id", app_id, "--origin", c["origin"]]
    if enable_inbox:
        args.append("--enable-inbox-stepup")
    run(args)
    print("请由本人完成真实授权、绑定、再次登录与退出；收件验证码须本人主动请求并核验实际接收。")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["start", "status", "stop", "open", "admin-password", "feishu-config", "install-launcher"])
    p.add_argument("--config", default=os.environ.get("HBOS_LOCAL_CONFIG", str(Path.home() / "Library/Application Support/HBOS/local/config.json")))
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--enable-inbox-stepup", action="store_true", help="feishu-config：已批准并发布机器人发送权限后启用本人验证码")
    args = p.parse_args()
    os.umask(0o077)
    c = config(args.config)
    if args.action == "install-launcher":
        install_launcher(c)
        return
    if args.action == "open":
        webbrowser.open(c["origin"] + "/hbos/login")
        return
    require_docker(start=args.action == "start")
    if args.action == "start":
        start(c, not args.no_open)
    elif args.action == "status":
        status(c)
    elif args.action == "admin-password":
        administrator_password(c)
    elif args.action == "feishu-config":
        feishu_config(c, args.enable_inbox_stepup)
    else:
        ids = [i for service in SERVICES for i in containers(c, service, False)]
        if ids:
            run(["docker", "stop", *ids], stdout=subprocess.DEVNULL)
        print("当前 project 已停止；Site、数据库、卷、制品和其他项目保留。")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as e:
        # Child failures can contain secrets. Never echo their captured stderr/argv.
        print(str(e) if not isinstance(e, subprocess.CalledProcessError) else "LOCAL_SERVICE_COMMAND_FAILED: 请检查当前 project 的保护日志", file=sys.stderr)
        sys.exit(1)
