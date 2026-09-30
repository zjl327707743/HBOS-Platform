# 统一账号与 Portal 正式部署说明

适用范围：后续公司服务器模式的部署与安全要求。当前 Mac 本轮已明确复用 P1 Site，无需寻找历史正式库；本地运行与 GitHub 同步按 `Mac本地运行与团队同步.md` 执行，不等待服务器、域名或本人 OAuth。公司生产上线仍须独立完成服务器 HTTPS 和本人验收。

## 版本与团队取得方式

实际交付为 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21)（Draft、未合并）。PR 目标为 `feature/hbos-portal-product`；本轮发布分支为 `codex/portal-unified-account-release`。接续已有 Portal/Knowledge/Twin 源码，以独立净化提交提供必要代码，不发布个人开发分支中的内部运行报告。团队使用 PR 的实际 HEAD SHA，禁止引用个人绝对路径。

`bash scripts/release/build_bundle.sh` 在 clean checkout 执行 `npm ci`、类型检查及 production build，生成 `.release/hbos-portal-release.tar.gz`。包内包含六个自定义 App、Gateway 通用源码、部署工具、前端编译资产、`release.json` 和资产 `build-info.json`。构建强制使用 Frappe 数据模式及同源 API。检查 `source_dirty=false`、commit、文件 SHA256 和 build ID；仅 `.release` 内的显式测试制品可以带 dirty 标记，不准用于正式发布。GitHub Actions 从真实 PR head SHA 上传同一构建流程的制品，保留 14 天；制品来源不能以短期合并预演 SHA 代替已审查 head。 打包统一规范时间/所有者并排除 macOS 资源分叉；构建自动校验归档安全路径、全量文件 SHA、来源提交及 Portal/LIMS 编译入口，避免本机元数据进入交付包。

兼容实测基线见 `scripts/release/依赖版本锁.json`。前端 npm lock 与 Gateway 完整 Python lock 已版本化；HRMS 使用官方仓库固定 commit。既有目标的 ERPNext/Frappe/HRMS 版本先核对，禁止为了匹配基线降级原站；不一致时在目标备份的隔离恢复环境验证兼容性。

团队 HRMS 依赖来自官方仓库固定 commit，不能依赖个人工作目录。已有服务器保留正在使用的 HRMS 源码与资产；若迁到新服务器，按目标备份记录的真实版本准备不可变依赖目录及编译资产。实测基线源码可用 `git init runtime/apps/hrms`、`git -C runtime/apps/hrms remote add origin https://github.com/frappe/hrms.git`、`git -C runtime/apps/hrms fetch --depth 1 origin c0a04b80eeb721417b75cea758e831464d0da041`、`git -C runtime/apps/hrms checkout --detach FETCH_HEAD` 取得，仅用于新目录，不能覆盖既有未核验依赖。源版本不同时，以原目标版本和隔离恢复验证为准。

## 先确认既有 Site

运维从现有 Compose project、站点配置、数据库和 accounts preservation manifest 定位原账号数据源。Site 名不等于域名；公开域名应通过 `FRAPPE_SITE_NAME_HEADER` 指向确切的既有 Site。新建或改名测试库不能替代原账号。

后续迁到公司服务器时，明确该服务器目标数据库与 HTTPS 域名，记录数据库指纹、原镜像及 source revision、已有 volumes 和 mounts。真实账号名、密码验证记录、业务数据、Site config、encryption key 和数据库备份仅进入权限 0700/0600 的服务器审计目录。先验证恢复，再升级同一库；绝不运行 `new-site`、`create-site` 或对未知库 `restore`。

## 备份、恢复验证与切换

1. 维护窗口停止写入口、禁用目标 Site scheduler，并等待正在执行的任务结束，再停 queue workers。记录原维护、调度状态，以便恢复。Docker 命令必须使用已确认的同一个 project name；不得另建同名站点或使用 `down -v`。
2. 在目标 bench Python 环境中只导入待发布 Portal 代码以生成清单，尚未安装 App。若源码未在默认 PYTHONPATH，显式传入 **制品内** `apps/hbos_portal` 路径。执行：

```sh
./env/bin/python /opt/hbos-release/scripts/release/prepare_existing_backup.py \
  --bench /home/frappe/frappe-bench --site "$HBOS_SITE" \
  --expected-database "$CONFIRMED_DB_FINGERPRINT" --audit-dir "$PRIVATE_AUDIT_DIR"
```

3. 把备份 SQL、public/private 文件、`auth-private.tar.gz` 和完整 site_config 私下传给受控恢复机。按 `backup-prepared.json` 实际文件名传参，运行 `scripts/release/verify_backup_restore.py --database ... --site-config ... --public-files ... --private-files ... --auth-files ... --before ...`，将 stdout 保存为审计目录 `restore-verified.json`。工具在无网络、无宿主端口的临时 MariaDB 中导入全部 SQL，逐项对比 User、密码验证记录、角色、User Permissions、业务关联及既有外部身份指纹，检查文件归档可读与 encryption key 存在；不修改源库。此验证不等于文件已在新主机完成业务恢复，换主机还须私下恢复文件/密钥并执行业务检查。
4. 制品解压到不可变版本目录。使用既有 Compose 主文件叠加 `scripts/release/docker-compose.production.yml`，显式保留原 project name、db/sites volumes；`HBOS_SITE` 指向已确认原 Site。先 `docker compose ... config --quiet`；预览有效 mounts，确认六个 App 在 backend、frontend、两类 queue、scheduler 和 websocket 中版本一致。不得调用原主文件里的 `create-site`。Gateway 仅在内部 Docker 网络提供 8080，无公网端口。
5. 运维将 release scripts 只读挂载至 `/opt/hbos-release`，在既有 backend bench 根目录执行：

```sh
bash /opt/hbos-release/scripts/release/apply_existing_site.sh \
  "$HBOS_SITE" "$CONFIRMED_DB_FINGERPRINT" "$HTTPS_ORIGIN" "$PRIVATE_AUDIT_DIR"
```

工具先检查确认库、备份恢复证明及备份后是否变化，仅安装缺少的已实现自定义 App、migrate、设置同源 origin/host_name、重建 Portal 资产链接。迁移后严格比较原用户、密码、角色、权限及业务计数；若原生安装自动产生角色差异，停止并人工审查差异，不能自动改原用户权限来让检查变绿。

6. 重启 backend/workers/scheduler/websocket/frontend，恢复原调度状态。用 `nginx.conf.template` 建正式 TLS 入口；`envsubst` **只替换**四个 HBOS 模板变量，保留 `$request_uri` 等 Nginx 变量。固定 HTTPS 域名下 `/hbos`、deep routes、`/api`、`/assets`、`/app` 都进入同一 Site。外围代理回调及恢复 key 不记 access log；验证 `X-Forwarded-Proto` 贯通、Secure/HttpOnly/SameSite cookies。后端和内部 frontend 端口仅由可信代理访问。
7. 原 Administrator 和原业务用户由本人通过真实表单登录。验证五应用实际跳转、业务数据、账户资料、原角色和 User Permissions。飞书双方身份验证及新账号设密按下节完成后，才放行正式发布。站点数量、configured 或单测通过均不代替这一 Gate。

## 飞书配置与网页使用

复用 Owner 已有应用，不创建新应用。程序生成应用/租户 token、读取用户、核验内部在职成员及精确外部身份；不让 Owner 搬运 Token、tenant_key 或 open_id。

控制台实际需要：有效 Secret、该固定域名的精确 callback、企业内部可用范围发布、用户基础及在职信息读取权限、企业信息查询权限。无密码新用户设密需启用应用机器人及向本人发消息权限，用本人收件验证码做强验证；网络不通或权限缺失时不能把 OAuth code 当作重新认证。

运维在 target bench 执行：

```sh
./env/bin/python /opt/hbos-release/scripts/release/configure_feishu.py \
  --bench /home/frappe/frappe-bench --site "$HBOS_SITE" \
  --app-id "$EXISTING_FEISHU_APP_ID" --origin "$HTTPS_ORIGIN" \
  --enable-inbox-stepup --enable-disable-sync
```

缺 Secret 时只通过 `getpass` 隐藏输入至 Site/private 0600 文件。已有有效 Secret 复用；仅实际失效或需处置泄露时使用 `--replace-secret`。企业信息由应用服务端凭据取得，Owner 只核对企业名称及控制台配置。首次真实授权、机器人收件验证码、二次认证和成员权限须在网页实测。未通过时保持入口关闭并报告实际缺项，不关闭 CSRF、state 或 tenant 校验。

旧用户：原密码登录 → 我的 → 账号与安全 → 验证原密码/原 MFA → 绑定本人飞书 → 授权后明确确认当前账号。首次飞书用户：先授权 → 选择验证已有账号，或明确新建普通永久账号。新 User 无管理员角色及默认密码；用本人飞书收件验证码（及已有 MFA）验证后在网页设密，仍是同一 User。

改密后清除所有旧会话与恢复票据并颁发标准新会话。已有密码的绑定用户忘记密码时，可在网页切换本人飞书消息验证码验证，再更新同一 User 的密码；收件能力未启用时明确提示，不能仅凭现有 SSO 会话改密。解绑须验证可用本地密码，最后一种登录方式不能解绑。冲突不转移、不按姓名/邮箱合并；恢复使用验证邮箱短时单次 key 或管理员重新认证后填写核验依据并签发恢复凭据。Administrator 保留原密码应急入口，外部绑定默认关闭，须 Owner 单独启用；绝不自动授予新飞书用户 Administrator。

中央 User 停用立即拒绝密码、SSO、旧会话与恢复，撤销绑定/票据并保留 tombstone。启用飞书停用同步后每五分钟检查明确 frozen/resigned/unjoin/exited 状态，停用同一普通 User；不自动重新启用，Administrator 不自动停用。范围撤销/API 权限缺失/网络失败不构成可靠离职证明：记录失败，拒绝新 SSO，管理员须核实并中央停用，不能承诺这种情况下本地密码自动被停用。调度队列积压会延迟五分钟目标，运维必须监控失败及调度时效。

邮件恢复依赖正式 SMTP 和已验证可投递邮箱。飞书创建的虚拟 User 标识不可当邮件地址投递；没有有效邮箱时使用本人飞书验证码或管理员受控恢复。

## 知识与模型的私下部署

`services/hbos_gateway` 是独立通用可部署实现 v1.2.0，包含 Dockerfile 和完整锁文件。只读复用已批准索引，不重建 Owner 索引，不复制个人私有服务，不调整 Hermes/MCP 权限。原文、index、token、policy、真实 GLB/照片/节点映射不进入 Git 或 CI 制品。

Gateway 挂载私有 `gateway_token`、`gateway_policy.json`、`index.jsonl`，文件 0600、目录 0700、uid/gid 与运行用户一致；通过 `HBOS_GATEWAY_UID/GID` 指定，不能 chmod 到全员可读。部署变量见 `部署配置示例.env`，均替换为目标服务器路径。backend 只读挂载批准私有配置至 `/run/hbos-private`、模型至 `/run/hbos-models`，模型未获批准时仅提供空目录并保持策略关闭。配置与 token 必须为 bench 运行用户所有；Gateway 使用同一 uid。审计目录独立可写且为 0700，不作为静态资产暴露。Frappe 私有 token 与 Gateway token 一致，后台 endpoint 指向内部 `http://gateway:8080`。正式 scope 和模型清单通过 `configure_domain.py` 与受保护私下 JSON 配置，示例见 `领域配置示例.json`，默认关闭。需私下同步既有批准策略、索引和模型，并保持版本/hash/设备及文档授权范围；代码可用不等于私有数据已到正式目标。

## 回退与未过 Gate 时处置

首次部署前保存原镜像/代码/Compose、完整数据库/文件/加密密钥并验证恢复。若只发生前端错误且没有不兼容迁移，可在维护窗口恢复上个不可变制品，仍验证 Site/版本/API。若有 schema/data 改变，不能只回退 JS 或 `uninstall-app`：优先在另外的明确隔离目标恢复完整备份，验证原 User/密码/权限/业务关联及文件密钥，再由 Owner 确认切换；需要原库回滚时必须停写并评估备份之后业务差异，经确认后按 Frappe 标准恢复步骤执行。自动脚本绝不覆盖未知库、删除 volume 或重置原密码/角色。

验证完成前保留原入口和维护预案。本轮实际生产 Gate 状态见里程碑主文档；不得把测试站域名换个名字作为正式交付。


## 接口依据

企业查询使用应用 tenant token，返回企业名称及 tenant_key；成员核验使用明确 UserStatus 字段。契约已对照[飞书官方 SDK 企业模型](https://github.com/larksuite/oapi-sdk-python/blob/0b9e6e48b74bb4b34462fc67b7e738b27e73e697/lark_oapi/api/tenant/v2/model/tenant.py)及[官方成员状态模型](https://github.com/larksuite/oapi-sdk-python/blob/0b9e6e48b74bb4b34462fc67b7e738b27e73e697/lark_oapi/api/contact/v3/model/user_status.py)。这只证明接口字段依据，不代替该应用真实权限/OAuth/PKCE 现场验证。
