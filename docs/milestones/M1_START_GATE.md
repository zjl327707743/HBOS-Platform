# M1 启动门禁

项目名称：新乡海滨智能运营管理平台。

## 文件定位

本文件记录 M1 启动前必须满足的门禁条件。M1-R0 已按本门禁完成规划收口，M1-R1 已按门禁只读验证 HRMS 原生考勤对象模型并收口为 COMPLETED，M1-R2 已按门禁形成 HRMS 原生考勤配置试运行方案并收口为 COMPLETED。M1-R3 已按用户授权尝试虚构 TEST 最小数据试运行并通过 Codex 审查，但实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED，尚未进入业务开发。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED。M1-R5 已通过 Codex 审查并收口为 COMPLETED。

## 必须满足的前置条件

- M0 状态必须为 COMPLETED。
- M0-REMOTE 必须完成：创建 GitHub Private remote、添加 `origin`、首次 push `main`。（已完成，见 `docs/milestones/M0_REMOTE.md`。）
- `git status` 必须 clean。
- 不允许提交 `.env`、备份文件、密钥、数据库、Docker volume 或运行时数据。
- 当前 Frappe / ERPNext / HRMS 环境应保持可访问；如 HRMS 丢失，必须先恢复环境，再讨论 M1。

## M1 初期范围

M1-R0 只做：

- 平台入口治理。
- 账号体系。
- 角色权限。
- 飞书 SSO 可行性。
- 中文化 / 本地化诊断。

M1-R0 当前状态：COMPLETED，已通过 Codex 独立审查。方案文件见 `docs/milestones/M1_R0_平台入口账号权限与本地化诊断方案.md`。

M1-R0 不做：

- 不开发考勤业务。
- 不创建 `hb_attendance_app`。
- 不接飞书真实写入。
- 不实现 Vue / React 驾驶舱。
- 不修改 Frappe / ERPNext / HRMS 核心源码。

M1-R1 才验证 HRMS 原生考勤对象模型。M1-R1 当前状态：COMPLETED，已通过 Codex 独立审查，验证记录见 `docs/milestones/M1_R1_HRMS原生考勤对象模型验证记录.md`。

M1-R2 当前状态：COMPLETED，已通过 Codex 独立审查。M1-R2 只做 HRMS 原生考勤配置试运行方案，未执行配置，未创建测试数据，未创建 App，未接真实考勤机，未接真实飞书，未录入生产数据。方案文件见 `docs/milestones/M1_R2_HRMS原生考勤配置试运行方案.md`。

M1-R3 当前状态：BLOCKED。M1-R3 已使用 `TEST-HBOS-M1R3-` 前缀尝试虚构最小测试数据试运行 HRMS 原生考勤配置；部分 TEST 数据已落库，但 Attendance 闭环与 14 个场景验证未完成。Codex 审查 PASS，但该轮不是成功完成，不得标记为 COMPLETED。记录见 `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`。

M1-R3A 当前状态：COMPLETED。M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查，记录见 `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`。本轮未继续创建测试数据，未执行配置试运行，未清理数据。

M1-R3B 当前状态：COMPLETED。M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查，记录见 `docs/milestones/M1_R3B_运行态最小修复方案.md`。本轮只是修复方案和状态收口，不是修复执行；未执行修复，未启动或重启服务，未清理 TEST 数据，未继续试运行。

M1-R3B-FIX 当前状态：COMPLETED。M1-R3B-FIX 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3B_FIX_运行态最小修复执行记录.md`。该轮只执行 `docker compose up -d redis-cache redis-queue`，`redis-cache`、`redis-queue`、queue worker、scheduler、`bench doctor` 和 `/login` 已恢复或改善；未清理 TEST 数据，未继续创建 TEST 数据，未执行 HRMS 考勤试运行。

M1-R3C 当前状态：COMPLETED。M1-R3C 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；结论为 PARTIAL / GAP_IDENTIFIED。M1-R3C 已在用户授权下使用 `TEST-HBOS-M1R3C-*` / `test-hbos-m1r3c-*` 虚构 TEST 数据重新试运行；Company / User / Employee 写入阻断已解除，13 条 Attendance 已生成，14 个场景中 8 个通过、6 个为 GAP / PARTIAL。迟到 / 早退未置位、缺卡 / 缺勤口径、请假 Leave Allocation、加班业务口径仍是后续 Gap。记录见 `docs/milestones/M1_R3C_HRMS原生考勤最小试运行复测记录.md`。

M1-R3D 当前状态：COMPLETED。M1-R3D 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3D_异常口径与Gap诊断.md`。结论为 Gap 四类分类（HRMS 配置、原生 / 自定义报表、海滨业务规则定义、未来自定义 App 候选），8 个 Gap 均不需要立即创建 `hb_attendance_app`。本轮未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码，未接真实考勤机、真实飞书或 SSO。

M1-R3E 当前状态：COMPLETED。M1-R3E 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3E_配置复核与业务口径确认表.md`。本轮仅做文档交付，未试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。配置复核清单覆盖 8 类问题，业务口径确认表覆盖 10 项业务口径，8/10 项阻塞 M1-R4。

M1-R3F 当前状态：COMPLETED。M1-R3F 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3F_业务口径确认包.md`。本轮完成文档交付并已收口，未试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。确认包共 9 项确认主题，7 项必须业务负责人确认才能进入 M1-R4。

M1-REQ-DESIGN-DRAFT 当前状态：COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查，审查结果 PASS（初审员工姓名脱敏 blocker 已修复，提交 `69aec6a`），并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_考勤一期真实需求确认.md`、`docs/milestones/M1_考勤一期产品需求说明书.md`、`docs/milestones/M1_考勤一期技术设计方案.md`、`docs/milestones/M1_Demo实施路线图.md`。本轮只写文档，未试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码，不修改核心源码。已补齐 M1 真实需求、PRD、技术设计、Demo 实施路线图四份文档。M1-R4 定位为 Demo 技术方案与实施路线拆分。

M1-R4 当前状态：COMPLETED。M1-R4 已完成 Demo 技术方案与实施路线拆分，主文档 `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` 已交付。审查记录：Codex 初审 FAIL（发现 3 类 blocker：Git 同步门槛、公共入口 M1-R4 过期状态残留、阶段文字错误），已在 `2fbb6dc` 中修复；Codex 复审 PASS。M1-R4 定位为规划拆分轮，已完成 R5/R6/R7 后续轮次拆分，未开发、未试运行、未创建 App/DocType/代码。

M1-R5 当前状态：COMPLETED。M1-R5 已完成 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 展示路径与 Excel 月报导出路径文档交付，主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。审查记录：Codex 审查 PASS，已从 REVIEWING 收口为 COMPLETED。

M1-R6A 当前状态：COMPLETED。M1-R6A 已完成 Excel 导入与异常流程落地方案 / Gate 判定文档交付，主文档 `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` 已交付。审查记录：Codex 初审 FAIL（未提交、工作区不 clean），复审 PASS（修复后 closeout 收口为 COMPLETED）。本轮未导入 Excel、未创建 App、未创建 DocType、未写代码。

M1-R6B 当前状态：REVIEWING。M1-R6B 已完成脱敏打卡流水导入最小实现，主文档 `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` 已交付。本轮先将 Owner 提供 Excel 判定为混合表，未将其作为 Employee Checkin 导入源；使用脱敏 Demo 原始打卡流水写入 5 条 Employee Checkin，并通过 HRMS 原生 Auto Attendance 生成 3 条 Attendance。本轮未提交 Excel / CSV，未创建 App，未创建自定义 DocType，未启动 R6C/R7。

M1-R6C 当前状态：PLANNED（待 R6B 审查 PASS 并 closeout 后用户授权启动）。
M1-R7 当前状态：PLANNED，待用户授权启动。
M1-R8 当前状态：PLANNED（可选缓冲轮，不预先承诺一定执行）。

## 中文化与核心源码边界

中文化问题只诊断，不改 Frappe / ERPNext / HRMS 核心源码。

优先使用：

- 原生配置。
- 角色权限。
- DocType。
- 报表。
- 导入。
- API。
- 低代码定制。

## 自定义 App 决策边界

M1 初期不创建 `hb_attendance_app`。

优先复用 HRMS 原生考勤能力。只有 HRMS 原生能力无法覆盖新乡海滨特有规则，或用户明确批准进入自定义 App 阶段时，才考虑创建自定义 App。

自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。

## 飞书边界

飞书真实写入必须用户明确授权。

飞书真实写入包括但不限于：

- 群消息发送。
- 多维表格写入。
- 通讯录修改。
- 审批操作。
- 邮件发送。
- 云文档编辑。
- 任务创建或修改。

## 环境保护规则

- 不得执行 `docker compose down -v`。
- 不得删除 Docker volume。
- 不得删除或重建 `frontend` site。
- 不得重新初始化 ERPNext。
- 不得提交 `.env`、备份文件、密钥、数据库、Docker volume 或运行时数据。

## 启动顺序

1. M1-R0：平台入口治理、账号体系、角色权限、飞书 SSO 可行性、中文化 / 本地化诊断。
2. M1-R1：HRMS 原生考勤对象模型验证。
3. M1-R2：HRMS 原生考勤配置试运行方案。
4. M1-R3：HRMS 原生考勤最小测试数据试运行。
5. M1-R3A：运行态阻断诊断与 TEST 数据隔离 / 清理方案。
6. M1-R3B：运行态最小修复方案。
7. M1-R3B-FIX：运行态最小修复执行，当前为 COMPLETED。
8. M1-R3C：HRMS 原生考勤最小试运行复测，当前为 COMPLETED。
9. M1-R3D：HRMS 原生考勤异常口径与配置 Gap 诊断，当前为 COMPLETED。
10. M1-R3E：配置复核清单与业务口径确认表，当前为 COMPLETED。
11. M1-R3F：业务口径确认包，当前为 COMPLETED。
12. M1-REQ-DESIGN-DRAFT：M1 考勤一期需求设计草案，当前为 COMPLETED。
13. M1-R4：M1 Demo 技术方案与实施路线拆分，当前为 COMPLETED。
14. M1-R5：HRMS 配置基线、考勤工作台与月度汇总 Demo，当前为 COMPLETED。
15. M1-R6A：Excel 导入与异常流程落地方案 / Gate 判定，当前为 COMPLETED。
16. M1-R6B：脱敏打卡流水导入最小实现，当前为 REVIEWING。
17. M1-R6C：异常说明流程与 R6 收口，当前为 PLANNED。
18. M1-R7：飞书登录、领导汇总 Demo 与 M1 收口，当前为 PLANNED。
19. M1-R8：M1 Demo 验收修复与文档收口（可选缓冲轮），当前为 PLANNED。

M0-REMOTE 已完成。M1-R0 已完成。M1-R1 已完成并通过 Codex 独立审查。M1-R2 已完成并通过 Codex 独立审查。M1-R3 已通过 Codex 审查并收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 为 COMPLETED。M1-R3C 为 COMPLETED。M1-R3D 为 COMPLETED。M1-R3E 为 COMPLETED。M1-R3F 为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED。M1-R6A 为 COMPLETED。M1-R6B 为 REVIEWING。M1-R6C/R7 为 PLANNED，尚未启动。
