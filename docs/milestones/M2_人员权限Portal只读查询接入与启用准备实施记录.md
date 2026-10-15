# M2 人员权限 Portal 只读查询接入与启用准备实施记录

2026-10-10 最新接续：[原站只读预检](M2_人员权限原站只读预检记录.md)已完成，**S02_ORIGINAL_READONLY_PREFLIGHT_COMPLETED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。实际frontend / DB摘要精确匹配，五来源InnoDB与24必需列PASS，COUNT18/0/1/14/31；八管理表全缺，正式预检在tables以STORAGE_PREFLIGHT_SCHEMA_INVALID停止。10诊断SELECT含正式预检2，零transaction_writes、rollback/destroy PASS，未初始化。只读诊断完成不等于结构或启用PASS；管理GET仍NOT_READY。原站备份工具release路径缺失，现已有镜像 / 权限 / 磁盘 / 备份总量仅元数据确认，原样stdin备份操作包已准备但未执行。下一段先确定停写一致性窗口 / 原服务恢复措施，再按同次私有备份与隔离SQL恢复范围执行；不建表 / 人员 / 政策 / pins或启GET。5178既有真实只读；本段未改代码 / 配置 / 服务 / 缓存 / schema，未备份 / 恢复或浏览器复验。前段14原生 / 428离线PASS为历史证据，本段未重跑。S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，Grant NOT_RUN，P4-F6-5 REVIEWING；原Q1/Q2、Date、固定P1 / 完整恢复 / Owner及管理门禁保留。 以下为前序交付当时的记录。

- 日期：2026-10-09；沿用 Owner 指定分支 `m2-r11@27d3558`。
- 状态：**S02_PORTAL_READONLY_INTEGRATION_PREPARED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。页面与客户端离线验证完成，正式管理读取 **NOT_READY**，改动后的 5178 浏览器复验 **NOT_RUN**。
- 授权：Owner“下一步 / 继续”，接续[普通查询旁路与人员目录边界](M2_人员权限普通查询旁路与人员目录边界实施记录.md)列明的前端分域、手机号筛选对齐和可审查启用准备。既有人员 / 权限页 V2 原型已获 Owner 接受，本轮沿用其布局和样式。
- 工程：superpowers / frontend-design 在当前环境不可用，按项目规则人工实现、测试与独立审查；未创建分支、提交或推送。
- 交付：[正式路径启用配置与验收清单](../plans/人员权限_5178只读管理启用配置与验收清单.md)、[无人员明细验收摘要](evidence/人员权限_Portal只读接入与启用准备验收摘要_20261009.json)。

## 1. 实际交付

人员页保持 ID、人员名称、部门、岗位、手机号、角色、操作七列；权限页保持角色、创建时间、描述及操作结构。手机号仅脱敏显示，移除不受支持的手机号筛选输入及请求参数；人员目录的姓名 / 部门 / 岗位筛选和原生角色读取继续按原生 ERP/HR 权限执行。User 和 Employee 仍须显式选择，不通过姓名、手机号或 User ID 推导 Employee 身份。

[人员页](../../frontend/hbos-portal-web/src/views/PeopleAccessView.vue)的 Employee 详情增加任职只读查询；只提交当前 Employee 的稳定 record_id。User 详情不查询任职。权限页增加“查看岗位”只读弹窗，使用相同页面表格 / 弹窗样式；它不读取或更改角色关联。新增 / 编辑 / 删除 / 保存和业务岗位授权继续关闭。

[管理查询组件](../../frontend/hbos-portal-web/src/components/peopleAccess/ManagedOrganizationReadOnly.vue)先请求当前管理上下文，再按独立 position.read 或 assignment.read 操作发出相应 GET。分页、搜索、total 均来自管理服务；不在客户端拉全量或合并政策范围。加载前清除旧行 / 计数，无权、未启用、错误不冒充“共0条”，不回退到原生目录或合成记录。目标切换、刷新与卸载的代次检查扣留旧响应；该客户端判断不是服务端授权证据。

岗位表显示最小岗位 / 组织 / 状态 / 版本字段；任职表显示稳定岗位标识、主岗、状态及 UTC 期限。为避免跨范围资料补全，任职表不通过原生组织 / 岗位目录换取名称；后续名称投影应由服务端在同等管理范围内提供。lookup_people 客户端已准备，但本轮没有另建人员选择或写入流程。

## 2. 两类读取契约

[peopleAccessApi](../../frontend/hbos-portal-web/src/services/peopleAccessApi.ts)要求明确 native_personnel、management_policy_applied=false、read_only=true；人员 / 角色页还要求 position_authorization_connected=false。严格校验来源、字段和脱敏电话，不接受未经声明的管理 / 批准 / 隐私投影；人员请求只有 source、page、page_size、name、department、position。原生目录可读不证明获准管理查询。

[organizationManagementApi](../../frontend/hbos-portal-web/src/services/organizationManagementApi.ts)仅提供 get_management_context、list_positions、get_person_assignments、lookup_people 四个固定 GET。请求参数白名单、页码 / 大小、Unicode 字数、稳定 UUID、UTC 微秒与日历 / 期限、最小投影、完整独立操作范围、Employee 请求身份、分页数量和重复标识均校验；未知字段或响应来源缺失拒绝。管理成功仍为 read_only=true / runtime_verified=false / authorization_effect=none / position_authorization_connected=false，不宣称业务 Grant 已接通。

[共享客户端](../../frontend/hbos-portal-web/src/services/frappeClient.ts)为这些受控 GET 显式取得原生保存的 CSRF token，保留 cookie、token 单飞和缓存；普通 GET 不增加 token 获取或请求头。共享 token bootstrap 与受控 GET 用内部 Axios config 代次标识保护错误副作用，标识不进入远程 header / params。受控 GET 发出前和成功返回后核对会话代次；旧成功、旧401 / CSRF错误和旧 bootstrap 错误不能恢复旧主体数据、清除新 token 或退出新会话。

仅固定管理 GET 的非2xx错误保留审核过的公开码 / 固定中文提示，包括 CONFLICT_RETRY_REQUIRED 与 retryable；不展示原始政策 / 服务器消息，不把所有403当作 token 过期，不自动重试 / 重放请求。其他端点和现有 POST 协议保持；本轮未新增任何写客户端调用。

## 3. 测试与独立审查

| 检查 | 最终结果 |
| --- | --- |
| 前端 Vitest，真实模式环境 | **179 / 179 PASS**，失败 / 跳过均0 |
| 本轮新增测试 | **88 项**：管理契约42、原生目录契约19、安全 GET15、管理组件11、真实人员页新增1；前序91保留 |
| Node 基础测试 | **35 / 35 PASS** |
| 类型 / Lint | PASS |
| Mock 内容门禁 / LIMS 前端契约 | PASS |
| `VITE_PORTAL_DATA_MODE=frappe npm run build` | PASS；3408模块，既有大 chunk 警告仍存在 |
| 独立代码审查及纯内存复现 | PASS；4项复现，不计入179项测试或真实 HTTP 验收 |
| 5178 改动后浏览器与正式管理 GET | **NOT_RUN** |

契约测试覆盖未知 / 敏感字段拒绝、原生 / 管理来源分离、范围 / 操作不能替代、最小投影、精确 Employee 身份、UTC / 分页、电话输入拒绝；组件测试覆盖上下文先行、独立操作、未启用 / 无权 / 服务错误、服务端筛选分页、刷新清空、目标切换及卸载。安全 GET 测试覆盖普通 GET 不变、token 单飞、失败时零查询、cached / pending token 代次、已发旧成功与旧401 / CSRF错误、新会话 token 保持及公开错误码 / 无自动重放。

首轮类型检查发现 Object.hasOwn 不符合仓库 ES2020 目标，改为 Object.prototype.hasOwnProperty.call 后通过。独立审查实际复现已发 GET 在换会话后释放旧成功结果，另发现 CONFLICT_RETRY_REQUIRED 映射缺失；已补响应代次、旧错误 / bootstrap 副作用保护和映射，新增6项安全测试后全部回归通过。中间162 / 173项测试结果是逐段实现证据，最终以179项为准。文件创建及一次 npm 执行目录输错在实际命令层失败，已纠正，没有因此更改产品行为。

前段后端372项离线、9批388请求 / 80模型检查、16管理查询 / 15写接口回归仅保留为历史证据，本轮未重跑、不能并入本轮真实运行结果。后端 Python / Hook / schema / 原机器证据按本轮开始指纹保持。

## 4. 5178 与自动审批阻断

本轮在改动前读取既有 5178 人员页，观察到旧手机号筛选和真实只读页面；这不是新实现的复验。已确认本机5178由既有 Node进程监听，使用原正式源码目录；本轮没有启动演示服务或切换模式、重启服务、刷新原站 Hook缓存或改写代理配置。真实模式构建产物包含新增只读页面，但构建通过不证明既有浏览器或后端进程已加载。

改动后的浏览器状态读取因自动审批传输断开未执行，审核并未判定动作不安全。工具明确禁止绕过或间接完成同一访问，本轮未再次尝试浏览器 / 替代网络页面验证；继续完成代码、测试、构建及配置清单。新页面在线展示、登录会话和当前后端契约加载仍 **NOT_RUN**，应由 Owner 直接打开5178确认或后续获准工具访问复验。没有新截图或在线成功声明。

原站 User18 / Employee0 / Company1 / Department14 / Designation31 与八类管理表不存在，来自前轮具名只读 SQL 摘要，本轮未再次 SQL 读取。没有 Site 账号、角色、政策、批准清单、schema、根锁、配置或数据库操作，没有 DDL / migrate / 新备份 / 完整恢复 / Grant / 对外发布。后端变更是否在线生效不能凭工作区源码推定。

## 5. 正式读取启用清单与缺口

新清单明确两类读取、事实 POST、业务 Grant 四个独立边界，列出现有 ManagedHTTPBinding / PolicyApprovalPin / 管理规则的精确字段和批准来源。它不是可直接填入 site_config 的新配置规范：源码尚无正式私有配置解析 / 多 Site 装配、生产 WSGI 安装 / 启动预检、政策运维导入 / 更新命令，以及原站定向 schema / 恢复准备流程。

现有管理 GET 也依赖八类 schema、relations-v1 根锁和当前政策。GET 运行不写岗位事实，但 schema / 根锁 / 政策初始化为持久准备，必须分别记录授权、备份 / 恢复和指纹；不能因为页面只读而自动在生产创建。仅查询包装可候选启用，四个 POST 保持独立关闭。真实 origin、Site / 数据库、Host / scheme、cookie SID / CSRF、当前政策 / pins 与返回前复核都须原站验证；不得把 Preview CLI改参数后用于原站。

原站 Employee0和管理事实缺失不能用虚构数据填充；合法空结果不足以证明跨组织隔离。回退关闭查询装配 / 私有配置，保留原生保护 Hook、schema、历史与当前政策，不删除表或恢复旧 active 政策。

## 6. 状态、门禁与下一段

**S01-B / S02 PARTIAL；C / S03—S06 NOT_STARTED；真实岗位授权 NOT_RUN；P4-F6-5 REVIEWING**。本轮前端子集 PASS 不替代 MG12 / MG19 / MG20 / MG21 / MG22 / MG23 整体门禁；可信内部 get_all / 忽略权限 / 无角色共享 / 自定义 SQL 仍不是沙箱。Administrator 无政策真实HTTP、容量阈值、完整生命周期 / 审计 / 网络中断、具名管理主体、Q1 / Q2、Employee Date、固定P1、完整恢复与 Owner真实验收继续保留。

下一段可先在既有分支实现并审查默认关闭的正式配置加载 / 查询装配与目标预检，完成错误配置 / pins / 多 Site / 关闭路径的离线和隔离验证；原站持久准备、管理主体和真实批准另按具体门禁推进。未以“继续”把本段前端接入自动扩成生产启用或下一业务里程碑。

已同步 PROJECT_STATUS、CURRENT_MILESTONE、M2 Gate、前序相关规格 / 主记录与 README / AI_CONTEXT / READING_GUIDE / 前端 README。CLAUDE.md / AGENTS.md仅承载规则，已检查，无需修改。本轮未创建分支、提交或推送。

收尾范围 QA PASS：本轮38文件变化（10个前端源码 / 测试、28个文档 / 证据），29个既有文件修改、9个新增、1258个既有文件保持，无删除或意外变更；402个本地Markdown链接、JSON、10个源码摘要、公共状态 / M2 Gate、ES2020类型 / 构建、空白与空冲突索引通过。后端 / Hook / schema / 前序机器证据、CLAUDE.md / AGENTS.md保持本轮开始指纹。分支仍为m2-r11@27d3558，没有新分支 / 提交 / 推送；代码独立审查PASS，浏览器阻断和原站NOT_READY限制如实保留。

最终独立文档复核PASS：测试计数、源码 / 构建摘要、原站NOT_READY、改动后浏览器NOT_RUN、前段历史证据及所有状态 / 门禁一致，未发现新增问题。
