# Current Milestone

## M1：平台入口、身份与考勤一期准备

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M1-R5：HRMS 配置基线、考勤工作台与月度汇总 Demo。当前状态：REVIEWING。

M1-R4：M1 Demo 技术方案与实施路线拆分。当前状态：COMPLETED。

M1-REQ-DESIGN-DRAFT-CLOSEOUT：M1 需求设计草案审查通过后状态收口。当前状态：COMPLETED。

M1 考勤一期仍在推进中。M0 已完成并封板。M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1 当前状态：IN_PROGRESS。M1-R0 已通过 Codex 独立审查并收口为 COMPLETED。M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED。M1-R5 已完成文档交付并进入 REVIEWING。M1-R6/R7/R8 均为 PLANNED，待用户逐轮授权。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M1-R5：HRMS 配置基线、考勤工作台与月度汇总 Demo。不得启动 M1-R6/R7。

交付内容：

- `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md`（本轮主文档）
- 项目状态、当前里程碑和里程碑索引文件更新
- 公共入口文件过期状态清理

本轮实际结果：

- M1-R5 已整理 HRMS / Frappe 原生考勤配置基线，覆盖 Company、Department、Employee、Shift Type、Shift Assignment、Holiday List、Employee Checkin、Attendance、Leave Application、Attendance Request、Role、Workspace、Report / 导出路径。
- 已形成“考勤工作台”入口方案，优先使用 Frappe Desk / Workspace 聚合员工信息、班次配置、排班、打卡记录、考勤结果、请假记录、考勤申请 / 补卡入口、月度汇总报表和 Excel 导出路径。
- 已形成月度汇总 Demo 展示路径，并对 14 个字段逐项标注原生可覆盖、需计算汇总和暂无法直接覆盖的部分。
- 已形成 Excel 月报导出路径，优先使用 Frappe Report Export、List View Export 和 Data Export。
- 已记录当前仓库没有可承载 Workspace / Report fixture 的已存在自定义 App，因此本轮不硬写 Frappe site 数据库配置，仅提交可审查的文档与配置说明。
- M1-R5 当前状态为 REVIEWING，等待审查或验收。
- M1-R6/R7 均为 PLANNED，待用户逐轮授权；M1-R8 为可选缓冲轮。
- 本轮未创建 App，未创建 DocType，未修改核心源码，未接真实考勤机，未接飞书登录，未正式接飞书请假，未接飞书工作台，未提交真实员工姓名或未脱敏数据。

## 本轮禁止事项

- 不创建 Frappe bench
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
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
- 不修改 `docker-compose.yml`、`.env.example`、`.gitignore`
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
- M1-R5 当前状态为 REVIEWING，主文档已交付。
- M1-R6 当前状态为 PLANNED，待授权，未启动。
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
- M1-R5 当前状态为 REVIEWING，等待审查或验收
- M1-R6/R7 保持 PLANNED，未启动
- 本轮未开发业务代码，未写入站点数据库，未创建海滨自定义 App / DocType / 核心源码变更

## 下一轮预告

M1-R5 当前为 REVIEWING。审查或验收通过后，由用户决定是否授权进入 M1-R6（脱敏 Excel 导入、异常识别与异常说明流程）。M1-R6/R7 均为 PLANNED，需用户逐轮授权后方可启动。
