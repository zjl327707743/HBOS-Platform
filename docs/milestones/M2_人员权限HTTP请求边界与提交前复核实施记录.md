# 人员与权限：HTTP 请求边界与提交前复核实施记录

2026-10-10 最新接续：[原站只读预检](M2_人员权限原站只读预检记录.md)已完成，**S02_ORIGINAL_READONLY_PREFLIGHT_COMPLETED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。实际frontend / DB摘要精确匹配，五来源InnoDB与24必需列PASS，COUNT18/0/1/14/31；八管理表全缺，正式预检在tables以STORAGE_PREFLIGHT_SCHEMA_INVALID停止。10诊断SELECT含正式预检2，零transaction_writes、rollback/destroy PASS，未初始化。只读诊断完成不等于结构或启用PASS；管理GET仍NOT_READY。原站备份工具release路径缺失，现已有镜像 / 权限 / 磁盘 / 备份总量仅元数据确认，原样stdin备份操作包已准备但未执行。下一段先确定停写一致性窗口 / 原服务恢复措施，再按同次私有备份与隔离SQL恢复范围执行；不建表 / 人员 / 政策 / pins或启GET。5178既有真实只读；本段未改代码 / 配置 / 服务 / 缓存 / schema，未备份 / 恢复或浏览器复验。前段14原生 / 428离线PASS为历史证据，本段未重跑。S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，Grant NOT_RUN，P4-F6-5 REVIEWING；原Q1/Q2、Date、固定P1 / 完整恢复 / Owner及管理门禁保留。 以下为前序交付当时的记录。

- 日期：2026-10-09；分支：`m2-r11@27d3558`，沿用 Owner 指定分支。
- 状态：**S02_MANAGEMENT_HTTP_PREVIEW_VALIDATED / PARTIAL / REVIEWING**。本段请求事务在既有隔离 Preview 验证；S01-B / S02 PARTIAL，C / S03—S06 NOT_STARTED，P4-F6-5 REVIEWING。
- 授权依据：Owner 在[完整管理适配与历史收窄](M2_人员权限完整管理适配与收窄实施记录.md)后指示“下一步”，推进已列明的 HTTP 整请求事务、提交前复核及普通角色写边界，不新增业务子轮。
- 本文为本段主记录；机器证据见[请求边界与复核验收摘要](evidence/人员权限_HTTP请求边界与提交前复核验收摘要_20261009.json)。superpowers 当前不可用，按项目规则人工执行。

## 1. 交付与默认边界

本轮修改一个既有源码文件，新增五个 Python 文件；技术文件名遵循 Python 导入约定，主记录和证据采用中文。

| 文件 | 实际变更 |
| --- | --- |
| [managed_relations.py](../../apps/hbos_portal/hbos_portal/organization/managed_relations.py) | 单次不可变待提交 proof，绑定真实 DB / 会话、政策匹配、原命令历史及当前事实；提交前重新锁定、取时和复核 |
| [management_http.py](../../apps/hbos_portal/hbos_portal/organization/management_http.py) | 默认关闭的服务端绑定、严格请求解析、请求提交 Gate、完整回滚、WSGI 响应缓冲与原生会话收尾 |
| [organization_relations.py](../../apps/hbos_portal/hbos_portal/api/organization_relations.py) | 四个固定 `@frappe.whitelist(methods=["POST"])` 方法，不接收任意命令或管理身份 |
| [test_management_http.py](../../apps/hbos_portal/tests/test_management_http.py) | 50 项正式离线请求 / 提交 / 原生生命周期模拟 |
| [test_management_finalization.py](../../apps/hbos_portal/tests/test_management_finalization.py) | 14 项 proof / 当前政策 / 来源 / 历史复核测试 |
| [integration_management_http.py](../../apps/hbos_portal/tests/integration_management_http.py) | 既有精确空 Preview，15 项真实原生密码会话及完整 WSGI 请求验收，无建表 / migrate |

`ManagedHTTPApplication(native_application, binding=None)` 默认关闭。启用须运维明确安装包装，提供精确 Site / 数据库 SHA256、Origin、可信固定批准清单和 enabled=True 服务端对象。请求不能选择工厂、clock、数据库、批准人或适配器。本轮只在 Preview 验收进程临时绑定合成政策；没有生产服务工厂、Site 配置或 Hook 自动安装，也没有真实管理人 / 批准清单。

普通 Frappe 应用即使分发到四个 Python 方法，缺请求局部能力仍返回 NOT_SUPPORTED 并回滚。只有四个精确路径受包装；别名 / 通用 cmd 不获得写能力，其他既有路由沿用原行为。本轮没有修改既有 people_access 查询、前端、schema、Frappe 核心或全局类方法。

## 2. 请求与响应契约

请求使用当前原生非 Guest cookie 会话，cookie.sid 须等于原生 session.sid；拒绝 Authorization 替代。精确 Origin、实际 scheme://host、POST 路径与服务端绑定一致；独立要求非空保存的原生 CSRF token 和正确请求头，不能因原生测试配置放宽 CSRF 而省略此检查。

原始 JSON 不超过 16 KiB；拒绝查询字符串、重复键、NaN / Infinity、非对象、额外字段。顶层只允许 payload、idempotency_key、expected_revision、reason，更新另需 record_id；事实 payload 沿用严格服务契约。创建版本为 0，修改正整数，同键同内容重放仍重新检查当前政策 / 来源；客户端 actor / subject_user / policy / proof / ignore_permissions 不接受。

Frappe 的成功 `message` 封装为 `{"ok": true, "data": ...}`。仅真实事实提交和原生请求收尾成功后释放，返回 `transaction_pending=false`、`save_status="committed"`。`runtime_verified=false`、`authorization_effect="none"`、`position_authorization_connected=false` 表示尚未连接岗位业务授权，不能提示“权限已生效”。内部 RelationService 仍返回 pending，且从不自行 commit。

| 错误码 | HTTP / 处理 |
| --- | --- |
| INVALID_REQUEST | 400；请求字段 / 格式不符，无自动重试 |
| UNAUTHENTICATED | 401；重新登录 |
| FORBIDDEN | 403；政策、本人受益、会话 / CSRF / 来源 / 方法拒绝 |
| CONFLICT | 409；revision 或同键异内容冲突，核对后重新发起 |
| CONFLICT_RETRY_REQUIRED | 409；来源 / 政策或整事务上下文变化，重启完整请求 |
| SOURCE_UNAVAILABLE | 503；可信来源 / 历史或回滚未确认，保留原键核对 |
| NOT_SUPPORTED | 503；未安装可信启用绑定 |
| SAVE_RESULT_UNKNOWN | 409；COMMIT 可能执行或已提交后收尾失败，保留原键和相同内容核对；不能声称已回滚 |

原生认证 / CSRF / 方法检查在执行器之前拒绝时，包装也丢弃其原始响应并按固定状态映射统一错误，不解析或复述原异常。统一错误只含既有 error_response 契约的 code、message、retryable、trace_id；不返回政策匹配、人员明文或原异常。所有响应 private/no-store。诊断清除 form_dict，应用日志仅记录代码及 trace，日志失败不放行，也不在失败事务中写审计并 commit。retryable 不是客户端自动重放或自动恢复业务的授权。

## 3. 同一请求的实际提交闭环

服务发出 `PendingManagementProof`，冻结原始请求摘要、命令 / actor、Site / 数据库、原 before / after 历史、当前主记录 / 岗位、来源摘要和当前政策匹配；实际对象绑定同一 service、实际 native.local.db、来源代次、实际 local.session 对象与 SID。copy / 替换、跨连接 / 服务 / 会话、已消费或丢弃 proof 都拒绝。

Gate 在请求校验前装入当前实际数据库实例，禁止服务内提前 commit、递归或重复事实 commit。先运行全部已排队 before_commit（包括其追加回调），然后将只读最终 guard 排在尾部。guard 在同一实际事务中重建根锁能力、读取当前政策头及历史，重新加载锁定来源和 UTC 时间，核对原命令与当前事实；失败完整 rollback，丢弃 proof。政策到期、撤销 / generation 改变、来源或主记录改变不能以此前 pending 放行。

只有 guard 已运行且原生 commit 正常返回才标记事实已提交；原生事务控制 suppress / no-op 不能变成保存成功。WSGI 包装缓存 status / headers / body，覆盖核心 sync_database 在路由异常捕获之外抛出的错误。提交前拒绝完整回滚；回滚失败关闭实际连接、禁用本请求 sql 防止 lazy reconnect，不继续新事务。真实 COMMIT 可能执行或 facts_committed 后的异常一律结果未知，同键核对返回原结果，不能追加重复事实。

Frappe.db 是 LocalProxy，frappe.destroy 后不再绑定；Gate 与 proof 持有本请求的实际 native.local.db，清理后恢复原方法，不通过已销毁代理访问数据库。本轮首轮实际验收暴露并修复这一问题，新增代理解绑 / 真实连接替换测试。

## 4. 原生会话收尾兼容与验证范围

本机 Preview 核心为 Frappe 16.26.3。实际核心先 sync_database 提交事实，再把原生 Session.update 排入 request.after_response；会话超过刷新阈值时该方法可能更新 tabSessions / User 登录元数据，并自行 commit。它在 ClosingIterator.close 内执行，单纯“一次 commit 后永远拒绝”会破坏合法原生会话刷新。

仅替换当前请求队列内精确原 Session 对象的原 update 绑定方法。事实已提交、DB / session_obj / session / SID / actor 不变、transaction_writes=0、before_commit / after_commit 的实际 `_functions` 队列为空，才临时允许该原生方法一次维护提交；第三次提交、其他回调或身份变化拒绝并报告结果未知。Session 类和核心文件没有改动。

这是已核验 Frappe 原生队列 ABI 的限定兼容；队列结构变化时关闭，须重新验收；未识别方法不授予尾部提交能力，其 commit 仍拒绝。没有为任意 after_response 业务写入发放第二次提交能力。真实刷新测试自然满足 601 秒阈值，执行原 Session.update，无替代原生方法的假成功。

## 5. 测试、缺陷修复与数据保持

**297 / 297 离线测试 PASS**：新 HTTP 50 + 提交复核 14 + 前序回归 233。覆盖请求白名单 / CSRF / 默认关闭、实际连接代理、单次 proof、原命令重放后的当前政策、源 / 历史改动、到期、完整回滚、提交未知、提交后重入、原生会话维护一次提交和 no-op commit 拒绝。纯内存测试不证明原生数据库事务；下面单列真实结果。

Preview 为既有 `hbos-portal-preview-backend-1 / portal-preview.localhost`，数据库 SHA256 `c1278fd11beed36c90a5d0b507015749e5c14a4627249507aeef9b95a726f953`，MariaDB 11.8.8、REPEATABLE-READ；八类关系 / 政策表预先存在且为空。沿用前序备份，不做 DDL、migrate、新 Site / bench / App、安装或服务重启；完整恢复仍 NOT_RUN。

**15 / 15 真实 WSGI 场景 PASS**。Werkzeug Client 调用实际原生 Frappe WSGI，合成 User 使用随机密码走原生 login，再复用真实 cookie / CSRF 会话；不使用 Owner / Administrator 密码，不伪造 SID。测试政策 clock 固定 2026-10-10，测的是明确 synthetic 政策时点，不宣称真实管理配置生效。场景包括四写路由、真实普通 System Manager 无政策拒绝、GET / 注入字段 / Guest / CSRF / Origin 拒绝、默认关闭、同键重放与冲突、延迟至到期、before_commit 政策 / 来源 / 主记录变化、提前或递归 commit、修订 / 收据 / 序列化故障完整回滚、回滚失败、SQL COMMIT 返回 / after_commit 故障后的 UNKNOWN 和原键核对，以及真实会话刷新后第三次提交拒绝。

四次实际执行结果均保留：首轮 13 项中 3 PASS / 10 ERROR（含子测试 16 个错误），根因为清理后 LocalProxy 解绑；产品已改实际 DB 引用。第二轮 15 项中 12 PASS / 3 ERROR，验收脚本错用 type(f.db) 捕获 LocalProxy 类，改为 type(f.local.db)。第四轮 15 PASS。四轮八类表清空和原生完整行指纹保持均 PASS；不删去失败证据。

三次自动审批传输连接中断时没有执行，后续相同范围恢复通过，没有绕过审核。SQL / 回滚 / 回调故障均为请求局部合成注入，不是实测网络分区。Administrator HTTP 无政策场景 NOT_RUN；实际管理人、完整 Date 资格、全量来源生命周期 HTTP / 独立连接组合、全审计链和备份恢复未验收。

合成政策、事实、历史、收据及人员精确清理；原生密码 __Auth、Has Role、tabSessions / Redis session 和本次新增 login / error log 按精确合成人员 / 新增记录清理，保留原记录。最后 Preview User 2，Employee / Company / Department / Designation 0，八类管理表全部 0，原生八类表指纹与测试前一致。

5178 对应 `frontend` 原站仅只读 SQL 聚合复核，数据库 SHA256 `98d2b2166d96e1969c24b420238b40e82a7572a59105b5e31d4f6f215b6aa4cb`：User 18 / Employee 0 / Company 1 / Department 14 / Designation 31，八类管理表仍不存在。没有原站写入、账号 / 角色 / schema / 配置 / 服务变更；本轮未做浏览器在线复验，5178 保持既有真实只读模式，正式写入未启用。

## 6. 门禁与下一段

| 门禁 | 当前可证明结果 |
| --- | --- |
| MG12 | 管理查询过滤前计数 / 分页 / lookup 未实施，NOT_RUN |
| MG13 | 原生 cookie / CSRF / POST、普通 System Manager 无政策写入拒绝通过；Administrator HTTP 场景未运行，整项 PARTIAL |
| MG19 | 本段延迟到期、before_commit 政策 / 来源 / 主记录变化与提交边界通过；完整入口 / 并发组合未覆盖，整项 PARTIAL |
| MG20 | 前段原生历史严格收窄结果保留；本段 proof 不放宽规则，完整 HTTP 失效来源清理 / 独立连接生命周期未覆盖，PARTIAL |
| MG21 / MG22 | 前段 ORM 保护证据保留，通用 REST / Desk / Report / import 等整条 HTTP 与统一查询域未验收；people_access 仍原生权限，不能以其可读当管理政策批准 |
| MG23 | 请求失败回滚 / 回滚失败终止、提交未知和本地日志失败拒绝通过；真实网络中断与完整审计投递仍未证明，PARTIAL |

S01-B / S02 保持 PARTIAL，C / S03—S06 NOT_STARTED；事实保存与业务 Grant 分离，真实岗位授权 NOT_RUN。Q1 / Q2、具名管理人 / 可信批准清单、Date 资格、固定 P1 / 完整恢复 / Owner 门禁保留。下一段实现默认关闭的管理 GET 查询：独立 read / lookup 政策、先限制数据范围再计算总数和分页、受限字段及普通角色查询边界；在 Preview 验证后再讨论生产启用和 UI 保存入口。

状态、当前里程碑、M2 Gate、当前 / 前序主记录、规格及公共入口已同步。CLAUDE.md / AGENTS.md 仅承载规则，检查无需修改。未创建分支、提交、推送或对外部署。

收尾复核 PASS：本轮相对开始时指纹共 29 个文件变化（6 个源码 / 测试、新主记录及证据、21 个既有文档），其余 1246 个既有文件保持；Python 3.10 语法、JSON / 源码摘要与测试计数、335 个本地 Markdown 链接、空白、公共状态和 M2 Gate 一致性通过，分支 / HEAD 保持、冲突索引为空。独立安全复核通过实际连接 / 会话 proof、原生会话维护限定能力、已提交后 UNKNOWN、预分发错误脱敏与日志失败仍拒绝；不提升尚未运行的门禁。
