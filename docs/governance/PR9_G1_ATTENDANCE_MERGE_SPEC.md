# PR #9 / Attendance G1 合并治理规范

> 状态：LOCKED FOR G1  
> 适用范围：PR #9 的 Attendance 成果治理，以及治理候选 PR #11。  
> 目标：形成可进入 HBOS 三 App 集成分支的 **Attendance Clean Candidate**。  
> 本文是 G1 合并门禁。任何 Agent、开发者或后续 PR 若与本文冲突，应先修改本文并由 Owner 重新确认，不能以“测试通过”或“当前能运行”为理由绕过。

---

## 1. G1 的最终产物

G1 不是把原 PR #9 原样合入 main。

最终 Attendance 候选必须满足：

- 业务 App：仅保留 `hb_attendance_app` 的有效考勤能力。
- 不包含 `hb_stock_app`、独立 stock site 或其运行时挂载。
- 不直接修改 Frappe / ERPNext / HRMS 核心源码。
- `frappe + erpnext + hrms` 是平台依赖；Attendance 通过自定义 App 扩展。
- G1 通过后进入 `integration/hbos-platform-v1`，与 Inventory / LIMS 联合验收；不得直接以“PR #9 GitHub 可合并”为依据进入 main。
- PR #11 作为治理工作分支可以保留历史；最终进入正式集成分支时应使用净化后的树状态（squash / curated integration），不把旧 stock 路线或应清理的真实人员数据历史带入正式平台历史。

---

## 2. 数据主权

### 2.1 ERPNext / HRMS 拥有

- User
- Employee
- Department
- Employee Checkin
- Attendance

Attendance App 可以扩展以上对象，但不得复制第二套 Employee / Department 主数据。

### 2.2 hb_attendance_app 拥有

- HBOS Attendance Import Log
- HBOS Shift Rule（G1 后必须具备稳定规则身份）
- HBOS Employee Shift
- HBOS Employee Schedule
- HBOS Leave Record
- HBOS Overtime Record
- HBOS Rest Leave Record
- Attendance 计算策略与外部同步适配

### 2.3 禁止

- 导入器因“员工不存在”自动创造 Employee / Department。
- 飞书、得力云或报表模块各自计算另一套正式考勤事实。
- 人员名单、排班归属、豁免人员长期以真实姓名/工号硬编码在 Python 作为权威主数据。

---

## 3. Attendance 唯一事实链

正式链路必须是：

```text
Raw Source
  ├─ Employee Checkin
  ├─ Leave / Overtime / Rest Leave
  └─ Schedule / Shift Policy
          ↓
Attendance Engine
          ↓
HRMS Attendance（HBOS lineage 标记）
          ↓
Dashboard / Report / Feishu / Future Portal
```

禁止：

```text
Feishu 自己重新算缺勤
Dashboard 自己重新算正式缺勤
Report 自己重新算另一套正式缺勤
```

展示层可做统计投影，但正式状态必须来自同一 Attendance Engine 的落库结果。

---

## 4. G1 强制门禁

### G1-A：重算边界与事务安全 — BLOCKER

`regenerate_attendance(range_start, range_end)` 必须满足：

1. 只允许删除 `[range_start, range_end]` 内由 HBOS 生成的 Attendance。
2. 不允许任何 `attendance_date > range_end` 的清理。
3. 删除旧结果后到新结果完成前不得中途 commit。
4. 任意异常必须 rollback，旧正式结果不能留下“已删但未重建”的空洞。
5. 所有 SQL 值必须参数化；批量 INSERT 若继续使用拼接，数据项必须由程序内部安全生成且需有回归测试，优先改为参数化批量写入。
6. 输入必须验证 `range_start <= range_end` 且日期格式有效。

验收：
- 重算 9/1–9/10，9/11+ 记录 hash/count 完全不变。
- 人为注入计算异常，事务回滚后目标区间旧记录仍完整。
- 同一区间连续重算两次结果一致（幂等）。

### G1-B：Shift Rule 稳定身份 / 版本 — BLOCKER

当前“员工绑定某个具体 HBOS-SHIFT-xxxx，修改规则再复制一个新 DocName”的模型不得作为最终 G1 设计。

必须具备：

- 稳定规则身份：`rule_code` / `rule_family`（不可随版本变化）。
- 版本记录：至少有 `effective_from`；如需要显式失效可增加 `effective_to`。
- Employee Shift 绑定稳定规则身份，而非某一版记录。
- 某个业务日期选择“该日有效的最后一个版本”。
- UI 一次提交完整规则变更，不允许 start/end/late_after 分三次创建三个版本。
- 历史版本不得因“当前停用”而失去历史重算能力。
- 删除已有历史引用的规则版本原则上禁止，改用停用/失效。

验收：
- 8 月使用旧时间，9 月生效的新时间不回写污染 8 月。
- 员工绑定不因升版失效。
- 一次 UI 保存只生成一个新版本。

### G1-C：Schedule 来源与唯一性 — BLOCKER

`HBOS Employee Schedule` 必须增加：

- `source_type`：至少 ROTATION / IMPORT / MANUAL / SWAP。
- `source_ref`：记录来源单据/导入批次/规则。
- 同一 Employee + schedule_date 必须有明确唯一业务语义；数据库或服务层必须阻止无解释重复。

自动轮转：
- 只能覆盖自己的 ROTATION 记录。
- 不能删除 MANUAL / IMPORT / SWAP。
- 人工调整优先级必须明确并写进测试。

### G1-D：服务端 RBAC — BLOCKER

任何 `@frappe.whitelist()` 均按功能归类：

读取人员/考勤：
- HR User
- HR Manager
- System Manager

修改班次、排班、外部写入、手工重算：
- HR Manager
- System Manager
- 如未来需要专门 HBOS 角色，应新增明确角色，不使用“页面隐藏”代替权限。

禁止：
- 只靠 Vue/Desk 按钮隐藏。
- whitelisted 写接口无服务端角色校验。
- 普通员工任意触发飞书、得力云同步或修改 Employee 班次。

### G1-E：文件与个人数据 — BLOCKER

含姓名、工号、部门、考勤、请假、排班的导出：
- 必须 `is_private=1`。
- API 必须进行 HR 权限检查。
- 不得返回可长期公开访问的 /files URL。

源码治理：
- 真实姓名 + 工号 + 部门对照表不得作为公开仓库长期配置。
- ADMIN / SPECIAL_SHIFT / FOOD / EXEMPT 等名单迁移到受控业务数据。
- 代码保留“规则类型”，数据库决定“谁属于规则”。
- 若公开 Git 历史已经包含真实人员信息，删除当前文件不等于历史净化；正式 integration/main 采用净化树，必要时另做历史清理。

### G1-F：Custom Field / clean-site 可重建 — BLOCKER

代码引用的所有自定义字段必须由版本化代码创建，包括至少：

Employee:
- hbos_fixed_shift（若 G1-B 新模型替代，则按新模型迁移）

Employee Checkin:
- hbos_terminal_sn
- hbos_delicloud_id
- hbos_employee_num
- hbos_dept_name
- hbos_check_type
- 既有 lineage 字段

Attendance:
- 既有 HBOS lineage / missing-out 字段

验收：
- 新建干净 site → install apps → bench migrate 后，无 Unknown column。
- migration 重复执行幂等。

### G1-G：外部系统同步 — BLOCKER

飞书 / 得力云：
- scheduler 入口与人工 API 使用同一业务 Service。
- 外部写入必须可通过 Feature Flag / 配置关闭。
- 默认的新环境不得因为漏配而进行真实外部写入。
- 调休 `sync → parse → verify` 必须由一个 orchestrator 显式保证顺序；不能依赖 scheduler 同一列表中的 job 顺序。
- 得力云游标只有在本批数据安全落库后才能推进；部分失败需要可重试且不能静默永久跳过。

### G1-H：AI 数据边界 — BLOCKER

月报 AI 复核 / 调休 LLM：
- AI 不得直接改写正式考勤结论。
- 发送给模型的字段最小化。
- 外部 AI endpoint 必须有显式 enable 开关；新环境默认关闭。
- 文档必须说明会发送哪些字段。
- 如果 endpoint 不是公司受控服务，不发送无必要的姓名、工号等身份信息；优先匿名业务 ID。

### G1-I：旧 Desk 页面安全 — BLOCKER

在 Vue + Ant Design Vue 改造完成前，旧 Desk 页面仍属于生产攻击面：

- 所有用户/主数据派生字符串拼 HTML 前必须 escape。
- 禁止把 Employee / Department / rule_name / server error 原样插入 HTML。
- 前端迁移不是推迟 XSS 修复的理由。

### G1-J：CI / Integration Gate — BLOCKER

现有 CI 必须修复：

- Checkout 获取足够 Git 历史（建议 `fetch-depth: 0`），否则 `git diff origin/main...HEAD` 门禁可能是假执行。
- 敏感文件扫描命令本身失败必须让 Job 失败，不能把“origin/main 不存在”当成“无敏感文件”。
- 保留现有离线回归。
- 旧 contract test 若与已批准的新架构冲突，更新测试契约；不得为了旧测试绿灯退回旧架构。

增加：
- governance tests
- clean-site migrate test
- Frappe DB integration test
- RBAC test
- regeneration rollback/idempotency test
- Docker smoke test（进入三 App Integration Gate 前必须有）

---

## 5. G1 非目标

G1 不要求：

- 完成 Vue 3 + Ant Design Vue 考勤前端。
- 创建企业总工作台。
- 把 Attendance 拆成微服务。
- 把 Frappe/ERPNext/HRMS 替换掉。
- 在本轮重构所有历史算法，只治理会阻断平台合并的数据安全、权限、边界和可重建性。

前端迁移另立阶段，但 G1 后所有服务必须已经能被新前端通过稳定 API 安全调用。

---

## 6. hb_stock_app 决策

G1 最终候选中：

- `hb_stock_app`：不进入。
- 独立 stock site 架构：不进入。
- 库存/仓储正式候选：由 PR #8 的 `hb_inventory_app` 后续治理决定。
- Attendance 的 Docker / PYTHONPATH 不得再引用 `hb_stock_app`。

---

## 7. G1 Definition of Done

只有全部满足才允许把 Attendance 标记为 **READY_FOR_PLATFORM_INTEGRATION**：

- [ ] G1-A 重算边界/事务 PASS
- [ ] G1-B Shift version PASS
- [ ] G1-C Schedule source/unique PASS
- [ ] G1-D RBAC PASS
- [ ] G1-E Private export + PII PASS
- [ ] G1-F clean-site migration PASS
- [ ] G1-G external sync PASS
- [ ] G1-H AI data boundary PASS
- [ ] G1-I XSS PASS
- [ ] G1-J CI/integration PASS
- [ ] hb_stock_app 不在候选树
- [ ] 原 445+ 考勤回归在更新后的正确契约下通过
- [ ] 新 governance tests 全通过
- [ ] PR 保持 Draft，直到 Owner 最终确认门禁结果

通过 G1 只代表“Attendance 可以进入平台集成”，**不代表可单独直接 merge main**。
