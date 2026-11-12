# R6 只读 DTO 合同补齐

状态：`G4_ISOLATED_UAT / NOT_MERGED`，2026-10-27。

Owner 已授权根据三个文件的提案另建独立后端 PR，补本人岗位、审计筛选与脱敏前后内容。该授权不含 schema、真实数据写入、合并、RC 或发布。基线是 #62/#61 实际集成后的 `feature/hbos-portal-product@22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`；正式前端独立在 [PR #63](https://github.com/zjl327707743/HBOS-Platform/pull/63)，没有将其源码混入本 PR。

## 合同

- `get_my_employee_status` 新增 `position`：仅取当前 User 通过既有唯一关联解析出的 Employee.designation；未关联/冲突返回 null，不接受他人 Employee 参数。
- `iam_audit.list_events` 新增可选 `date_from`、`date_to`、`operation`、`result`。日期 YYYY-MM-DD，结束日期含当天；操作/结果为准确值。日期、类型、长度和对象参数先验证。count/page 共用同一带括号的对象可见性条件与 AND 筛选，查询参数化；分页上限 50 保留。
- `iam_audit.get_event(name)` 先要求独立 audit capability，复用原 list_events 对该对象的可见性判断，包含角色所有管理公司的 audit/role read；只返回原元数据及再次经过 safe_snapshot 的 before/after，不输出原 JSON 字符串或凭据字段。不存在/越域记录均拒绝。
- 部分对象筛选现在对根账号也拒绝，避免类型/标识缺一的含糊查询；没有扩大任何管理范围。

不修改：持久化模型、角色赋予/执行、登录、CSRF、proof、MFA、写接口、既有发布/个人禁止、Site 配置或数据库。

## 验证与门禁

先写 12 项合同测试，确认旧代码缺少对应能力；初次测试夹具缺 rate_limiter 导入未计为产品回归证据，补齐夹具后重新取得真实旧代码失败。补丁后加入非法对象类型用例，共新增 13 项；Python 3.11 与 3.12 各全量 **261 tests PASS**。覆盖范围内读取、越域拒绝、没有 audit capability 的拒绝、角色多公司门禁、count/page 过滤一致性、SQL 参数化、错误日期与类型、嵌套凭据键脱敏、损坏快照拒绝，以及岗位只来自当前主体。

这些是离线合同测试，不替代真实 Site/HTTP 的允许与 403。Owner 已另行批准 18191 纯合成 Site 的 R6 联调方案，测试组合 `97e0272` 已部署该隔离窗口；真实数据、18090、8080 和飞书不在该窗口范围。固定 head/base 合并仍须专门 Owner 决定，非作者审查门禁没有由 #61/#62 的历史偏差解除。回退定位为本 PR 单独分支与产品 22，不授权恢复任何真实数据库。

## G4 实际联调修复

测试组合 `97e0272` 的本人岗位为 FAIL：真实 policy.resolve_employee 只投影身份字段，不含 designation。修复为先唯一解析当前 User 的 Employee，再仅按该已解析主键读取 designation，不改变共享授权解析器。回归夹具改为与真实解析结果一致；旧实现出现 AttributeError，修复后 Python 3.11/3.12 各 261 tests PASS。裸系统 Python 缺锁定 pypinyin 的运行不计 PASS；通过结果来自已有锁定依赖虚拟环境。未关联/冲突断言不查询 designation。修复后须重新组合、构建并复测真实岗位；旧组合不计完整验收通过。

旧组合真实 HTTP 已通过普通员工无管理 capability、people/audit/native User 的 403、人事公司内 9 人与准确 total、公司外员工及审计列表/详情 403、受控审计详情、日期与操作/结果组合筛选、参数化输入和未发布角色前业务拒绝。Guest 被 Frappe whitelist 提前拒绝为 403，原验收脚本误设 401；应断言未认证拒绝且不返回安全 DTO，不修改接口授权语义。
