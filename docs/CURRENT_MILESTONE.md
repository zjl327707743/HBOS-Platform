# Current Milestone

## M1：平台入口、身份与考勤一期准备

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M1-R3E：配置复核清单与业务口径确认表。当前状态：REVIEWING。

M0 整体已完成并封板。M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1 当前状态：IN_PROGRESS。M1-R0 已通过 Codex 独立审查并收口为 COMPLETED。M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已完成配置复核清单与业务口径确认表文档交付，当前为 REVIEWING。M1-R4 为 PLANNED，尚未启动。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M1-R3E 文档交付：基于 M1-R3C / M1-R3D 形成 HRMS 配置复核清单与海滨业务口径确认表。不得继续试运行，不得清理 TEST 数据，不得创建 App / DocType / 代码，不得启动 M1-R4。

交付内容：

- `docs/milestones/M1_R3E_配置复核与业务口径确认表.md`
- 项目状态、当前里程碑和里程碑索引文件更新
- 公共入口文件过期状态清理

本轮实际结果：

- M1-R3E 已新增配置复核与业务口径确认表。
- 配置复核清单覆盖迟到、早退、全天缺勤、Leave Allocation、缺卡基础字段、加班候选、节假日出勤和临时调班。
- 业务口径确认表覆盖迟到、早退、上班缺卡、下班缺卡、缺勤、半天请假、全天请假、加班、节假日出勤和临时调班。
- 明确 Attendance 生成不等同于海滨考勤业务闭环完成。
- 当前仍不建议创建 `hb_attendance_app`。
- M1-R3E 当前为 REVIEWING，等待 Codex 审查；M1-R4 保持 PLANNED，尚未启动。
- 本轮未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。

## 本轮禁止事项

- 不创建 Frappe bench
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不创建任何海滨自定义 Frappe App
- 不做业务代码
- 不开发考勤业务
- 不接飞书
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
- M1-R3E 为 REVIEWING。
- M1-R4 为 PLANNED，尚未启动。

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
- M1-R3E 为 REVIEWING，等待 Codex 审查
- M1-R4 保持 PLANNED
- 本轮未继续试运行，未创建、删除或清理 TEST 数据，未创建海滨自定义 App、未开发考勤业务、未接真实考勤机、未接飞书真实写入、未实现 SSO、未修改核心源码、未修改中文化源码、未录入真实业务数据

## 下一轮预告

下一步先交给 Codex 审查 M1-R3E。审查通过后，再由用户决定是否进入 M1-R4：二次最小验证或报表设计。M1-R4 仍为 PLANNED，尚未启动。
