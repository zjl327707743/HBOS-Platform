# Current Milestone

## M1：平台入口、身份与考勤一期准备

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M1-R4：M1 Demo 技术方案与实施路线拆分。当前状态：COMPLETED。

M1-REQ-DESIGN-DRAFT-CLOSEOUT：M1 需求设计草案审查通过后状态收口。当前状态：COMPLETED。

M1 考勤一期仍在推进中。M0 已完成并封板。M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1 当前状态：IN_PROGRESS。M1-R0 已通过 Codex 独立审查并收口为 COMPLETED。M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED。M1-R5/R6/R7/R8 均为 PLANNED，待用户逐轮授权。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M1-R4：M1 Demo 技术方案与实施路线拆分。不得启动 M1-R5/R6/R7。

交付内容：

- `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md`（本轮主文档）
- 项目状态、当前里程碑和里程碑索引文件更新
- 公共入口文件过期状态清理

本轮实际结果：

- M1-R4 Demo 技术方案与实施路线拆分已通过 Codex 审查并收口为 COMPLETED。
- Codex 初审 FAIL：发现 3 类 blocker（Git 同步门槛、公共入口 M1-R4 过期状态残留、阶段文字错误），已在 `2fbb6dc` 中修复。
- Codex 复审 PASS。
- 基于 4 份已完成的 M1 设计文档，已拆分出后续 R5/R6/R7/可选 R8 的详细执行路线。
- 每轮有明确的目标、输入、范围、禁止项、验收点和审查/closeout 要求。
- 已重申 M1 技术边界（复用优先、不修改核心源码、本地 Docker 运行）。
- 已明确数据与脱敏边界（虚构员工姓名、两类导入区分、导入批次、操作留痕）。
- 已列出 12 项 Gate 检查点（均为技术评估/待验证，非已确认需求）。
- M1-R5/R6/R7 均为 PLANNED，待用户逐轮授权。M1-R8 为可选缓冲轮。
- 当前仍不建议创建 `hb_hr_app`。
- 本轮未开发，未试运行，未动数据库，未创建 App / DocType / 代码。

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
- M1-R3E 为 COMPLETED。
- M1-R3F 为 COMPLETED。
- M1-REQ-DESIGN-DRAFT 为 COMPLETED。
- M1-R4 当前状态为 COMPLETED，已通过 Codex 审查并收口。

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
- M1-R5/R6/R7 保持 PLANNED，未启动
- 本轮未开发，未试运行，未动数据库，未创建海滨自定义 App / DocType / 代码

## 下一轮预告

M1-R4 已通过 Codex 审查并收口为 COMPLETED。Codex PASS 后由用户决定是否授权进入 M1-R5（HRMS 配置基线、考勤工作台与月度汇总 Demo）。M1-R5/R6/R7 均为 PLANNED，需用户逐轮授权后方可启动。
