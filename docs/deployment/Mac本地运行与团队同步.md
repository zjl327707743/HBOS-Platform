# Mac 本地运行与团队同步

本轮复用已有 P1 Site、Compose project 和卷，固定入口为 `http://p1-knowledge-twin.localhost:5188/hbos`。这是本机使用环境；公司服务器首次部署、固定 IP 和正式 HTTPS 留到后续，不再阻塞本轮运行与 GitHub 同步。

## 常用命令：只有一套入口

部署人员通过 `install-launcher` 安装保护目录中的 `hbos` 薄启动器，配置默认读取 `~/Library/Application Support/HBOS/local/config.json`，也可用 `--config` 指定。启动器跟随配置中的不可变制品版本，保留本机交互式 TTY。下列 `HBOS_LOCAL` 指向已安装启动器：

```bash
"$HBOS_LOCAL" start
"$HBOS_LOCAL" status
"$HBOS_LOCAL" stop
"$HBOS_LOCAL" open
```

`start` 启动已安装的 Docker Desktop、接续原项目服务、检查目标数据库指纹及 Portal/LIMS 资产，打开登录页。重复启动使用同一组容器。它不创建 Site、不迁移、不修改密码、不删除卷；`stop` 只停止配置的 project 中运行服务。Mac 睡眠、关机或 Docker 停止期间不能承诺访问。

首页 `/hbos`、登录 `/hbos/login`、应用中心 `/hbos/apps` 均属于同源入口。入口监听 `127.0.0.1`，拒绝其他 Host；不开放局域网，不建公网隧道。服务器工具 `scripts/release/apply_existing_site.sh` 继续强制 HTTPS；CSRF、Origin、Cookie 与 Site 会话隔离继续保留。

## Administrator

账号为当前 Site 的 `Administrator`。已有密码直接使用，启动工具不会重置。不知道密码时，由本人在本机终端执行：

```bash
"$HBOS_LOCAL" admin-password
```

两次隐藏输入至少 16 位密码，并输入当前 Site 名称确认后才执行。密码仅走 stdin，不进入 argv、环境变量、聊天或日志；撤销当前 Site 的 Administrator 旧会话，不更改其他 Site。代理/运维认证会话验证不等于 Owner 本人密码登录验收。

## 首次接入与升级（部署人员）

本工具接续**已部署的** Frappe/ERPNext/HRMS v16 项目。没有 backend/Site 的新机器会明确报 `EXISTING_SERVICE_REQUIRED`，不会猜库或自动创建替代库。首次部署基础环境按仓库 `docker-compose.yml` 和部署说明完成；本轮 Owner Mac 已存在该环境，无需重装。

1. 保护备份目标数据库、Site config、private files、知识/设备授权和必要原代码，记录 `hbos_portal.auth.site_inventory.inspect` 的无身份指纹；备份须在 Git 之外且 0600/0700。需要恢复时使用已验证备份，由人员指定原库；不通过清库修复。
2. 从干净发布提交运行 `bash scripts/release/build_bundle.sh`，或取得该 PR HEAD 对应 CI 的 `hbos-portal-production-bundle`。用 `validate_bundle.py --source-commit <完整SHA>` 验证后解压到独立版本目录，保留上一版。不要将开发工作区挂作常用运行源码。
3. 将 `scripts/local/config.example.json` 复制到上述保护配置位置并设为 0600。配置 `base_compose` 为原项目 Compose，`env_file` 为复用现有数据库凭据的保护环境文件，`project`/`site`/`expected_database` 精确匹配备份目标，`release_root` 指向验证制品，`runtime_root` 指向持久运行目录。基础 HRMS/font 挂载复用原项目；不复制私有文件到仓库。
4. `model_root`、`gateway_config_root`、`knowledge_index` 安全连接已经批准的原私有文件；Gateway token/policy 为当前用户所有的 0600 文件。Docker bind 映射后须核对容器 UID。没有私有资产时留空：Gateway 报未配置、模型报未配置，页面不加载 mock、不崩溃。无需重复扫描、导入或建模。
5. 如旧端口被 Vite 占用，先核对 PID、cwd、命令和 project。只停止已确认属于此 P1 的进程；启动器遇到未知占用报 `PORT_CONFLICT`，不杀进程。
6. 安装启动器并启动；首次代码升级须在备份后用制品 `scripts/local/apply_site.py` 核对目标指纹、运行迁移及迁移后保留检查。`before`/`audit` 文件由保护挂载传入；常用 `start` 永不隐式迁移。检查完成后保留服务运行。

配置完成后安装一次，之后始终使用同一启动器：

```bash
export HBOS_LOCAL_CONFIG="$HOME/Library/Application Support/HBOS/local/config.json"
python3 scripts/local/manage.py install-launcher --config "$HBOS_LOCAL_CONFIG"
export HBOS_LOCAL="$(python3 -c 'import json,os;print(json.load(open(os.environ["HBOS_LOCAL_CONFIG"]))["runtime_root"]+"/hbos")')"
"$HBOS_LOCAL" start
```

升级时先核验新制品，再只修改保护配置中的 `release_root`；旧版本目录及备份保留。启动器自动指向新制品，代码路径不依赖原 Agent 或终端。第一次切换的迁移命令在既有 backend 中执行：

```bash
docker exec "$HBOS_BACKEND" /home/frappe/frappe-bench/env/bin/python \
  /opt/hbos-release/scripts/local/apply_site.py --site "$HBOS_SITE" \
  --origin "$HBOS_LOCAL_ORIGIN" --expected-database "$CONFIRMED_DB_FINGERPRINT" \
  --before "$PRIVATE_BEFORE_IN_CONTAINER" --audit "$PRIVATE_AUDIT_IN_CONTAINER"
```

这些变量均由已核验配置/备份提供；不把密码或 Secret 放入命令。若原 ERPNext/HRMS Site 尚未完成初始化，应通过原生 setup wizard 完成本地公司、会计期间与默认仓库设置，再检查 Desk 入口；不直接改 `setup_complete` 绕过初始化，也不导入演示业务交易。

`status` 区分 Docker 未启动、缺少 Site/App/编译资产、版本不一致、Gateway 未配置、模型未配置和飞书未配置。密码登录错误在登录页单独报告，健康检查不冒充认证成功。五应用业务 Provider、角色、数据权限与真实空状态继续由各 App 管理。

## 飞书与本人操作

回调必须精确登记为当前 origin 加 `/api/method/hbos_portal.auth.feishu.callback`。服务端已有有效 Secret 时复用；当前 Site 缺失时本人执行 `"$HBOS_LOCAL" feishu-config`，在本机 TTY 隐藏输入已有应用 Secret。工具自动请求企业信息，不要求搬运 Token、tenant_key 或 open_id。本人在控制台核对回调、内部发布范围与成员读取权限后，输入程序发现的企业全称确认。

默认动作不启用收件验证码。普通 OAuth、Administrator 绑定许可、本人收件验证码分别核对。`configured=true` 不等于 OAuth 成功；须本人完成授权、确认绑定、退出后再次飞书登录及验证码实际查收。控制台若拒绝本机回调，记录实际错误，不绕过校验。

基础身份 scope 仅使用 `contact:user.base:readonly`；后端另以应用身份核验当前范围内在职成员；必要状态需要 contact:user.employee:readonly，已由本人申请待审批生效。无需增加用户 OAuth 受雇 scope、部门或聊天读取权限。部分成员可用范围下，第二位开户验收身份也必须在原批准范围内。无密码新用户可直接使用飞书工作，密码是可选项。

机器人和最小发送权限 `im:message:send_as_bot` 已批准并发布后，同一启动器执行 `"$HBOS_LOCAL" feishu-config --enable-inbox-stepup`。工具复用 Secret、核验机器人，让本人确认发送权限。只向持久绑定本人、且由本人主动请求的收件箱发送验证码；取得飞书 message acknowledgement 才显示发送成功，失败不保存新验证码。状态检查不发消息，不读聊天、不群发。未启用时无密码设密/恢复不可用，已有密码和知识/设备不受影响。

Administrator 许可 `hbos_feishu_allow_administrator_link` 只在 Owner 指定 Site 开启；仍须管理员密码及已有 MFA，再授权本人飞书并明确确认。冲突不删除、不转移。忘记管理员密码执行上述 `admin-password`，不用普通员工恢复凭据。

## 普通员工恢复

恢复页只展示实际配置渠道：飞书恢复、已验证邮箱及管理员协助。Frappe User 的邮箱字段不等于邮箱所有权已验证；SMTP 可用且运维完成核验后，保护 Site config 的 `hbos_account_verified_recovery_emails` 才登记 User 到同一真实地址的映射。私有映射、邮箱和核验记录不进 Git；虚拟 User 标识永远不能成为恢复邮箱。未配置则隐藏邮箱，所有请求保持统一存在性提示。

管理员须重新验证密码/MFA、填写身份核验依据并审计，再签发 15 分钟单次、绑定指定普通 User 的链接。key 使用 URL fragment，不进入 HTTP URL；只在浏览器组件内存保留。服务端验证后显示目标姓名、登录名和 User 标识，绑定浏览器、会话与安全 epoch；保存仍须原 MFA，锁定 User 后重核有效期/启用状态，成功撤销 key、旧会话与安全票据。管理员只复制并私下交付链接，不设置或知道最终密码。Administrator/Guest 不接受匿名恢复 key。

本机两层 Nginx 不记录认证访问 URL，Frappe 保留不含凭据的认证审计。

## 团队获取同一版本

产品代码 Authority 是 `feature/hbos-portal-product`。原 `codex/portal-unified-account-release` 已作为 PR #21 的历史来源在 GitHub 删除，不再用于获取代码。

首次获取：

```bash
export HBOS_CODE_DIR="$PWD/HBOS-Platform"
git clone --branch feature/hbos-portal-product --single-branch https://github.com/zjl327707743/HBOS-Platform.git "$HBOS_CODE_DIR"
git -C "$HBOS_CODE_DIR" rev-parse HEAD
```

已有工作区安全更新，先看状态。若有未提交工作或发布分支占用，使用新目录或现有合适 worktree，不强切换、不 stash/reset/clean：

```bash
git -C "$HBOS_CODE_DIR" status --short --branch
git -C "$HBOS_CODE_DIR" fetch origin feature/hbos-portal-product
git -C "$HBOS_CODE_DIR" merge --ff-only origin/feature/hbos-portal-product
```

后两条仅在当前工作区就是 `feature/hbos-portal-product`、且工作区干净、且该目录没有同时作为正在运行服务的可变源码挂载时执行；存在分歧时停止并审查整合。PR #21 保留为已合并的审查证据，PR #15 仍为 Draft（base `main`），不用于获取团队代码、不推 main/base、不强推、不自动合并。产品分支状态以 [项目状态](../PROJECT_STATUS.md) 顶部的**核验日快照**为准（快照 SHA 不自动前进，引用前须当日重新 `git ls-remote` 核验）；源码已合并不等于本机已部署。

> 历史为何对不上：本机曾运行的 `2d138f8` 与产品分支不共享父提交，**主要原因是 PR #21 采用 squash 合并**。这不代表旧账号/飞书功能被遗漏——运行版本独有的提交内容已随 PR #21 进入产品分支，逐文件内容差很小。因此**不要把“重新合并旧分支”当作升级手段**；版本对齐只能通过“构建新制品 → 备份 → 迁移”完成，且必须另行授权。

两份旧考勤同步脚本已改为读取部署环境变量 `HBOS_FEISHU_LEAVE_APP_TOKEN` / `HBOS_FEISHU_LEAVE_TABLE_ID`、`HBOS_FEISHU_EXCEPTION_APP_TOKEN` / `HBOS_FEISHU_EXCEPTION_TABLE_ID`。它们是其他业务同步的资源标识，与 Portal OAuth Secret 分开配置；未接入时不启动同步，不使用仓库中的真实表格标识。

运行 SHA 和 build ID 以 `/assets/hbos_portal/portal/build-info.json`、制品 `release.json` 与**用于构建的源码提交**（`feature/hbos-portal-product` 的当日 HEAD）三者一致为准。新提交必须重新构建、部署并验证。每次 CI 必须核对最新提交的本次结果及制品，历史 PASS 不代表本次 PASS。

上传仅包含通用 App、Gateway、运行工具、配置模板、锁文件及编译资产。数据库备份、用户、密码散列、Secret/Token、个人映射、知识原文/索引、私有模型/图纸/照片、证书私钥与本机报告保留在本机。截图和本人验收报告单独交付，不放入公共 Git。

账号自动开户、拼音登录名和受控换绑/管理员交接，见 [飞书自动开户与受控账号变更](飞书自动开户与受控账号变更.md)。当前 Secret/企业确认已完成，不再按缺少 Secret 处理。真实 Site 不执行保管人交接；普通登录不增加交接门禁。
