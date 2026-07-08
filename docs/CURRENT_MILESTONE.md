# Current Milestone

## M1：平台入口、身份与考勤一期准备

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M1-REQ-DESIGN-DRAFT：M1 考勤一期需求设计草案。当前状态：REVIEWING。

M0 整体已完成并封板。M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1 当前状态：IN_PROGRESS。M1-R0 已通过 Codex 独立审查并收口为 COMPLETED。M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已完成需求确认、PRD、技术设计和 Demo 路线图四份文档交付，当前为 REVIEWING。M1-R4 为 PLANNED，尚未启动。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M1-REQ-DESIGN-DRAFT 文档交付：基于 Owner 与 ChatGPT 5 轮需求访谈结论，补齐 M1 考勤一期真实需求确认、PRD、技术设计和 Demo 实施路线图。不得启动 M1-R4，不得创建 App / DocType / 代码。

交付内容：

- `docs/milestones/M1_考勤一期真实需求确认.md`
- `docs/milestones/M1_考勤一期产品需求说明书.md`
- `docs/milestones/M1_考勤一期技术设计方案.md`
- `docs/milestones/M1_Demo实施路线图.md`
- 项目状态、当前里程碑和里程碑索引文件更新
- 公共入口文件过期状态清理

本轮实际结果：

- M1-REQ-DESIGN-DRAFT 已完成四份文档交付。
- 真实需求确认覆盖 M1 定位、一周优先级、用户角色、考勤规则、数据来源与导入、页面策略、飞书登录边界、技术路线边界和 12 项验收标准。
- PRD 已定义 5 个使用场景、6 个页面入口、三级异常处理流程、数据权限矩阵和月度汇总导出方案。
- 技术设计方案基于 Frappe/ERPNext/HRMS v16 原生对象，含 Excel 导入设计（两类导入严格区分）、通用适配层接口契约、异常流程 DocType 评估、飞书登录匹配设计、权限映射和导入批次结构。
- Demo 路线图拆分 M1-R4（路线拆分）→ R5（配置+工作台）→ R6（导入+异常）→ R7（飞书+领导Demo）四轮递进。
- 本轮不创建 `hb_hr_app`，不创建 DocType，不修改核心源码。
- M1-REQ-DESIGN-DRAFT 当前为 REVIEWING，M1-R4 保持 PLANNED，尚未启动。

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
- M1-REQ-DESIGN-DRAFT 为 REVIEWING。
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
- M1-R3E 已通过 Codex 审查并收口为 COMPLETED
- M1-R3F 已通过 Codex 审查并收口为 COMPLETED
- M1-R4 保持 PLANNED
- 本轮未继续试运行，未创建、删除或清理 TEST 数据，未创建海滨自定义 App、未开发考勤业务、未接真实考勤机、未接飞书真实写入、未实现 SSO、未修改核心源码、未修改中文化源码、未录入真实业务数据

## 下一轮预告

下一步由用户决定是否进入 M1-R4：二次最小验证或报表设计。M1-R4 仍为 PLANNED，尚未启动；M1-R4 之前必须完成 7 项阻塞性确认主题的业务口径确认或 Owner 临时拍板。
