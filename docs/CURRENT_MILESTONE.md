# Current Milestone

## M0：工程启动与上下文治理

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M0-R3B：Frappe HR / HRMS 安装前评估与安装方案。当前状态：REVIEWING。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

评估 Frappe HR / HRMS 在当前 Frappe / ERPNext v16 Docker 最小环境中的安装可行性，比较安装方案，明确 M0-R3C 安装验证边界、风险和回滚方式。

交付内容：

- `docs/deployment/M0-R3B_Frappe_HR安装前评估.md`
- 项目状态、当前里程碑和 M0 里程碑文件更新

## 本轮禁止事项

- 不创建 Frappe bench
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不安装 Frappe HR / HRMS
- 不安装自定义 Frappe App
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
- M0-R3B 已完成评估：HRMS `version-16` 与当前 v16 环境主版本范围一致，推荐 M0-R3C 在备份和可回滚前提下执行安装验证。

## 验收标准

- HRMS 官方仓库、文档、v16 branch / tag 和依赖范围已记录
- 当前环境事实、site 名称、访问地址、Frappe / ERPNext 版本、HRMS 未安装状态已记录
- 至少比较两种安装方案，并说明优点、风险、适配性、污染风险和回滚方式
- M0-R3C 边界、风险和回滚建议已明确
- `docs/PROJECT_STATUS.md` 和 `docs/milestones/M0.md` 同步 M0-R3B 状态
- 未安装 HRMS、未创建自定义 App、未开发业务、未接飞书真实写入、未做前端驾驶舱

## 下一轮预告

下一步交给 Codex 做 M0-R3B 审查。审查通过后再决定是否进入 M0-R3C：Frappe HR / HRMS 安装验证，本轮不启动下一轮。
