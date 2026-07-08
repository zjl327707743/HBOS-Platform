# Current Milestone

## M1：平台入口、身份与考勤一期准备

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M1-R6B：脱敏打卡流水导入最小实现。当前状态：COMPLETED。

M1-R6A：Excel 导入与异常流程落地方案 / Gate 判定。当前状态：COMPLETED。

M1-R5：HRMS 配置基线、考勤工作台与月度汇总 Demo。当前状态：COMPLETED。

M1-REQ-DESIGN-DRAFT-CLOSEOUT：M1 需求设计草案审查通过后状态收口。当前状态：COMPLETED。

M1 考勤一期仍在推进中。M0 已完成并封板。M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1 当前状态：IN_PROGRESS。M1-R0 已通过 Codex 独立审查并收口为 COMPLETED。M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED。M1-R5 已通过 Codex 审查并收口为 COMPLETED。M1-R6A 为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C/R7/R8 均为 PLANNED / 待授权 / 未启动。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M1-R6B：脱敏打卡流水导入最小实现。不得启动 M1-R6C/R7。

在 M1-R6B closeout 后，Owner 确认新增前端实施流程规范 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`，确立"原型先行 + Owner 审查 + 复刻实现 + 功能接入"的前端开发流程。此为项目长期规范，不改变 M1 当前范围。

交付内容：

- `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md`（本轮主文档）
- 项目状态、当前里程碑和里程碑索引文件更新
- 公共入口文件过期状态清理

本轮实际结果：

- Owner 提供 Excel 已判定为混合表，不适合作为 `Employee Checkin` 直接导入源。
- 已补充 `.gitignore` 覆盖 `docs/data/*.xlsx`、`docs/data/*.xls`、`docs/data/*.csv`，防止真实导出文件误提交。
- 已固定 Demo 脱敏原始打卡流水模板和 `attendance_device_id` 匹配规则。
- 已在本地 `frontend` site 写入 3 名虚构员工、1 个 R6B Shift Type、3 条 Shift Assignment 和 5 条 Employee Checkin。
- 已调用 HRMS 原生 `process_auto_attendance()`，生成 3 条 Attendance。
- 已验证 `Employee Checkin -> Auto Attendance -> Attendance` 最小链路通过。
- 迟到 / 早退候选 Attendance 已生成，但 `late_entry` / `early_exit` 未置位，留给 R6C 或后续配置复核。
- M1-R6B 已通过 Codex 审查并收口为 COMPLETED。
- M1-R6C/R7 均为 PLANNED / 待授权 / 未启动；M1-R8 为可选缓冲轮。
- 本轮未提交 Excel / CSV，未创建 App，未创建 DocType，未修改核心源码，未接真实考勤机，未接飞书，未提交真实员工姓名或未脱敏数据。

## 本轮禁止事项

- 不实现完整 Excel 导入生产功能
- 不导入真实或脱敏 Excel
- 不使用真实 Employee Checkin / Attendance 数据
- 不创建 Frappe bench
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不创建 `hb_hr_app`
- 不创建任何海滨自定义 Frappe App
- 不做业务代码
- 不开发考勤业务
- 不接飞书登录
- 不正式接飞书请假
- 不接飞书工作台
- 不接飞书真实写入
- 不实现 SSO
- 不修改中文翻译源码
- 不做前端驾驶舱
- 不引入外部源码
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site
- 不重新安装 HRMS
- 不修改 `docker-compose.yml`、`.env.example`
- `.gitignore` 仅允许为防止 `docs/data` 本地 Excel / CSV 误提交做最小更新
- 不创建新的 Frappe App
- 不创建新的自定义 DocType
- 不提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物

## 当前批次状态

- M0-R2 设计文档已完成并提交。
- M0-R2A 默认入口文档过期描述修复已完成。
- M0-R2B 里程碑状态管理规范已完成。
- M0-R2C AI Skill 路由文档纳入已完成。
- M0-R2D 中文提交与文档命名规范已完成。
- M0-R2E README 阶段描述修复与公共入口文件收尾规则补强已完成。
- M0-R3A 已完成：镜像拉取成功，容器启动成功，测试 site 初始化成功，Frappe Desk 登录页验证成功。
- M0-R3B 已完成评估并通过 Codex 审查。
- M0-R3C 已完成：HRMS 已安装到 `frontend` site，`hrms 16.12.0 version-16` 已验证，Desk 与基础 HR 模块可访问。
- M0-R3C-FIX 已完成：HRMS 资源 404、Frappe HR 图标缺失和 Roster 白屏已修复，`/hr/roster/` 已验证渲染 Roster 月视图。
- M0-R3D 已完成能力盘点与 M1 考勤一期边界设计。
- M0-R3E 已完成 HRMS 环境可复现性收口并通过 Codex 审查。
- M0 已完成并封板。
- M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。
- M1-R0 已完成平台入口、账号体系、角色权限、飞书 SSO 可行性、中文化 / 本地化诊断方案，并已通过 Codex 独立审查，状态为 COMPLETED。
- M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。
- M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。
- M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态为 BLOCKED。
- M1-R3A 为 COMPLETED。
- M1-R3B 为 COMPLETED。
- M1-R3B-FIX 为 COMPLETED。
- M1-R3C 为 COMPLETED。
- M1-R3D 为 COMPLETED。
- M1-R3E 为 COMPLETED。
- M1-R3F 为 COMPLETED。
- M1-REQ-DESIGN-DRAFT 为 COMPLETED。
- M1-R4 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R5 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6A 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6B 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6C 当前状态为 PLANNED，待授权，未启动。
- M1-R7 当前状态为 PLANNED，待授权，未启动。

## 验收标准

- M1-R2 已通过 Codex 独立审查并收口为 COMPLETED
- M1-R3 已通过 Codex 审查并收口为 BLOCKED，不得标记为 COMPLETED
- M1-R3A 已通过 Codex 审查并收口为 COMPLETED
- M1-R0 飞书登录目标已保留为：飞书登录为主，HBOS 内部 User 自动映射，Frappe 权限体系承接系统权限和审计
- M1 状态已同步为 IN_PROGRESS
- M1-R3B 已通过 Codex 审查并收口为 COMPLETED
- M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED
- M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED
- M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app
- M1-R3E 已通过 Codex 审查并收口为 COMPLETED
- M1-R3F 已通过 Codex 审查并收口为 COMPLETED
- M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED
- M1-R4 当前状态为 COMPLETED，已通过 Codex 审查并收口
- M1-R5 当前状态为 COMPLETED，Codex 审查 PASS 后完成 closeout 收口
- M1-R6A 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6B 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6C 保持 PLANNED / 待授权 / 未启动
- M1-R7/R8 保持 PLANNED / 待授权 / 未启动
- 本轮未开发业务代码；仅写入虚构脱敏 R6B 本地验证数据到 `frontend` site；未创建海滨自定义 App / DocType / 核心源码变更

## 下一轮预告

M1-R6B 已通过 Codex 审查并收口为 COMPLETED。M1-R6C/R7 均为 PLANNED / 待授权 / 未启动。
