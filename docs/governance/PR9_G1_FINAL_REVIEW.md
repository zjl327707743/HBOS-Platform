# PR #9 / Attendance G1 最终验收

> 候选：PR #11 `integration/pr9-attendance-clean`
> 结论：**READY_FOR_PLATFORM_INTEGRATION**
> 说明：本结论只允许进入 `integration/hbos-platform-v1`，不代表直接合入 `main`。

## A-J Gate

| Gate | 结果 | 主要证据 |
| --- | --- | --- |
| G1-A 重算边界/事务 | PASS | bounded delete；savepoint/rollback；DB 注入失败后旧记录恢复；幂等检查 PASS |
| G1-B Shift version | PASS | stable `rule_code`；版本链；按业务日期选 effective version；旧指针迁移 |
| G1-C Schedule source | PASS | LEGACY/ROTATION/IMPORT/MANUAL/SWAP；同人同日唯一；自动任务只覆盖自有来源 |
| G1-D RBAC | PASS | HR read/write 服务端门禁；外部同步/排班修改不可由普通员工触发 |
| G1-E Private/PII | PASS | HR 导出 private；真实人员策略迁移为 Policy Assignment；私有 seed runbook |
| G1-F clean-site | PASS | 从零建站安装 ERPNext/HRMS/Attendance；双 migrate；关键 Custom Field 检查 |
| G1-G external sync | PASS | Feishu/DeliCloud 默认关闭；调休 orchestrator；DeliCloud 写失败不推进游标 |
| G1-H AI boundary | PASS | AI 默认关闭；PII 独立开关；AI 不改写正式 Attendance |
| G1-I XSS | PASS | 旧 Desk 关键动态身份字段 escape；动态 selector 收口 |
| G1-J CI/integration | PASS | Quality Gate + Attendance Integration Gate 均为强制验证路径 |

## 实际 CI 结果

最终验收前最近一次完整成功：
- HBOS Quality Gate：run #136，PASS
- HBOS Attendance Integration Gate：run #9，PASS

Integration Gate 真实执行并确认：
- Frappe / ERPNext / HRMS / hb_attendance_app 从零安装
- `bench migrate` 连续执行两次
- Employee / Employee Checkin / Attendance 关键自定义字段存在
- regeneration rollback：PASS
- regeneration idempotency：PASS
- Policy Assignment private seed 重复导入：PASS

## 架构结果

- `hb_stock_app` 不进入 Attendance 候选。
- Attendance 继续复用 HRMS Employee / Employee Checkin / Attendance。
- 人员策略成员不再硬编码在 Python。
- Dashboard / Report / Feishu 以正式 Attendance 为事实源。
- 外部集成默认关闭，必须显式配置才能真实出站。

## 后续

1. 将本候选以 **squash** 方式进入 `integration/hbos-platform-v1`。
2. 原始 PR #9 不进入 main，最终标记为被治理候选替代。
3. 平台集成完成前 PR #11 不作为独立 main 合并路径。
