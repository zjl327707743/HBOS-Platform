# M1-RP3：统一账号、飞书绑定与正式发布

轮次代号 RP3 表示 Owner 授权的 Portal 执行任务书 v3，并非考勤历史 M1-R3。

状态：**LOCAL_RUNNING / FUNCTION_VERIFIED / REMOTE_PR_TRACKED / LIVE_OWNER_PENDING**。

本轮最新决策（2026-09-30）：复用现有 P1 为固定 Mac 使用环境；无需寻找历史正式库。保留既有数据库/用户/文件/卷及批准知识和模型，部署六 App 与 Portal/LIMS 编译资产，验证五入口并推送 PR #21。公司服务器、固定 IP、正式 HTTPS 留到后续。本人密码/飞书验收独立记录，不以自动化测试替代。

## 已交付通用实现

- 原账号密码重新认证后绑定本人飞书；首次飞书登录先选择绑定已有账号或永久普通开户。不按姓名/邮箱匹配，不创建独立密码表。
- 密码less User 经本人收件验证码及原 MFA 设置密码；改密、解绑、身份唯一性/tombstone、邮件短时恢复与管理员受控签发、中央停用和旧会话/票据撤销。
- Frappe 原生密码 API 和 User 文档路径均要求强验证；外部映射只信任服务端验证上下文，客户端 Document.flags 无法伪造。旧飞书 Social Login Key fail-closed；保留 Administrator 原生登录，不自动授权普通飞书用户。
- 飞书明确离职/停用状态同步每五分钟，可显式启用；网络/权限/范围异常不自动停用本地密码，具体边界已说明并测试。
- 同一 Site 托管 production SPA、deep routes 与 API/assets/Desk；六 App + 通用 Gateway v1.2.0 + 版本锁 + 保护备份/隔离恢复/目标匹配/保留校验工具。
- 前端真实能力矩阵、管理员诊断、安全页面、空状态/错误/未实现控件整理，清除生产通知示例和错误捷径。

## 当前 P1 本机部署与验证（2026-09-30）

当前唯一常用入口为 `http://p1-knowledge-twin.localhost:5188/hbos`，复用 Site `p1-knowledge-twin.localhost` / Compose `hbos-p1-knowledge-twin`。Docker Desktop、原数据库与命名卷均保留；数据库、配置、私有文件和原源码已保护备份。现有六 App 经原生 migrate 和保留核对，User、密码验证记录、角色、数据权限、Employee/Checkin/Attendance、业务关联及外部身份指纹一致。

Portal 与 LIMS 使用 clean 提交生成的编译资产，同源连接 Frappe。常用入口不依赖 Vite/Agent 会话。原知识私有索引以只读挂载连接通用 Gateway；五份已批准资料未重新导入。M607B 已批准模型、版本、授权和待核部件映射复用，没有伪造实时数据。

| 验证 | 真实结果与范围 |
| --- | --- |
| Administrator bootstrap | 五个 App 均 installed、registered、available，诊断失败数 0 |
| 考勤 | 应用中心进入原生异常仪表盘；无记录显示“暂无数据”，非 100%/0% 演示出勤率 |
| 仓储库存 | 进入原生入库拍照识别页面；默认仓库设置可读取。未上传业务照片、执行 OCR 或创建库存交易 |
| LIMS | 自己的编译资产加载工作台总览，真实后端返回空任务/样品；未执行新业务交易 |
| 知识 | 真实 Frappe → Gateway → 私有索引返回相关证据；证据抽屉可用，未开放原文/get_source；跨用户证据被拒绝 |
| 设备与工艺 | 真实 M607B 模型加载并支持旋转、点选、高亮、聚焦、隔离、复位，设备级知识可检索；未核节点继续待核 |
| 普通用户 | 复用现有普通验证用户与原角色，仅有知识/设备两个入口；真实检索与 GLB 哈希核对通过，管理员诊断 403、Guest 模型访问拒绝 |
| 页面与返回 | 首页、我的工作、应用中心、知识、设备、我的/设置与账号安全逐页验证；同源跳转及返回有效 |

上述 Administrator 与普通用户使用运维建立的受控原生验证会话，未读取/重置原密码，未增授管理角色，**不是 Owner 密码表单或飞书授权验收**。自动化结束撤销测试会话，交付匿名登录页；本人通过原密码或本机隐藏输入工具进入。

本轮修复实际错误：未完成的 ERPNext/HRMS 原生初始化阻挡 Desk，已完成本地公司及默认主数据设置，不导入 demo 交易；实时代理丢失 5188 端口，现经 P1 内部别名及保留 Origin 的专用 socket 路由访问；考勤空记录及旧 Page 缓存显示错误，已更新页面版本；管理员诊断调用 set_user 会损坏原会话，现保留 session/CSRF/权限上下文并以真实 HTTP 回归验证。服务器安全要求未全局关闭，本 Site 的临时开发 Origin 放行已关闭。

本轮通用契约为 Portal 32、Knowledge 18、Twin 9、Gateway 5、本地边界 5 项通过；Portal/LIMS 类型检查与 production build 通过。凭据扫描覆盖待发布提交及解压制品；manifest 校验值单独核对为哈希，无私有账号/资料/模型进入发布包。本机截图、备份、私有映射与运行报告不提交 Git。

## 前序测试的独立证据范围

此前受控测试 Site 的 25 项 Frappe ORM/SQL 账号生命周期、标准 HTTP 表单/CSRF/Origin/撤销验证与 SQL 隔离恢复已通过。测试身份为合成，不能替代 Owner 本人或当前飞书应用授权。当前 Mac 复用已明确的 P1，不再等待历史“原正式库”选择；后续迁公司服务器仍须指定该服务器目标并保留备份/恢复与 HTTPS 要求。

## 本轮状态（分别记录）

| 项目 | 当前状态 |
| --- | --- |
| Mac 固定本地环境 | LOCAL_RUNNING：固定 loopback 5188，原 Site/项目/卷保留，编译 Portal/LIMS 与真实 Gateway 已运行 |
| 功能验证 | FUNCTION_VERIFIED：上述五入口、普通角色、知识/模型与返回已验证；不代表未操作业务交易已验收 |
| GitHub 同步 | REMOTE_PR_TRACKED：[PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 为团队发布入口；最终 SHA、最新 CI 和制品以该 PR 当前记录为准 |
| 飞书 | NOT_CONFIGURED：当前 Site 无有效 Secret/企业发现；服务端尚无回调登记及内部发布确认，控制台状态须本人核对。本人 OAuth 未执行，不阻塞密码/知识/模型 |
| Owner 本人验收 | LIVE_OWNER_PENDING：本人尚未登录；原密码保留，未知密码由本人在当前 Site 专用工具中隐藏输入确认 |
| 公司服务器 | NOT_DEPLOYED：固定 IP 与正式 HTTPS 后续，不作为本轮 Mac 门禁 |

CI 必须核对 PR **最新** HEAD 的本次结果；历史通过记录不替代本次检查。运行制品 `source_commit`、`build_id`、前端 build-info 与远端 HEAD 必须一致；后续任何新提交重新构建并验证。

## 配套文档

- `docs/deployment/Mac本地运行与团队同步.md`
- `docs/deployment/统一账号与Portal正式部署说明.md`（后续服务器模式）
- `docs/frontend/统一账号发布与前端完整性矩阵.md`
- `scripts/release/依赖版本锁.json`

本轮接续既有 Portal 成果；保留原开发分支及个人工作，净化发布分支从 Portal 产品分支派生。允许安全扫描后 commit/push/真实 PR；禁止推 main、强推、自动合并。没有重新执行 P0、没有扩展考勤或库存独立里程碑。
