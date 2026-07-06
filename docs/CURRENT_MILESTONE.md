# Current Milestone

## M0：工程启动与上下文治理

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M0-R3C：Frappe HR / HRMS 安装验证。当前状态：COMPLETED。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

在当前 Frappe / ERPNext v16 Docker 最小环境中备份 site，安装 Frappe HR / HRMS，验证 HRMS App、Desk 登录页和基础 HR 模块可访问，并记录安装日志、版本、风险与回滚方式。

交付内容：

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

## 验收标准

- 安装前 site 已备份，安装前版本和 App 清单已记录
- HRMS 官方来源、分支、版本已记录
- `bench get-app`、`install-app`、`migrate`、服务刷新结果已记录
- 安装后 `bench version` 和 `list-apps` 均显示 HRMS
- Desk 登录页和基础 HR 模块访问已验证
- `docs/PROJECT_STATUS.md` 和 `docs/milestones/M0.md` 同步 M0-R3C 状态
- 未创建海滨自定义 App、未开发业务、未接飞书真实写入、未做前端驾驶舱

## 下一轮预告

下一步交给 Codex 做 M0-R3C 审查。审查通过后再规划 M0-R3D：HRMS 能力盘点与 M1 考勤一期边界设计，本轮不启动下一轮。
