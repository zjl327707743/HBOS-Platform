# PR #10 LIMS 深度审计

> 审计对象：PR #10 `codex/m2-r8-public-pr`  
> 审计 HEAD：`59f7abe699fcfeb21f9c6d2262b89de90bbb28a2`  
> 结论：BLOCKED — 当前 Draft 不可直接合入 main；应先形成 LIMS Clean Candidate。  
> 原则：保留现有 LIMS 领域模型、Vue 3 + Ant Design Vue 前端与状态机成果，但先修复数据主权、审计完整性、职责分离和可重建部署问题。

---

## 1. 建议保留的主体

- `apps/hb_lims_app/**`
- `frontend/hbos-lims-web/**`
- Vue 3 + Ant Design Vue + Pinia + Vue Router 方向
- LIMS 独立工作台，不升级为企业总工作台
- 样品 / 检验任务 / 检验结果 / COA / 质量标准
- 留样管理
- 稳定性管理
- 变更 / 稳定性室 / 设备
- Workflow Contract + Service 层权限架构
- OOS 锁定、版本链、快照与审计思路
- 私有 COA PDF

不建议推倒重写。

---

## 2. P0 / Merge Blockers

### L10-P0-01：审计“独立提交”会提交当前业务事务

当前：
- `audit_log(..., commit=True)` 直接调用 `frappe.db.commit()`
- Stability / Retention 的 `_audit_commit()`
- 删除拦截、SoD 拦截、越权拦截

均把它称为“独立提交，避免随业务回滚”。

但它们使用的是当前 Frappe 请求的同一数据库事务；普通 `frappe.db.commit()` 并不是独立事务。

风险：
- 某个业务动作已经产生部分未提交修改；
- 随后发现 SoD / 非法状态 / 删除违规；
- 为了记录违规审计先 `commit()`；
- 当前事务内先前的业务修改也被一起提交；
- 随后 `frappe.throw()` 已无法回滚前面已提交内容。

必须：
- 禁止在业务事务内部通过普通 `frappe.db.commit()` 实现“独立审计提交”。
- 成功业务审计与业务事务同成败。
- 失败/越权尝试若要求即使业务回滚也保留，应通过真正隔离的 outbox / 独立连接 / 日志管道实现。
- 增加测试：SoD/非法操作被拒绝后，业务对象所有字段均保持原值，同时违规审计按设计留存。

### L10-P0-02：当前 checksum 不是“防篡改”

`_checksum()` 使用未加密、未加密钥的 SHA-1，且只覆盖：
- doctype_target
- doc_name
- log_type
- user
- created_at
- old_value
- new_value

没有覆盖：
- action_text
- field_changed
- reason

因此即使只按当前 checksum 逻辑，以上字段改变也无法检测。

更根本地：
- checksum 与内容保存在同一数据库行；
- 具备 DB 直接写权限的人可以同时修改内容与 checksum；
- 单条无链式关系的 SHA-1 只能算完整性指纹，不能称为真正“防篡改”。

必须二选一：
1. 若只是应用级误修改检测：完整覆盖所有字段、升级 SHA-256，并准确称“完整性校验”；
2. 若作为正式合规审计证据：增加 hash chain / HMAC / 外部 append-only anchor / 独立日志存储之一，并定义密钥与审计策略。

在真正实现前，代码和文档不得把当前机制描述成强“防篡改”。

### L10-P0-03：普通检验结果链缺完整 SoD

稳定性结果链已经实现：
- 检测人 ≠ 复核人
- 复核人 ≠ 批准人
- 甚至检查是否仍存在独立批准人

但普通 `HBOS Test Result`：

`review_result()`
- 仅检查角色和状态；
- 没有明确拒绝 `current_user == analyst`。

`approve_result()`
- 仅检查角色和状态；
- 没有明确拒绝 `current_user == reviewer`。

`LIMS Manager` 同时具备 submit / review / approve 权限，因此普通检验链可由同一账号连续完成多级签署。

必须：
- 基础检验结果与稳定性结果采用同一 SoD 原则。
- submit 还应验证普通 Analyst 只能提交本人/本人任务的草稿；Manager 的代操作必须显式、留痕并有受控理由。
- review：reviewer != analyst。
- approve：approver != reviewer；是否还要求 approver != analyst 按质量 SOP 明确。
- SoD 拦截必须测试并审计。

### L10-P0-04：Active Specification 可以原地改内容但版本号不变

`HBOS Specification.validate()` 当前只：
- 守卫 `status/effective_date`
- 校验版本唯一
- 校验限度逻辑

没有禁止“已生效/已废止”标准的业务内容直接修改。

而 LIMS Manager 拥有该 DocType write 权限。

因此可能出现：
- `SPEC-A v1.0` 已生效；
- 直接修改检验项目/限度/物料/标准来源；
- 名字仍叫 v1.0；
- 新样品读到变更后的 v1.0；
- 历史上出现“同一个版本号代表两个内容”的情况。

必须：
- 已生效/已废止 Specification 内容整体不可原地修改。
- 变更必须创建新版本，并保留 supersedes / previous version 关系。
- 生效动作冻结完整内容快照。
- 新样品引用新版本，历史样品继续指旧版本。

### L10-P0-05：COA 已审核/已发布后子表内容仍可原地修改

`HBOSCOA._validate_locked_after_review()`：
- 锁了部分头字段；
- 只判断 `len(self.items) != len(before.items)`；
- 没有比较同长度子表的每一行内容。

`HBOS COA Item` 自身没有保护控制器。

因此在已审核/已发布状态下，有写权限的角色理论上仍可修改：
- 检验项目
- 方法 SOP
- 标准限度
- 结果
- 判定
- 备注

只要不改变行数。

必须：
- 审核后冻结整个 COA snapshot，包括全部 child row 内容与顺序/唯一语义。
- 发布后禁止任何业务内容修改。
- 如需更正，走正式 COA revision / void + reissue 流程，不修改原件。
- 发布 PDF 与结构化 COA 内容必须能验证为同一版本。

### L10-P0-06：System Manager 被当成质量业务绕过角色

通用 `guard_system_fields()` 复用了 `stability_guards._privileged()`：

- Administrator → bypass
- System Manager → bypass

这意味着 System Manager 可绕过“系统字段只能通过业务 Service 修改”的规则，直接改：
- status
- reviewer / approver
- signatures
- version chain
- 其它受控字段

技术管理员与质量批准人不是同一概念。

必须：
- System Manager 不能自动拥有质量状态/签署业务绕过权。
- 技术运维逃生口需独立、受审计、显式 break-glass。
- 迁移/系统 Service 使用内部 flag / service principal，而不是泛化到所有 System Manager。
- Administrator 的 break-glass 行为也应明确留痕。

### L10-P0-07：当前“电子签名”只是用户+时间字符串

普通结果签署当前核心形式是：
`meaning: user @ timestamp`

并由当前已登录 session 自动生成。

它能提供操作归属，但并不等价于完整电子签名控制，例如：
- 未做签署时二次认证 / re-auth；
- 未证明签署意图；
- 未绑定签署原因；
- System Manager 当前还能绕过系统字段；
- 没有独立不可篡改签名证据。

若 HBOS LIMS 仅作为内部流程系统，可以准确称“用户签署记录/操作归属”。

若要作为正式 GMP / 电子记录签名能力，则必须另建 e-signature 设计并验证。

在完成前，不应以当前字符串实现宣称强电子签名合规。

### L10-P0-08：LIMS 与 ERPNext Item / Batch 主数据没有正式关系

当前：
- `HBOS Sample.material_code/material_name/batch_no` 是 Data；
- `HBOS Specification.material_code/material_name` 是 Data；
- `HBOS Stability Product` 又维护 product_code / product_name / default_uom 等。

而 ERPNext 已有：
- Item
- Batch
- UOM

这会形成第二套主数据。

必须采用“引用 + 快照”：

```text
item_ref      Link -> Item
batch_ref     Link -> Batch

material_code_snapshot
material_name_snapshot
batch_no_snapshot
spec_snapshot...
```

原则：
- ERPNext Item / Batch 是当前主数据源。
- LIMS 在业务发生时冻结快照，历史记录不跟随 ERP 主数据改名而漂移。
- 老 LIMS 数据可保留 Data 快照，新增 Link 字段做向后兼容迁移。
- register_sample 必须验证 Batch 与 Item 关系，不接受任意字符串组合。
- Specification / Stability Product 的“产品主数据”也要区分 ERP 引用与 LIMS 专属质量属性。

### L10-P0-09：LIMS Release 与 Inventory Batch Release 尚未接通

当前 `release_sample()` 只改变：
- `HBOS Sample.status = 已放行`

没有更新 ERPNext Batch。

而 PR #8 Inventory 的出库门禁读取：
- Batch.hbos_release_status
- Batch.hbos_certificate_no

必须建立正式：

`LIMS Quality Release Service -> ERPNext Batch projection`

建议 Batch 投影：
- hbos_release_status
- hbos_release_date
- hbos_certificate_no
- hbos_certificate_file
- hbos_lims_reference
- hbos_release_source = LIMS

Warehouse 只读，不拥有放行决定权。

### L10-P0-10：release_sample 未要求已发布 COA

当前 `release_sample()`：
- 检查 OOS lock
- 按状态机从检验完成 → 已放行

没有确认该 Sample 已存在“已发布 COA”。

而 Inventory 的出库业务规则要求：
- QA 放行
- 合格证

因此最终业务链必须明确。

建议：
```text
全部结果批准
→ COA 创建
→ QA 审核
→ COA 发布
→ Sample Release
→ Batch Release Projection
→ Warehouse 可出库
```

如果某类样品业务允许“无 COA 放行”，必须配置为明确业务类型，而不能默认所有样品都允许。

### L10-P0-11：COA 权限动作复用了不相关 action 名

当前：
- `create_coa()` 使用 `_check_action("release_sample")`
- `review_coa()` 使用 `_check_action("review_result")`
- `publish_coa()` 也使用 `_check_action("review_result")`

这使 COA 自己没有清晰的：
- create_coa
- review_coa
- publish_coa
- void/reissue_coa

权限矩阵。

必须在 workflow_contract 中建立 COA 独立动作和角色，不借用 Sample/Result 动作名称。
是否要求 review/publish SoD 由质量流程明确并写入测试。

### L10-P0-12：依赖声明与实际依赖不一致

当前：
`required_apps = ["frappe"]`

但 hooks 已直接注册：
`Customer.validate`

稳定性专项报告也使用 ERPNext Customer。

在最终 HBOS 同 Site 架构下，LIMS 实际依赖 ERPNext。

必须：
- `required_apps = ["frappe", "erpnext"]`
- pyproject 声明 ERPNext 版本范围
- clean-site 测试验证依赖顺序
- 不允许“代码隐性依赖 ERPNext、包声明说只依赖 Frappe”。

### L10-P0-13：clean-site Docker 并不会安装 LIMS

PR #10 docker-compose 虽然：
- mount `hb_lims_app`
- 加入 PYTHONPATH

但 `create-site` 仍只有：
`--install-app erpnext`

没有安装：
- hrms
- hb_attendance_app
- hb_lims_app

所以这份 Compose 只能依赖已有站点/后续人工安装，不能从零重建 HBOS。

必须：
- 最终统一平台镜像/安装清单显式安装所有 App；
- clean site 从零执行后 `bench list-apps` 必须包含预期 App；
- `bench migrate` 必须无人工补步骤。

### L10-P0-14：LIMS Vue 生产部署仍是运行时手工注入

仓库中有完整 `frontend/hbos-lims-web`，但当前 Compose 没有：
- 构建 SPA
- 将 dist 作为确定构建产物注入镜像
- 配置版本化 nginx SPA fallback

阶段文档显示历史部署大量依赖：
- `npm run build:prod`
- docker cp
- 清旧 assets
- 重启/补 nginx fallback

最终生产不能依赖“把文件拷进正在运行的容器”。

必须：
- CI 构建前端；
- 自定义 HBOS image / static artifact；
- frontend/backend/worker 使用同一版本构建产物；
- 部署可回滚、可复现。

### L10-P0-15：#10 当前没有真正的合并 CI / migrate Gate

PR #10 目前：
- Draft
- mergeable=false
- 当前 HEAD 没有对应 GitHub workflow run
- PR 描述中的 404 passed / 10 skipped、Vue 7/7、build 是本地结果
- 明确没有执行 Docker deployment / DB migrate

而当前 workflow 本身只运行 Attendance unittest，不运行 LIMS pytest / Vue tests。

必须将以下变成 GitHub merge gate：
- LIMS Python tests
- Vue typecheck/unit/build
- clean-site install/migrate
- runtime permission tests
- audit transaction tests
- SoD tests
- LIMS ↔ Inventory release integration tests
- Docker/browser smoke

---

## 3. P1 / 高优先级治理

### L10-P1-01：数值判定/公式计算使用 float

`result_contract.py`：
- `judge_result` 用 float
- `apply_formula` 用 float
- 最后修约才转 Decimal

对接近规格限度的质量结果，二进制浮点误差不适合作为长期权威计算基础。

建议：
- 输入、公式和规格比较全程 Decimal；
- 明确定义修约发生在“计算后/判定前/报告时”的顺序；
- 增加边界值药典修约测试。

### L10-P1-02：独立前端路由未登录时仍允许进入 Shell

router guard 只做 `checkSession()`，最后始终 `return true`。

后端权限仍会保护数据，因此不是服务端授权漏洞，但 Guest 会进入业务壳后再遇到 API 错误。

建议：
- 未登录跳 Frappe 登录页并带安全的站内 redirect-to；
- 已登录但无任何 LIMS role 显示 403/无权限页；
- route meta 可用于 UX 级角色导航，但不能替代后端 RBAC。

### L10-P1-03：多个 projection API 使用 get_all 绕过 DocType permission

核心业务 Service 有角色门禁，但部分查询使用 `frappe.get_all`，等价于“具备某 LIMS 角色即可看全域”。

需要确认未来是否存在：
- 实验室部门隔离
- 厂区隔离
- 产品/客户级数据范围

若存在，应增加 row-level scope，而不是只做 role-level scope。

### L10-P1-04：Frappe 16.26.3 Sidebar workaround 应版本化

`boot_session = sync_user_perm_can_read_cache` 是针对特定 Frappe bug 的 workaround。

建议：
- 明确适用版本范围；
- 升级后自动禁用或通过 feature flag；
- 不长期把框架内部 cache key 当稳定 API。

### L10-P1-05：Specification / COA / 结果的“删除”策略应统一

例如 draft Specification 使用 `frappe.delete_doc(..., force=1)`，稳定性/留样又普遍采用“终态不可删”。

建议定义统一质量数据生命周期：
- 草稿是否允许物理删除；
- 生效/提交后只允许 void/cancel；
- 删除审计与引用检查规则统一。

---

## 4. 已确认的优点

以下设计质量较高，治理时应保留：

- 大部分公开写接口统一通过 `_check_action` 做角色控制。
- Stability/Retention 已有较系统的 SoD 设计。
- 结果提交后关键原始数据锁定，并提供 revision 版本链。
- OOS 候选可锁定样品。
- 质量标准检验项目快照进入 Sample。
- COA PDF 使用 private File。
- Stability 业务结果投影具备 source_test_result 幂等键和版本链思路。
- 多处关键并发场景使用 row lock / for_update。
- Todo 聚合使用 permission-aware `frappe.get_list`，不接受调用者伪造 user/roles。
- Vue 3 + Ant Design Vue 前端可继续作为 LIMS 独立工作台，不需要推翻。

---

## 5. LIMS Clean Candidate 目标

建议后续建立：

`integration/pr10-lims-clean`

保留：
```text
apps/hb_lims_app/**
frontend/hbos-lims-web/**
LIMS tests / 必要 docs
```

但先完成：
- audit transaction redesign
- audit integrity semantics
- base Result SoD
- Specification immutable versioning
- COA full snapshot lock
- technical admin vs quality authority separation
- ERP Item/Batch link + snapshot
- LIMS → Batch release projection
- ERPNext dependency declaration
- reproducible frontend/backend deployment
- real CI/migrate gate

最终 docker-compose 不采用 #10 当前版本直接覆盖，而由三 App integration 生成统一平台部署。

---

## 6. LIMS Definition of Done

只有全部满足才标记 READY_FOR_PLATFORM_INTEGRATION：

- [ ] 审计违规记录不会 commit 当前业务事务
- [ ] 审计完整性机制与文档表述一致
- [ ] 普通检验 Result SoD PASS
- [ ] Analyst 不能提交他人的普通检验结果（除显式授权代办）
- [ ] Active Specification 内容不可原地改
- [ ] Reviewed/Published COA 全快照不可原地改
- [ ] System Manager 不再自动成为质量业务 bypass
- [ ] “电子签名”能力按实际实现准确命名；正式 e-sign 需求另行满足
- [ ] ERP Item/Batch 引用 + LIMS snapshot 数据模型确定
- [ ] Sample 的 Item/Batch 关系校验 PASS
- [ ] Published COA / Release 规则确定
- [ ] LIMS release → Batch projection PASS
- [ ] COA 独立权限动作矩阵 PASS
- [ ] required_apps / pyproject 显式声明 ERPNext
- [ ] clean-site 安装 + migrate PASS
- [ ] Vue build/deploy 可复现
- [ ] LIMS Python + Vue + runtime integration CI PASS
- [ ] 与 Inventory “待检→检验→COA→放行→出库”联合测试 PASS

通过只表示可以进入 `integration/hbos-platform-v1`，不代表可直接 merge main。
