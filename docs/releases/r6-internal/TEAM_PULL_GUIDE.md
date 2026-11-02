# HBOS R6 团队固定版本拉取指南（待最终产品 SHA）

状态：`GUIDE_PREPARED`；`TEAM_PULL_REPRODUCED=NOT_RUN`；`TEAM_PULL_READY=NO`。2026-11-02（Asia/Shanghai）。本指南须由主执行者在最终六 PR 合并后的干净产品提交 M 上实际执行并补收据，才可标记可复现。下列操作只用于每人新建的隔离合成环境。

仓库：[zjl327707743/HBOS-Platform](https://github.com/zjl327707743/HBOS-Platform)。产品分支 `feature/hbos-portal-product`。完整 SHA 和可用标签以随版本交付、经校验的外部 `RELEASE_MANIFEST.json` 为准；当前没有最终 M，`02f574ca…` 是历史组合，不能填作最终产品。建议标签 `hbos-v1.0-rc2` 尚未授权创建。

共同验收入口是 `http://pr61-synth.localhost:18191/hbos/login`，由主执行者维护。团队各自在本机创建新的 project、Site、卷与回环端口，不接管这个入口。本机保护端口 18090、8080，以及其他工作位、真实账号/飞书绑定、main、RC1、共享 HRMS 和真实业务库均不使用。

## 1. 拉取准确源码

需 Git、Python 3.12+、Docker Compose（支持 `!override`）和最终清单记录的 Node/npm 精确版本。镜像 digest、HRMS 完整 revision、工具链、锁文件摘要和制品摘要缺失时先停；不能用可移动 tag 或 `version-16` 分支 tip 代填。

下面的路径须指向本机已登记的短期演练目录或团队自己的项目根；每轮使用新的空目录。`HBOS_TEAM_MANIFEST` 是该版本随附的最终外部清单，不是仓库内 template。

```bash
export HBOS_TEAM_MANIFEST='/absolute/path/to/approved/RELEASE_MANIFEST.json'
export HBOS_TEAM_CHECKOUT='/absolute/path/to/empty/r6-checkout'
export HBOS_TEAM_PRIVATE='/absolute/path/to/new/private-r6-runtime'
export HBOS_TEAM_SHA="$(python3 -c 'import json,os,re; m=json.load(open(os.environ["HBOS_TEAM_MANIFEST"])); s=m["source"]["commit"]; assert m["status"]=="FINAL_VERIFIED" and re.fullmatch("[0-9a-f]{40}",s); print(s)')"
test ! -e "$HBOS_TEAM_CHECKOUT"
git clone --no-checkout https://github.com/zjl327707743/HBOS-Platform.git "$HBOS_TEAM_CHECKOUT"
git -C "$HBOS_TEAM_CHECKOUT" checkout --detach "$HBOS_TEAM_SHA"
test "$(git -C "$HBOS_TEAM_CHECKOUT" rev-parse HEAD)" = "$HBOS_TEAM_SHA"
test -z "$(git -C "$HBOS_TEAM_CHECKOUT" status --porcelain)"
cd "$HBOS_TEAM_CHECKOUT"
```

已有本地仓库时，先 `git -C /absolute/existing/path status --short --branch` 了解其状态，随后仍使用上面的新 clone 路径。保留原 dirty 仓库、stash、分支及运行，不在旧目录执行 pull、checkout、reset、clean 或自动 migrate。新工作从产品 M 派生短期分支，不能在 main 开发。

核验依赖锁与工具链：

```bash
python3 - <<'PY'
import hashlib,json,os,subprocess
from pathlib import Path
m=json.load(open(os.environ['HBOS_TEAM_MANIFEST']))
assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()==m['source']['tree']
for path,want in m['build']['lock_sha256'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==want, path
for executable,key in [('node','node'),('npm','npm')]:
    assert subprocess.check_output([executable,'--version'],text=True).strip()==m['build']['toolchain'][key], key
assert m['dependencies']['frappe_base']['reference'].split('@sha256:')[1]
assert len(m['dependencies']['hrms']['commit'])==40
PY
```

## 2. 从 M 构建，并准备私有运行参数

`build_bundle.sh` 对 Portal、LIMS 执行 `npm ci` 与真实 Frappe 模式构建，按 allowlist 打包、验证文件摘要。不能只修改旧包的 `build-info.json`。不要使用 `deploy/build_candidate.py` 或 `deploy/release_candidate.py`：它们是知识 RC1 的专用部署工具。

```bash
umask 077
mkdir -m 700 -p "$HBOS_TEAM_PRIVATE"
python3 - <<'PY'
import json,os,subprocess
from pathlib import Path
m=json.load(open(os.environ['HBOS_TEAM_MANIFEST']))
root=Path(os.environ['HBOS_TEAM_CHECKOUT']); hrms=root/'runtime/apps/hrms'
assert not hrms.exists(), '只在新的空 checkout 准备 HRMS'
hrms.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['git','clone','--no-checkout',m['dependencies']['hrms']['source'],str(hrms)],check=True)
subprocess.run(['git','-C',str(hrms),'checkout','--detach',m['dependencies']['hrms']['commit']],check=True)
assert subprocess.check_output(['git','-C',str(hrms),'rev-parse','HEAD'],text=True).strip()==m['dependencies']['hrms']['commit']
PY
bash scripts/setup_fonts.sh --no-container-check
bash scripts/release/build_bundle.sh "$HBOS_TEAM_PRIVATE/artifact"
python3 scripts/release/validate_bundle.py "$HBOS_TEAM_PRIVATE/artifact/hbos-portal-release.tar.gz" --source-commit "$HBOS_TEAM_SHA"
```

将本次包 sha256 与版本清单对比；若不同先比构建工具链、锁文件和逐文件资产摘要并由主执行者裁定，不能改清单迎合当前包。

```bash
python3 - <<'PY'
import hashlib,json,os,tarfile
from pathlib import Path
m=json.load(open(os.environ['HBOS_TEAM_MANIFEST'])); p=Path(os.environ['HBOS_TEAM_PRIVATE'])
a=p/'artifact/hbos-portal-release.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()==m['artifact']['sha256']
r=p/'release'; assert not r.exists(); r.mkdir()
with tarfile.open(a) as t: t.extractall(r,filter='data')
assert json.loads((r/'release.json').read_text())['source_commit']==m['source']['commit']
PY
```

配置和密码只保存在 `HBOS_TEAM_PRIVATE`，不得提交或分享 Owner 的配置。以下程序生成新的私有密码、关闭所有外部同步，并产生仅本 project 使用的配置。端口自行选择未占用回环端口；本机 HBOS 演练还需登记，不得选保护端口或 18191。

```bash
export HBOS_TEAM_PORT='18291'
export HBOS_TEAM_SITE='team-r6.localhost'
export HBOS_TEAM_PROJECT='hbos-team-r6-personal'
python3 - <<'PY'
import json,os,re,secrets,socket,subprocess
from pathlib import Path
p=Path(os.environ['HBOS_TEAM_PRIVATE']); port=int(os.environ['HBOS_TEAM_PORT'])
project=os.environ['HBOS_TEAM_PROJECT']; assert re.fullmatch(r'hbos-team-[a-z0-9_-]+',project)
assert not subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project='+project],text=True).strip(), '本段只用于新的空 project'
assert port not in (8080,18090,18191)
with socket.socket() as sock: sock.bind(('127.0.0.1',port))
m=json.load(open(os.environ['HBOS_TEAM_MANIFEST'])); cfg=Path(os.environ['HBOS_TEAM_CHECKOUT'])/'.env.example'
v={line.split('=',1)[0]:'' for line in cfg.read_text().splitlines() if line and not line.startswith('#') and '=' in line}
pw=secrets.token_urlsafe(32)
v.update(COMPOSE_PROJECT_NAME=os.environ['HBOS_TEAM_PROJECT'],ERPNEXT_VERSION=m['dependencies']['frappe_base']['reference'].split('frappe/erpnext:',1)[1],SITE_NAME=os.environ['HBOS_TEAM_SITE'],FRAPPE_SITE_NAME_HEADER=os.environ['HBOS_TEAM_SITE'],HTTP_PORT=str(port),MARIADB_HOST='db',DB_PORT='3306',DB_ROOT_PASSWORD=pw,MYSQL_ROOT_PASSWORD=pw,ADMIN_PASSWORD=secrets.token_urlsafe(32),REDIS_CACHE='redis-cache:6379',REDIS_QUEUE='redis-queue:6379',SOCKETIO_PORT='9000',UPSTREAM_REAL_IP_ADDRESS='127.0.0.1',UPSTREAM_REAL_IP_HEADER='X-Forwarded-For',UPSTREAM_REAL_IP_RECURSIVE='off',PROXY_READ_TIMEOUT='120',CLIENT_MAX_BODY_SIZE='50m',HBOS_FEISHU_SYNC_ENABLED='0',HBOS_DELICLOUD_SYNC_ENABLED='0',HBOS_AI_ENABLED='0',HBOS_AI_ALLOW_PII='0',HBOS_AI_TIMEOUT='60',HBOS_NOTIFY_DRY_RUN='1')
(p/'compose.env').write_text('\n'.join(k+'='+x for k,x in v.items())+'\n'); (p/'compose.env').chmod(0o600)
PY
```

Administrator 密码是新隔离 Site 的本机私有值；使用自己的密码管理方式保存并登录。不要将 `compose.env`、完整 Compose 渲染结果或 Site 配置打印进共享日志。

## 3. 隔离安装与启动

下面的 overlay 给全部自有 App 增加只读挂载，覆盖旧 LIMS dist 卷，显式固定 DB/Redis/Node 镜像，且前端仅监听回环地址。base Compose 的 `create-site` 默认命令没有逐条失败保护，因此安装时使用显式 `bash -ec`；本段只适用于新建空 Site。所有运行镜像与 mount 必须记录到本次复现收据。

```bash
python3 - <<'PY'
import json,os,subprocess
from pathlib import Path
p=Path(os.environ['HBOS_TEAM_PRIVATE']); r=p/'release'; c=Path(os.environ['HBOS_TEAM_CHECKOUT']); m=json.load(open(os.environ['HBOS_TEAM_MANIFEST']))
base=m['dependencies']['frappe_base']['reference']; image='hbos-team-frappe:'+m['source']['commit']
subprocess.run(['docker','build','--build-arg','FRAPPE_IMAGE='+base,'-t',image,'-f',str(c/'scripts/release/Dockerfile.portal'),str(c)],check=True)
apps=['hb_attendance_app','hb_inventory_app','hb_lims_app','hbos_portal','hb_knowledge_app','hb_twin_app']
def mount(src,dst):return {'type':'bind','source':str(src),'target':dst,'read_only':True}
bench='/home/frappe/frappe-bench'; code=[mount(r/'apps'/a,bench+'/apps/'+a) for a in apps]
code.append(mount(c/'runtime/apps/hrms',bench+'/apps/hrms'))
py=':'.join(bench+'/apps/'+a for a in ['hrms']+apps)
services={}
for name in ['backend','frontend','websocket','configurator','create-site','scheduler','queue-short','queue-long']:
    mounts=list(code)
    if name!='websocket':mounts.append(mount(r/'apps/hb_lims_app/hb_lims_app/public/hbos-lims',bench+'/apps/hb_lims_app/hb_lims_app/public/hbos-lims'))
    services[name]={'image':image,'volumes':mounts,'environment':{'PYTHONPATH':py}}
services['db']={'image':m['dependencies']['mariadb']['reference']}
services['redis-cache']={'image':m['dependencies']['redis']['reference']}
services['redis-queue']={'image':m['dependencies']['redis']['reference']}
services['hbos-web-prepare']={'image':m['dependencies']['node_builder']['reference']}
for dependency in ['frappe_base','mariadb','redis','node_builder']:
    assert '@sha256:' in m['dependencies'][dependency]['reference'],dependency
(p/'compose.code.json').write_text(json.dumps({'services':services},indent=2))
(p/'compose.loopback.yml').write_text('services:\n  frontend:\n    ports: !override\n      - "127.0.0.1:'+os.environ['HBOS_TEAM_PORT']+':8080"\n')
PY
hbteam() {
  docker compose --project-directory "$HBOS_TEAM_CHECKOUT" --env-file "$HBOS_TEAM_PRIVATE/compose.env" -p "$HBOS_TEAM_PROJECT" -f "$HBOS_TEAM_CHECKOUT/docker-compose.yml" -f "$HBOS_TEAM_PRIVATE/compose.code.json" -f "$HBOS_TEAM_PRIVATE/compose.loopback.yml" "$@"
}
hbteam config --quiet
hbteam up -d db redis-cache redis-queue
hbteam run --rm --no-deps configurator
hbteam run --rm --no-deps --entrypoint bash create-site -ec '
  wait-for-it -t 120 "$DB_HOST:$DB_PORT"
  wait-for-it -t 120 redis-cache:6379
  wait-for-it -t 120 redis-queue:6379
  test ! -e "sites/$SITE_NAME/site_config.json"
  bench new-site "$SITE_NAME" --mariadb-user-host-login-scope="%" --admin-password="$ADMIN_PASSWORD" --db-root-username=root --db-root-password="$DB_ROOT_PASSWORD" --install-app erpnext --set-default
  for app in hrms hb_attendance_app hb_inventory_app hb_lims_app hbos_portal hb_knowledge_app hb_twin_app; do bench --site "$SITE_NAME" install-app "$app"; done
'
hbteam up -d --no-deps backend
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" migrate
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" migrate
hbteam exec -T backend bash -ec 'for app in hb_attendance_app hb_inventory_app hb_lims_app hbos_portal hb_knowledge_app hb_twin_app; do ln -sfn "/home/frappe/frappe-bench/apps/$app/$app/public" "/home/frappe/frappe-bench/assets/$app"; done'
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" set-config host_name "http://$HBOS_TEAM_SITE:$HBOS_TEAM_PORT"
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" set-config hbos_portal_origin "http://$HBOS_TEAM_SITE:$HBOS_TEAM_PORT"
hbteam up -d --no-deps websocket frontend
hbteam ps
hbteam exec -T backend bench version
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" list-apps
curl --noproxy '*' -fsS "http://$HBOS_TEAM_SITE:$HBOS_TEAM_PORT/api/method/ping"
curl --noproxy '*' -fsS "http://$HBOS_TEAM_SITE:$HBOS_TEAM_PORT/assets/hbos_portal/portal/build-info.json"
curl --noproxy '*' -fsS -o /dev/null "http://$HBOS_TEAM_SITE:$HBOS_TEAM_PORT/hbos/login"
```

确认 ping=pong、build-info 的完整 commit=M/dirty=false/build_id 与本次制品一致，Portal/LIMS manifest 中每个资产均可获取且摘要相同。`list-apps` 缺应用或 migrate 出错即失败；不得用私有 monkeypatch、合成 Site 名特判或关闭安全校验继续。

默认不启动 scheduler/queue，不发送消息或外部同步；如本版验收依赖后台服务，按最终清单指定的获准范围补启动并记录，不能把未运行异步链记为 PASS。

## 4. 新 Site 的管理员引导与合成数据

首次登录使用本机新 Site 的 Administrator。按 ERPNext 正常初始化流程创建虚构公司/部门及独立合成管理、员工账号，并在本地完成 Employee 与 User 关联。不要导入真实员工，也不要复制 18191 私有账号。初始化之前 IAM 开关保持关闭；准备好合成主数据后，显式启用本地 IAM：

```bash
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" set-config hbos_iam_enabled 1
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" set-config hbos_iam_roles_enabled 1
# 填入自己创建的合成公司与账号；以下变量不是秘密。
export HBOS_TEAM_COMPANY='your-existing-synthetic-company'
export HBOS_TEAM_ADMIN_USER='your-synthetic-admin@example.invalid'
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" init-roles --company "$HBOS_TEAM_COMPANY" --actor team-local-operator --reason '初始化本地隔离验收考勤角色'
# 阅读预览后才加 --apply，命令只创建草稿，不发布、不分配、不授予原生角色。
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" init-roles --company "$HBOS_TEAM_COMPANY" --actor team-local-operator --reason '初始化本地隔离验收考勤角色' --apply
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" delegate-admin --user "$HBOS_TEAM_ADMIN_USER" --company "$HBOS_TEAM_COMPANY" --actor team-local-operator --reason '建立本地合成管理账号的公司范围委派'
# 确认预览仅含此公司后，再执行同命令加 --apply。
```

随后从 `/hbos/login` 用各自账号登录，在“角色与权限”按服务端影响预览及本人密码 proof 发布角色；通过管理中心分配部门默认和个人例外，管理型部门默认须逐人确认。新 Site 未初始化角色、未发布或未关联 Employee 时，空态/拒绝是预期，不能宣称自动拥有全部权限。不要设置 `hbos_iam_test_site`、`hbos_account_test_site` 或 demo bypass 来走通产品流程。

飞书登录保留现有实现，但新 Site 默认为未配置，应显示缺失配置/不可用。不要运行 `configure_feishu.py`、绑定真实账号或启用自动开户。知识独立服务、私有索引及模型没有交付时，导航和明确的不可用提示可验，检索问答/真实资料不能报通过。

## 5. 现有隔离 Site 升级

升级由其唯一维护者在明确维护窗口执行，不套用新 Site 的 `new-site`/install 初始化命令。先核对 project、Site、DB 指纹、卷和 mount；备份数据库、public/private 文件、完整私有 Site 配置及加密/收据签名密钥，并在单独 namespace 恢复成功。只记录存在性和安全摘要，不共享密钥。

切换到 M 的只读来源和新构建资产后，按对应 project 的准确 Compose 文件执行 `bench --site SITE migrate` 连续两次，核对用户、凭据、身份绑定、角色、权限、业务关联及审计保留。#67 收据模型/唯一索引/签名密钥、#68 逐人准入模型均需纳入。必须复验收据重放与旧会话拒绝。18191 的准确命令与备份由主执行者冻结交付，不从本示例推断其他环境可写。

回退要求旧完整源码/资产/运行参数和迁移前一致性恢复点。不能承诺只换前端就撤销迁移，不能删除当前收据或审计以重试。

## 6. 复现回执与停止

按 `TEAM_PULL_CHECKLIST.md` 完成允许/拒绝/重放/恢复检查，保留带时区时间、完整 M/tree、工具链、镜像 ID、锁文件/制品摘要和清洁环境证据。由执行人签明实际结果；主执行者复验后再更新外部 manifest 的 `TEAM_PULL_REPRODUCED`、`TEAM_PULL_READY`。

日常停止仅 `hbteam stop frontend backend websocket` 并保留本次私有 DB/Redis/卷；不得用全局 stop/prune 或照抄 CI 脚本的 EXIT trap。当前指南尚未演练，所有安装和本地 bootstrap 命令均待实际验证。
