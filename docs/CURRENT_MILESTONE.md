# Current Milestone

## M0：工程启动与上下文治理

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M0-R3C-FIX：HRMS 前端资源与 Roster 白屏诊断修复。当前状态：COMPLETED。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

在当前 Frappe / ERPNext v16 Docker 最小环境中诊断并修复 HRMS 前端资源 404、Frappe HR 图标缺失、HRMS 模块图标缺失和 `/hr/roster` 白屏问题，并记录复现证据、修复命令、验证结果、风险与回滚方式。

交付内容：

- `docs/deployment/M0-R3C_FIX_HRMS前端资源与Roster白屏修复记录.md`
- `docs/deployment/M0-R3C_Frappe_HR安装验证记录.md`
- 项目状态、当前里程碑和 M0 里程碑文件更新

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

## 验收标准

- HRMS 前端资源 404 复现证据已记录
- HRMS 资源根因、修复命令和验证结果已记录
- Frappe HR 图标、基础 HR 模块和 Roster 页面已通过浏览器验证
- `docs/PROJECT_STATUS.md` 和 `docs/milestones/M0.md` 同步 M0-R3C-FIX 状态
- 未创建海滨自定义 App、未开发业务、未接飞书真实写入、未做前端驾驶舱

## 下一轮预告

下一步交给 Codex 做 M0-R3C-FIX 审查。审查通过后再由用户决定是否恢复 M0-R3D：HRMS 能力盘点与 M1 考勤一期边界设计，本轮不启动下一轮。
