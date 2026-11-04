# HBOS R6 团队固定版本拉取指南（待最终产品 SHA）

状态：`GUIDE_PREPARED`；`TEAM_PULL_REPRODUCED=NOT_RUN`；`TEAM_PULL_READY=NO`。2026-11-02（Asia/Shanghai）。本指南须由主执行者在最终六 PR 合并后的干净产品提交 M 上实际执行并补收据，才可标记可复现。下列操作只用于每人新建的隔离合成环境。

仓库：[zjl327707743/HBOS-Platform](https://github.com/zjl327707743/HBOS-Platform)。产品分支 `feature/hbos-portal-product`。完整 SHA 和可用标签以随版本交付、经校验的外部 `RELEASE_MANIFEST.json` 为准；六 PR 已形成产品提交，但干净安装修复仍需独立审定及最终版本验证。`02f574ca…` 是历史组合，不能填作最终产品。`hbos-v1.0-rc2` 仅在最终版本全部验证通过且取得准确目标许可后创建。

共同验收入口是 `http://pr61-synth.localhost:18191/hbos/login`，由主执行者维护。团队各自在本机创建新的 project、Site、卷与回环端口，不接管这个入口。本机保护端口 18090、8080，以及其他工作位、真实账号/飞书绑定、main、RC1、共享 HRMS 和真实业务库均不使用。

## 1. 拉取准确源码

下面所有 shell 代码块在**同一个新 Bash 会话**中按顺序执行；不要分别启动子 shell 丢失变量。首先执行 `bash`，然后执行 `set -euo pipefail`。任一断言/命令失败即停止本次流程，保留证据后排查，不继续下一段。

需 Git、Python 3.12+、Docker Compose（支持 `!override`）和最终清单记录的 Node/npm 精确版本。镜像 digest、HRMS 完整 revision、工具链、锁文件摘要和制品摘要缺失时先停；不能用可移动 tag 或 `version-16` 分支 tip 代填。当前18191所用 HRMS 已按1553个tracked blob及文件模式核验为 `e0142b17b6b21d0f94aec8788e80c0a8bd0b44f1` / tree `07f4c5ee8552369fac45ab87fef5b7f17110d444` / v16.13.0；clean安装沿用这个独立副本，不使用旧依赖锁中的16.20.0升级共享目录。最终清单应登记此准确来源。

下面的路径须指向本机已登记的短期演练目录或团队自己的项目根；每轮使用新的空目录。`HBOS_TEAM_MANIFEST` 是该版本随附的最终外部清单，不是仓库内 template。

```bash
set -euo pipefail
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
assert m['dependencies']['hrms']['commit']=='e0142b17b6b21d0f94aec8788e80c0a8bd0b44f1'
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

固定运行镜像按 Portal 与 Knowledge 运行锁安装声明的必要 Python 依赖，构建时执行 pip check 和关键符号导入预检；不启动独立知识服务或导入真实资料。新 project 首次准备 assets-data 时，从固定镜像复制原生资产，将该新卷归属 uid/gid 1000，并核对原生资产链接，随后才运行正常安装钩子。该准备只允许空卷，不覆盖任何已有 Site。

下面的 overlay 给全部自有 App 增加只读挂载，覆盖旧 LIMS dist 卷，显式固定 DB/Redis/Node 镜像，且前端仅监听回环地址。八个 Frappe 服务都显式挂载本 project 的同一 `assets-data` 到 `sites/assets`；backend/frontend 的 `bench/assets` 也沿用此卷。base Compose 的 `create-site` 默认命令没有逐条失败保护，因此安装时使用显式 `bash -ec`；本段只适用于新建空 Site。所有运行镜像与 mount 必须记录到本次复现收据。

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
    mounts.append({'type':'volume','source':'assets-data','target':bench+'/sites/assets'})
    if name!='websocket':mounts.append(mount(r/'apps/hb_lims_app/hb_lims_app/public/hbos-lims',bench+'/apps/hb_lims_app/hb_lims_app/public/hbos-lims'))
    services[name]={'image':image,'volumes':mounts,'environment':{'PYTHONPATH':py}}
# The fixed image's wrapper removes sites/assets before exec, which conflicts
# with the explicit volume mounted there. Keep the native service commands.
for name in ['backend','frontend','websocket','scheduler','queue-short','queue-long']:
    services[name]['entrypoint']=[]
services['backend']['command']=['/usr/local/bin/start.sh']
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
hbteam run --rm --no-deps --user 0 --env SITE_NAME="$HBOS_TEAM_SITE" --entrypoint bash configurator -ec '
  test ! -e "sites/$SITE_NAME/site_config.json"
  test -z "$(find sites/assets -mindepth 1 -maxdepth 1 -print -quit)"
  cp -a assets/. sites/assets/
  chown -R 1000:1000 sites/assets
  test "$(stat -c %u sites/assets)" = 1000
  test -f sites/assets/assets.json
  for app in frappe erpnext; do
    test -L "sites/assets/$app"
    test "$(readlink -f "sites/assets/$app")" = "$(readlink -f "apps/$app/$app/public")"
  done
'
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
```

新 clone 没有 HRMS 和考勤的已编译 Desk bundle。先在私有构建副本中构建，不能借用共享 HRMS 的 `public/dist`、已有 Site 的 assets.json，也不能对只读运行源码执行 `bench build`。此处使用固定 Frappe 镜像内已安装的 esbuild 工具链；直接运行其 production 命令，只构建 HRMS/考勤 Desk bundles，不执行 HRMS 的 PWA/roster自定义构建。这两个额外前端不在本版团队验收范围。

固定 Frappe 的 postcss 会把随机临时目录写入四个 CSS/RTL sourcemap，连带改变 CSS 文件名；Desk CSS 的全字节复现为 `NO`。下段不改写资产，只对四对已知 CSS/map 的派生文件名、唯一末尾 map 引用和严格匹配的临时 source 路径作规范化；CSS 规则、sourcesContent、mappings、其他 map 字段及全部 JS/map 内容仍比较。未知路径、额外字段、重复 JSON 键、缺失/新增内容或规范化摘要不符均停止。每轮原始文件清单与摘要另存，不能用内容比较通过冒称全字节一致。

本段命令已从当前固定镜像的实际 `frappe/build.py`、`apps/frappe/package.json`、`esbuild/esbuild.js` 核对接口，仍须最终 M 的干净 Site 实际执行。当前实读工具链为 Node `v24.12.0`、Yarn `1.22.22`；最终 manifest须分别记录容器Desk构建工具链与前面Portal/LIMS主机构建的Node/npm。

```bash
python3 - <<'PY_DESK_PREP'
import json,os,shutil
from pathlib import Path
p=Path(os.environ['HBOS_TEAM_PRIVATE']); c=Path(os.environ['HBOS_TEAM_CHECKOUT']); stage=p/'desk-build-source'
assert not stage.exists(); stage.mkdir()
shutil.copytree(c/'runtime/apps/hrms',stage/'hrms',ignore=shutil.ignore_patterns('.git','node_modules','__pycache__','*.pyc'))
shutil.copytree(p/'release/apps/hb_attendance_app',stage/'hb_attendance_app',ignore=shutil.ignore_patterns('node_modules','__pycache__','*.pyc'))
bench='/home/frappe/frappe-bench'
# CLI --volume does not clear read_only inherited from the service definition.
# This overlay applies only to the one-off build, using private source copies.
volumes=[{'type':'bind','source':str(stage/app),'target':bench+'/apps/'+app,'read_only':False}
         for app in ['hrms','hb_attendance_app']]
(p/'compose.desk-build.json').write_text(json.dumps({'services':{'create-site':{'volumes':volumes}}},indent=2))
PY_DESK_PREP
hbteam -f "$HBOS_TEAM_PRIVATE/compose.desk-build.json" run --rm --no-deps --entrypoint bash create-site -ec '
    test "$(node --version)" = "v24.12.0"
    test "$(yarn --version)" = "1.22.22"
    cd /home/frappe/frappe-bench/apps/hrms
    yarn install --frozen-lockfile --ignore-scripts --non-interactive
    test -f yarn.lock
    cd /home/frappe/frappe-bench
    for app in hrms hb_attendance_app; do ln -sfn "/home/frappe/frappe-bench/apps/$app/$app/public" "sites/assets/$app"; done
    cd apps/frappe
    CI=1 yarn run production --apps hrms,hb_attendance_app
  '
python3 - <<'PY_DESK_VERIFY'
import hashlib,json,os,pathlib,re
from pathlib import Path
NORMALIZER_VERSION = 'frappe-v16-css-map-tmp-v1'

def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'Duplicate JSON key: ' + key
        result[key] = value
    return result

def manifests(stage):
    raw, normalized, differences = {}, {}, []
    for app in ['hrms', 'hb_attendance_app']:
        dist = pathlib.Path(stage) / app / app / 'public/dist'
        assert dist.is_dir(), app
        for f in sorted(dist.rglob('*')):
            if not f.is_file():
                continue
            relative = f.relative_to(dist).as_posix()
            key, content = app + '/' + relative, f.read_bytes()
            raw[key] = hashlib.sha256(content).hexdigest()
            logical = key
            if '.css' in f.name:
                bundle = 'hrms.bundle' if app == 'hrms' else 'hbos_attendance.bundle'
                assert re.fullmatch(r'css(?:-rtl)?/' + re.escape(bundle) + r'\.[A-Z0-9]{8}\.css(?:\.map)?', relative), key
                logical = re.sub(r'\.[A-Z0-9]{8}(\.css(?:\.map)?)$', r'\1', key)
            if f.name.endswith('.css.map'):
                value = json.loads(content, object_pairs_hook=unique_keys)
                assert set(value) == {'version', 'sources', 'sourcesContent', 'mappings', 'names'}, key
                assert value['version'] == 3 and isinstance(value['mappings'], str), key
                assert isinstance(value['names'], list) and all(isinstance(x, str) for x in value['names']), key
                assert isinstance(value['sources'], list) and len(value['sources']) == 1 and isinstance(value['sources'][0], str), key
                assert isinstance(value['sourcesContent'], list) and len(value['sourcesContent']) == 1 and isinstance(value['sourcesContent'][0], str), key
                source = value['sources'][0]
                pattern = r'(?:\.\./){8}tmp/tmp-[0-9]+-[A-Za-z0-9]+/' + app + '/' + app + r'/public/(?:scss|css)/' + re.escape(bundle) + r'\.css'
                assert re.fullmatch(pattern, source), (key, source)
                value['sources'][0], count = re.subn(r'/tmp-[0-9]+-[A-Za-z0-9]+/', '/HBOS_CSS_BUILD_TMP/', source)
                assert count == 1
                content = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
                differences.append({'file': key, 'normalization': 'Only random postcss temporary source directory; all other map values retained'})
            elif f.name.endswith('.css'):
                suffix = b'\n/*# sourceMappingURL=' + f.name.encode() + b'.map */\n'
                assert f.with_name(f.name + '.map').is_file(), key
                assert content.endswith(suffix) and content.count(b'sourceMappingURL=') == 1, key
                content = content[:-len(suffix)] + b'\n/*# sourceMappingURL=' + pathlib.PurePosixPath(logical).name.encode() + b'.map */\n'
                differences.append({'file': key, 'normalization': 'Only exact terminal sourcemap filename; CSS rules unchanged'})
            else:
                assert logical == key, key
            assert logical not in normalized, logical
            normalized[logical] = hashlib.sha256(content).hexdigest()
    assert raw and len(raw) == len(normalized)
    assert len(differences) == 8, 'Expected exactly four known CSS/map pairs'
    return raw, normalized, differences

def digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

p=Path(os.environ['HBOS_TEAM_PRIVATE']); manifest=json.load(open(os.environ['HBOS_TEAM_MANIFEST']))
c=Path(os.environ['HBOS_TEAM_CHECKOUT'])
raw,normalized,_=manifests(p/'desk-build-source')
expected=manifest['artifact']['desk_assets']
assert expected['normalizer_version']==NORMALIZER_VERSION
assert digest(normalized)==expected['normalized_manifest_sha256'], 'Desk内容与最终版本清单不符'
for name,files in [('desk-assets-manifest.json',raw),('desk-assets-normalized.json',normalized)]:
    (p/name).write_text(json.dumps(files,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps({'Desk_content':'PASS_SCOPED','Desk_BYTE_REPRODUCIBLE':'NO','raw_manifest_sha256':digest(raw),'normalized_manifest_sha256':digest(normalized)}))
# 构建结束后才给长期服务添加生成目录的只读挂载；release原包保持不变。
# Nested mount destinations must exist before their parent code bind is RO.
for app in ['hrms','hb_attendance_app']:
    root=c/'runtime/apps/hrms' if app=='hrms' else p/'release/apps'/app
    (root/app/'public/dist').mkdir(parents=True,exist_ok=True)
config=json.loads((p/'compose.code.json').read_text())
for service in ['backend','frontend','websocket','configurator','create-site','scheduler','queue-short','queue-long']:
    for app in ['hrms','hb_attendance_app']:
        config['services'][service]['volumes'].append({'type':'bind','source':str(p/'desk-build-source'/app/app/'public/dist'),'target':'/home/frappe/frappe-bench/apps/'+app+'/'+app+'/public/dist','read_only':True})
(p/'compose.code.json').write_text(json.dumps(config,indent=2))
PY_DESK_VERIFY
hbteam config --quiet
hbteam up -d --no-deps backend
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" migrate
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" migrate
hbteam exec -T backend bash -ec 'for app in hrms hb_attendance_app hb_inventory_app hb_lims_app hbos_portal hb_knowledge_app hb_twin_app; do ln -sfn "/home/frappe/frappe-bench/apps/$app/$app/public" "/home/frappe/frappe-bench/assets/$app"; done'
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

确认 ping=pong、build-info 的完整 commit=M/dirty=false/build_id 与本次制品一致，Portal/LIMS manifest 中每个资产均可获取且摘要相同；同时核对 served `/assets/assets.json` 中 `hrms.bundle.js`、`hrms.bundle.css`、`hbos_attendance.bundle.js`、`hbos_attendance.bundle.css` 都指向本轮真实存在的资源，并逐项 HTTP 获取验证摘要。`list-apps` 缺应用或 migrate 出错即失败；不得用私有 monkeypatch、合成 Site 名特判或关闭安全校验继续。

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
# 确认预览仅含此公司后执行写入，仍只影响自己的隔离Site。
hbteam exec -T backend bench --site "$HBOS_TEAM_SITE" delegate-admin --user "$HBOS_TEAM_ADMIN_USER" --company "$HBOS_TEAM_COMPANY" --actor team-local-operator --reason '建立本地合成管理账号的公司范围委派' --apply
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
