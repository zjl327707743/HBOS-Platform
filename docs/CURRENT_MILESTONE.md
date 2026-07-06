# Current Milestone

## M0：工程启动与上下文治理

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M0-FINAL：文档与状态收口。当前状态：COMPLETED。

M0-R3E HRMS 环境可复现性收口已通过 Codex 审查，状态为 COMPLETED。M0 整体已完成并封板。M1 尚未启动。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M0-FINAL 文档与状态收口：将 M0-R3E 从待审查收口为 COMPLETED，将 M0 整体收口为 COMPLETED，建立 M1 启动门禁，并同步公共入口文件。

交付内容：

- `docs/milestones/M1_START_GATE.md`
- 项目状态、当前里程碑和 M0 里程碑文件更新
- 公共入口文件过期状态清理

## 本轮禁止事项

- 不创建 Frappe bench
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不创建任何海滨自定义 Frappe App
- 不做业务代码
- 不开发考勤业务
- 不接飞书
- 不接飞书真实写入
- 不做前端驾驶舱
- 不引入外部源码
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site
- 不重新安装 HRMS
- 不修改 `docker-compose.yml`、`.env.example`、`.gitignore`
- 不创建 remote
- 不 push

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

## 验收标准

- M0-R3E 状态已同步为 COMPLETED
- M0 整体状态已同步为 COMPLETED
- M1 启动门禁已建立
- 下一步路线记录为先 M0-REMOTE，再 M1-R0，再 M1-R1
- M1 / M2 未提前启动，未创建海滨自定义 App、未开发业务、未接飞书真实写入、未做前端驾驶舱，未修改 Compose 配置，未创建 remote，未 push

## 下一轮预告

下一步建议先执行 M0-REMOTE：创建 GitHub Private remote、添加 `origin`、首次 push `main`。M0-REMOTE 完成后，再按 `docs/milestones/M1_START_GATE.md` 进入 M1-R0；M1-R1 才验证 HRMS 原生考勤对象模型。本轮不启动 M1。
