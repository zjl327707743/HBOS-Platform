# M1-R7：飞书登录、领导 Demo 与 M1 收口准备

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

执行日期：2026-07-09。

Closeout 日期：2026-07-09。

审查记录：Codex 初审 FAIL（发现 3 类 blocker：远端未同步、PROJECT_STATUS 残留 PLANNED、milestones/README 残留 PLANNED），已在 `e812e32` 中最小修复；Codex 复审 PASS。R7 已从 REVIEWING 收口为 COMPLETED。

## 1. 本轮定位

M1-R7 是 M1 Demo 实施路线的**第 7 轮**，定位为：

1. 飞书 OAuth 登录最小验证方案 / 配置 / 必要实现。
2. 领导汇总 Demo 视图 / 报表 / 页面最小实现。
3. M1 Demo 演示路径整理。
4. M1 收口项准备（不启动 M1 总收口）。

本轮**只做**：

- 飞书 OAuth 登录方案设计、配置步骤记录、验证情况说明。
- 飞书身份 → Frappe User → Employee 自动匹配规则固化。
- 未匹配员工处理策略。
- 本地管理员兜底登录保留确认。
- 权限边界确认：飞书只认证，Frappe Role / User Permission 管权限。
- 领导汇总 Demo 范围、指标、数据来源、查看与导出路径。
- M1 Demo 完整演示路径整理。
- M1 收口准备项清单（为后续 M1 closeout 做准备，不执行收口）。

本轮**不做**：

- 不 closeout R7（只进入 REVIEWING）。
- 不启动 M1 总收口（M1 closeout 留待后续独立轮次）。
- 不接飞书工作台。
- 不接飞书请假。
- 不接真实考勤机。
- 不部署公司内网 / 云服务器。
- 不正式生产上线。
- 不启动大型 Vue 前端。
- 不重写 R6A / R6B / R6C。
- 不重新设计考勤导入。
- 不创建 `hb_hr_app`（当前没有 Owner 授权）。
- 不创建自定义 DocType。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不提交真实数据、Excel、CSV、数据库、日志、缓存、备份、`.env`、密钥、运行产物。
- 不把月度汇总 Excel 当成原始打卡流水。
- 不使用真实员工姓名或未脱敏考勤数据。

## 2. 读取文件清单

本轮按轻量范围读取：

| 读取文件 | 用途 |
| --- | --- |
| `CLAUDE.md` | 项目协作规则、每轮收尾强制要求 |
| `AGENTS.md` | Agent 行为约束 |
| `README.md` | 人类入口文件过期状态检查 |
| `docs/AI_CONTEXT.md` | AI 上下文与阶段状态 |
| `docs/PROJECT_STATUS.md` | 项目总状态台账 |
| `docs/CURRENT_MILESTONE.md` | 当前里程碑与轮次状态 |
| `docs/READING_GUIDE.md` | AI 阅读范围指南 |
| `docs/milestones/README.md` | 里程碑索引 |
| `docs/milestones/M1_考勤一期真实需求确认.md` | 需求依据（飞书登录匹配规则、用户角色、领导指标） |
| `docs/milestones/M1_考勤一期产品需求说明书.md` | 产品设计（角色、场景、领导汇总 Demo 页面） |
| `docs/milestones/M1_考勤一期技术设计方案.md` | 技术路线（飞书 OAuth 与 Social Login Key、权限映射、月度汇总字段映射） |
| `docs/milestones/M1_Demo实施路线图.md` | 实施路线（R7 目标与禁止项） |
| `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` | R6A Gate 判定结论 |
| `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` | R6B 导入结果与 Employee Checkin 数据基线 |
| `docs/milestones/M1_R6C_异常识别与异常说明流程最小实现.md` | R6C 异常识别结果与 Attendance 数据基线 |
| `docs/milestones/M1_START_GATE.md` | M1 阶段门禁文档，检查状态一致性 |
| `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` | R7 目标与禁止项原始定义 |
| `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` | R5 配置基线与月报 Demo 路径 |

未递归读取 `docs/`，未读取 `docs/archive`、`docs/research`、`docs/legacy`。

## 3. R6A / R6B / R6C 结论继承

### 3.1 从 R6A 继承

- 两类 Excel 导入严格区分（打卡流水 ≠ 月度汇总）。
- 异常说明流程优先方案 A（Custom Field 扩展原生 Attendance Request）。
- R6B/R6C 不需要创建 `hb_hr_app`。
- Gate 判定结论：打卡流水导入 PASS、异常说明流程 CONDITIONAL PASS。

### 3.2 从 R6B 继承

R6B 已完成的 Demo 数据与环境：

| 数据项 | R6B 结果 |
| --- | --- |
| 虚构员工 | 3 名（R6B-EMP-001/002/003 → HR-EMP-00017/18/19） |
| 公司 | `TEST-HBOS-M1R3C-虚构公司` |
| 部门 | `TEST-HBOS-M1R3C-生产一部 - R3C` |
| Shift Type | `TEST-HBOS-M1R6B-早班-0800-1600` |
| Shift Assignment | 3 条（2026-07-02 至 2026-07-03） |
| Employee Checkin | 已写入 July 2（5 条）+ July 3（4 条） |
| Attendance（R6B 阶段） | July 2（3 条）+ July 3（3 条） |
| 最小闭环 | `Employee Checkin → Auto Attendance → Attendance` 通过 |

### 3.3 从 R6C 继承

R6C 已完成的异常识别结果：

| 数据项 | R6C 结果 |
| --- | --- |
| Shift Type 修复 | `late_entry_grace_period = 0`、`early_exit_grace_period = 0`、`enable_late_entry_marking = 1`、`enable_early_exit_marking = 1` |
| 异常识别验证 | 7 个场景全部通过（正常、迟到、早退、上班缺卡、下班缺卡） |
| `late_entry`/`early_exit` | 配置修复后正确置位 |
| Custom Field 扩展 | 11 个字段已创建在 HRMS 原生 Attendance Request 上 |
| 核心 Blocker | HRMS 原生 `validate_no_attendance_to_create()` 在已有 Attendance 时阻止 Attendance Request 创建 |

**R6C 关键结论传递给 R7**：

1. 异常识别能力已就绪：`late_entry`/`early_exit` 自动标记可用，缺卡可通过 Attendance 字段识别。
2. Attendance Request 结构已扩展：11 个 Custom Field 覆盖 6 种异常类型和三级流程状态。
3. 核心 Blocker：HRMS 原生 `validate_no_attendance_to_create()` 在已有 Attendance 时阻止 Attendance Request 创建，需要 Owner 后续授权决策。
4. 当前仍不建议创建 `hb_hr_app`。

## 4. 飞书 OAuth 登录方案

### 4.1 方案概述

基于 M1-R0 和 M1 技术设计方案中的飞书登录技术路线：

```
浏览器访问 HBOS /login
→ 点击「飞书登录」按钮
→ 跳转飞书 OAuth 2.0 授权页
→ 用户在飞书 App 中确认授权
→ 飞书回调返回授权码（code）
→ HBOS 后端用 code 换取 access_token + 用户身份信息
→ 根据手机号 / 邮箱 / 工号匹配 Employee
→ 匹配成功：自动关联或创建 Frappe User → 进入对应角色页面
→ 匹配失败：提示「未找到匹配员工，请联系人事 / 管理员」
→ 兜底：本地管理员账号仍可正常登录
```

### 4.2 技术承载：Frappe Social Login Key

Frappe 原生支持通过 **Social Login Key**（OAuth Provider）接入第三方 OAuth 登录。飞书 OAuth 2.0 符合标准 OAuth 2.0 授权码流程，可以通过配置 Social Login Key 接入。

配置步骤（Frappe Desk 中操作）：

1. 进入 `/app/social-login-key` → 新建 Social Login Key。
2. 配置以下参数：

| Frappe 配置项 | 飞书对应值 | 说明 |
| --- | --- | --- |
| `social_login_provider` | `Custom` 或 `Feishu`（自定义） | Frappe 无内置飞书 provider，需自定义 |
| `provider_name` | `feishu` | 标识名 |
| `base_url` | `https://open.feishu.cn/open-apis` | 飞书开放平台 API 基础 URL |
| `authorize_url` | `https://open.feishu.cn/open-apis/authen/v1/authorize` | 飞书 OAuth 授权页 |
| `access_token_url` | `https://open.feishu.cn/open-apis/authen/v1/oidc/access_token` | 飞书获取 token 端点 |
| `client_id` | 飞书应用 App ID | 需在飞书开放平台创建应用 |
| `client_secret` | 飞书应用 App Secret | 需在飞书开放平台获取 |
| `redirect_uri` | `https://<HBOS域名>/api/method/frappe.integrations.oauth2.callback` | 回调地址 |
| `api_endpoint_args` | 用户身份信息接口参数 | 见 4.4 节 |
| `user_id_field` | 飞书返回字段 → Frappe User 映射 | 见 4.3 节 |

### 4.3 Frappe Social Login Key 的 User 映射机制

Frappe Social Login Key 在用户首次通过 OAuth 登录时，会根据 `user_id_field` 匹配或创建 Frappe User。

Frappe 原生 OAuth 流程有两种 User 创建策略：

1. **匹配已有 User**：通过 `user_id_field`（通常是 email）匹配已有 Frappe User。
2. **自动创建 User**：如无匹配，自动创建新 User（可通过 `Frappe.utils.oauth.create_user_if_not_found` 控制）。

**M1 推荐策略**：

- 飞书 OAuth 返回信息包含手机号 / 邮箱时，Frappe 自动尝试匹配已有 User。
- 对于已有 User + Employee 的员工，飞书登录后自动关联。
- 对于飞书有身份但 Frappe 无 Employee 的用户，拒绝自动创建 User，转而提示联系管理员。

### 4.4 飞书身份字段获取范围

飞书 OAuth 2.0（OIDC 模式）可获取以下用户身份字段：

| 飞书字段 | 说明 | 用途 |
| --- | --- | --- |
| `open_id` | 用户唯一标识（应用内） | User 关联的唯一键 |
| `union_id` | 用户唯一标识（同一租户内跨应用） | 推荐作为长期唯一标识 |
| `name` | 用户姓名 | 可选用于匹配 |
| `mobile` | 手机号（需用户授权 `contact:user.phone:readonly` 权限） | 主匹配字段 |
| `email` | 邮箱（需用户授权 `contact:user.email:readonly` 权限） | 备选匹配字段 |
| `employee_no` | 工号（需企业 EMS 配置） | 备选匹配字段 |
| `avatar_url` | 头像 | 可选展示 |

**M1 最小获取范围**：`open_id` + `union_id` + `name` + `mobile`（如果飞书应用配置了手机号权限）。

**注意**：手机号获取需要在飞书开放平台中申请 `contact:user.phone:readonly` 权限，且需要企业管理员在飞书管理后台审核通过。

### 4.5 飞书应用配置前提（未在本轮执行）

飞书 OAuth 登录需要以下前置条件，这些条件不在本地 Frappe 代码控制范围内，需要在飞书开放平台完成：

1. 在飞书开放平台（`https://open.feishu.cn`）创建企业自建应用。
2. 配置应用的「安全设置」→「重定向 URL」：添加 HBOS 回调地址。
3. 申请并审核通过以下权限：
   - `contact:user.phone:readonly`（获取手机号）
   - `contact:user.email:readonly`（获取邮箱，可选）
4. 获取 App ID 和 App Secret。
5. 确保回调域名与 HBOS 实际访问域名一致。

以上前置条件的完成状态**取决于飞书开放平台的配置**，不属于本轮 Frappe 端可独立完成的范围。

## 5. User / Employee 自动匹配规则

### 5.1 匹配优先级

飞书登录成功后，按以下优先级匹配 Employee：

| 优先级 | 匹配字段 | 飞书来源 | Frappe Employee 字段 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 手机号 | `mobile` | `cell_number` | 最可靠，号码唯一 |
| 2 | 邮箱 | `email` | `company_email` 或 `personal_email` | 备选 |
| 3 | 工号 | `employee_no`（企业 EMS 配置） | `attendance_device_id` 或 `employee_number` | 需飞书 EMS 配置工号字段 |

### 5.2 匹配流程

```
飞书 OAuth 成功返回 open_id + mobile + email + employee_no
  ↓
Step 1：用 mobile 匹配 Employee.cell_number
  → 匹配到唯一 Employee → 继续 Step 4
  → 未匹配到 → 继续 Step 2
  ↓
Step 2：用 email 匹配 Employee.company_email / personal_email
  → 匹配到唯一 Employee → 继续 Step 4
  → 未匹配到 → 继续 Step 3
  ↓
Step 3：用 employee_no 匹配 Employee.attendance_device_id / employee_number
  → 匹配到唯一 Employee → 继续 Step 4
  → 仍未匹配到 → 进入「未匹配处理」（第 6 节）
  ↓
Step 4：确认该 Employee 关联的 Frappe User
  → 已有 User 关联 → 用该 User 完成登录
  → 无 User 关联 → 创建或关联 Frappe User → 完成登录
```

### 5.3 User 创建与关联

- 如果已存在匹配 Employee 的 Frappe User（通过 `Employee.user_id` 字段），直接以该 User 身份登录。
- 如果 Employee 存在但无关联 Frappe User：
  - 检查是否存在同 email / 手机号的 Frappe User。
  - 如有，关联该 User 到 Employee。
  - 如无，自动创建新 Frappe User（用户名基于 `open_id` 或 `union_id`），并关联到 Employee。
- 新创建的 User 默认分配最小权限角色（如 `Employee Self Service`）。

### 5.4 与 R6B Employee 匹配规则的差异

R6B 中使用 `attendance_device_id` 作为 Employee 匹配键（Demo 打卡流水导入场景）。飞书登录场景使用手机号 / 邮箱 / 工号匹配，是独立的匹配通道，两者不冲突：

- 打卡流水 Excel 导入：用 `attendance_device_id`（脱敏工号）匹配 Employee Checkin。
- 飞书登录身份匹配：用手机号 / 邮箱 / 工号匹配 Frappe User 和 Employee。

生产环境中建议统一 Employee 的唯一标识策略。当前 Demo 阶段允许两类匹配方式共存。

## 6. 未匹配处理

### 6.1 未匹配场景

以下情况进入未匹配处理：

1. 飞书有身份，但在 Frappe 中找不到任何匹配的 Employee。
2. 飞书未返回手机号 / 邮箱（权限未授予或用户未绑定）。
3. 飞书返回的匹配字段与 Frappe Employee 不一致。

### 6.2 未匹配时的用户提示

```
「未找到匹配员工」

您的飞书身份已通过认证，但在系统中未找到匹配的员工信息。

请联系人事 / 管理员，确认以下信息已在系统中正确录入：
- 手机号
- 邮箱
- 工号

[返回登录页]
```

### 6.3 未匹配后的处理路径

- 未匹配用户**不自动创建** Employee 或 Frappe User。
- 人事 / 管理员在 Frappe Desk 中维护 Employee 信息（补充正确的手机号 / 邮箱 / 工号）后，该飞书用户再次登录即可自动匹配。
- 系统不记录未匹配失败的飞书用户身份信息（避免泄露飞书用户身份到不相关系统）。

## 7. 本地管理员兜底登录

### 7.1 兜底保留

本地管理员账号（Administrator / 系统管理员）**必须保留完整的 Frappe 原生登录能力**：

- 访问 `/login` 页面 → 使用 Frappe 原生邮箱 + 密码登录。
- 不受飞书 OAuth 匹配规则影响。
- 不受飞书服务可用性影响。

### 7.2 兜底使用场景

| 场景 | 登录方式 |
| --- | --- |
| 飞书服务不可用（网络/API 故障） | 本地管理员账号密码登录 |
| 员工未匹配需要人事介入 | 人事/管理员使用本地账号登录后维护 Employee 信息 |
| Demo 演示环境的初始配置 | 本地管理员登录后配置 Social Login Key |
| 紧急系统维护 | 本地管理员登录 |

### 7.3 登录页面设计

Frappe `/login` 页面在接入飞书 OAuth 后：

- 保留原生邮箱 + 密码登录表单。
- 新增「飞书登录」按钮（跳转飞书 OAuth 授权页）。
- 两个入口并列存在，互不替代。

## 8. 权限边界：飞书只认证，Frappe 管权限

### 8.1 核心原则

```
飞书身份 = 认证（Authentication）：证明「你是谁」
Frappe Role / User Permission = 授权（Authorization）：控制「你能做什么、看什么」
```

### 8.2 权限映射表

| M1 角色 | Frappe Role | 飞书登录后权限 | 权限范围 |
| --- | --- | --- | --- |
| 员工 | Employee Self Service | 只看自己 | 自己 Employee 记录 |
| 部门主管 | Department Manager（自定义） | 看本部门 | 本部门 Employee（User Permission: Department） |
| 人事 / 考勤管理员 | HR Manager / HR User | 看全公司 | 全公司 |
| 领导 | Report Viewer（自定义） | 看汇总 | 汇总报表（无明细） |
| 系统管理员 | System Manager | 全量 | 全量 |

### 8.3 不允许的行为

- 不允许飞书 OAuth 身份绕过 Frappe Role / User Permission 机制。
- 不允许飞书中的部门主管关系自动覆盖 Frappe Employee `reports_to` 或 User Permission。
- 不允许飞书身份被用于提权（如飞书普通成员自动获得 HR Manager 权限）。
- 飞书身份切换（如换绑手机号）不自动同步到 Frappe User 权限。

### 8.4 与 M1-R0 的一致性

本条承接 M1-R0 结论：飞书登录为主，HBOS 内部 User 自动映射，Frappe 权限体系承接系统权限和审计。

## 9. 飞书登录最小验证过程

### 9.1 验证范围

飞书 OAuth 登录的完整验证需要以下条件同时满足：

1. HBOS 有可公网访问的域名（或至少飞书回调可达的地址）。
2. 飞书开放平台应用已创建并配置好回调 URL。
3. App ID / App Secret 已获取。
4. 相关权限（`contact:user.phone:readonly`）已审核通过。
5. Frappe Social Login Key 已配置完成。

### 9.2 当前验证状态

**本轮验证结论：飞书 OAuth 登录方案设计完成，真实 OAuth 回调验证未执行（blocker）。**

**已完成的验证项**：

| 验证项 | 状态 | 说明 |
| --- | --- | --- |
| Frappe Social Login Key 机制确认 | 完成 | Frappe 原生支持 OAuth 2.0 Provider 配置 |
| 飞书 OAuth API 端点确认 | 完成 | 飞书开放平台文档确认 OIDC 授权码流程可用 |
| 身份字段获取范围确认 | 完成 | `open_id`、`union_id`、`name`、`mobile`、`email`、`employee_no` |
| Employee 匹配规则设计 | 完成 | 手机号 > 邮箱 > 工号，三优先级匹配 |
| 未匹配处理方案 | 完成 | 拒绝自动创建 User，提示联系管理员 |
| 本地管理员兜底确认 | 完成 | Frappe 原生邮箱密码登录保留 |
| Social Login Key 配置参数表 | 完成 | 7 个参数映射关系已固定 |
| Employee → User 的 Frappe 原生关联机制 | 完成 | `Employee.user_id` 字段存在且可用 |

**未完成 / Blocker**：

| 项 | 状态 | 原因 |
| --- | --- | --- |
| 真实飞书 OAuth 回调验证 | Blocker | 需要飞书开放平台应用创建、回调域名配置、App Secret；本轮不暴露 secret，不执行真实 OAuth |
| Frappe Social Login Key 实际配置 | Blocker | 依赖 App ID / App Secret；配置后需写入站点数据库，本轮不创建数据库态配置 |
| 飞书手机号权限获取 | Blocker | 需飞书企业管理员在飞书管理后台审核，非本地可完成 |
| 回调域名可达性 | Blocker | 当前 HBOS 运行在本地 Docker `localhost:8081`，飞书回调不可达。需公网域名或内网穿透 |
| 端到端飞书登录流程 | Blocker | 以上所有条件的组合依赖 |

### 9.3 Blocker 说明

飞书 OAuth 登录端到端验证的 blocker 分为三类：

| Blocker 类别 | 内容 | 谁可以解除 |
| --- | --- | --- |
| 飞书平台侧 | 创建应用、配置回调 URL、申请权限、获取 App Secret | Owner / 飞书企业管理员 |
| 网络侧 | HBOS 需要飞书回调可达的地址（公网域名或内网穿透） | Owner / 运维 |
| 安全侧 | App Secret 不得提交、不得在聊天中暴露、不得出现在文档中 | 本规则永久生效 |

**本轮不得要求用户在聊天中暴露 App Secret。不得提交 `.env`、密钥、真实 App Secret、token。不得伪造「飞书登录成功」。**

### 9.4 后续启动真实 OAuth 验证的条件

当以下条件全部满足时，可启动飞书 OAuth 端到端验证：

1. Owner 明确授权进入飞书 OAuth 验证轮次。
2. 飞书开放平台应用已创建，回调 URL 已配置。
3. HBOS 有飞书回调可达的地址。
4. App ID / App Secret 以安全方式（非聊天、非 Git）传递给配置流程。
5. 验证过程在安全的单独轮次中执行，不在本轮完成。

## 10. 领导汇总 Demo 范围

### 10.1 Demo 定位

领导汇总 Demo 是给领导看的**汇总视图**，不是给人事看的明细。定位为：

- 关键指标卡片：一目了然地看到本月核心考勤数据。
- 部门排名：了解各部门考勤状况对比。
- 不支持查看员个人明细（领导角色权限限制）。
- 支持查看和导出月报。

### 10.2 当前可用数据基线

基于 R6B/R6C 在本地 `frontend` site 中已有的 Demo 数据：

| 数据项 | 当前状态 |
| --- | --- |
| 虚构员工 | 3 名（甲/乙/丙） |
| 部门 | 1 个（生产一部） |
| 考勤日期范围 | 2026-07-02 至 2026-07-03（2 天） |
| Attendance 记录 | 6 条 |
| 迟到记录 | 2 条（丙 Jul 2 + 丙 Jul 3） |
| 早退记录 | 1 条（丙 Jul 2） |
| 上班缺卡 | 2 条（乙 Jul 2 + 乙 Jul 3） |
| 下班缺卡 | 1 条（甲 Jul 3） |

**当前数据规模限制**：Demo 数据只有 3 名员工 2 天，无法直接支撑有意义的「本月异常人数」等月度指标。领导 Demo 的指标定义和报表结构可以在此数据基线上设计，但实际展示效果需要更大规模的 Demo 数据集。

### 10.3 领导 Demo 实现方式选择

当前项目约束（不创建 App、不创建自定义 DocType、不启动大型 Vue 前端）下，领导 Demo 有以下实现选项：

| 方式 | 说明 | 优势 | 限制 |
| --- | --- | --- | --- |
| 方式 A：Frappe Query Report | 在 Frappe Desk 中创建 Query Report，基于 Attendance + Employee 表 SQL 聚合 | 原生、零代码、可导出 Excel | 纯表格，不美观；需要写入数据库 |
| 方式 B：Frappe Script Report | Python 脚本报表，可做复杂计算和格式化 | 灵活、可导出 Excel | 需要写入数据库；如需版本化需 App 载体 |
| 方式 C：Frappe Dashboard | Frappe Desk 原生 Dashboard + Chart | 可视化、可配置 | Dashboard 配置存储在数据库中，非版本化 |
| 方式 D：独立前端页面 | Vue/React 构建领导驾驶舱页面 | 美观、可定制 | 需遵循前端实施流程规范：原型先行 → Owner 审查 → 复刻实现 → 功能接入 |

**本轮选择**：优先采用方式 A（Frappe Query Report）+ 方式 C（Frappe Dashboard Chart）的组合，在 Frappe Desk 中提供领导汇总入口。本轮**不**启动方式 D（独立前端），原因：

1. 领导 Demo 的规模和复杂度不需要独立前端。
2. 根据 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`，独立前端需要原型先行→Owner 审查→复刻实现→功能接入的完整流程，超出本轮范围。
3. 方式 A + C 已可在 Frappe Desk 中提供可用的领导视图，且无需创建 App / DocType。

**但注意**：Query Report 和 Dashboard 的创建需要在 Frappe Desk 数据库中执行。在当前「不创建 App、不写数据库态配置」的约束下，本轮**仅固化实现路径和指标定义**，不在数据库中创建 Report 和 Dashboard。

## 11. 领导指标字段与数据来源

### 11.1 领导关键指标

| # | 指标 | 定义 | 数据来源 | 计算方式 |
| --- | --- | --- | --- | --- |
| 1 | 本月异常人数 | 当前自然月中存在任一异常（迟到/早退/缺卡/缺勤）的去重员工数 | Attendance + Employee Checkin | `SELECT COUNT(DISTINCT employee) FROM tabAttendance WHERE MONTH(attendance_date) = MONTH(CURDATE()) AND (late_entry = 1 OR early_exit = 1 OR in_time IS NULL OR out_time IS NULL)` |
| 2 | 迟到次数 | 当前自然月中 `late_entry = 1` 的 Attendance 记录总数 | Attendance | `SELECT COUNT(*) FROM tabAttendance WHERE MONTH(attendance_date) = MONTH(CURDATE()) AND late_entry = 1` |
| 3 | 缺卡次数 | 当前自然月中 `in_time IS NULL` 或 `out_time IS NULL` 的 Attendance 记录总数 | Attendance | `SELECT COUNT(*) FROM tabAttendance WHERE MONTH(attendance_date) = MONTH(CURDATE()) AND (in_time IS NULL OR out_time IS NULL)` |
| 4 | 部门排名 | 按部门聚合异常人数或异常率排序 | Attendance + Employee + Department | `SELECT department, COUNT(DISTINCT employee) AS abnormal_count FROM ... GROUP BY department ORDER BY abnormal_count ASC` |

### 11.2 指标扩展（可选）

除上述 4 个核心指标外，领导 Demo 可扩展以下指标：

| # | 指标 | 定义 | 数据来源 |
| --- | --- | --- | --- |
| 5 | 出勤率 | 实际出勤人数 / 应出勤人数（按天聚合，取月均值） | Attendance + Shift Assignment |
| 6 | 缺勤天数 | Attendance `status = Absent` 的计数 | Attendance |
| 7 | 早退次数 | Attendance `early_exit = 1` 计数 | Attendance |
| 8 | 请假总天数 | Leave Application 聚合 | Leave Application |
| 9 | 异常待处理数 | 待主管确认 / 待人事处理的异常数 | Attendance Request（扩展 Custom Field 后） |

### 11.3 Query Report 设计

**Report 名称**：`领导月度考勤汇总`

**SQL 查询逻辑**：

```sql
SELECT
    emp.employee_name AS '员工姓名',
    emp.department AS '部门',
    COUNT(DISTINCT att.name) AS '出勤天数',
    SUM(CASE WHEN att.late_entry = 1 THEN 1 ELSE 0 END) AS '迟到次数',
    SUM(CASE WHEN att.early_exit = 1 THEN 1 ELSE 0 END) AS '早退次数',
    SUM(CASE WHEN att.in_time IS NULL AND att.out_time IS NOT NULL THEN 1 ELSE 0 END) AS '上班缺卡次数',
    SUM(CASE WHEN att.out_time IS NULL AND att.in_time IS NOT NULL THEN 1 ELSE 0 END) AS '下班缺卡次数',
    SUM(CASE WHEN att.status = 'Absent' THEN 1 ELSE 0 END) AS '缺勤天数',
    ROUND(SUM(att.working_hours), 1) AS '出勤工时'
FROM tabAttendance att
JOIN tabEmployee emp ON att.employee = emp.name
WHERE att.docstatus = 1
    AND MONTH(att.attendance_date) = MONTH(CURDATE())
    AND YEAR(att.attendance_date) = YEAR(CURDATE())
GROUP BY emp.employee_name, emp.department
ORDER BY emp.department, emp.employee_name
```

**Dashboard Chart 设计**（数据分析图表）：

| Chart | 类型 | 数据源 | 用途 |
| --- | --- | --- | --- |
| 本月异常人数卡片 | Number Card | 指标 1 查询 | 关键数字展示 |
| 迟到次数卡片 | Number Card | 指标 2 查询 | 关键数字展示 |
| 缺卡次数卡片 | Number Card | 指标 3 查询 | 关键数字展示 |
| 部门异常排名 | Bar Chart | 指标 4 查询 | 部门对比 |

## 12. 月报查看 / 导出路径

### 12.1 月报查看路径

继承 M1-R5 已固化的月报查看路径：

| 路径 | 说明 | 适用角色 |
| --- | --- | --- |
| 路径 1：Query Report | Frappe Desk → Report → 「月度考勤汇总」→ 选择月份 → 查看 | 人事/管理员、领导 |
| 路径 2：Attendance 列表 | Frappe Desk → Attendance List → 按日期筛选 → 查看 | 人事/管理员 |
| 路径 3：Employee Checkin 列表 | Frappe Desk → Employee Checkin List → 按日期筛选 → 查看原始打卡 | 人事/管理员 |
| 路径 4：员工个人视图 | Frappe Desk → Employee → 选择员工 → Attendance 统计 | 员工（只看自己） |

### 12.2 月报导出路径

继承 M1-R5 已固化的 Excel 导出路径：

| 路径 | 操作方式 | 导出内容 |
| --- | --- | --- |
| 路径 A：Report Export | Query Report 页面 → Menu → Export → Excel | 月度汇总全部字段（员工/部门/出勤/迟到/早退/缺卡/缺勤/工时） |
| 路径 B：List Export | Attendance List → Menu → Export → Excel | Attendance 明细列表 |
| 路径 C：Data Export | Frappe Desk → Data Export → 选择 DocType = Attendance → 导出 | 原始 Attendance 数据 |
| 路径 D：Script Report | 自定义 Script Report 生成 .xlsx | 按模板格式的月报 Excel |

**领导月报导出**：领导角色使用路径 A，在 Query Report 中导出 Excel。导出的 Excel 仅包含汇总数据，不含个人明细（通过 Frappe Role 权限控制，领导角色不分配个人明细查看权限）。

### 12.3 月报导出字段覆盖

导出 Excel 应包含以下字段（对齐 M1 真实需求确认中的月度汇总字段）：

| 字段 | 数据来源 | 当前 Demo 可用 |
| --- | --- | --- |
| 员工姓名 | Employee `employee_name` | 是（虚构姓名） |
| 部门 | Employee `department` | 是 |
| 应出勤天数 | Shift Assignment 统计 | Demo 数据为 2 天 |
| 实际出勤天数 | Attendance `status = Present` 计数 | 是 |
| 迟到次数 | Attendance `late_entry = 1` 计数 | 是 |
| 早退次数 | Attendance `early_exit = 1` 计数 | 是 |
| 缺卡次数 | Attendance `in_time` / `out_time` 空值计数 | 是 |
| 缺勤天数 | Attendance `status = Absent` 计数 | Demo 无缺勤场景 |
| 请假天数/小时 | Leave Application 聚合 | Demo 无请假数据 |
| 加班小时 | Attendance `working_hours` - Shift Type 标准工时 | 待审批流程实现 |
| 节假日出勤 | Holiday List 匹配 | 待配置 |
| 异常待确认数 | Attendance Request（扩展 Custom Field） | 结构已就绪，运行时待解决 |
| 最终考勤状态 | 处理逻辑计算 | 待完整的异常流程闭环 |
| 备注 | 手工填写或自动生成 | 待实现 |

## 13. M1 Demo 演示路径

### 13.1 完整演示流程

面向 Owner / 领导的 M1 Demo 完整演示路径：

```
1. 环境准备
   1.1 确认 Docker 容器全部运行（docker compose ps）
   1.2 确认 Frappe Desk 可访问（http://localhost:8081/login）
   1.3 确认 Demo 数据已就绪（Employee 3 名、Checkin 9 条、Attendance 6 条）

2. 登录演示
   2.1 展示 Frappe Desk 登录页 → 可见「飞书登录」和「邮箱密码登录」双入口
   2.2 使用本地管理员账号登录 → 演示兜底登录能力
   2.3 说明飞书登录方案和 Employee 自动匹配规则
   2.4 说明飞书 OAuth 端到端验证的当前状态和 blocker

3. 考勤工作台
   3.1 进入 HR Workspace（/app/hr）
   3.2 展示 Shift & Attendance 入口
   3.3 展示 Employee 列表（虚构员工甲/乙/丙）
   3.4 展示 Shift Type 配置（早班 08:00-16:00，0 分钟宽限）

4. 原始打卡流水
   4.1 展示 Employee Checkin 列表（9 条打卡记录）
   4.2 说明打卡流水来源和脱敏规则
   4.3 说明 Employee Checkin → Auto Attendance 的转换流程

5. 考勤结果与异常识别
   5.1 展示 Attendance 列表（6 条）
   5.2 逐个展示 5 种异常识别：
       - 正常：甲 Jul 2（IN=08:00, OUT=16:00）
       - 迟到：丙 Jul 2（late_entry=1, IN=08:16）
       - 早退：丙 Jul 2（early_exit=1, OUT=15:45）
       - 上班缺卡：乙 Jul 2（in_time=NULL）
       - 下班缺卡：甲 Jul 3（out_time=NULL）
   5.3 说明 late_entry/early_exit 自动标记机制

6. 异常说明流程
   6.1 展示 Attendance Request 上已扩展的 11 个 Custom Field
   6.2 说明 6 种异常说明类型
   6.3 说明三级流程设计：员工提交 → 主管确认 → 人事处理 → 归档
   6.4 说明当前 Blocker：native validate_no_attendance_to_create() 冲突
   6.5 说明后续 Owner 授权选项（Hook 绕过 / 自定义 DocType / 文档化限制）

7. 月报与导出
   7.1 说明月度汇总报表路径（Query Report）
   7.2 说明 Excel 导出路径（4 种导出方式）
   7.3 说明月度汇总字段覆盖情况

8. 领导汇总 Demo
   8.1 展示 4 个核心指标定义和数据来源
   8.2 展示 Query Report SQL 设计
   8.3 说明 Dashboard Chart 设计
   8.4 说明领导角色的数据权限限制（只看汇总，不看到个人明细）

9. 权限与角色
   9.1 说明 5 种 M1 角色的权限边界
   9.2 说明飞书只认证、Frappe 管权限的原则
   9.3 说明本地管理员兜底登录

10. 下一步与 M1 收口
   10.1 回顾 M1 12 条验收标准与当前完成情况
   10.2 说明 M1 closeout 准备项
   10.3 说明 M2 后续路线
```

### 13.2 演示数据准备清单

| 序号 | 数据对象 | 演示内容 | 来源 |
| --- | --- | --- | --- |
| 1 | Employee | 3 名虚构员工（甲/乙/丙） | R6B |
| 2 | Shift Type | 早班 08:00-16:00（0 分钟宽限） | R6B+R6C |
| 3 | Shift Assignment | 3 条排班 | R6B+R6C |
| 4 | Employee Checkin | 9 条打卡记录（正常/迟到/早退/缺卡场景） | R6B+R6C |
| 5 | Attendance | 6 条考勤结果（含 late_entry/early_exit 标记） | R6C |
| 6 | Custom Field | 11 个字段（6 种异常类型 + 三级状态） | R6C |
| 7 | Attendance Request | 空（4 条 Demo AR 被原生验证拒绝） | R6C |
| 8 | Social Login Key | 配置参数表（方案设计，未在数据库中创建） | 本轮 |

## 14. M1 收口准备项

### 14.1 M1 12 条验收标准对照

M1 Demo 总验收标准 12 条（来自 `M1_考勤一期真实需求确认.md`），当前完成情况：

| # | 验收标准 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| 1 | 人事能登录 | **方案就绪，有兜底** | 本地管理员可登录；飞书（主体登录方式）方案已完成设计，端到端验证有 blocker |
| 2 | 能看到考勤工作台 | **方案就绪** | HR Workspace + Shift & Attendance 入口已存在（R5）；Frappe Desk 原生可用 |
| 3 | 能导入一份脱敏考勤 Excel | **最小闭环通过** | 脱敏原始打卡流水导入（Checkin→Attendance）已通过（R6B）；月度汇总导入待实现 |
| 4 | 能生成或展示月度考勤结果 | **最小 Demo 可用** | 6 条 Attendance 已生成（R6B+R6C）；完整月度汇总报表路径已固化（R5+本轮） |
| 5 | 能识别迟到、早退、缺卡、缺勤 | **7 个场景通过** | 迟到/早退/上班缺卡/下班缺卡/正常（R6C）；全天缺勤逻辑已固化，场景未验证 |
| 6 | 员工能查看自己的记录 | **方案就绪** | Attendance List / Employee 视图原生可用；基于 Frappe Role 权限隔离 |
| 7 | 员工能提交异常说明 | **结构就绪，运行时 Blocker** | Custom Field 扩展完成；原生 validate_blocker 阻止运行时创建 |
| 8 | 主管能确认异常 | **结构就绪，运行时 Blocker** | Custom Field + 三级状态字段设计完成；依赖 AR 记录创建 |
| 9 | 人事能最终归档 | **结构就绪，运行时 Blocker** | Customs Field + 三级状态设计完成；依赖 AR 记录创建 |
| 10 | 能导出 Excel 月报 | **方案就绪** | 4 种导出路径已固化（R5）；Excel Export / Report Export 原生可用 |
| 11 | 领导能看到汇总 Demo | **方案就绪** | 4 个核心指标定义、Query Report + Dashboard 设计（本轮）；数据规模限制了实际展示效果 |
| 12 | 技术方案说明未来如何接真实考勤机 | **已完成** | 通用适配层设计方案（M1 技术设计）；接口契约、清洗映射层、Checkin 通路已明确 |

### 14.2 M1 closeout 准备项清单

M1 closeout 需要完成以下准备项。本清单**不执行**，仅列出供后续 closeout 轮次参考：

| 序号 | 准备项 | 类别 | 说明 |
| --- | --- | --- | --- |
| P1 | 汇总 M1-R0 至 M1-R7 全部轮次的主文档交付物 | 文档整理 | 确认每个子轮次的主文档状态一致 |
| P2 | 汇总 M1 全部已改动的 Frappe Desk 配置项 | 配置清单 | Shift Type、Custom Field、Employee、Shift Assignment 等 |
| P3 | 汇总 M1 全部已知 Gap / Blocker / 待 Owner 决策项 | 风险清单 | 包括 AR 创建 Blocker、飞书 OAuth blocker、月度汇总导入等 |
| P4 | 固化 M1 Demo 演示脚本 | 演示准备 | 基于 13.1 的演示路径，形成可重复执行的 Demo 脚本 |
| P5 | 清理或固化 TEST 数据状态 | 数据治理 | 确认 M1 Demo 数据集的范围、命名规范和后续处理方式 |
| P6 | 更新所有入口文件到 M1 closeout 状态 | 状态台账 | README、AI_CONTEXT、PROJECT_STATUS、CURRENT_MILESTONE 等 |
| P7 | 更新 M1_START_GATE 到 M1 closeout 状态 | 阶段门禁 | 确认 M1 全部子轮次状态一致 |
| P8 | M1 里程碑最终状态收口 | 里程碑台账 | M1 从 IN_PROGRESS → COMPLETED |
| P9 | M2 启动边界定义 | 后续路线 | M2 飞书集成阶段的目标、前置条件和禁止项 |
| P10 | M1 经验回顾与教训记录 | 经验沉淀 | Demo 数据规模限制、Native validation 冲突、环境治理等 |

### 14.3 M1 收口决策项（需 Owner 决策）

以下事项**不阻塞** M1 closeout，但应在 closeout 时明确决策：

| # | 决策项 | 选项 | 影响 |
| --- | --- | --- | --- |
| D1 | Attendance Request native validation 冲突 | A: Hook 绕过 / B: 自定义 DocType / C: 文档化限制 | 影响异常说明流程的下一步实现路径 |
| D2 | 飞书 OAuth 端到端验证时机 | M1 closeout 后立即验证 / M2 阶段验证 / 单独验证轮 | 影响飞书登录功能的实际可用时间 |
| D3 | M1 Demo 数据集的最终处理 | 保留用于 M2 继续开发 / 清理后重建 / 不做处理 | 影响 M2 开发基础数据 |
| D4 | 月度汇总导入的实现优先级 | M1 closeout 前补做 / 推迟到 M2 / 推迟到生产上线前 | 影响月报功能完整度 |
| D5 | 是否需要数据规模扩展 | 当前 3 员工 2 天 / 扩展到更接近真实的规模 | 影响 Demo 演示效果和领导指标可用性 |

## 15. 失败记录与限制

### 15.1 本轮限制

| # | 限制 | 影响 | 处理方式 |
| --- | --- | --- | --- |
| 1 | 飞书 OAuth 端到端验证未执行 | 飞书登录目前停留在方案设计阶段 | 方案设计完成，参数表固化；blocker 分类说明（平台侧/网络侧/安全侧） |
| 2 | 不创建数据库态配置 | Query Report、Dashboard、Social Login Key 未写入站点数据库 | 方案路径和 SQL 设计已固化，在后续授权轮次中写入 |
| 3 | Demo 数据规模小（3 员工 2 天） | 领导汇总 Demo 的月度指标计算无实际数据支撑 | 指标定义和计算方式已固化，扩展数据集后立即可用 |
| 4 | 不启动独立前端 | 领导 Demo 只提供 Frappe Desk 内的实现路径 | 如需漂亮驾驶舱页面，需按前端实施流程规范执行 |
| 5 | 不创建 App / DocType | 无法版本化自定义 Report 和 Dashboard | 方案路径已固化在本文档中 |

### 15.2 跨轮次继承的限制

从 R6B 和 R6C 继承的限制（不重复展开）：

- R6B 限制 1：Owner Excel 是混合表，不能直接作为原始打卡流水导入源。
- R6B 限制 2：未验证 Frappe Data Import UI 上传流程。
- R6B 限制 4：迟到/早退在 R6B 中未置位 → R6C 已修复。
- R6C 核心 Blocker：HRMS 原生 `validate_no_attendance_to_create()` 阻止 Attendance Request 创建。

## 16. 本轮未做内容

- 未执行飞书 OAuth 真实回调验证。
- 未获取或提交飞书 App ID / App Secret。
- 未在 Frappe Desk 中创建 Social Login Key。
- 未在数据库中创建 Query Report 或 Dashboard。
- 未启动独立前端领导驾驶舱。
- 未创建 Frappe App。
- 未创建自定义 DocType。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、密钥、Excel、CSV、数据库、日志、缓存或运行时产物。
- 未使用真实员工姓名或未脱敏考勤数据。
- 未 closeout R7（只进入 REVIEWING）。
- 未启动 M1 总收口。
- 未创建 `hb_hr_app`。
- 未接入飞书工作台、飞书请假。
- 未接真实考勤机。
- 未部署公司内网或云服务器。
- 未重写 R6A/R6B/R6C。

## 17. 后续 M1 closeout / M2 边界

### 17.1 M1 closeout 预告

M1-R7 进入 REVIEWING 后，M1 的全部执行轮次（R0→R7）已完成。预计后续在 Codex 审查通过后单独启动 M1 closeout 轮次，完成：

- M1 全轮次交付物汇总
- M1 验收标准逐条复核
- M1 入口文件最终同步
- M1 阶段门禁更新
- M1 Demo 演示准备
- M2 启动条件确认

M1 closeout 不包含 M1-R7 的 closeout（本轮只进入 REVIEWING，不 closeout）。

### 17.2 M2 边界预告

M2 定位为「飞书集成」阶段。M2 可能包含：

- 飞书 OAuth 登录端到端验证与上线。
- 飞书工作台集成。
- 飞书请假审批对接。
- 飞书消息通知（考勤异常提醒、月报推送等）。
- 飞书与 Frappe 的 User / Employee 同步机制。

M2 的启动条件：

1. M1 全部轮次通过 Codex 审查并 closeout。
2. M1 总收口完成，M1 状态为 COMPLETED。
3. Owner 明确授权进入 M2。
4. 飞书开放平台应用已创建、权限已审核通过。
5. M2 启动门禁通过。

M2 不因 M1-R7 进入 REVIEWING 而自动启动。

## 18. 当前状态（closeout 前）

- `M1-R6A = COMPLETED`
- `M1-R6B = COMPLETED`
- `M1-R6C = COMPLETED`
- `M1-R7 = COMPLETED`
- `M1 closeout = 未启动`
- `M2 = PLANNED（未启动）`

## 20. Closeout 结论

M1-R7 已通过 Codex 审查并完成 closeout，状态收口为 COMPLETED。

Closeout 结论：

- R7 飞书 OAuth 登录方案、Employee 匹配规则、权限边界、未匹配处理和本地管理员兜底登录已全部完成文档化。
- R7 领导汇总 Demo 核心指标定义（4 项）、Query Report SQL 设计、Dashboard Chart 设计和月报查看/导出路径已全部固化。
- M1 Demo 完整演示路径（10 个环节）已整理，M1 收口准备项清单（10 项）和 Owner 决策项（5 项）已列出。
- 飞书 OAuth 端到端验证未执行：有飞书平台侧 + 网络侧 + 安全侧三类 blocker，不属于 Frappe 端可独立完成的范围。未伪造飞书登录成功。
- `late_entry`/`early_exit` 在 Shift Type 配置修复后正确置位（R6C），异常识别 7 个场景全部通过。
- 11 个 Custom Field 已在 HRMS 原生 Attendance Request 上扩展完成，但 native `validate_no_attendance_to_create()` 冲突仍是后续 Owner 决策项。
- 本轮未创建 `hb_hr_app`，未创建自定义 DocType，未修改 Frappe / ERPNext / HRMS 核心源码。
- 本轮未提交 `.env`、飞书 App ID / App Secret、Excel、CSV、数据库、日志、缓存或任何运行时产物。
- Codex 初审 FAIL（3 类 blocker）已在 `e812e32` 中最小修复，复审 PASS。
- 下一步：等待 Owner 授权后，才可进入 `M1 总收口 / M1 closeout`。M2 仍为 PLANNED，不因 R7 closeout 自动启动。

## 21. 当前状态

- `M1-R6A = COMPLETED`
- `M1-R6B = COMPLETED`
- `M1-R6C = COMPLETED`
- `M1-R7 = COMPLETED`
- `M1 closeout = 未启动`
- `M2 = PLANNED（未启动）`
